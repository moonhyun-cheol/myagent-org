"""End-to-end pipeline CLI with HITL interrupt/resume."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from langgraph.types import Command

from cqr_product_pipeline.agents.deep_research import _parse_brief_hints
from cqr_product_pipeline.cli.hitl_summary import format_feasibility_review_md, format_resume_hints
from cqr_product_pipeline.cli.parse_approve_text import parse_approve_text
from cqr_product_pipeline.cli.research_report_md import format_research_report_md
from cqr_product_pipeline.config.settings import get_settings
from cqr_product_pipeline.graph.workflow import compile_pipeline_graph, parse_human_feedback
from cqr_product_pipeline.rag.ingest import ingest_corpus
from cqr_product_pipeline.schemas.models import HumanFeedback


def _write_outputs(
    output_dir: Path,
    *,
    session_id: str,
    state: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    research = state.get("research_report")
    feasibility = state.get("feasibility_report")
    plan = state.get("final_product_plan")
    brief = str(state.get("user_brief") or state.get("brief") or "")
    target = state.get("target_category")

    if research:
        (output_dir / "research_report.json").write_text(
            research.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (output_dir / "research_report.md").write_text(
            format_research_report_md(
                research,
                session_id=session_id,
                lang=get_settings().report_language,
                brief_lock=_parse_brief_hints(brief, target) if brief else None,
            ),
            encoding="utf-8",
        )
    if feasibility and research:
        (output_dir / "feasibility_review.md").write_text(
            format_feasibility_review_md(
                session_id=session_id,
                research_report=research,
                feasibility_report=feasibility,
            ),
            encoding="utf-8",
        )
        (output_dir / "feasibility_report.json").write_text(
            feasibility.model_dump_json(indent=2),
            encoding="utf-8",
        )
    if plan:
        (output_dir / "final_product_plan.md").write_text(plan, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CQR product pipeline")
    parser.add_argument("--brief", type=str, help="User brief / category seed")
    parser.add_argument("--target-category", type=str, default=None)
    parser.add_argument("--thread-id", type=str, default=None, help="Session / checkpoint thread id")
    parser.add_argument("--dry-run", action="store_true", help="Skip live LLM/web (template mode)")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild Chroma before run")
    parser.add_argument("--resume", action="store_true", help="Resume after HITL interrupt")
    parser.add_argument("--feedback", type=Path, help="HumanFeedback JSON for resume")
    parser.add_argument(
        "--approve-text",
        type=str,
        help="Natural-language HITL approval (e.g. 'A 승인, B 거절')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for JSON/MD artifacts",
    )
    args = parser.parse_args()

    if args.rebuild_index:
        counts = ingest_corpus(rebuild=True)
        print("Ingest:", counts)

    session_id = args.thread_id or str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": session_id}}
    graph = compile_pipeline_graph(dry_run=args.dry_run)

    if args.resume:
        if args.feedback and args.approve_text:
            parser.error("Use only one of --feedback or --approve-text")
        if not args.feedback and not args.approve_text:
            parser.error("--resume requires --feedback or --approve-text")

        if args.feedback:
            feedback = HumanFeedback.model_validate_json(
                args.feedback.read_text(encoding="utf-8")
            )
        else:
            concept_ids: list[str] = []
            try:
                prior = graph.get_state(config)
                feas = prior.values.get("feasibility_report")
                if feas and hasattr(feas, "concepts"):
                    concept_ids = [c.concept_id for c in feas.concepts]
            except Exception:
                pass
            feedback = parse_approve_text(args.approve_text, default_concept_ids=concept_ids or None)

        result = graph.invoke(
            Command(resume=feedback.model_dump()),
            config=config,
        )
    else:
        if not args.brief:
            parser.error("--brief is required unless --resume")
        initial = {
            "session_id": session_id,
            "user_brief": args.brief,
            "target_category": args.target_category,
            "iteration": 0,
        }
        result = graph.invoke(initial, config=config)

    state = graph.get_state(config)
    merged = {**state.values, **(result or {})}
    _write_outputs(args.output_dir, session_id=session_id, state=merged)

    if state.next:
        concept_ids: list[str] = []
        feas = merged.get("feasibility_report")
        if feas and hasattr(feas, "concepts"):
            concept_ids = [c.concept_id for c in feas.concepts]
        print(f"\n⏸ HITL interrupt before: {state.next}")
        print(f"Session thread-id: {session_id}")
        print(f"Research: {args.output_dir / 'research_report.md'}")
        print(f"Review: {args.output_dir / 'feasibility_review.md'}")
        for line in format_resume_hints(session_id=session_id, concept_ids=concept_ids):
            print(line)
        return

    print(f"\n✓ Pipeline complete — session {session_id}")
    if merged.get("research_report"):
        print(f"Research: {args.output_dir / 'research_report.md'}")
    if merged.get("final_product_plan"):
        print(f"Plan: {args.output_dir / 'final_product_plan.md'}")
    else:
        print("No product plan generated (no approved concepts or early exit).")


if __name__ == "__main__":
    main()
