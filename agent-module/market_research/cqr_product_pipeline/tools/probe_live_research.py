# -*- coding: utf-8 -*-
"""Live improve loop: lock + search + LLM synthesize (or grounded fallback)."""
from __future__ import annotations

import os
import sys


def main() -> int:
    brief = os.environ.get(
        "CQR_PROBE_BRIEF",
        "2028 ss시즌에 맞는 다이빙복 시장조사",
    )
    from cqr_product_pipeline.config.settings import get_settings

    get_settings.cache_clear()
    from cqr_product_pipeline.config.providers import get_chat_model, get_search_tool
    from cqr_product_pipeline.agents.deep_research import (
        _parse_brief_hints,
        _build_search_queries,
        _run_search_loop,
        _synthesize_from_snippets,
        _grounded_report_from_snippets,
        _dry_run_report,
    )
    from cqr_product_pipeline.cli.research_report_md import format_research_report_md

    s = get_settings()
    print("provider", s.llm_provider, "model", s.llm_model)
    try:
        m = get_chat_model(s)
        print("chat_ok", type(m).__name__)
    except Exception as e:
        print("chat_FAIL", type(e).__name__, e)
        return 2

    h = _parse_brief_hints(brief, None)
    print("lock", h["product_brief"], h["product_family"], h["competitors"][:70])
    tool = get_search_tool(s)
    qs = _build_search_queries(brief, h)[:4]
    print("queries", qs)
    snips = _run_search_loop(qs, tool, max_calls=4)
    print("snippets", len(snips))
    mode = "empty"
    if snips:
        try:
            rep = _synthesize_from_snippets(brief, None, snips[:20], s)
            mode = "llm"
        except Exception as e:
            print("synth_fail", type(e).__name__, str(e)[:200])
            rep = _grounded_report_from_snippets(
                brief,
                None,
                snips,
                fallback_note=f"LLM 종합 실패 ({type(e).__name__})",
            )
            mode = "grounded"
    else:
        rep = _dry_run_report(brief, None, fallback_note="웹 검색 근거 0건")
        mode = "empty"

    md = format_research_report_md(rep, session_id="live1", brief_lock=h)
    print("MODE", mode)
    print("HAS_SCOPE", "조사 범위" in md and h["product_brief"] in md)
    print("HAS_COLUMBIA_BATTLE", "### vs Columbia" in md)
    print("---HEAD---")
    print("\n".join(md.splitlines()[:30]))
    return 0 if mode in ("llm", "grounded") else 1


if __name__ == "__main__":
    sys.exit(main())
