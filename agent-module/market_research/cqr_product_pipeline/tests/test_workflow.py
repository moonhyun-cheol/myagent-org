"""Workflow graph tests (dry-run, no LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from cqr_product_pipeline.graph.workflow import compile_pipeline_graph
from cqr_product_pipeline.rag.ingest import ingest_corpus
from cqr_product_pipeline.schemas.models import (
    HumanFeedback,
    HumanFeedbackDecision,
    ResearchReport,
)


@pytest.fixture(scope="module")
def indexed_chroma(tmp_path_factory):
    chroma_path = tmp_path_factory.mktemp("chroma")
    counts = ingest_corpus(chroma_path=chroma_path, rebuild=True)
    assert sum(counts.values()) > 0
    return chroma_path


@pytest.fixture(autouse=True)
def _use_test_chroma(indexed_chroma, monkeypatch):
    from cqr_product_pipeline.config.settings import get_settings

    monkeypatch.setenv("CHROMA_PATH", str(indexed_chroma))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_pipeline_interrupts_at_hitl(indexed_chroma, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(indexed_chroma))
    graph = compile_pipeline_graph(dry_run=True, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-hitl-1"}}

    result = graph.invoke(
        {
            "session_id": "test-hitl-1",
            "user_brief": "Liberator summer lightweight cargo gap",
            "iteration": 0,
        },
        config=config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.next
    assert "human_review" in snapshot.next or snapshot.interrupts
    assert snapshot.values.get("research_report") is not None
    assert snapshot.values.get("feasibility_report") is not None
    assert not snapshot.values.get("final_product_plan")
    assert result is not None or snapshot.values


def test_pipeline_resume_to_product_plan(indexed_chroma, monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PATH", str(indexed_chroma))
    graph = compile_pipeline_graph(dry_run=True, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-resume-1"}}

    graph.invoke(
        {
            "session_id": "test-resume-1",
            "user_brief": "Liberator summer lightweight cargo gap",
            "iteration": 0,
        },
        config=config,
    )

    feedback = HumanFeedback(
        decisions=[
            HumanFeedbackDecision(
                concept_id="A",
                action="approve",
                notes="Approve lightweight summer cargo sibling",
            )
        ],
        override_notes="Position below TLP125",
    )

    graph.invoke(
        Command(resume=feedback.model_dump()),
        config=config,
    )

    snapshot = graph.get_state(config)
    plan = snapshot.values.get("final_product_plan")
    assert plan
    assert "제품 기획서" in plan
    assert snapshot.next == ()


def test_route_revise_loops_feasibility(indexed_chroma, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(indexed_chroma))
    graph = compile_pipeline_graph(dry_run=True, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-revise-1"}}

    graph.invoke(
        {
            "session_id": "test-revise-1",
            "user_brief": "Liberator summer cargo",
            "iteration": 0,
        },
        config=config,
    )

    feedback = HumanFeedback(
        decisions=[
            HumanFeedbackDecision(
                concept_id="A",
                action="revise",
                notes="Reduce to 5 pockets and verify L-tier fabric",
            )
        ]
    )

    graph.invoke(
        Command(resume=feedback.model_dump()),
        config=config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.values.get("feasibility_report") is not None
    report = snapshot.values["research_report"]
    if not isinstance(report, ResearchReport):
        report = ResearchReport.model_validate(report)
    concept_a = next(c for c in report.concepts if c.concept_id == "A")
    assert "revise" in (concept_a.usp_hypothesis or "").lower()
    assert snapshot.next
    assert "human_review" in snapshot.next
