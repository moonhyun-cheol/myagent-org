"""Feasibility agent — RAG retrieval + LLM or heuristic scoring."""

from __future__ import annotations

import logging
import re

from cqr_product_pipeline.config.providers import get_chat_model
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.prompts.feasibility import FEASIBILITY_SYSTEM, format_evidence_blocks
from cqr_product_pipeline.prompts.language import with_language
from cqr_product_pipeline.rag.retriever import CQRKnowledgeRetriever, retrieve_for_feasibility
from cqr_product_pipeline.schemas.models import (
    ConceptCandidate,
    FeasibilityConceptResult,
    FeasibilityLLMScores,
    FeasibilityReport,
    HumanFeedback,
    PreMortemRisk,
    PriorityAssessment,
    RAGContextBundle,
    ResearchReport,
    Verdict,
)
from cqr_product_pipeline.utils.llm import invoke_structured

logger = logging.getLogger(__name__)


def _clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def _compute_risk_and_verdict(
    brand: int,
    manufacturing: int,
    cannibalization: int,
    settings: Settings,
) -> tuple[int, Verdict]:
    brand = _clamp_score(brand)
    manufacturing = _clamp_score(manufacturing)
    cannibalization = _clamp_score(cannibalization)
    overall = int(
        brand * settings.brand_weight
        + manufacturing * settings.manufacturing_weight
        + cannibalization * settings.cannibalization_weight
    )
    overall = _clamp_score(overall)
    if overall > 70:
        verdict = Verdict.KILL
    elif overall >= 40:
        verdict = Verdict.HOLD
    else:
        verdict = Verdict.GO
    return overall, verdict


def _keyword_risk(text: str, patterns: list[str], *, base: int = 35, step: int = 12) -> int:
    score = base
    lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, lower):
            score += step
    return min(score, 100)


def _score_concept_heuristic(
    concept: ConceptCandidate,
    bundle: RAGContextBundle,
    settings: Settings,
) -> FeasibilityConceptResult:
    evidence_text = "\n".join(b.excerpt for b in bundle.blocks)
    combined = f"{concept.name} {concept.usp_hypothesis or ''} {evidence_text}"

    brand = _keyword_risk(
        combined,
        [r"covert", r"sub rosa", r"purpose above all", r"mission persona", r"quiet authority"],
        base=25,
    )
    manufacturing = _keyword_risk(
        combined,
        [r"gusset", r"pocket", r"heat", r"ripstop", r"fabric tier", r"do not", r"확인 필요"],
        base=30,
    )
    cannibal = _keyword_risk(
        combined,
        [r"tlp125", r"tlp\d+", r"flex tactical", r"brand_index", r"hero color", r"avoid"],
        base=28,
    )

    overall, verdict = _compute_risk_and_verdict(brand, manufacturing, cannibal, settings)

    blockers: list[str] = []
    if manufacturing >= 55:
        blockers.append("PRODUCT_DEV_SPEC 기준으로 포켓 구성·원단 등급 발열 리스크 확인 필요")
    if cannibal >= 50:
        blockers.append("출시 포지셔닝 전 BRAND_INDEX의 라이브 SKU 중복 확인 필요")

    collections_hit = {b.collection for b in bundle.blocks}
    data_gaps: list[str] = []
    for required in ("brand", "product_spec", "catalog"):
        if required not in collections_hit:
            data_gaps.append(f"{required} 근거 없음 — 재인제스트 또는 쿼리 확대 필요")

    evidence_confidence = min(0.8, round(len(bundle.blocks) / 12, 2))
    priority = PriorityAssessment(
        reach=None,
        impact=2.0,
        confidence=evidence_confidence,
        effort=max(1.0, round(manufacturing / 25, 1)),
        rice_score=None,
        rationale=(
            "도달 규모(reach) 근거가 없어 RICE 점수는 잠금하지 않음. "
            "시장 세그먼트 규모와 예상 판매량을 확인한 뒤 산출 필요."
        ),
    )
    pre_mortem = [
        PreMortemRisk(
            failure_scenario="샘플이 핵심 TPO의 착용·보호 성능을 충족하지 못함",
            cause="원단·패턴·기능 사양을 실제 사용 조건으로 검증하지 않음",
            likelihood="medium",
            impact="high",
            early_warning="1차 샘플 필드 테스트에서 반복되는 핏·통기·보호 불만",
            mitigation="1차 샘플 전에 TPO별 합격 기준을 잠그고 착용 테스트를 수행",
            owner="Product / QA",
        ),
        PreMortemRisk(
            failure_scenario="기존 SKU와 차별성이 약해 자기잠식 또는 전환 저조 발생",
            cause="가격·기능·핏의 비교 근거 없이 유사 포지션으로 출시",
            likelihood="medium" if cannibal >= 40 else "low",
            impact="high",
            early_warning="상세페이지 비교에서 차별점 회상률과 구매의향이 낮음",
            mitigation="라이브 SKU 대비 delta 표와 구매 전환 가설을 사전 검증",
            owner="PM / Merchandising",
        ),
    ]

    return FeasibilityConceptResult(
        concept_id=concept.concept_id,
        name=concept.name,
        brand_alignment_score=brand,
        manufacturing_score=manufacturing,
        cannibalization_score=cannibal,
        overall_risk=overall,
        verdict=verdict,
        evidence=bundle.blocks,
        blockers=blockers,
        data_gaps=data_gaps,
        recommended_line=concept.line_recommendation,
        priority=priority,
        pre_mortem=pre_mortem,
        summary=(
            f"휴리스틱 타당성 ({concept.name}): "
            f"브랜드={brand}, 생산={manufacturing}, 자기잠식={cannibal}, 판정={verdict.value}"
        ),
    )


def build_feasibility_prompt(
    concept: ConceptCandidate,
    bundle: RAGContextBundle,
) -> str:
    return (
        f"Evaluate this concept for CQR internal feasibility.\n\n"
        f"## Concept\n"
        f"concept_id: {concept.concept_id}\n"
        f"name: {concept.name}\n"
        f"line: {concept.line_recommendation}\n"
        f"garment: {concept.garment_type}\n"
        f"tpo: {concept.target_tpo}\n"
        f"usp: {concept.usp_hypothesis}\n\n"
        f"{format_evidence_blocks(bundle.blocks)}\n\n"
        "Return JSON with brand_alignment_score, manufacturing_score, "
        "cannibalization_score, blockers, data_gaps, recommended_line, summary, "
        "priority (RICE: reach/impact/confidence/effort/rice_score/rationale), and "
        "pre_mortem (3-5 failure scenarios with cause, likelihood, impact, early warning, mitigation, owner). "
        "If reach evidence is absent, leave reach/rice_score null rather than inventing it. "
        "Do not invent evidence beyond [INTERNAL_EVIDENCE]."
    )


def _score_concept_llm(
    concept: ConceptCandidate,
    bundle: RAGContextBundle,
    settings: Settings,
) -> FeasibilityConceptResult:
    llm = get_chat_model(settings)
    user = build_feasibility_prompt(concept, bundle)
    scores = invoke_structured(
        llm,
        with_language(FEASIBILITY_SYSTEM, settings.report_language),
        user,
        FeasibilityLLMScores,
    )

    brand = _clamp_score(scores.brand_alignment_score)
    manufacturing = _clamp_score(scores.manufacturing_score)
    cannibal = _clamp_score(scores.cannibalization_score)
    overall, verdict = _compute_risk_and_verdict(brand, manufacturing, cannibal, settings)

    blockers = list(scores.blockers)
    data_gaps = list(scores.data_gaps)
    for required in ("brand", "product_spec", "catalog"):
        if required not in {b.collection for b in bundle.blocks}:
            gap = f"Missing {required} evidence — re-ingest or broaden query"
            if gap not in data_gaps:
                data_gaps.append(gap)

    return FeasibilityConceptResult(
        concept_id=concept.concept_id,
        name=concept.name,
        brand_alignment_score=brand,
        manufacturing_score=manufacturing,
        cannibalization_score=cannibal,
        overall_risk=overall,
        verdict=verdict,
        evidence=bundle.blocks,
        blockers=blockers,
        data_gaps=data_gaps,
        recommended_line=scores.recommended_line or concept.line_recommendation,
        priority=scores.priority,
        pre_mortem=scores.pre_mortem,
        summary=scores.summary,
    )


def _score_concept(
    concept: ConceptCandidate,
    bundle: RAGContextBundle,
    settings: Settings,
    *,
    use_llm: bool,
) -> FeasibilityConceptResult:
    if not use_llm:
        return _score_concept_heuristic(concept, bundle, settings)
    try:
        return _score_concept_llm(concept, bundle, settings)
    except Exception as exc:
        if not settings.llm_fallback_heuristic:
            raise
        logger.warning(
            "LLM feasibility failed for %s (%s), falling back to heuristic",
            concept.concept_id,
            exc,
        )
        return _score_concept_heuristic(concept, bundle, settings)


def run_feasibility(
    research_report: ResearchReport,
    *,
    retriever: CQRKnowledgeRetriever | None = None,
    settings: Settings | None = None,
    use_llm: bool | None = None,
) -> tuple[FeasibilityReport, list[RAGContextBundle]]:
    settings = settings or get_settings()
    retriever = retriever or CQRKnowledgeRetriever(settings=settings)
    llm_enabled = settings.use_llm_scoring if use_llm is None else use_llm

    concepts = research_report.concepts
    if not concepts:
        raise ValueError("ResearchReport has no concepts to evaluate")

    bundles: list[RAGContextBundle] = []
    results: list[FeasibilityConceptResult] = []

    for concept in concepts:
        bundle = retrieve_for_feasibility(
            concept,
            retriever=retriever,
            k_per_collection=settings.k_per_collection,
        )
        bundles.append(bundle)
        results.append(_score_concept(concept, bundle, settings, use_llm=llm_enabled))

    mode = "llm" if llm_enabled else "heuristic"
    return FeasibilityReport(concepts=results, session_notes=f"scoring_mode={mode}"), bundles


def apply_revise_feedback(
    research_report: ResearchReport,
    feedback: HumanFeedback,
) -> ResearchReport:
    """Merge human revise notes into concept hypotheses before re-feasibility."""
    revise_map = {
        d.concept_id: d.notes
        for d in feedback.decisions
        if d.action == "revise" and d.notes
    }
    if not revise_map:
        return research_report

    updated: list[ConceptCandidate] = []
    for concept in research_report.concepts:
        note = revise_map.get(concept.concept_id)
        if note:
            merged = concept.model_copy(
                update={
                    "usp_hypothesis": f"{concept.usp_hypothesis or concept.name}; revise: {note}",
                    "keywords": list(dict.fromkeys([*concept.keywords, *note.split()])),
                }
            )
            updated.append(merged)
        else:
            updated.append(concept)
    return research_report.model_copy(update={"concepts": updated})


def resolve_approved_concepts(
    research_report: ResearchReport,
    feedback: HumanFeedback,
) -> list[ConceptCandidate]:
    approved_ids = {d.concept_id for d in feedback.decisions if d.action == "approve"}
    return [c for c in research_report.concepts if c.concept_id in approved_ids]
