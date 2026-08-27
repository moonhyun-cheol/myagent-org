"""Reproduce the deep-research synthesis call shapes to locate gateway failures.

Run via CQR_PA: node tools/probe-pipeline-llm.mjs research
"""

from __future__ import annotations

import json
import time

from cqr_product_pipeline.agents.deep_research import (
    _parse_brief_hints,
    _synthesize_from_snippets,
)
from cqr_product_pipeline.config.providers import get_chat_model
from cqr_product_pipeline.config.settings import get_settings
from cqr_product_pipeline.schemas.models import ResearchReport

BRIEF = "2027 가을겨울 스키바지 시장조사"


def _snippets(count: int) -> list[dict]:
    return [
        {
            "title": f"Best ski pants review {i}",
            "link": f"https://example.com/ski-review-{i}",
            "snippet": (
                "Reviewers note the seams leak after a season, vents are too small for "
                "spring slush, and sizing runs long in the inseam. Price band $120-$180. "
            )
            * 3,
            "_query": "ski pants waterproofing complaints",
        }
        for i in range(count)
    ]


def _report(name: str, fn) -> None:
    t0 = time.time()
    try:
        out = fn()
        sec = round(time.time() - t0)
        size = len(out.model_dump_json()) if isinstance(out, ResearchReport) else len(str(out))
        gaps = len(out.market_gaps) if isinstance(out, ResearchReport) else 0
        print(f"{name} -> OK ({sec}s, {size}B, gaps={gaps})", flush=True)
    except Exception as exc:  # noqa: BLE001 - probe reports every failure shape
        sec = round(time.time() - t0)
        print(f"{name} -> FAIL ({sec}s) {type(exc).__name__}: {str(exc)[:300]}", flush=True)


def main() -> None:
    settings = get_settings()
    print(
        f"provider={settings.llm_provider} model={settings.llm_model} "
        f"lang={settings.report_language}",
        flush=True,
    )
    llm = get_chat_model(settings)
    print(f"hints={json.dumps(_parse_brief_hints(BRIEF, None), ensure_ascii=False)}", flush=True)

    for count in (5, 30):
        snippets = _snippets(count)
        payload_kb = round(len(json.dumps(snippets, ensure_ascii=False)) / 1024)
        _report(
            f"synthesize {count:>2} snippets (~{payload_kb}KB)",
            lambda s=snippets: _synthesize_from_snippets(BRIEF, None, s, settings),
        )

    del llm


if __name__ == "__main__":
    main()
