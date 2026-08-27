"""CLI — run feasibility MVP on sample or supplied concepts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cqr_product_pipeline.agents.feasibility import run_feasibility
from cqr_product_pipeline.rag.ingest import ingest_corpus
from cqr_product_pipeline.schemas.models import ConceptCandidate, ResearchReport


def _sample_research() -> ResearchReport:
    return ResearchReport(
        market_gaps=["Summer lightweight cargo heat complaints in $40-55 band"],
        consumer_pain_points=["pocket bulk", "thigh heat in humid weather"],
        concepts=[
            ConceptCandidate(
                concept_id="A",
                name="Liberator Lite Summer Cargo",
                line_recommendation="Liberator",
                garment_type="cargo pants",
                target_tpo="hot weather field / range",
                usp_hypothesis="6-pocket stack vs TLP125 8-pocket; mac pocket 1pc left thigh",
                keywords=["Liberator", "lightweight", "cargo", "summer", "TLP125", "pocket"],
            )
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CQR feasibility MVP")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild Chroma before run")
    parser.add_argument("--input", type=Path, help="ResearchReport JSON file")
    parser.add_argument("--output", type=Path, help="Write FeasibilityReport JSON here")
    parser.add_argument("--dry-run", action="store_true", help="Heuristic scoring only (no LLM)")
    parser.add_argument("--use-llm", action="store_true", help="Force LLM scoring")
    args = parser.parse_args()

    if args.rebuild_index:
        counts = ingest_corpus(rebuild=True)
        print("Ingest:", counts)

    report = _sample_research()
    if args.input:
        report = ResearchReport.model_validate_json(args.input.read_text(encoding="utf-8"))

    use_llm = False if args.dry_run else (True if args.use_llm else None)
    feasibility_report, bundles = run_feasibility(report, use_llm=use_llm)

    if feasibility_report.session_notes:
        print(f"Mode: {feasibility_report.session_notes}")

    print(f"\nFeasibility — {len(feasibility_report.concepts)} concept(s)\n")
    for result in feasibility_report.concepts:
        print(f"## {result.name} ({result.concept_id})")
        print(f"  brand={result.brand_alignment_score} mfg={result.manufacturing_score} "
              f"cannibal={result.cannibalization_score} → {result.verdict.value}")
        print(f"  evidence blocks: {len(result.evidence)}")
        collections = sorted({b.collection for b in result.evidence})
        print(f"  collections: {', '.join(collections) or '(none)'}")
        if result.blockers:
            print(f"  blockers: {'; '.join(result.blockers)}")

    if args.output:
        args.output.write_text(
            feasibility_report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
