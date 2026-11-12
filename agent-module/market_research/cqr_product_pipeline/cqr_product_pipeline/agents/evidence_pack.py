"""Evidence-pack research: structured brief -> web evidence -> validated excerpts.

No LLM and no templates. Every line of the output is one of: the brief as the
user gave it, a counted statistic, or a verbatim excerpt with its URL. Market
gaps, personas, sizing and pricing conclusions are deliberately not produced
here; a section without evidence is reported as missing instead of being filled.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

PACK_SCHEMA = "cqr.market_research.evidence_pack/1"
MIN_EVIDENCE = 3
MAX_QUERIES = 10
RESULTS_PER_QUERY = 6
MAX_FETCH = 16
MAX_EVIDENCE = 18
MAX_PER_DOMAIN = 3
MIN_BODY_CHARS = 400
SEARCH_SPACING = 0.8  # seconds between live queries; back-to-back calls get throttled
SEARCH_RETRY_DELAY = 2.0
# Search-engine redirect / ad links are not sources.
_NON_SOURCE_HOSTS = ("bing.com", "duckduckgo.com", "google.com")
_SENTENCE_END_RE = re.compile(r"[.!?…](?:\s|$)")

Searcher = Callable[[str, int], list[dict]]
Fetcher = Callable[[str], str]

# field -> accepted keys in an inline ``키: 값`` brief (longest key wins).
FIELD_KEYS: dict[str, tuple[str, ...]] = {
    "product": ("품목", "제품", "product", "item"),
    "product_en": ("영문명", "영문", "검색어", "product_en", "english"),
    "category": ("카테고리", "category"),
    "season": ("시즌", "season"),
    "channel": ("채널", "channel"),
    "price_band": ("가격대", "가격", "price_band", "price"),
    "competitors": ("경쟁사", "competitors", "competitor"),
    "focus": ("초점", "포커스", "focus"),
}
FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("product", "품목"),
    ("product_en", "검색용 영문명"),
    ("category", "카테고리"),
    ("season", "시즌"),
    ("channel", "채널"),
    ("price_band", "가격대"),
    ("competitors", "경쟁사"),
    ("focus", "초점"),
)
KIND_LABELS: tuple[tuple[str, str], ...] = (
    ("review", "리뷰·불만 근거"),
    ("competitor", "경쟁사·가격 근거"),
    ("market", "시장·트렌드 근거"),
)
FROM_FIELD = "입력 필드"
FROM_TEXT = "문장 해석(규칙)"
FIELD_EXAMPLE = "/심층리서치 품목: 스키바지 / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280"

_KEY_TO_FIELD = {key.lower(): name for name, keys in FIELD_KEYS.items() for key in keys}
_FIELD_RE = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(k) for k in sorted(_KEY_TO_FIELD, key=len, reverse=True))
    + r")\s*[:=]\s*",
    re.IGNORECASE,
)
_PRICE_BAND_RE = re.compile(r"\$\s?\d{1,4}(?:\s?[-–~]\s?\$?\d{1,4})?")
_PRICE_RE = re.compile(r"\$\s?\d{2,4}(?:\.\d{2})?")
_SEASON_CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?:(20\d\d)\s*)?(FW|F/W|SS|S/S)(?![A-Za-z])", re.IGNORECASE)
# 「봄버재킷」「살펴봄」 must not read as spring: the word has to stand alone.
_SEASON_KO_RE = re.compile(r"(?<![가-힣])(봄|여름|가을|겨울)(?:용|철|에|시즌)?(?![가-힣])")
_SEASON_EN_RE = re.compile(r"\b(winter|summer)\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(20[2-4]\d)(?!\d)")
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


@dataclass
class ResearchBrief:
    raw: str = ""
    product: str = ""
    product_en: str = ""
    category: str = ""
    season: str = ""
    channel: str = ""
    price_band: str = ""
    competitors: list[str] = field(default_factory=list)
    focus: str = ""
    origin: dict[str, str] = field(default_factory=dict)

    @property
    def scope(self) -> str:
        return self.product or self.category

    @property
    def search_term(self) -> str:
        return self.product_en or self.product or self.category


@dataclass
class Evidence:
    id: str
    kind: str
    title: str
    url: str
    domain: str
    source: str  # "본문" (page body read) | "요약문" (search snippet only)
    excerpt: str
    prices: list[str]
    query: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _season_from_text(text: str) -> str:
    code = _SEASON_CODE_RE.search(text)
    if code:
        return " ".join(x for x in (code.group(1), code.group(2).upper().replace("/", "")) if x)
    word = _SEASON_KO_RE.search(text) or _SEASON_EN_RE.search(text)
    year = _YEAR_RE.search(text)
    return " ".join(x for x in (year.group(1) if year else "", word.group(1) if word else "") if x)


def _rule_product(text: str) -> tuple[str, str]:
    """Product phrase read from free text by the legacy rule parser (fallback only)."""
    try:
        from cqr_product_pipeline.agents.deep_research import (
            _parse_brief_hints,
            brief_needs_clarification,
        )
    except Exception:  # noqa: BLE001 - legacy parser needs the LLM stack
        return "", ""
    hints = _parse_brief_hints(text, None)
    if brief_needs_clarification(hints):
        return "", ""
    product = _clean(hints.get("product_brief"))  # phrase as written in the brief
    english = _clean(hints.get("garment"))  # English search label
    if not english.isascii():
        english = product if product.isascii() else ""
    return product, english


def parse_brief(raw: str, overrides: dict[str, str] | None = None) -> ResearchBrief:
    """Explicit fields are used verbatim; only what is missing is read from the sentence."""
    raw = (raw or "").strip()
    values: dict[str, str] = {}
    origin: dict[str, str] = {}
    matches = list(_FIELD_RE.finditer(raw))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        value = raw[match.end() : end].strip(" \t\r\n,;/|·—-")
        name = _KEY_TO_FIELD[match.group(1).lower()]
        if value and name not in values:
            values[name], origin[name] = value, FROM_FIELD
    for name, value in (overrides or {}).items():
        if name in FIELD_KEYS and value and value.strip():
            values[name], origin[name] = value.strip(), FROM_FIELD
    free = raw[: matches[0].start()].strip() if matches else raw

    if "season" not in values and (season := _season_from_text(free)):
        values["season"], origin["season"] = season, FROM_TEXT
    if "price_band" not in values and (price := _PRICE_BAND_RE.search(free)):
        values["price_band"], origin["price_band"] = _clean(price.group(0)), FROM_TEXT
    if not values.get("product") and values.get("product_en") and not values.get("category"):
        values["product"], origin["product"] = values["product_en"], origin["product_en"]
    if not values.get("product") and not values.get("category") and free:
        product, english = _rule_product(free)
        if product:
            values["product"], origin["product"] = product, FROM_TEXT
            if english and "product_en" not in values:
                values["product_en"], origin["product_en"] = english, FROM_TEXT
    if values.get("product") and "product_en" not in values:
        if values["product"].isascii():
            values["product_en"], origin["product_en"] = values["product"], origin["product"]
        else:
            _same, english = _rule_product(values["product"])
            if english:
                values["product_en"], origin["product_en"] = english, "규칙 사전"

    competitors = [
        c
        for c in (_clean(x) for x in re.split(r",|·|/|;|\band\b|및", values.get("competitors", "")))
        if c
    ]
    return ResearchBrief(
        raw=raw,
        product=values.get("product", ""),
        product_en=values.get("product_en", ""),
        category=values.get("category", ""),
        season=values.get("season", ""),
        channel=values.get("channel", ""),
        price_band=values.get("price_band", ""),
        competitors=competitors,
        focus=values.get("focus", ""),
        origin=origin,
    )


def brief_gate(brief: ResearchBrief) -> str | None:
    """Reason code when there is nothing to research, else None."""
    return None if brief.scope else "no_scope"


def build_queries(brief: ResearchBrief) -> list[tuple[str, str]]:
    """Search plan built only from brief values (no seeded brands or price bands)."""
    term = brief.search_term
    korean = not term.isascii()
    queries: list[tuple[str, str]] = []

    def add(text: str, kind: str) -> None:
        text = _clean(text)
        if text and text not in {q for q, _ in queries}:
            queries.append((text, kind))

    if brief.product:
        if korean:
            add(f"{term} 후기 단점", "review")
            add(f"{term} 리뷰 불만 {brief.focus}", "review")
        else:
            add(f"{term} review complaints problems", "review")
            add(f"{term} reddit issues worth it", "review")
            if brief.focus:
                add(f"{term} {brief.focus} complaints", "review")
            add(f"{term} {brief.channel or 'amazon'} customer reviews 1 star", "review")
            if brief.product != term:
                add(f"{brief.product} 후기 단점", "review")
        for name in brief.competitors[:4]:
            add(f"{name} {term} 후기 가격" if korean else f"{name} {term} review price", "competitor")
        if not brief.competitors:
            add(f"{term} 추천 비교 가격" if korean else f"best {term} comparison price", "competitor")
        if brief.price_band:
            add(
                f"{term} {brief.price_band} 가성비 비교" if korean else f"{term} {brief.price_band} best value",
                "competitor",
            )
    else:
        for name in brief.competitors[:5]:
            add(
                f"{name} {term} 후기 단점" if korean else f"{name} {term} review complaints quality",
                "review",
            )
        add(f"{term} 브랜드 후기 불만" if korean else f"{term} brands customer complaints reddit", "review")
        add(
            f"{term} 브랜드 가격대 비교 {brief.price_band}"
            if korean
            else f"{term} brands price comparison {brief.price_band}",
            "competitor",
        )
    # A Korean season word does not help an English query (and the reverse is fine).
    season = brief.season if korean or brief.season.isascii() else ""
    add(f"{term} 시장 트렌드 {season}" if korean else f"{term} market trends {season}", "market")
    return queries[:MAX_QUERIES]


def scope_terms(brief: ResearchBrief) -> list[str]:
    if brief.product:
        return [t for t in (brief.product, brief.product_en) if t]
    return [t for t in (brief.category, brief.product_en, *brief.competitors) if t]


def _tokens(term: str) -> list[str]:
    out = []
    for tok in re.findall(r"[a-z0-9]+|[가-힣]+", term.lower()):
        if tok.isascii() and len(tok) > 3 and tok.endswith("s"):
            tok = tok[:-1]  # pants ~ pant
        out.append(tok)
    return out


def _term_hit(term: str, low_text: str) -> bool:
    tokens = _tokens(term)
    if not tokens:
        return False
    for tok in tokens:
        if tok.isascii():
            if not re.search(r"(?<![a-z0-9])" + re.escape(tok), low_text):
                return False
        elif tok not in low_text:
            return False
    return True


def on_topic(terms: list[str], text: str) -> bool:
    low = text.lower()
    return any(_term_hit(term, low) for term in terms)


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "form", "iframe"}
    _BREAK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_data(self, data):  # noqa: ANN001
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed markup: keep what was parsed
        pass
    # One block per line, so excerpts can tell prose from menus and link lists.
    lines = (_clean(line) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


def fetch_text(url: str, timeout: float = 8.0) -> str:
    """Page body as plain text. Raises on network errors; '' for non-HTML."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.8,ko;q=0.6",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - http(s) only
        if "html" not in (response.headers.get("Content-Type") or "").lower():
            return ""
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read(800_000)
    try:
        return html_to_text(raw.decode(charset, errors="replace"))
    except LookupError:
        return html_to_text(raw.decode("utf-8", errors="replace"))


_last_search = 0.0


def ddg_search(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    global _last_search
    wait = _last_search + SEARCH_SPACING - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    region = "kr-kr" if re.search(r"[가-힣]", query) else "us-en"
    try:
        rows = DDGS().text(query, max_results=max_results, region=region)
    finally:
        _last_search = time.monotonic()
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in rows or []
    ]


def _search(searcher: Searcher, query: str) -> list[dict]:
    try:
        return searcher(query, RESULTS_PER_QUERY)
    except Exception:  # noqa: BLE001 - throttled or flaky backend: one more try
        time.sleep(SEARCH_RETRY_DELAY)
        return searcher(query, RESULTS_PER_QUERY)


def _unmerge(found: list[dict]) -> list[dict]:
    """Normalize rows and cut back a row that a backend glued together from its neighbours.

    Some backends return the first hit with the titles and snippets of the next
    hits appended. Left alone, a sentence from one page is quoted under another URL.
    """
    rows = [
        {"title": _clean(r.get("title")), "snippet": _clean(r.get("snippet")), "url": _clean(r.get("url"))}
        for r in found or []
    ]
    for row in rows:
        for other in rows:
            if other is row:
                continue
            for key, size in (("title", 12), ("snippet", 40)):
                probe = other[key][:80]
                cut = row[key].find(probe) if len(probe) >= size else -1
                if cut > 0:
                    row[key] = row[key][:cut].strip()
    return rows


def _excerpt(text: str, terms: list[str], width: int = 340, windows: int = 2) -> str:
    """Up to ``windows`` on-topic passages, in page order. Blocks without a sentence are skipped."""
    scored: list[tuple[int, int, int, str]] = []
    for index, block in enumerate(text.split("\n")):
        if len(block) < 60:
            continue
        low = block.lower()
        hits = sum(1 for term in terms if _term_hit(term, low))
        sentences = len(_SENTENCE_END_RE.findall(block))
        if hits and sentences:
            scored.append((hits, min(sentences, 6), -index, block))
    chunks: list[str] = []
    for _hits, _sentences, _order, block in sorted(sorted(scored, reverse=True)[:windows], key=lambda s: -s[2]):
        if len(block) > width:
            low = block.lower()
            found = [p for p in (low.find(tok) for term in terms for tok in _tokens(term)[:1]) if p >= 0]
            begin = max(0, min(found) - 110) if found else 0
            if begin:  # start on a word boundary, not mid-word
                begin = block.find(" ", begin) + 1
            block = block[begin : begin + width]
        chunks.append(block.strip())
    return " … ".join(chunks)


def collect_evidence(
    brief: ResearchBrief,
    searcher: Searcher | None = None,
    fetcher: Fetcher | None = None,
) -> tuple[list[Evidence], dict]:
    searcher = searcher or ddg_search
    fetcher = fetcher or fetch_text
    queries = build_queries(brief)
    rows: list[dict] = []
    seen: set[str] = set()
    search_errors: list[str] = []
    for query, kind in queries:
        try:
            found = _search(searcher, query)
        except Exception as exc:  # noqa: BLE001 - one failed query must not end the run
            search_errors.append(f"{query} ({type(exc).__name__}: {_clean(str(exc))[:60]})")
            continue
        for rank, row in enumerate(_unmerge(found)):
            parts = urlsplit(row["url"])
            domain = parts.netloc.lower().removeprefix("www.")
            key = (parts.netloc.lower() + parts.path).rstrip("/")
            if (
                parts.scheme not in {"http", "https"}
                or key in seen
                or any(domain == host or domain.endswith("." + host) for host in _NON_SOURCE_HOSTS)
            ):
                continue
            seen.add(key)
            rows.append({**row, "domain": domain, "kind": kind, "query": query, "rank": rank})
    # Round-robin across queries so every evidence kind gets page bodies.
    rows.sort(key=lambda r: r["rank"])

    def _body(row: dict) -> str:
        try:
            return fetcher(row["url"])
        except Exception:  # noqa: BLE001 - blocked/slow page: fall back to the snippet
            return ""

    with ThreadPoolExecutor(max_workers=8) as pool:
        bodies = list(pool.map(_body, rows[:MAX_FETCH]))
    bodies += [""] * (len(rows) - len(bodies))

    terms = scope_terms(brief)
    excerpt_terms = [t for t in re.split(r"[,/·]", brief.focus) if t.strip()] + terms
    evidence: list[Evidence] = []
    per_domain: dict[str, int] = {}
    off_topic = 0
    for row, body in zip(rows, bodies):
        head_ok = on_topic(terms, f"{row['title']} {row['snippet']}")
        body_ok = len(body) >= MIN_BODY_CHARS and on_topic(terms, body)
        from_body = _excerpt(body, excerpt_terms) if body_ok else ""
        if not from_body and not head_ok:
            off_topic += 1
            continue
        if per_domain.get(row["domain"], 0) >= MAX_PER_DOMAIN or len(evidence) >= MAX_EVIDENCE:
            continue
        excerpt = from_body or row["snippet"]
        if not excerpt:
            continue
        per_domain[row["domain"]] = per_domain.get(row["domain"], 0) + 1
        evidence.append(
            Evidence(
                id=f"E{len(evidence) + 1}",
                kind=row["kind"],
                title=row["title"][:140],
                url=row["url"],
                domain=row["domain"],
                source="본문" if from_body else "요약문",
                excerpt=excerpt[:720],
                prices=list(dict.fromkeys(_clean(p) for p in _PRICE_RE.findall(excerpt)))[:5],
                query=row["query"],
            )
        )
    stats = {
        "queries": len(queries),
        "search_errors": search_errors,
        "results": len(rows),
        "fetch_attempted": min(len(rows), MAX_FETCH),
        "fetch_ok": sum(1 for b in bodies if len(b) >= MIN_BODY_CHARS),
        "off_topic_dropped": off_topic,
        "evidence": len(evidence),
        "evidence_body": sum(1 for e in evidence if e.source == "본문"),
    }
    return evidence, stats


def _cell(text: str) -> str:
    return _clean(text).replace("|", "\\|")


def _brief_table(brief: ResearchBrief) -> list[str]:
    lines = ["| 항목 | 값 | 출처 |", "|---|---|---|"]
    for name, label in FIELD_LABELS:
        value = getattr(brief, name)
        value = ", ".join(value) if isinstance(value, list) else value
        lines.append(f"| {label} | {_cell(value) or '미지정'} | {brief.origin.get(name, '-') if value else '-'} |")
    lines += ["", f"해석이 틀렸거나 항목을 더 지정하려면 필드로 다시 요청하세요: `{FIELD_EXAMPLE}`"]
    return lines


def render_markdown(
    brief: ResearchBrief,
    evidence: list[Evidence],
    stats: dict,
    queries: list[tuple[str, str]],
    session_id: str,
    dry_run: bool = False,
) -> str:
    out = [f"# 시장조사 근거 팩 — {brief.scope}", "", f"- 세션: `{session_id}`"]
    if brief.raw:
        out.append(f"- 요청 원문: {_clean(brief.raw)}")
    out += ["", "## 브리프 해석", "", *_brief_table(brief), ""]
    if dry_run:
        out += [
            "> DRY RUN — 검색을 실행하지 않았습니다. 아래는 실행 예정 검색어이며 조사 결과가 아닙니다.",
            "",
            "## 실행 예정 검색어",
            "",
            *[f"- `{q}`" for q, _ in queries],
            "",
        ]
        return "\n".join(out)

    out += [
        "> 웹에서 수집해 브리프 주제와 맞는지 확인한 근거 모음입니다. 발췌는 원문 그대로입니다. "
        "시장 공백·페르소나·시장 규모·가격 전략 같은 종합 결론은 이 문서에 없습니다.",
        "",
        "## 수집 요약",
        "",
        f"- 검색 {stats['queries']}회, 결과 {stats['results']}건, 주제와 무관해 제외 {stats['off_topic_dropped']}건",
        f"- 본문 수집 {stats['fetch_ok']}/{stats['fetch_attempted']}건",
        f"- 채택 근거 {stats['evidence']}건 (본문 {stats['evidence_body']}건, "
        f"검색 요약문만 {stats['evidence'] - stats['evidence_body']}건)",
    ]
    if stats["search_errors"]:
        out.append(f"- 실패한 검색 {len(stats['search_errors'])}회: " + "; ".join(stats["search_errors"]))
    out.append("")

    missing: list[str] = []
    for kind, label in KIND_LABELS:
        items = [e for e in evidence if e.kind == kind]
        if not items:
            missing.append(f"{label}: 0건")
            continue
        out += [f"## {label} ({len(items)}건)", ""]
        for item in items:
            out += [f"### {item.id}. {item.title}", "", f"- 출처: {item.domain} · {item.source} · 검색어 `{item.query}`"]
            if item.prices:
                out.append(f"- 발췌 안 가격 표기: {', '.join(item.prices)}")
            out += [f"- {item.url}", "", f"> {item.excerpt}", ""]
    for name in brief.competitors:
        low = name.lower()
        if not any(low in f"{e.title} {e.excerpt}".lower() for e in evidence):
            missing.append(f"경쟁사 `{name}`: 이 브랜드를 언급한 근거 0건")
    missing.append("시장 규모·페르소나·세그먼트·가격 전략·컨셉 후보: 이 파이프라인은 산출하지 않습니다(종합 단계 없음)")
    out += ["## 근거가 없는 항목", "", *[f"- {m}" for m in missing], ""]
    out += ["## 실행한 검색어", "", *[f"- `{q}`" for q, _ in queries], ""]
    return "\n".join(out)


def run_evidence_pack(
    brief: ResearchBrief,
    output_dir: Path,
    session_id: str,
    dry_run: bool = False,
    searcher: Searcher | None = None,
    fetcher: Fetcher | None = None,
) -> dict:
    """Write the pack. ``status`` is ``ok`` or ``insufficient_evidence`` (no report written)."""
    queries = build_queries(brief)
    evidence: list[Evidence] = []
    stats: dict = {"queries": len(queries)}
    if not dry_run:
        evidence, stats = collect_evidence(brief, searcher, fetcher)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evidence_pack.json").write_text(
        json.dumps(
            {
                "schema": PACK_SCHEMA,
                "session_id": session_id,
                "dry_run": dry_run,
                "brief": asdict(brief),
                "queries": [{"query": q, "kind": k} for q, k in queries],
                "stats": stats,
                "evidence": [asdict(e) for e in evidence],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    result = {"status": "ok", "evidence_count": len(evidence), "stats": stats, "dry_run": dry_run}
    if not dry_run and len(evidence) < MIN_EVIDENCE:
        result["status"] = "insufficient_evidence"
        return result
    markdown = render_markdown(brief, evidence, stats, queries, session_id, dry_run)
    (output_dir / "research_report.md").write_text(markdown, encoding="utf-8")
    result["markdown"] = markdown
    return result
