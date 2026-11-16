"""Market research CLI: structured brief -> evidence pack (no LLM, no templates)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from cqr_product_pipeline.agents.evidence_pack import (
    FIELD_EXAMPLE,
    FIELD_KEYS,
    MIN_EVIDENCE,
    brief_gate,
    parse_brief,
    run_evidence_pack,
)
from cqr_product_pipeline.config.paths import MARKET_RESEARCH_ROOT

# Exit code for briefs without a product or category, or without an English name
# to search the US market with. The host wrapper maps it to ``status=needs_brief``;
# no search runs and no report is written.
NEEDS_BRIEF_EXIT = 3
NEEDS_BRIEF_ERRORS = {
    "no_scope": "브리프에서 조사할 품목이나 카테고리를 찾지 못했습니다. 웹 검색을 실행하지 않았습니다.",
    "no_english_name": (
        "미국 시장을 검색할 영문 품목명을 찾지 못했습니다. `영문명:` 필드를 붙여 주세요. "
        "웹 검색을 실행하지 않았습니다."
    ),
}
# Exit code when fewer than MIN_EVIDENCE on-topic sources were found. The
# wrapper maps it to ``status=insufficient_evidence``; no report is written.
INSUFFICIENT_EVIDENCE_EXIT = 4


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
    parser = argparse.ArgumentParser(description="CQR market research evidence pack")
    parser.add_argument("--brief", type=str, default="", help="Brief sentence and/or inline fields")
    for name in FIELD_KEYS:
        parser.add_argument("--" + name.replace("_", "-"), type=str, default=None)
    parser.add_argument("--target-category", type=str, default=None, help="Deprecated alias of --category")
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Show the search plan without searching")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: market_research/output/<session>)",
    )
    parser.add_argument("--json-only", action="store_true", help="Print result JSON only, no markdown")
    args = parser.parse_args()

    overrides = {name: getattr(args, name) for name in FIELD_KEYS if getattr(args, name)}
    if args.target_category and "category" not in overrides:
        overrides["category"] = args.target_category
    brief = parse_brief(args.brief, overrides)
    reason = brief_gate(brief)
    if reason:
        print(
            json.dumps(
                {
                    "status": "needs_brief",
                    "reason": reason,
                    "brief": args.brief,
                    "error": NEEDS_BRIEF_ERRORS.get(reason, NEEDS_BRIEF_ERRORS["no_scope"]),
                    "example": FIELD_EXAMPLE,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        raise SystemExit(NEEDS_BRIEF_EXIT)

    session_id = args.session_id or str(uuid.uuid4())[:8]
    output_dir = args.output_dir or (MARKET_RESEARCH_ROOT / "output" / session_id)

    print("브리프 해석 -> 웹 검색 -> 본문 수집 -> 주제 검증 -> 근거 팩 작성", flush=True)
    result = run_evidence_pack(brief, output_dir, session_id, dry_run=args.dry_run)
    summary = {
        "status": result["status"],
        "evidence_count": result["evidence_count"],
        "min_evidence": MIN_EVIDENCE,
        "stats": result["stats"],
    }
    if result["status"] != "ok":
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        raise SystemExit(INSUFFICIENT_EVIDENCE_EXIT)

    _write_session_meta(output_dir, session_id, args.brief)
    if args.json_only:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        md = result["markdown"]
        try:
            print(md)
        except UnicodeEncodeError:
            # Windows cp949 consoles cannot print every character. Host reads the MD file.
            print(md.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ))

    print(f"\n---\nSession: {session_id}")
    print(f"JSON: {output_dir / 'evidence_pack.json'}")
    print(f"MD:   {output_dir / 'research_report.md'}")


if __name__ == "__main__":
    main()
