"""Regression tests for PM market-research framework integration."""

from cqr_product_pipeline.agents.deep_research import _dry_run_report
from cqr_product_pipeline.agents.feasibility import _score_concept_heuristic
from cqr_product_pipeline.agents.product_planning import run_product_planning
from cqr_product_pipeline.cli.hitl_summary import format_feasibility_review_md
from cqr_product_pipeline.cli.research_report_md import format_research_report_md
from cqr_product_pipeline.config.settings import Settings
from cqr_product_pipeline.schemas.models import (
    ConceptCandidate,
    EvidenceBlock,
    FeasibilityReport,
    MarketSizing,
    RAGContextBundle,
    ResearchReport,
)


def _research_with_sizing() -> ResearchReport:
    return ResearchReport(
        market_gaps=["Short-inseam waterproof ski pants at a mid-market price"],
        market_sizing=MarketSizing(
            market_definition="US women's ski pants, annual retail revenue",
            tam="$1.0B",
            sam="$250M",
            som="$2.5M",
            top_down_method="Industry total narrowed by category",
            bottom_up_method="Buyers × units × ASP",
            assumptions=["USD", "US", "annual"],
            confidence="low",
        ),
    )


def test_feasibility_review_carries_market_sizing():
    md = format_feasibility_review_md(
        session_id="sizing1",
        research_report=_research_with_sizing(),
        feasibility_report=FeasibilityReport(),
    )
    assert "시장 규모 검증" in m d
    assert "TAM: $1.0B" in md
    assert "Bottom-up 교차검증" in md
    assert "신뢰도: low" in md


def test_product_plan_carries_market_sizing():
    plan = run_product_planning(
        [
            ConceptCandidate(
                concept_id="A",
                name="Short-inseam ski pant",
                garment_type="ski pant",
                target_tpo="resort skiing",
            )
        ],
        research_report=_research_with_sizing(),
        dry_run=True,
    )
    assert "Market Opportunity — TAM / SAM / SOM" in plan
    assert "TAM: $1.0B" in plan
    assert "Bottom-up: Buyers × units × ASP" in plan


def test_dry_research_populates_p0_to_p2_pm_frameworks():
    report = _dry_run_report("2027 가을겨울 스키바지 시장조사", None)

    assert len(report.personas) >= 2
    assert all(p.job_to_be_done and p.pains and p.gains for p in report.personas)
    assert len(report.market_segments) >= 3
    assert report.pricing_strategy.target_price_band
    assert report.pricing_strategy.experiment
    assert len(report.competitive_battlecards) >= 3
    assert len(report.job_stories) >= 3
    assert report.customer_journeys
    assert len(report.customer_journeys[0].stages) >= 4


def test_research_markdown_exposes_p0_to_p2_sections():
    md = format_research_report_md(
        _dry_run_report("2027 가을겨울 스키바지 시장조사", None),
        session_id="pm1",
    )

    for heading in (
        "핵심 페르소나",
        "시장·사용자 세그먼트",
        "가격 전략",
        "경쟁 배틀카드",
        "Job Stories",
        "고객 여정",
    ):
        assert heading in md


def test_heuristic_feasibility_adds_priority_and_pre_mortem():
    concept = ConceptCandidate(
        concept_id="A",
        name="Resort shell ski pant",
        garment_type="ski pants",
        target_tpo="2027 FW resort",
    )
    bundle = RAGContextBundle(
        concept_id="A",
        query="ski pant",
        blocks=[
            EvidenceBlock(
                source_path="internal",
                excerpt="PRODUCT_DEV_SPEC requires field validation",
                relevance=0.9,
                collection="product_spec",
            )
        ],
    )
    result = _score_concept_heuristic(concept, bundle, Settings())

    assert result.priority.reach is None
    assert result.priority.rice_score is None
    assert "잠금" in (result.priority.rationale or "")
    assert len(result.pre_mortem) >= 2
    assert all(r.early_warning and r.mitigation for r in result.pre_mortem)


def test_product_plan_is_prd_and_carries_p0_to_p2_inputs():
    report = _dry_run_report("2027 가을겨울 스키바지 시장조사", None)
    concept = report.concepts[0]
    feasibility = FeasibilityReport(
        concepts=[
            _score_concept_heuristic(
                concept,
                RAGContextBundle(concept_id=concept.concept_id, query="ski", blocks=[]),
                Settings(),
            )
        ]
    )

    plan = run_product_planning(
        [concept],
        research_report=report,
        feasibility_report=feasibility,
        dry_run=True,
    )

    for section in (
        "문제 / 기회와 근거",
        "목표 · 성공 지표",
        "타깃 세그먼트 · 페르소나 · JTBD",
        "Job Stories",
        "범위 · 비범위 · 요구사항",
        "가격 전략 · GTM",
        "Pre-mortem",
        "검증 계획",
    ):
        assert section in plan
    assert "Score=잠금 안 함" in plan
