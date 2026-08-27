"""Standalone deep research CLI (Gemini-style, no full pipeline)."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from cqr_product_pipeline.agents.deep_research import (
    ensure_concept_ids,
    run_deep_research,
    _parse_brief_hints,
)
from cqr_product_pipeline.cli.research_report_md import format_research_report_md
from cqr_product_pipeline.config.paths import MARKET_RESEARCH_ROOT
from cqr_product_pipeline.config.settings import get_settings


def _write_session_meta(output_dir: Path, session_id: str, brief: str) -> None:
    meta = {
        "session_id": session_id,
        "brief": brief,
        "mode": "research",
        "output_dir": str(output_dir.resolve()),
    }
    (MARKET_RESEARCH_ROOT / ".session.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CQR deep research only")
    parser.add_argument("--brief", type=str, required=True, help="Research question / brief")
    parser.add_argument("--target-category", type=str, default=None)
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Template mode without live LLM/web")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: market_research/output/<session>)",
    )
    parser.add_argument("--json-only", action="store_true", help="Print JSON only, no markdown summary")
    args = parser.parse_args()

    session_id = args.session_id or str(uuid.uuid4())[:8]
    output_dir = args.output_dir or (MARKET_RESEARCH_ROOT / "output" / session_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("조사 계획 수립 → 웹 검색 → 근거 정리 → 리포트 작성")

    report = run_deep_research(
        args.brief,
        target_category=args.target_category,
        dry_run=args.dry_run,
    )
    report = ensure_concept_ids(report)

    (output_dir / "research_report.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md = format_research_report_md(
        report,
        session_id=session_id,
        lang=get_settings().report_language,
        brief_lock=_parse_brief_hints(args.brief, args.target_category),
    )
    (output_dir / "research_report.md").write_text(md, encoding="utf-8")
    _write_session_meta(output_dir, session_id, args.brief)

    if args.json_only:
        print(report.model_dump_json(indent=2))
    else:
        print(md)

    print(f"\n---\nSession: {session_id}")
    print(f"JSON: {output_dir / 'research_report.json'}")
    print(f"MD:   {output_dir / 'research_report.md'}")


if __name__ == "__main__":
    main()
