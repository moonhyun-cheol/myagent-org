"""Evidence-pack bench: fixed briefs, live or replayed runs, quality metrics.

Live run, recording the raw search rows and page bodies::

    python tools/bench_evidence.py --label live --runs 2 --record _local/cache/mr-bench/rec

Replay a recording through the current rules (no network, deterministic)::

    python tools/bench_evidence.py --label replay --replay _local/cache/mr-bench/rec

Replay isolates rule changes (topic check, price pattern, listing and market
filters) from search-engine variance: both sides read the same rows and bodies.
A page the replayed code wants but the recording never fetched counts as a
failed fetch and is reported as ``unrecorded``.

``--sheet`` writes a Markdown table with one row per evidence item and an empty
verdict column, for a person to mark each item usable or not. Counts alone say
how many slots were filled, not whether the excerpts are usable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
os.environ.setdefault("CQR_MANAGER_ROOT", str(PROJECT.parents[1]))

from cqr_product_pipeline.agents import evidence_pack as ep  # noqa: E402

BRIEFS = {
    "work_boots": "품목: 작업화 / 영문명: work boots / 경쟁사: Timberland PRO, Keen / 가격: $120-200 / 초점: waterproof, comfort",
    "cargo_pants": "품목: 카고바지 / 영문명: tactical cargo pants / 경쟁사: 5.11, TRUEWERK / 가격: $35-65",
    "ski_pants": "품목: 스키바지 / 영문명: ski pants / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280",
    "slacks": "품목: 슬랙스 / 영문명: slacks / 시즌: 겨울 / 가격: $40-90",
    # What the host's brief step sends for the same request: a US search name and a category.
    "slacks_host": "품목: 슬랙스 / 영문명: men's dress slacks / 카테고리: men's dress pants / 시즌: 겨울 / 가격: $40-90",
    "outdoor_category": "카테고리: outdoor apparel / 경쟁사: Columbia, Patagonia / 가격: $60-150 / 시즌: 2027 FW",
}
SOCIAL = ("tiktok.com", "youtube.com", "instagram.com", "facebook.com", "pinterest.com", "x.com", "twitter.com")
# A market excerpt "has a figure" when it states a share, a growth rate or a money amount with a magnitude.
_FIGURE_RE = re.compile(
    r"\d+(?:\.\d+)?\s?%|\$\s?\d[\d,.]*\s?(?:billion|million|trillion|bn|mn|[BM])\b|\bCAGR\b", re.IGNORECASE
)


def _domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _social(domain: str) -> bool:
    return any(domain == s or domain.endswith("." + s) for s in SOCIAL)


def _as_page(text: str, locales: list[str], offers: list[str] | None = None, via: str = "urllib") -> str:
    page_cls = getattr(ep, "Page", None)
    if page_cls is None:
        return text
    page = page_cls(text)
    page.locales = tuple(locales)
    page.offers = tuple(offers or ())
    page.via = via
    return page


def live_io(record: dict):
    """Real searcher/fetcher that also write every row and body into ``record``."""
    record.setdefault("searches", {})
    record.setdefault("pages", {})

    def searcher(query: str, max_results: int) -> list[dict]:
        try:
            rows = ep.ddg_search(query, max_results)
        except Exception as exc:  # noqa: BLE001
            record["searches"][query] = {"error": f"{type(exc).__name__}: {str(exc)[:80]}"}
            raise
        record["searches"][query] = {"rows": rows}
        return rows

    def fetcher(url: str) -> str:
        started = time.time()
        try:
            body = ep.fetch_text(url)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", "")
            record["pages"][url] = {"error": f"{type(exc).__name__}{' ' + str(code) if code else ''}"}
            raise
        record["pages"][url] = {
            "text": str(body),
            "locales": list(getattr(body, "locales", ()) or ()),
            "offers": list(getattr(body, "offers", ()) or ()),
            "via": getattr(body, "via", "urllib"),
            "secs": round(time.time() - started, 1),
        }
        return body

    return searcher, fetcher


def replay_io(record: dict, misses: list[str]):
    searches = record.get("searches", {})
    pages = record.get("pages", {})

    def searcher(query: str, _max_results: int) -> list[dict]:
        entry = searches.get(query)
        if entry is None:
            misses.append(f"search: {query}")
            return []
        if "error" in entry:
            raise RuntimeError(entry["error"])
        return entry["rows"]

    def fetcher(url: str) -> str:
        entry = pages.get(url)
        if entry is None:
            misses.append(f"fetch: {url}")
            raise OSError("unrecorded")
        if "error" in entry:
            raise OSError(entry["error"])
        return _as_page(entry["text"], entry.get("locales", []), entry.get("offers"), entry.get("via", "urllib"))

    return searcher, fetcher


def metrics(evidence: list, stats: dict, secs: float, searches: dict | None) -> dict:
    empty = stats.get("empty_queries")
    if empty is None and searches is not None:  # code before empty_queries was counted
        empty = [q for q, e in searches.items() if not e.get("rows")]
    return {
        "secs": round(secs),
        "queries": stats.get("queries"),
        "empty_queries": len(empty or []),
        "search_errors": len(stats.get("search_errors") or []),
        "search_via": stats.get("search_via"),
        "results": stats.get("results"),
        "off_market": stats.get("off_market_dropped"),
        "off_market_by": stats.get("off_market_by"),
        "off_market_domains": stats.get("off_market_domains"),
        "listing": stats.get("listing_dropped"),
        "off_topic": stats.get("off_topic_dropped"),
        "fetch": f"{stats.get('fetch_ok')}/{stats.get('fetch_attempted')}",
        "evidence": len(evidence),
        "body": sum(1 for e in evidence if e.source == "본문"),
        "kinds": dict(Counter(e.kind for e in evidence)),
        "competitor_with_price": sum(
            1 for e in evidence if e.kind == "competitor" and (e.prices or getattr(e, "page_prices", None))
        ),
        "fetch_impersonated_ok": stats.get("fetch_impersonated_ok", 0),
        "market_with_figure": sum(1 for e in evidence if e.kind == "market" and _FIGURE_RE.search(e.excerpt)),
        "social": sum(1 for e in evidence if _social(e.domain)),
        "prices": sorted({p for e in evidence for p in e.prices}),
    }


def evidence_rows(evidence: list) -> list[dict]:
    keys = ("id", "kind", "source", "domain", "title", "url", "query", "prices", "page_prices", "excerpt", "detail")
    return [{k: getattr(e, k, None) for k in keys} for e in evidence]


def write_sheet(path: Path, runs: list[dict]) -> None:
    lines = [
        "# 근거 판정표",
        "",
        "`판정` 칸에 O(쓸 수 있음) / X(쓸 수 없음)를 적습니다. 기준: 발췌가 그 종류의 근거로 실제 쓰일 수 있는가 "
        "(리뷰·불만은 제품에 대한 불만·문제, 경쟁사·가격은 특정 브랜드 제품이나 가격, 시장은 미국 시장 수치·동향).",
        "",
    ]
    for run in runs:
        lines += [f"## {run['brief']} · run {run['run']}", "", "| 판정 | ID | 종류 | 출처 | 제목 | 발췌 |", "|---|---|---|---|---|---|"]
        for row in run["evidence"]:
            cells = [row["id"], row["kind"], f"{row['domain']} ({row['source']})", row["title"][:60], row["excerpt"][:200]]
            lines.append("|  | " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="run")
    parser.add_argument("--briefs", default="all", help="comma list of: " + ", ".join(BRIEFS))
    parser.add_argument("--runs", type=int, default=1, help="live runs per brief")
    parser.add_argument("--record", type=Path, help="directory to save raw rows and bodies of live runs")
    parser.add_argument("--replay", type=Path, help="directory of recordings to replay instead of searching")
    parser.add_argument("--out-dir", type=Path, default=Path("_local/cache/mr-bench"))
    parser.add_argument("--sheet", action="store_true", help="also write a judgment sheet")
    args = parser.parse_args()
    names = list(BRIEFS) if args.briefs == "all" else [b.strip() for b in args.briefs.split(",") if b.strip()]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    plan: list[tuple[str, int, dict | None]] = []
    if args.replay:
        for file in sorted(args.replay.glob("*.json")):
            record = json.loads(file.read_text(encoding="utf-8"))
            if record["brief"] in names:
                plan.append((record["brief"], record["run"], record))
    else:
        plan = [(name, n, None) for name in names for n in range(args.runs)]

    report: list[dict] = []
    for name, n, recorded in plan:
        brief = ep.parse_brief(BRIEFS[name])
        misses: list[str] = []
        if recorded is not None:
            searcher, fetcher = replay_io(recorded, misses)
            searches = recorded.get("searches")
        else:
            recorded_now: dict = {"brief": name, "run": n, "text": BRIEFS[name]}
            searcher, fetcher = live_io(recorded_now)
            searches = recorded_now["searches"]
        started = time.time()
        evidence, stats = ep.collect_evidence(brief, searcher, fetcher)
        run = {"brief": name, "run": n, **metrics(evidence, stats, time.time() - started, searches)}
        if recorded is not None:
            run["unrecorded"] = len(misses)
        print(json.dumps(run, ensure_ascii=False))
        report.append({**run, "evidence": evidence_rows(evidence)})
        if recorded is None and args.record:
            args.record.mkdir(parents=True, exist_ok=True)
            (args.record / f"{name}-{n}.json").write_text(json.dumps(recorded_now, ensure_ascii=False), encoding="utf-8")

    out = args.out_dir / f"{args.label}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved:", out)
    if args.sheet:
        sheet = args.out_dir / f"{args.label}-sheet.md"
        write_sheet(sheet, report)
        print("sheet:", sheet)


if __name__ == "__main__":
    main()
