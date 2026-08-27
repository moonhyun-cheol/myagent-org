from __future__ import annotations

from typing import TypedDict

from cqr_product_pipeline.schemas.models import (
    ConceptCandidate,
    FeasibilityReport,
    HumanFeedback,
    RAGContextBundle,
    ResearchReport,
)


class PipelineState(TypedDict, total=False):
    session_id: str
    user_brief: str
    target_category: str | None
    research_report: ResearchReport
    rag_contexts: list[RAGContextBundle]
    feasibility_report: FeasibilityReport
    human_feedback: HumanFeedback | None
    approved_concepts: list[ConceptCandidate]
    final_product_plan: str
    iteration: int
