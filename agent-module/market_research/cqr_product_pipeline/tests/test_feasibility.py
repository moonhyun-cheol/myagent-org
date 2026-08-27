"""Feasibility scoring unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cqr_product_pipeline.agents.feasibility import (
    _compute_risk_and_verdict,
    _score_concept,
    run_feasibility,
)
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.rag.ingest import ingest_corpus
from cqr_product_pipeline.schemas.models import (
    ConceptCandidate,
    FeasibilityLLMScores,
    RAGContextBundle,
    ResearchReport,
    Verdict,
)


@pytest.fixture(scope="module")
def indexed_chroma(tmp_path_factory):
    chroma_path = tmp_path_factory.mktemp("chroma-feas")
    counts = ingest_corpus(chroma_path=chroma_path, rebuild=True)
    assert sum(counts.values()) > 0
    return chroma_path


@pytest.fixture(autouse=True)
def _use_test_chroma(indexed_chroma, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(indexed_chroma))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_verdict_thresholds():
    settings = Settings()
    _, go = _compute_risk_and_verdict(20, 20, 20, settings)
    assert go == Verdict.GO

    _, hold = _compute_risk_and_verdict(50, 50, 50, settings)
    assert hold == Verdict.HOLD

    _, kill = _compute_risk_and_verdict(90, 90, 90, settings)
    assert kill == Verdict.KILL


def test_heuristic_feasibility_run(indexed_chroma):
    report = ResearchReport(
        concepts=[
            ConceptCandidate(
                concept_id="A",
                name="Liberator summer cargo",
                line_recommendation="Liberator",
                usp_hypothesis="Lightweight 6-pocket cargo for hot weather",
            )
        ]
    )
    feasibility, bundles = run_feasibility(report, use_llm=False)
    assert len(feasibility.concepts) == 1
    assert feasibility.concepts[0].concept_id == "A"
    assert feasibility.session_notes == "scoring_mode=heuristic"
    assert len(bundles) == 1


@patch("cqr_product_pipeline.agents.feasibility.invoke_structured")
@patch("cqr_product_pipeline.agents.feasibility.get_chat_model")
def test_llm_scoring_path(mock_get_chat, mock_invoke, indexed_chroma):
    mock_get_chat.return_value = MagicMock()
    mock_invoke.return_value = FeasibilityLLMScores(
        brand_alignment_score=25,
        manufacturing_score=35,
        cannibalization_score=30,
        blockers=["Check TLP125 overlap"],
        data_gaps=[],
        recommended_line="Liberator",
        summary="LLM assessed concept as moderate risk with line fit.",
    )

    concept = ConceptCandidate(concept_id="A", name="Test concept")
    bundle = RAGContextBundle(concept_id="A", query="test", blocks=[])
    settings = Settings(use_llm_scoring=True, llm_fallback_heuristic=True)

    result = _score_concept(concept, bundle, settings, use_llm=True)
    assert result.summary.startswith("LLM assessed")
    assert result.brand_alignment_score == 25
    assert result.verdict in (Verdict.GO, Verdict.HOLD, Verdict.KILL)
    mock_invoke.assert_called_once()


@patch("cqr_product_pipeline.agents.feasibility.invoke_structured")
@patch("cqr_product_pipeline.agents.feasibility.get_chat_model")
def test_llm_fallback_on_failure(mock_get_chat, mock_invoke, indexed_chroma):
    mock_get_chat.return_value = MagicMock()
    mock_invoke.side_effect = RuntimeError("ollama unreachable")

    concept = ConceptCandidate(concept_id="A", name="Fallback concept")
    bundle = RAGContextBundle(concept_id="A", query="test", blocks=[])
    settings = Settings(llm_fallback_heuristic=True)

    result = _score_concept(concept, bundle, settings, use_llm=True)
    assert "휴리스틱 타당성" in (result.summary or "")
