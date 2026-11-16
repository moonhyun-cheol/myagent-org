"""Evidence-pack research: structured brief -> web evidence -> validated excerpts.

No LLM and no templates. Every line of the output is one of: the brief as the
user gave it, a counted statistic, or a verbatim excerpt with its URL. Market
gaps, personas, sizing and pricing conclusions are deliberately not produced
here; a section without evidence is reported as missing instead of being filled.

The target market is the United States (CQR is a US brand). Queries are English;
results on another country's domain or country edition, in a non-Latin script,
priced only in another currency, or on a page that declares another country's
locale are dropped and counted. A brief whose product or category has no
English name is not searched at all.

Search goes to search.yahoo.com first (see ``yahoo_search``): in the runtime the
host uses, Yahoo is the only ddgs text engine that answers, it ignores the
region parameter, and ddgs reads only one of the two page layouts Yahoo serves,
so most ddgs calls came back empty. ddgs stays as the fallback.

Each evidence item carries a short ``excerpt`` (shown in the pack) and a longer
``detail`` (more on-topic passages, and on competitor pages the lines that state
a price) for the host's synthesis step, which must cite evidence ids and may only
quote amounts that appear in the cited items.

A market/trend study (``study: trend``, or any brief with a ``period``) searches each
year of the period, gives most slots to market evidence, and records the date a page
was published so the synthesis can tell what was said about which year.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import unquote_plus, urlsplit

PACK_SCHEMA = "cqr.market_research.evidence_pack/1"
MIN_EVIDENCE = 3
MAX_QUERIES = 10
# Market queries are planned last but never cut: they get these slots out of MAX_QUERIES.
MARKET_QUERIES = 2
RESULTS_PER_QUERY = 6
MAX_FETCH = 16
MAX_EVIDENCE = 18
# Evidence and fetch slots per kind, taken in rank order. A kind that cannot fill its
# share hands the rest to the others, so the totals stay MAX_EVIDENCE / MAX_FETCH.
# Without shares the review queries (3-4 of 8) used the slots up before the single
# market query's second and third hits were reached.
KIND_QUOTA = {"review": 8, "competitor": 6, "market": 4}
FETCH_QUOTA = {"review": 7, "competitor": 5, "market": 4}
# A market/trend study asks how the market moved, so market evidence takes most slots.
STUDY_TREND = "trend"
STUDY_PRODUCT = "product"
TREND_KIND_QUOTA = {"review": 3, "competitor": 5, "market": 10}
TREND_FETCH_QUOTA = {"review": 2, "competitor": 4, "market": 10}
TREND_DEFAULT_YEARS = 3  # a trend study without a period looks at the last 3 years
MAX_PERIOD_YEARS = 4  # one query per year; older years of a longer period are left out
MAX_PER_DOMAIN = 3
MIN_BODY_CHARS = 400
EXCERPT_CHARS = 720
DETAIL_CHARS = 2400
PRICE_LINES = 6
SEARCH_SPACING = 0.8  # seconds between live queries; back-to-back calls get throttled
SEARCH_RETRY_DELAY = 2.0
SEARCH_TIMEOUT = 10
YAHOO_SEARCH_URL = "https://search.yahoo.com/search"
# Search-engine redirect / ad links are not sources.
_NON_SOURCE_HOSTS = ("bing.com", "duckduckgo.com", "google.com", "search.yahoo.com")
# Hosts whose pages never gave a readable body in measured runs (login wall /
# bot page). Their search snippet is still used; no fetch slot is spent on them.
_NO_FETCH_HOSTS = ("reddit.com", "amazon.com")
_SENTENCE_END_RE = re.compile(r"[.!?…](?:\s|$)")
MARKET = "US"
MARKET_LABEL = "미국"
SEARCH_REGION = "us-en"
# Two-letter TLDs used as generic ones, not as another country's market.
_GENERIC_CC_TLDS = frozenset({"us", "co", "io", "ai", "me", "tv", "cc", "gg", "ly", "to", "fm"})
# ISO 3166-1 alpha-2 codes (+ "uk"). A first host label like ca. / uk. / en-gb. is that
# country's edition of a site (ca.pinterest.com), so it is not a US source.
_COUNTRY_CODES = frozenset(
    (
        "ad ae af ag ai al am ao aq ar as at au aw ax az ba bb bd be bf bg bh bi bj bl bm bn bo bq br bs bt bv bw "
        "by bz ca cc cd cf cg ch ci ck cl cm cn co cr cu cv cw cx cy cz de dj dk dm do dz ec ee eg eh er es et fi "
        "fj fk fm fo fr ga gb gd ge gf gg gh gi gl gm gn gp gq gr gs gt gu gw gy hk hm hn hr ht hu id ie il im in "
        "io iq ir is it je jm jo jp ke kg kh ki km kn kp kr kw ky kz la lb lc li lk lr ls lt lu lv ly ma mc md me "
        "mf mg mh mk ml mm mn mo mp mq mr ms mt mu mv mw mx my mz na nc ne nf ng ni nl no np nr nu nz om pa pe pf "
        "pg ph pk pl pm pn pr ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si sj sk sl sm sn so sr ss st sv "
        "sx sy sz tc td tf tg th tj tk tl tm tn to tr tt tv tw tz ua ug um us uy uz va vc ve vg vi vn vu wf ws ye "
        "yt za zm zw uk"
    ).split()
)
# First labels that are the US or a US territory, or that sites use for a function rather
# than a country: ir. investor relations, my. account, hr. careers, id. login.
_NOT_A_COUNTRY_EDITION = frozenset({"us", "pr", "gu", "vi", "as", "mp", "um", "ir", "my", "hr", "id"}) | _GENERIC_CC_TLDS
_EDITION_LABEL_RE = re.compile(r"^(?:[a-z]{2}-)?([a-z]{2})$")  # ca / en-gb / fr-ca
_US_REGIONS = frozenset({"us", "pr", "gu", "vi", "as", "mp", "um"})
# Retailer pages about one item: a product page or its reviews. Anything else on the
# retailer's main host (search /s?k=…, category /b?node=… /browse/ /c/, stores, best-seller
# lists) is a product list whose snippet is shop navigation, not a review or a price for
# one product. Matched on the exact host, so corporate.target.com and the like are kept.
_RETAIL_ITEM_PATHS = {
    "amazon.com": re.compile(r"/(?:dp|gp/product|gp/aw/d|product-reviews|gp/customer-reviews)/"),
    "walmart.com": re.compile(r"/(?:ip|reviews/product)/"),
    "target.com": re.compile(r"/p/"),
}
# Money written in another currency. A result priced only this way is not a US listing.
_FOREIGN_CURRENCY_RE = re.compile(
    r"[£€₹]\s?\d|\d\s?€|(?<![A-Za-z])(?:CA|AU|NZ|HK|SG|C|A|S)\$\s?\d"
    r"|\b(?:GBP|EUR|CAD|AUD|NZD|INR)\s?\d|\d\s?(?:GBP|EUR|CAD|AUD|NZD|INR)\b"
)
_USD_RE = re.compile(r"(?:(?<=US)|(?<![A-Za-z]))\$\s?\d|\bUSD\b")
_HTML_LANG_RE = re.compile(r"<html\b[^>]*?\blang\s*=\s*[\"']?([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*)", re.IGNORECASE)
_OG_LOCALE_RE = re.compile(r"<meta\b[^>]*?(?:property|name)\s*=\s*[\"']og:locale[\"'][^>]*>", re.IGNORECASE)
_CONTENT_RE = re.compile(r"\bcontent\s*=\s*[\"']([^\"']+)", re.IGNORECASE)
# Structured product price: schema.org Offer in JSON-LD, or a product:price meta tag.
# Product pages often render the visible price with script, so it is not in the text.
_LD_JSON_RE = re.compile(
    r"<script\b[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL
)
_META_PRICE_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:product:price:amount|og:price:amount)[\"'][^>]*>",
    re.IGNORECASE,
)
_META_CURRENCY_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:product:price:currency|og:price:currency)[\"'][^>]*>",
    re.IGNORECASE,
)
# Status codes a browser-like client sometimes gets past (bot walls, rate limits).
_RETRY_IMPERSONATED = frozenset({401, 403, 429, 503})
OFF_MARKET_LABELS = {
    "domain": "국가 도메인",
    "edition": "국가판 서브도메인",
    "script": "비라틴 문자",
    "currency": "외화로만 적힌 가격",
    "locale": "페이지가 선언한 언어·지역",
}
_KOREAN_RE = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]")
# Season wording for an English query.
_SEASON_EN = {
    "봄": "spring",
    "여름": "summer",
    "가을": "fall",
    "겨울": "winter",
    "봄여름": "spring summer",
    "가을겨울": "fall winter",
    "SS": "spring summer",
    "FW": "fall winter",
}

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
    "study": ("조사유형", "조사 유형", "study"),
    "period": ("기간", "period"),
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
    ("study", "조사 유형"),
    ("period", "기간"),
)
STUDY_LABELS = {STUDY_TREND: "시장·트렌드 추이", STUDY_PRODUCT: "제품 조사(불만·경쟁·시장)"}
# Accepted ``조사유형:`` values (lower case).
_STUDY_VALUES = {
    "trend": STUDY_TREND,
    "trends": STUDY_TREND,
    "market": STUDY_TREND,
    "market trend": STUDY_TREND,
    "트렌드": STUDY_TREND,
    "추이": STUDY_TREND,
    "시장": STUDY_TREND,
    "시장·트렌드": STUDY_TREND,
    "product": STUDY_PRODUCT,
    "제품": STUDY_PRODUCT,
}
KIND_LABELS: tuple[tuple[str, str], ...] = (
    ("review", "리뷰·불만 근거"),
    ("competitor", "경쟁사·가격 근거"),
    ("market", "시장·트렌드 근거"),
)
FROM_FIELD = "입력 필드"
FROM_TEXT = "문장 해석(규칙)"
FIELD_EXAMPLE = (
    "/심층리서치 품목: 스키바지 / 영문명: ski pants / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280"
)

_KEY_TO_FIELD = {key.lower(): name for name, keys in FIELD_KEYS.items() for key in keys}
_FIELD_RE = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(k) for k in sorted(_KEY_TO_FIELD, key=len, reverse=True))
    + r")\s*[:=]\s*",
    re.IGNORECASE,
)
_PRICE_BAND_RE = re.compile(r"\$\s?\d{1,4}(?:\s?[-–~]\s?\$?\d{1,4})?")
# A US-dollar price: $89, $9.99, $1,299. Not CA$/A$ amounts, and not a figure with a
# magnitude ($17.9 billion, $2.5M, $100k), which is a market size rather than a price.
_PRICE_RE = re.compile(
    r"(?:(?<=US)|(?<![A-Za-z]))\$\s?(?:\d{1,3}(?:,\d{3})+|\d{1,5})(?:\.\d{1,2})?"
    r"(?!\d|[.,]\d)(?!\s?(?:[mb]illion|trillion|bn|mn|[mbk])\b)",
    re.IGNORECASE,
)
_SEASON_CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?:(20\d\d)\s*)?(FW|F/W|SS|S/S)(?![A-Za-z])", re.IGNORECASE)
# 「봄버재킷」「살펴봄」 must not read as spring: the word has to stand alone.
_SEASON_KO_RE = re.compile(r"(?<![가-힣])(봄|여름|가을|겨울)(?:용|철|에|시즌)?(?![가-힣])")
_SEASON_EN_RE = re.compile(r"\b(winter|summer)\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(20[2-4]\d)(?!\d)")
# A period: 2024-2026 / 2024년~2026년, or a relative one: 최근 3년 / 지난 2개년 / last 3 years.
_PERIOD_RANGE_RE = re.compile(r"(?<!\d)(20\d\d)\s*년?\s*[-–~]\s*(20\d\d)(?!\d)\s*년?")
_RECENT_YEARS_RE = re.compile(r"(?:최근|지난)\s*(\d{1,2})\s*개?년|\b(?:last|past)\s+(\d{1,2})\s+years\b", re.IGNORECASE)
# Publication date a page declares, and the date Yahoo prints before a snippet ("Mar 5, 2025 · …").
_PUBLISHED_META_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:article:published_time|og:published_time|"
    r"datePublished|publish[-_]?date|pubdate|parsely-pub-date|sailthru\.date|date)[\"'][^>]*>",
    re.IGNORECASE,
)
_LD_PUBLISHED_RE = re.compile(r"\"datePublished\"\s*:\s*\"([^\"]{8,40})\"")
_ISO_DATE_RE = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)")
_MONTHS = {m: n for n, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
_SNIPPET_DATE_RE = re.compile(r"^\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(20\d\d)\b")
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
    study: str = ""  # STUDY_TREND | STUDY_PRODUCT | "" (product study)
    period: str = ""  # "2024-2026" / "2025"
    origin: dict[str, str] = field(default_factory=dict)

    @property
    def scope(self) -> str:
        return self.product or self.category

    @property
    def search_term(self) -> str:
        """English name the US-market queries are built on ('' when the brief has none)."""
        for value in (self.product_en, self.product, self.category):
            if value and not _has_korean(value):
                return value
        return ""


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
    # Longer on-topic passages (+ price lines on competitor pages) for the synthesis step.
    detail: str = ""
    # USD prices from the page's structured product data or its price lines.
    page_prices: list[str] = field(default_factory=list)
    # Publication date the page declares, or the date in front of the search snippet (YYYY-MM-DD).
    published: str = ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text or ""))


def _english(value: str) -> str:
    return "" if _has_korean(value) else value


def _parts(value: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,/·]", value or "") if p.strip()]


def _season_words(season: str) -> list[str]:
    return [_SEASON_EN.get(w.upper() if w.isascii() else w, w) for w in (season or "").split()]


def _season_en(season: str) -> str:
    """Season for an English query: 겨울 -> winter, FW -> fall winter; untranslatable words are left out."""
    return " ".join(w for w in _season_words(season) if not _has_korean(w))


def _unsearchable(brief: ResearchBrief) -> list[str]:
    """Brief values left out of the English queries because they are written in Korean."""
    left_out = [f"경쟁사 `{c}`" for c in brief.competitors if _has_korean(c)]
    left_out += [f"초점 `{p}`" for p in _parts(brief.focus) if _has_korean(p)]
    for label, value in (("채널", brief.channel), ("가격대", brief.price_band)):
        if _has_korean(value):
            left_out.append(f"{label} `{value}`")
    if any(_has_korean(w) for w in _season_words(brief.season)):
        left_out.append(f"시즌 `{brief.season}`")
    return left_out


def _season_from_text(text: str) -> str:
    code = _SEASON_CODE_RE.search(text)
    if code:
        return " ".join(x for x in (code.group(1), code.group(2).upper().replace("/", "")) if x)
    word = _SEASON_KO_RE.search(text) or _SEASON_EN_RE.search(text)
    year = _YEAR_RE.search(text)
    return " ".join(x for x in (year.group(1) if year else "", word.group(1) if word else "") if x)


def _study_value(value: str) -> str:
    return _STUDY_VALUES.get(_clean(value).lower(), "")


def period_years(period: str, current_year: int | None = None) -> list[int]:
    """Years a period covers, oldest first. Future years are left out, and of a long period
    only the last MAX_PERIOD_YEARS are kept (one search per year)."""
    now = current_year or date.today().year
    text = period or ""
    if match := _PERIOD_RANGE_RE.search(text):
        first, last = sorted((int(match.group(1)), int(match.group(2))))
        years = list(range(first, last + 1))
    elif match := _RECENT_YEARS_RE.search(text):
        count = int(match.group(1) or match.group(2))
        years = list(range(now - count + 1, now + 1)) if count > 0 else []
    else:
        years = sorted({int(y) for y in _YEAR_RE.findall(text)})
    return [y for y in years if y <= now][-MAX_PERIOD_YEARS:]


def study_years(brief: ResearchBrief, current_year: int | None = None) -> list[int]:
    """Years a trend study searches: the period's, else the last TREND_DEFAULT_YEARS."""
    years = period_years(brief.period, current_year)
    if years:
        return years
    now = current_year or date.today().year
    return list(range(now - TREND_DEFAULT_YEARS + 1, now + 1))


def _period_text(years: list[int]) -> str:
    return "" if not years else str(years[0]) if len(years) == 1 else f"{years[0]}-{years[-1]}"


def _period_from_text(text: str) -> str:
    """A period written in the sentence (최근 3년, 2024~2026) as "2024-2026"; a lone year is a season, not a period."""
    if _PERIOD_RANGE_RE.search(text) or _RECENT_YEARS_RE.search(text):
        return _period_text(period_years(text))
    return ""


def page_published(html: str) -> str:
    """Publication date a page declares (article:published_time, JSON-LD datePublished, …) as YYYY-MM-DD."""
    head = html[:300_000]
    values = [c.group(1) for tag in _PUBLISHED_META_RE.findall(head) if (c := _CONTENT_RE.search(tag))]
    values += _LD_PUBLISHED_RE.findall(head)
    for value in values:
        if match := _ISO_DATE_RE.search(value):
            return "-".join(match.groups())
    return ""


def snippet_published(snippet: str) -> str:
    """The date a search engine prints in front of a snippet ("Mar 5, 2025 · …") as YYYY-MM-DD."""
    match = _SNIPPET_DATE_RE.match(snippet or "")
    if not match:
        return ""
    return f"{match.group(3)}-{_MONTHS[match.group(1)]:02d}-{int(match.group(2)):02d}"


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

    if "period" not in values and (period := _period_from_text(free)):
        values["period"], origin["period"] = period, FROM_TEXT
    elif values.get("period") and (years := period_years(values["period"])):
        values["period"] = _period_text(years)  # 최근 3년 -> 2024-2026
    # A period (최근 3년, 2024-2026) is not a season year.
    season_text = _RECENT_YEARS_RE.sub(" ", _PERIOD_RANGE_RE.sub(" ", free))
    if "season" not in values and (season := _season_from_text(season_text)):
        values["season"], origin["season"] = season, FROM_TEXT
    if study := _study_value(values.get("study", "")):
        values["study"] = study
    else:
        values.pop("study", None)
        origin.pop("study", None)
        if period_years(values.get("period", "")):
            values["study"], origin["study"] = STUDY_TREND, "기간에서 추론"
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
        study=values.get("study", ""),
        period=values.get("period", ""),
        origin=origin,
    )


def brief_gate(brief: ResearchBrief) -> str | None:
    """Reason code when the brief cannot be researched, else None."""
    if not brief.scope:
        return "no_scope"
    if not brief.search_term:
        return "no_english_name"  # nothing to search the US market with
    return None


def build_queries(brief: ResearchBrief) -> list[tuple[str, str]]:
    """English, US-market search plan built only from brief values (no seeded brands or price bands)."""
    term = brief.search_term
    queries: list[tuple[str, str]] = []
    if not term:
        return queries

    def add(text: str, kind: str) -> None:
        text = _clean(text)
        if text and text not in {q for q, _ in queries}:
            queries.append((text, kind))

    # Korean values would only pull Korean pages into a US study; see _unsearchable().
    focus = " ".join(p for p in _parts(brief.focus) if not _has_korean(p))
    channel = _english(brief.channel) or "amazon"
    price = _english(brief.price_band)
    competitors = [c for c in brief.competitors if not _has_korean(c)]
    if brief.study == STUDY_TREND:
        # How the market moved: one query per year, market size, then a few brand and review queries.
        years = study_years(brief)
        for year in years:
            add(f"{term} trend {year}", "market")
        category = _english(brief.category)
        add(f"{term} market size growth", "market")
        if category and category.lower() != term.lower():
            add(f"{category} US market size growth", "market")
        for name in competitors[:2]:
            add(f"{name} {term} {years[-1]}", "competitor")
        add(f"best {term} brands {years[-1]}", "competitor")
        add(f"{term} review complaints problems", "review")
        return queries[:MAX_QUERIES]
    if brief.product:
        add(f"{term} review complaints problems", "review")
        add(f"{term} reddit issues worth it", "review")
        if focus:
            add(f"{term} {focus} complaints", "review")
        add(f"{term} {channel} customer reviews 1 star", "review")
        for name in competitors[:4]:
            add(f"{name} {term} review price", "competitor")
        if not competitors:
            add(f"best {term} comparison price", "competitor")
        if price:
            add(f"{term} {price} best value", "competitor")
    else:
        for name in competitors[:5]:
            add(f"{name} {term} review complaints quality", "review")
        add(f"{term} brands customer complaints reddit", "review")
        add(f"{term} brands price comparison {price}", "competitor")
    queries = queries[: MAX_QUERIES - MARKET_QUERIES]
    # A narrow product name rarely appears in market reports ("slacks US market trends winter"
    # returned winter-wear reports only), so the second market query asks for size and growth
    # without the season, at the brief's category level when one is given in English.
    category = _english(brief.category) if brief.product else ""
    add(f"{term} US market trends {_season_en(brief.season)}", "market")
    if category and category.lower() != term.lower():
        add(f"{category} US market size growth", "market")
    else:
        add(f"{term} market size growth", "market")
    return queries


def scope_terms(brief: ResearchBrief, kind: str = "") -> list[str]:
    """Terms a kept result must mention. Korean terms are left out: kept pages are English.

    A market result may name the brief's category instead of the product: a market report
    covers the category (men's dress pants), not one product name in it (slacks).
    """
    if brief.product:
        terms = [brief.product, brief.product_en]
        if kind == "market":
            terms.append(brief.category)
    else:
        terms = [brief.category, brief.product_en, *brief.competitors]
    return list(dict.fromkeys(t for t in terms if t and not _has_korean(t)))


def _token_pairs(term: str) -> list[tuple[str, str]]:
    """(word as written, stem) per word: pants -> pant. 'ss' / 'us' / 'is' endings are not plurals."""
    out = []
    for tok in re.findall(r"[a-z0-9]+|[가-힣]+", re.sub(r"['’]s\b", "", term.lower())):  # men's -> men
        stem = tok
        if tok.isascii() and len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
            stem = tok[:-1]  # pants ~ pant
        out.append((tok, stem))
    return out


def _tokens(term: str) -> list[str]:
    return [stem for _word, stem in _token_pairs(term)]


def _token_hit(tok: str, low_text: str) -> bool:
    """A modifier word with a regular ending: ski ~ skiing / skier, men ~ men's, work ~ workers.

    Not a bare prefix: "men" must not match "mention", nor "work" "workflow".
    """
    if tok.isascii():
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?:s|es|['’]s|ing|ers?|ly)?(?![a-z0-9])", low_text))
    return tok in low_text


def _noun_hit(stem: str, low_text: str, plural_only: str = "") -> bool:
    """The head noun as a whole word, singular or plural: pant / pants, not panther or bootcut."""
    if not stem.isascii():
        return stem in low_text
    word = re.escape(plural_only) if plural_only else re.escape(stem) + r"(?:s|es)?"
    return bool(re.search(r"(?<![a-z0-9])" + word + r"(?![a-z0-9])", low_text))


def _term_hit(term: str, low_text: str) -> bool:
    """The term's last word (the noun: pants, boots, apparel) and at least half of the words before it.

    ``tactical cargo pants`` matches a page about cargo pants or tactical pants; ``ski pants``
    and ``work boots`` still need both words. Requiring every word dropped most cargo-pants pages.

    The singular of a plural noun counts only next to another word of the term: "Peak Cargo
    Pant" is a cargo pants page, but "Slack" alone is the chat app, not slacks.
    """
    pairs = _token_pairs(term)
    if not pairs:
        return False
    *modifiers, (head_word, head) = pairs
    if not _noun_hit(head, low_text):
        return False
    hits = sum(1 for _word, stem in modifiers if _token_hit(stem, low_text))
    if hits * 2 < len(modifiers):
        return False
    if head_word != head and not hits:
        return _noun_hit(head, low_text, plural_only=head_word)
    return True


def on_topic(terms: list[str], text: str) -> bool:
    low = text.lower()
    return any(_term_hit(term, low) for term in terms)


def _off_market_reason(domain: str, text: str) -> str:
    """Why a search result is not a US source ('' when it may be one); keys of OFF_MARKET_LABELS."""
    labels = domain.split(".")
    tld = labels[-1]
    if len(tld) == 2 and tld.isalpha() and tld not in _GENERIC_CC_TLDS:
        return "domain"
    edition = _EDITION_LABEL_RE.match(labels[0]) if len(labels) >= 3 else None
    if edition and edition.group(1) in _COUNTRY_CODES and edition.group(1) not in _NOT_A_COUNTRY_EDITION:
        return "edition"
    letters = [ch for ch in text if ch.isalpha()]
    if sum(1 for ch in letters if ord(ch) > 0x24F) * 10 > len(letters) * 3:
        return "script"
    if _FOREIGN_CURRENCY_RE.search(text) and not _USD_RE.search(text):
        return "currency"
    return ""


def page_locales(html: str) -> tuple[str, ...]:
    """Language tags a page declares in ``<html lang>`` and ``og:locale`` (lower case, ``-`` separated)."""
    head = html[:60_000]
    found: list[str] = []
    if match := _HTML_LANG_RE.search(head):
        found.append(match.group(1))
    for tag in _OG_LOCALE_RE.findall(head):
        if content := _CONTENT_RE.search(tag):
            found.append(content.group(1))
    return tuple(dict.fromkeys(tag.strip().lower().replace("_", "-") for tag in found if tag.strip()))


def foreign_locale(locales: tuple[str, ...] | list[str]) -> bool:
    """A declared locale of another country (en-gb, en_CA) or another language without the US (de, fr-fr)."""
    for tag in locales:
        parts = tag.strip().lower().replace("_", "-").split("-")
        lang = parts[0]
        region = next((p for p in parts[1:] if len(p) == 2 and p.isalpha()), "")
        if region:
            if region in _COUNTRY_CODES and region not in _US_REGIONS:
                return True
        elif lang != "en" and 2 <= len(lang) <= 3 and lang.isalpha():
            return True
    return False


class Page(str):
    """Page text that also carries what the markup said: declared locales (``page_locales``),
    structured USD prices (``structured_prices``) and how it was fetched (``via``)."""

    locales: tuple[str, ...] = ()
    offers: tuple[str, ...] = ()
    via: str = "urllib"
    published: str = ""


def _usd(value: object) -> str:
    try:
        amount = float(str(value).replace(",", "").strip())
    except ValueError:
        return ""
    if not 0 < amount < 100_000:
        return ""
    return f"${int(amount):,}" if amount == int(amount) else f"${amount:,.2f}"


def structured_prices(html: str) -> tuple[str, ...]:
    """USD prices a page states in schema.org Offer data (JSON-LD) or product:price meta tags."""
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("@type")
        kinds = " ".join(kind) if isinstance(kind, list) else str(kind or "")
        if "Offer" in kinds or "priceCurrency" in node:
            if str(node.get("priceCurrency") or "USD").upper() == "USD":
                for key in ("price", "lowPrice", "highPrice"):
                    if isinstance(node.get(key), (int, float, str)) and (amount := _usd(node[key])):
                        found.append(amount)
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for block in _LD_JSON_RE.findall(html):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    currency_tag = _META_CURRENCY_RE.search(html[:200_000])
    currency = _CONTENT_RE.search(currency_tag.group(0)) if currency_tag else None
    if (currency.group(1) if currency else "USD").strip().upper() == "USD":
        for tag in _META_PRICE_RE.findall(html[:200_000]):
            if (content := _CONTENT_RE.search(tag)) and (amount := _usd(content.group(1))):
                found.append(amount)
    return tuple(dict.fromkeys(found))[:6]


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


def _fetch_urllib(url: str, timeout: float) -> str | None:
    """Raw HTML, or None when the response is not HTML."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - http(s) only
        if "html" not in (response.headers.get("Content-Type") or "").lower():
            return None
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read(800_000)
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _fetch_impersonated(url: str, timeout: float) -> str:
    """Raw HTML through the browser-impersonating client ddgs ships (primp). Raises when it fails too."""
    from ddgs.http_client import HttpClient

    response = HttpClient(timeout=max(1, int(timeout))).get(url)
    if response.status_code >= 400:
        raise OSError(f"HTTP {response.status_code}")
    html = (response.text or "")[:800_000]
    return html if "<html" in html[:5000].lower() or "<body" in html.lower() else ""


def fetch_text(url: str, timeout: float = 8.0) -> str:
    """Page body as plain text. Raises on network errors; '' for non-HTML.

    A 403 / 429 / 503 or a dropped connection is retried once with a browser-like client:
    some review and retail sites refuse a plain urllib request but serve a browser.
    """
    via = "urllib"
    try:
        html = _fetch_urllib(url, timeout)
    except urllib.error.HTTPError as exc:
        if exc.code not in _RETRY_IMPERSONATED:
            raise
        html, via = _fetch_impersonated(url, timeout), "impersonated"
    except (urllib.error.URLError, ConnectionError) as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            raise  # a slow page is not retried: it would only double the wait
        html, via = _fetch_impersonated(url, timeout), "impersonated"
    if html is None:
        return ""
    page = Page(html_to_text(html))
    page.locales = page_locales(html)
    page.offers = structured_prices(html)
    page.published = page_published(html)
    page.via = via
    return page


_last_search = 0.0


def _host_in(domain: str, hosts: tuple[str, ...]) -> bool:
    return any(domain == host or domain.endswith("." + host) for host in hosts)


def _listing_page(domain: str, path: str) -> bool:
    """A retailer's search, category or store page (see _RETAIL_ITEM_PATHS)."""
    item_path = _RETAIL_ITEM_PATHS.get(domain)
    return bool(item_path) and not item_path.search(path + "/")


def _allocate(
    rows: list[dict], candidates: list[int], quota: dict[str, int], total: int, per_domain: int = 0
) -> list[int]:
    """Row indexes picked in candidate (rank) order: each kind up to its quota first, then any kind up to ``total``.

    ``per_domain`` > 0 caps how many picks a single domain may take.
    """
    picked: list[int] = []
    taken: set[int] = set()
    kinds: dict[str, int] = {}
    domains: dict[str, int] = {}
    for within_quota in (True, False):
        for index in candidates:
            if len(picked) >= total:
                return picked
            row = rows[index]
            if index in taken:
                continue
            if within_quota and kinds.get(row["kind"], 0) >= quota.get(row["kind"], 0):
                continue
            if per_domain and domains.get(row["domain"], 0) >= per_domain:
                continue
            taken.add(index)
            picked.append(index)
            kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
            domains[row["domain"]] = domains.get(row["domain"], 0) + 1
    return picked


def _yahoo_target(href: str) -> str:
    """Real URL behind a r.search.yahoo.com redirect link."""
    if "/RU=" not in href:
        return href
    target = href.split("/RU=", 1)[1]
    return unquote_plus(target.split("/RK=", 1)[0].split("/RS=", 1)[0])


def parse_yahoo_results(page: str) -> list[dict]:
    """Organic results from a Yahoo result page, in page order.

    Yahoo serves a desktop and a mobile layout depending on the browser profile,
    and result blocks sit inside one another in the parsed tree. Reading every
    title under a block therefore glues the next result's title onto it. Each
    result has exactly one linked title, so titles and bodies are walked in
    document order instead: a body belongs to the linked title right before it.
    """
    from lxml import html as lxml_html

    tree = lxml_html.fromstring(page)
    nodes = tree.xpath(
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' algo-sr ')]"
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' compTitle ')"
        " or contains(concat(' ', normalize-space(@class), ' '), ' compText ')]"
    )
    rows: list[dict] = []
    open_row: dict | None = None  # last linked title still waiting for its body
    for node in nodes:
        classes = f" {node.get('class', '')} "
        if " compTitle " in classes:
            open_row = None  # a heading without a link ("Related searches") ends the result
            heading = node.xpath(".//h3[1]")
            if not heading:
                continue
            # desktop: <a><h3>title</h3></a>; mobile: <h3><a aria-label="title">site › crumbs</a></h3>
            link = heading[0].xpath("ancestor::a[1]") or heading[0].xpath(".//a[@href][1]")
            if not link or not link[0].get("href"):
                continue
            title = link[0].get("aria-label") or heading[0].text_content()
            open_row = {"title": _clean(title), "url": _yahoo_target(link[0].get("href")), "snippet": ""}
            rows.append(open_row)
        elif open_row is not None:
            open_row["snippet"] = _clean(node.text_content())
            open_row = None
    return [row for row in rows if row["title"] and row["url"].startswith("http")]


def yahoo_search(query: str, max_results: int) -> list[dict]:
    """One request to search.yahoo.com through the HTTP client ddgs ships (browser impersonation)."""
    from ddgs.http_client import HttpClient

    response = HttpClient(timeout=SEARCH_TIMEOUT).get(YAHOO_SEARCH_URL, params={"p": query})
    if response.status_code != 200:
        return []
    return parse_yahoo_results(response.text or "")[:max_results]


def ddg_search(query: str, max_results: int) -> list[dict]:
    """Search rows tagged with the path that produced them (``via``: ``yahoo`` or ``ddgs``)."""
    global _last_search
    wait = _last_search + SEARCH_SPACING - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    try:
        try:
            rows = yahoo_search(query, max_results)
        except Exception:  # noqa: BLE001 - markup or client changed: use the library path
            rows = []
        if rows:
            return [{**row, "via": "yahoo"} for row in rows]
        from ddgs import DDGS

        found = DDGS(timeout=SEARCH_TIMEOUT).text(query, max_results=max_results, region=SEARCH_REGION)
    finally:
        _last_search = time.monotonic()
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", ""), "via": "ddgs"}
        for r in found or []
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


def _price_lines(text: str, limit: int = PRICE_LINES) -> list[str]:
    """Lines of a page that state a US-dollar price, with the line before when the price stands alone.

    Product tiles and spec tables put the price on its own short line under the name.
    """
    lines = text.split("\n")
    out: list[str] = []
    for index, line in enumerate(lines):
        if len(line) > 240 or not _PRICE_RE.search(line) or _FOREIGN_CURRENCY_RE.search(line):
            continue
        if len(line) < 40 and index:
            line = f"{lines[index - 1][:160]} {line}"
        if line not in out:
            out.append(line.strip())
        if len(out) >= limit:
            break
    return out


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
            found = [p for p in (low.find(tok) for term in terms for tok in _tokens(term)[-1:]) if p >= 0]
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
    empty_queries: list[str] = []
    off_market: list[str] = []
    off_market_by: dict[str, int] = {}
    listing: list[str] = []
    search_via: dict[str, int] = {}  # queries answered per search path

    def _drop_off_market(domain: str, reason: str) -> None:
        off_market.append(domain)
        off_market_by[reason] = off_market_by.get(reason, 0) + 1

    for query, kind in queries:
        try:
            found = _search(searcher, query)
        except Exception as exc:  # noqa: BLE001 - one failed query must not end the run
            search_errors.append(f"{query} ({type(exc).__name__}: {_clean(str(exc))[:60]})")
            continue
        if not found:
            empty_queries.append(query)
        if found and found[0].get("via"):
            search_via[found[0]["via"]] = search_via.get(found[0]["via"], 0) + 1
        for rank, row in enumerate(_unmerge(found)):
            parts = urlsplit(row["url"])
            domain = parts.netloc.lower().removeprefix("www.")
            key = (parts.netloc.lower() + parts.path).rstrip("/")
            if parts.scheme not in {"http", "https"} or key in seen or _host_in(domain, _NON_SOURCE_HOSTS):
                continue
            seen.add(key)
            if reason := _off_market_reason(domain, f"{row['title']} {row['snippet']}"):
                _drop_off_market(domain, reason)
                continue
            if _listing_page(domain, parts.path):
                listing.append(row["url"])
                continue
            rows.append({**row, "domain": domain, "kind": kind, "query": query, "rank": rank})
    results = len(rows) + len(off_market) + len(listing)
    # Rank order across queries: every query's first hit, then every second hit, …
    rows.sort(key=lambda r: r["rank"])

    def _body(row: dict) -> str:
        try:
            return fetcher(row["url"])
        except Exception:  # noqa: BLE001 - blocked/slow page: fall back to the snippet
            return ""

    # Fetch slots go to pages that can be read, shared out per kind; the rest keep their snippet.
    trend = brief.study == STUDY_TREND
    kind_quota, fetch_quota = (TREND_KIND_QUOTA, TREND_FETCH_QUOTA) if trend else (KIND_QUOTA, FETCH_QUOTA)
    readable = [i for i, row in enumerate(rows) if not _host_in(row["domain"], _NO_FETCH_HOSTS)]
    to_fetch = _allocate(rows, readable, fetch_quota, MAX_FETCH)
    bodies = [""] * len(rows)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, body in zip(to_fetch, pool.map(_body, [rows[i] for i in to_fetch])):
            bodies[index] = body

    terms = scope_terms(brief)
    market_terms = scope_terms(brief, "market")
    excerpt_terms = [t for t in _parts(brief.focus) if not _has_korean(t)] + terms
    usable: list[int] = []
    excerpts: dict[int, tuple[str, str]] = {}
    off_topic = 0
    for index, (row, body) in enumerate(zip(rows, bodies)):
        if foreign_locale(getattr(body, "locales", ())):
            _drop_off_market(row["domain"], "locale")  # e.g. a UK or Canadian site on a .com domain
            continue
        row_terms = market_terms if row["kind"] == "market" else terms
        head_ok = on_topic(row_terms, f"{row['title']} {row['snippet']}")
        body_ok = len(body) >= MIN_BODY_CHARS and on_topic(row_terms, body)
        from_body = _excerpt(body, excerpt_terms + row_terms[len(terms):]) if body_ok else ""
        if not from_body and not head_ok:
            off_topic += 1
            continue
        if excerpt := from_body or row["snippet"]:
            usable.append(index)
            excerpts[index] = (excerpt, "본문" if from_body else "요약문")
    kind_order = {kind: n for n, (kind, _label) in enumerate(KIND_LABELS)}
    chosen = sorted(
        _allocate(rows, usable, kind_quota, MAX_EVIDENCE, MAX_PER_DOMAIN),
        key=lambda i: (kind_order.get(rows[i]["kind"], len(kind_order)), i),
    )
    evidence: list[Evidence] = []
    for number, index in enumerate(chosen, 1):  # numbered in the order the pack lists them
        row = rows[index]
        excerpt, source = excerpts[index]
        body = bodies[index]
        detail, page_prices = excerpt, list(getattr(body, "offers", ()) or ())
        if source == "본문":
            row_terms = market_terms if row["kind"] == "market" else terms
            detail = _excerpt(body, excerpt_terms + row_terms[len(terms):], width=600, windows=4)
            if row["kind"] == "competitor":
                lines = _price_lines(body)
                if lines:
                    detail += "\n[가격 표기 줄] " + " | ".join(lines)
                page_prices += [p for line in lines for p in _PRICE_RE.findall(line)]
        evidence.append(
            Evidence(
                id=f"E{number}",
                kind=row["kind"],
                title=row["title"][:140],
                url=row["url"],
                domain=row["domain"],
                source=source,
                excerpt=excerpt[:EXCERPT_CHARS],
                prices=list(dict.fromkeys(_clean(p) for p in _PRICE_RE.findall(excerpt)))[:5],
                query=row["query"],
                detail=detail[:DETAIL_CHARS],
                page_prices=list(dict.fromkeys(_clean(p) for p in page_prices))[:8],
                published=getattr(body, "published", "") or snippet_published(row["snippet"]),
            )
        )
    stats = {
        "queries": len(queries),
        "search_errors": search_errors,
        "empty_queries": empty_queries,
        "search_via": search_via,
        "results": results,
        "off_market_dropped": len(off_market),
        "off_market_domains": sorted(set(off_market)),
        "off_market_by": off_market_by,
        "listing_dropped": len(listing),
        "fetch_attempted": len(to_fetch),
        "fetch_ok": sum(1 for b in bodies if len(b) >= MIN_BODY_CHARS),
        "fetch_impersonated_ok": sum(
            1 for b in bodies if len(b) >= MIN_BODY_CHARS and getattr(b, "via", "") == "impersonated"
        ),
        "off_topic_dropped": off_topic,
        "evidence": len(evidence),
        "evidence_body": sum(1 for e in evidence if e.source == "본문"),
        "kind_quota": dict(kind_quota),
        "evidence_by_kind": {kind: sum(1 for e in evidence if e.kind == kind) for kind, _label in KIND_LABELS},
    }
    if trend:
        years = study_years(brief)
        stats["years"] = years
        stats["evidence_by_year"] = {str(y): sum(1 for e in evidence if about_year(e, y)) for y in years}
    return evidence, stats


def about_year(item: Evidence, year: int) -> bool:
    """Published that year, or the item's text names the year."""
    if item.published.startswith(str(year)):
        return True
    return bool(re.search(rf"(?<!\d){year}(?!\d)", f"{item.title} {item.excerpt} {item.detail}"))


def _cell(text: str) -> str:
    return _clean(text).replace("|", "\\|")


def _brief_table(brief: ResearchBrief) -> list[str]:
    lines = ["| 항목 | 값 | 출처 |", "|---|---|---|"]
    for name, label in FIELD_LABELS:
        value = getattr(brief, name)
        value = ", ".join(value) if isinstance(value, list) else value
        if name == "study":
            value = STUDY_LABELS.get(value, value)
        lines.append(f"| {label} | {_cell(value) or '미지정'} | {brief.origin.get(name, '-') if value else '-'} |")
    if left_out := _unsearchable(brief):
        lines += [
            "",
            "한국어로 적혀 미국 시장 검색에 쓰지 않은 값: " + ", ".join(left_out) + ". 영어로 적으면 검색에 반영됩니다.",
        ]
    if brief.study == STUDY_TREND:
        years = ", ".join(str(y) for y in study_years(brief))
        default = "" if period_years(brief.period) else f" (기간을 지정하지 않아 최근 {TREND_DEFAULT_YEARS}년)"
        lines += ["", f"연도별로 검색한 해: {years}{default}"]
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
    out = [
        f"# 시장조사 근거 팩 — {brief.scope}",
        "",
        f"- 세션: `{session_id}`",
        f"- 대상 시장: {MARKET_LABEL} (영어 검색어 · 다른 나라 도메인과 한글 등 비라틴 문자 페이지 제외)",
    ]
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

    dropped_from = f"({', '.join(stats['off_market_domains'][:8])})" if stats["off_market_domains"] else ""
    out += [
        "> 웹에서 수집해 브리프 주제와 맞는지 확인한 근거 모음입니다. 발췌는 원문 그대로입니다. "
        "시장 공백·페르소나·시장 규모·가격 전략 같은 종합 결론은 이 문서에 없습니다.",
        "",
        "## 수집 요약",
        "",
        f"- 검색 {stats['queries']}회, 결과 {stats['results']}건, "
        f"미국 외 출처라 제외 {stats['off_market_dropped']}건{dropped_from}, "
        f"소매처(Amazon·Walmart·Target) 상품 목록 페이지라 제외 {stats.get('listing_dropped', 0)}건, "
        f"주제와 무관해 제외 {stats['off_topic_dropped']}건",
    ]
    if by := stats.get("off_market_by"):
        out.append(
            "- 미국 외 출처로 본 이유: "
            + ", ".join(f"{OFF_MARKET_LABELS.get(k, k)} {n}건" for k, n in sorted(by.items(), key=lambda kv: -kv[1]))
        )
    fallback = stats.get("fetch_impersonated_ok", 0)
    out += [
        f"- 본문 수집 {stats['fetch_ok']}/{stats['fetch_attempted']}건"
        + (f" (일반 요청이 막혀 브라우저형 요청으로 읽은 {fallback}건 포함)" if fallback else ""),
        f"- 채택 근거 {stats['evidence']}건 (본문 {stats['evidence_body']}건, "
        f"검색 요약문만 {stats['evidence'] - stats['evidence_body']}건)",
    ]
    quota = stats.get("kind_quota") or {}
    by_kind = stats.get("evidence_by_kind") or {}
    if quota:
        out.append(
            "- 종류별 채택 건수(할당): "
            + ", ".join(f"{label} {by_kind.get(kind, 0)}({quota.get(kind, 0)})" for kind, label in KIND_LABELS)
            + ". 할당을 못 채운 종류의 남은 자리는 다른 종류가 씁니다."
        )
    by_year = stats.get("evidence_by_year") or {}
    if by_year:
        out.append(
            "- 연도별 근거(게시일이 그해이거나 내용에 그해가 나온 근거): "
            + ", ".join(f"{year}년 {n}건" for year, n in by_year.items())
        )
    if via := stats.get("search_via"):
        labels = {"yahoo": "Yahoo 직접 조회", "ddgs": "ddgs 라이브러리(대체 경로)"}
        out.append("- 검색 경로: " + ", ".join(f"{labels.get(k, k)} {n}회" for k, n in sorted(via.items())))
    if stats["search_errors"]:
        out.append(f"- 실패한 검색 {len(stats['search_errors'])}회: " + "; ".join(stats["search_errors"]))
    if empty := stats.get("empty_queries"):
        out.append(f"- 결과가 없던 검색 {len(empty)}회: " + "; ".join(f"`{q}`" for q in empty))
    out.append("")

    missing: list[str] = []
    for kind, label in KIND_LABELS:
        items = [e for e in evidence if e.kind == kind]
        if not items:
            missing.append(f"{label}: 0건")
            continue
        if len(items) < quota.get(kind, 0):
            missing.append(f"{label}: 할당 {quota[kind]}건 중 {len(items)}건만 확보")
        out += [f"## {label} ({len(items)}건)", ""]
        for item in items:
            published = f" · 게시일 {item.published}" if item.published else ""
            out += [
                f"### {item.id}. {item.title}",
                "",
                f"- 출처: {item.domain} · {item.source}{published} · 검색어 `{item.query}`",
            ]
            if item.prices:
                out.append(f"- 발췌 안 가격 표기: {', '.join(item.prices)}")
            if extra := [p for p in item.page_prices if p not in item.prices]:
                out.append(f"- 페이지의 상품 정보·가격 줄에 적힌 가격: {', '.join(extra)}")
            out += [f"- {item.url}", "", f"> {item.excerpt}", ""]
    for name in brief.competitors:
        low = name.lower()
        if not any(low in f"{e.title} {e.excerpt}".lower() for e in evidence):
            missing.append(f"경쟁사 `{name}`: 이 브랜드를 언급한 근거 0건")
    missing += [f"{year}년: 그해를 다룬 근거 0건" for year, n in by_year.items() if not n]
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
                "market": MARKET,
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
