from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    GO = "GO"
    HOLD = "HOLD"
    KILL = "KILL"


class SourceRef(BaseModel):
    url: str
    title: str | None = None
    source_type: Literal[
        "competitor_listing",
        "review_aggregate",
        "industry_report",
        "forum",
        "other",
    ] = "other"


class ConceptCandidate(BaseModel):
    concept_id: str
    name: str
    line_recommendation: str | None = None
    garment_type: str | None = None
    target_tpo: str | None = None
    usp_hypothesis: str | None = None
    keywords: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class QuantSignals(BaseModel):
    pain_theme_frequencies: dict[str, float] = Field(default_factory=dict)
    price_band_notes: str | None = None
    review_rating_notes: str | None = None


class MarketSizing(BaseModel):
    """Evidence-backed TAM/SAM/SOM triangulation for the scoped apparel market."""

    market_definition: str | None = None
    tam: str | None = None
    sam: str | None = None
    som: str | None = None
    top_down_method: str | None = None
    bottom_up_method: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "insufficient_evidence"] = "insufficient_evidence"


class PersonaProfile(BaseModel):
    """Research-backed target persona, not a fictional demographic profile."""

    persona_id: str
    name: str
    segment: str
    context: str
    job_to_be_done: str
    pains: list[str] = Field(default_factory=list)
    gains: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)
    unexpected_insight: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class MarketSegmentProfile(BaseModel):
    segment_id: str
    name: str
    size_signal: str | None = None
    defining_need: str
    behavior_and_tpo: str
    willingness_to_pay: str | None = None
    competitive_intensity: Literal["high", "medium", "low", "unknown"] = "unknown"
    priority: Literal["invest", "maintain", "deprioritize", "validate"] = "validate"
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class PricingStrategy(BaseModel):
    value_metric: str | None = None
    target_price_band: str | None = None
    recommended_price: str | None = None
    competitor_benchmarks: list[str] = Field(default_factory=list)
    pricing_gap: str | None = None
    rationale: str | None = None
    experiment: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "insufficient_evidence"] = "insufficient_evidence"


class CompetitiveBattlecard(BaseModel):
    competitor: str
    target_customer: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    our_advantages: list[str] = Field(default_factory=list)
    objection: str | None = None
    response: str | None = None
    avoid_claims: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class JobStory(BaseModel):
    when: str
    want: str
    so_that: str
    evidence_refs: list[str] = Field(default_factory=list)


class JourneyStage(BaseModel):
    stage: str
    goal: str
    actions: list[str] = Field(default_factory=list)
    touchpoints: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    emotion: str | None = None
    opportunities: list[str] = Field(default_factory=list)


class CustomerJourney(BaseModel):
    persona_id: str
    journey_name: str
    stages: list[JourneyStage] = Field(default_factory=list)
    priority_improvements: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    market_gaps: list[str] = Field(default_factory=list)
    competitor_moves: list[str] = Field(default_factory=list)
    consumer_pain_points: list[str] = Field(default_factory=list)
    quant_signals: QuantSignals = Field(default_factory=QuantSignals)
    market_sizing: MarketSizing = Field(default_factory=MarketSizing)
    personas: list[PersonaProfile] = Field(default_factory=list)
    market_segments: list[MarketSegmentProfile] = Field(default_factory=list)
    pricing_strategy: PricingStrategy = Field(default_factory=PricingStrategy)
    competitive_battlecards: list[CompetitiveBattlecard] = Field(default_factory=list)
    job_stories: list[JobStory] = Field(default_factory=list)
    customer_journeys: list[CustomerJourney] = Field(default_factory=list)
    qual_themes: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    concepts: list[ConceptCandidate] = Field(default_factory=list)


class EvidenceBlock(BaseModel):
    source_path: str
    excerpt: str
    relevance: float = 0.0
    collection: str


class RAGContextBundle(BaseModel):
    concept_id: str
    query: str
    blocks: list[EvidenceBlock] = Field(default_factory=list)


class PriorityAssessment(BaseModel):
    """RICE-style opportunity score. Unknown values must remain explicit."""

    reach: float | None = Field(default=None, ge=0)
    impact: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    effort: float | None = Field(default=None, gt=0)
    rice_score: float | None = Field(default=None, ge=0)
    rank: int | None = Field(default=None, ge=1)
    rationale: str | None = None


class PreMortemRisk(BaseModel):
    failure_scenario: str
    cause: str
    likelihood: Literal["high", "medium", "low", "unknown"] = "unknown"
    impact: Literal["high", "medium", "low", "unknown"] = "unknown"
    early_warning: str | None = None
    mitigation: str
    owner: str | None = None


class FeasibilityConceptResult(BaseModel):
    concept_id: str
    name: str
    brand_alignment_score: int = Field(ge=0, le=100)
    manufacturing_score: int = Field(ge=0, le=100)
    cannibalization_score: int = Field(ge=0, le=100)
    overall_risk: int = Field(ge=0, le=100)
    verdict: Verdict
    evidence: list[EvidenceBlock] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommended_line: str | None = None
    priority: PriorityAssessment = Field(default_factory=PriorityAssessment)
    pre_mortem: list[PreMortemRisk] = Field(default_factory=list)
    summary: str | None = None


class FeasibilityLLMScores(BaseModel):
    """Structured LLM output for a single concept feasibility assessment."""

    brand_alignment_score: int = Field(ge=0, le=100, description="Risk 0-100, higher=worse")
    manufacturing_score: int = Field(ge=0, le=100)
    cannibalization_score: int = Field(ge=0, le=100)
    blockers: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommended_line: str | None = None
    priority: PriorityAssessment = Field(default_factory=PriorityAssessment)
    pre_mortem: list[PreMortemRisk] = Field(default_factory=list)
    summary: str = Field(description="2-4 sentence rationale citing evidence themes only")


class FeasibilityReport(BaseModel):
    concepts: list[FeasibilityConceptResult] = Field(default_factory=list)
    session_notes: str | None = None


class HumanFeedbackDecision(BaseModel):
    concept_id: str
    action: Literal["approve", "reject", "revise"]
    override_verdict: Verdict | None = None
    notes: str | None = None


class HumanFeedback(BaseModel):
    decisions: list[HumanFeedbackDecision] = Field(default_factory=list)
    override_notes: str | None = None
    request_research: str | None = None
