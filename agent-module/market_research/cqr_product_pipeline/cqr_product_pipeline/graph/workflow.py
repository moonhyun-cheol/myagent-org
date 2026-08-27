"""LangGraph workflow — Deep Research → Feasibility → HITL → Product Planning."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from cqr_product_pipeline.agents.deep_research import (
    ensure_concept_ids,
    merge_research_request,
    run_deep_research,
)
from cqr_product_pipeline.agents.feasibility import (
    apply_revise_feedback,
    resolve_approved_concepts,
    run_feasibility,
)
from cqr_product_pipeline.agents.product_planning import run_product_planning
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.schemas.models import HumanFeedback, ResearchReport
from cqr_product_pipeline.schemas.state import PipelineState

Route = Literal["deep_research", "feasibility", "product_planning", "__end__"]


def _as_research_report(value) -> ResearchReport:
    if isinstance(value, ResearchReport):
        return value
    return ResearchReport.model_validate(value)


def _as_human_feedback(value) -> HumanFeedback | None:
    if value is None:
        return None
    return parse_human_feedback(value)


def build_pipeline_graph(
    *,
    settings: Settings | None = None,
    dry_run: bool = False,
) -> StateGraph:
    settings = settings or get_settings()
    graph: StateGraph = StateGraph(PipelineState)

    def deep_research_node(state: PipelineState) -> dict:
        iteration = state.get("iteration", 0)
        feedback = _as_human_feedback(state.get("human_feedback"))
        extra_note = feedback.request_research if feedback else None
        if extra_note:
            iteration += 1

        report = run_deep_research(
            state["user_brief"],
            target_category=state.get("target_category"),
            settings=settings,
            dry_run=dry_run,
            extra_research_note=extra_note,
        )
        report = ensure_concept_ids(report)
        if extra_note and state.get("research_report"):
            report = merge_research_request(report, extra_note)

        return {
            "research_report": report,
            "iteration": iteration,
            "human_feedback": None,
            "approved_concepts": [],
            "final_product_plan": "",
        }

    def feasibility_node(state: PipelineState) -> dict:
        report = _as_research_report(state["research_report"])
        feedback = _as_human_feedback(state.get("human_feedback"))
        if feedback:
            report = apply_revise_feedback(report, feedback)

        feasibility_report, rag_contexts = run_feasibility(
            report,
            settings=settings,
            use_llm=not dry_run,
        )
        return {
            "research_report": report,
            "feasibility_report": feasibility_report,
            "rag_contexts": rag_contexts,
            "human_feedback": None,
        }

    def human_review_node(state: PipelineState) -> dict:
        if state.get("human_feedback"):
            feedback = _as_human_feedback(state["human_feedback"])
        else:
            feedback_raw = interrupt(
                {
                    "session_id": state.get("session_id"),
                    "message": "Feasibility review required — submit HumanFeedback to resume",
                    "feasibility_report": state.get("feasibility_report"),
                    "research_report": state.get("research_report"),
                }
            )
            feedback = parse_human_feedback(feedback_raw)

        approved = resolve_approved_concepts(
            _as_research_report(state["research_report"]),
            feedback,
        )
        return {"human_feedback": feedback, "approved_concepts": approved}

    def product_planning_node(state: PipelineState) -> dict:
        plan = run_product_planning(
            state.get("approved_concepts") or [],
            research_report=state.get("research_report"),
            feasibility_report=state.get("feasibility_report"),
            human_feedback=state.get("human_feedback"),
            settings=settings,
            dry_run=dry_run,
        )
        return {"final_product_plan": plan}

    graph.add_node("deep_research", deep_research_node)
    graph.add_node("feasibility", feasibility_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("product_planning", product_planning_node)

    graph.set_entry_point("deep_research")
    graph.add_edge("deep_research", "feasibility")
    graph.add_edge("feasibility", "human_review")
    graph.add_conditional_edges("human_review", _route_after_human, {
        "deep_research": "deep_research",
        "feasibility": "feasibility",
        "product_planning": "product_planning",
        "__end__": END,
    })
    graph.add_edge("product_planning", END)

    return graph


def _route_after_human(state: PipelineState) -> Route:
    settings = get_settings()
    feedback = _as_human_feedback(state.get("human_feedback"))
    iteration = state.get("iteration", 0)

    if feedback and feedback.request_research and iteration < settings.hitl_max_iterations:
        return "deep_research"

    if feedback and any(d.action == "revise" for d in feedback.decisions):
        return "feasibility"

    if state.get("approved_concepts"):
        return "product_planning"

    return "__end__"


def compile_pipeline_graph(
    *,
    settings: Settings | None = None,
    dry_run: bool = False,
    checkpointer=None,
):
    settings = settings or get_settings()
    graph = build_pipeline_graph(settings=settings, dry_run=dry_run)

    if checkpointer is not None:
        saver = checkpointer
    else:
        import sqlite3

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from langgraph.checkpoint.sqlite import SqliteSaver

        settings.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(settings.checkpoint_path), check_same_thread=False)
        serde = JsonPlusSerializer(
            allowed_msgpack_modules=[
                ("cqr_product_pipeline.schemas.models", "CompetitiveBattlecard"),
                ("cqr_product_pipeline.schemas.models", "ConceptCandidate"),
                ("cqr_product_pipeline.schemas.models", "CustomerJourney"),
                ("cqr_product_pipeline.schemas.models", "EvidenceBlock"),
                ("cqr_product_pipeline.schemas.models", "FeasibilityConceptResult"),
                ("cqr_product_pipeline.schemas.models", "FeasibilityLLMScores"),
                ("cqr_product_pipeline.schemas.models", "FeasibilityReport"),
                ("cqr_product_pipeline.schemas.models", "HumanFeedback"),
                ("cqr_product_pipeline.schemas.models", "HumanFeedbackDecision"),
                ("cqr_product_pipeline.schemas.models", "JobStory"),
                ("cqr_product_pipeline.schemas.models", "JourneyStage"),
                ("cqr_product_pipeline.schemas.models", "MarketSegmentProfile"),
                ("cqr_product_pipeline.schemas.models", "MarketSizing"),
                ("cqr_product_pipeline.schemas.models", "PersonaProfile"),
                ("cqr_product_pipeline.schemas.models", "PreMortemRisk"),
                ("cqr_product_pipeline.schemas.models", "PricingStrategy"),
                ("cqr_product_pipeline.schemas.models", "PriorityAssessment"),
                ("cqr_product_pipeline.schemas.models", "QuantSignals"),
                ("cqr_product_pipeline.schemas.models", "RAGContextBundle"),
                ("cqr_product_pipeline.schemas.models", "ResearchReport"),
                ("cqr_product_pipeline.schemas.models", "SourceRef"),
                ("cqr_product_pipeline.schemas.models", "Verdict"),
            ]
        )
        saver = SqliteSaver(conn, serde=serde)

    return graph.compile(checkpointer=saver)


def parse_human_feedback(payload: dict | HumanFeedback) -> HumanFeedback:
    if isinstance(payload, HumanFeedback):
        return payload
    return HumanFeedback.model_validate(payload)
