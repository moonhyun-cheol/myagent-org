"""Product Planning agent — final CQR product plan markdown."""

from __future__ import annotations

from cqr_product_pipeline.config.providers import get_chat_model
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.prompts.language import with_language
from cqr_product_pipeline.prompts.product_planning import PRODUCT_PLANNING_SYSTEM
from cqr_product_pipeline.schemas.models import (
    ConceptCandidate,
    FeasibilityReport,
    HumanFeedback,
    ResearchReport,
)
from cqr_product_pipeline.utils.llm import invoke_structured
from pydantic import BaseModel, Field


class ProductPlanDraft(BaseModel):
    markdown: str = Field(description="Full product plan in markdown")


def _dry_run_plan(
    concept: ConceptCandidate,
    *,
    research_report: ResearchReport | None,
    feasibility_report: FeasibilityReport | None,
    human_feedback: HumanFeedback | None,
) -> str:
    line = concept.line_recommendation or "TBD"
    garment = concept.garment_type or "garment"
    usp = concept.usp_hypothesis or concept.name
    model_code = "TLP131 (suggested)"

    fb_log = ""
    if human_feedback and human_feedback.override_notes:
        fb_log = human_feedback.override_notes

    gaps = ""
    if research_report and research_report.market_gaps:
        gaps = research_report.market_gaps[0]

    sizing = research_report.market_sizing if research_report else None
    market_opportunity = (
        f"TAM: {sizing.tam or '확인 필요'} | SAM: {sizing.sam or '확인 필요'} | "
        f"SOM (1–3년): {sizing.som or '확인 필요'} | 신뢰도: {sizing.confidence}"
        if sizing
        else "TAM/SAM/SOM: 확인 필요 | 신뢰도: insufficient_evidence"
    )

    verdict = "HOLD"
    selected_feasibility = None
    if feasibility_report:
        for row in feasibility_report.concepts:
            if row.concept_id == concept.concept_id:
                verdict = row.verdict.value
                selected_feasibility = row
                break

    persona = research_report.personas[0] if research_report and research_report.personas else None
    segment = (
        next((s for s in research_report.market_segments if s.priority == "invest"), None)
        if research_report
        else None
    )
    if not segment and research_report and research_report.market_segments:
        segment = research_report.market_segments[0]
    pricing = research_report.pricing_strategy if research_report else None
    job_stories = research_report.job_stories if research_report else []
    journeys = research_report.customer_journeys if research_report else []
    journey_improvements = journeys[0].priority_improvements if journeys else []
    pre_mortem = selected_feasibility.pre_mortem if selected_feasibility else []
    priority = selected_feasibility.priority if selected_feasibility else None

    persona_text = (
        f"{persona.name} ({persona.segment}) — {persona.context}; JTBD: {persona.job_to_be_done}"
        if persona
        else "확인 필요 — 리서치 페르소나를 먼저 생성"
    )
    segment_text = (
        f"{segment.name}: {segment.defining_need}; {segment.behavior_and_tpo}; 우선순위={segment.priority}"
        if segment
        else "확인 필요"
    )
    job_story_text = "\n".join(
        f"- When {story.when}, I want {story.want}, so that {story.so_that}."
        for story in job_stories[:3]
    ) or "- 확인 필요"
    risk_text = "\n".join(
        f"- [{risk.likelihood}/{risk.impact}] {risk.failure_scenario} — "
        f"조기 신호: {risk.early_warning or '확인 필요'}; 대응: {risk.mitigation}; "
        f"담당: {risk.owner or '확인 필요'}"
        for risk in pre_mortem
    ) or "- 확인 필요 — 타당성 단계에서 pre-mortem 수행"
    rice_text = (
        f"Reach={priority.reach if priority and priority.reach is not None else '확인 필요'}, "
        f"Impact={priority.impact if priority and priority.impact is not None else '확인 필요'}, "
        f"Confidence={priority.confidence if priority and priority.confidence is not None else '확인 필요'}, "
        f"Effort={priority.effort if priority and priority.effort is not None else '확인 필요'}, "
        f"Score={priority.rice_score if priority and priority.rice_score is not None else '잠금 안 함'}"
    )
    pricing_text = (
        f"목표 밴드: {pricing.target_price_band or '확인 필요'} | "
        f"권장 가격: {pricing.recommended_price or '확인 필요'} | "
        f"신뢰도: {pricing.confidence} | 실험: {pricing.experiment or '확인 필요'}"
        if pricing
        else "확인 필요"
    )

    return f"""# {model_code} 제품 기획서

## 1. 문제 / 기회와 근거
시장 공백: {gaps or '확인 필요'}
핵심 페인: {'; '.join(research_report.consumer_pain_points[:3]) if research_report else '확인 필요'}

## 2. 목표 · 성공 지표
- Outcome: 핵심 TPO에서 기존 대안 대비 구매·사용 실패를 줄인다.
- KPI baseline / target / period: 확인 필요 — 출시 전 전환율·반품률·사용성 기준 수집.
- 우선순위 (RICE): {rice_text}

## 3. 타깃 세그먼트 · 페르소나 · JTBD
Persona: {persona_text}
Segment: {segment_text}

### Job Stories
{job_story_text}

### 고객 여정 우선 개선
{'; '.join(journey_improvements) if journey_improvements else '확인 필요'}

## 4. 가치 제안 / USP
{usp}. 시장 공백 근거: {gaps}. 타당성 게이트: {verdict}.

## 5. 범위 · 비범위 · 요구사항
- In scope: {garment} 핵심 TPO 사양, 핏, 가격 검증, Amazon US 상세페이지 근거.
- Out of scope: 근거 없는 신규 소재 성능, 미확인 SKU 코드, 검증 전 전체 색상·사이즈 확대.
- Acceptance: 샘플 착용 테스트, 핵심 기능 기준, 핏·사이즈 선택성, 가격 실험을 통과해야 함.

## 6. Garment-TPO Lock
Line: {line} | Garment: {garment} | TPO: {concept.target_tpo or '확인 필요'}

## 7. Market Opportunity — TAM / SAM / SOM
{market_opportunity}
Top-down: {sizing.top_down_method if sizing and sizing.top_down_method else '확인 필요'}
Bottom-up: {sizing.bottom_up_method if sizing and sizing.bottom_up_method else '확인 필요'}

## 8. 가격 전략 · GTM
{pricing_text}
Channel: Amazon US CQR storefront | Launch/phase-2 SKU는 내부 카탈로그·마진 확인 후 잠금.

## 제품 스펙 (pocket/waist/colorway matrices — counts mandatory)
| Requirement | Zone | Target | Verification |
|---|---|---|---|
| 보호·통기 핵심 기능 | category-specific | 확인 필요 | TPO 필드 테스트 |
| 고마모 보강 | seat/knee/hem as applicable | 확인 필요 | 반복 마모 테스트 |
| 핏·조절 | waist/inseam/closure | 확인 필요 | 사이즈별 착용 테스트 |

Waist / pocket / closure counts: PRODUCT_DEV_SPEC와 카테고리 요구사항 확인 후 잠금.
Colorway: COLOR_CODE 및 라이브 SKU 충돌 확인 후 잠금.

## 패키징 · 라벨 · listing hero color
Hero color / hangtag / listing claims: 내부 근거 및 경쟁 배틀카드 검증 후 잠금.

## vs 기존 SKU delta / cannibalization mitigation
라이브 카탈로그 대비 기능·핏·가격 delta 표를 작성하고 대체/보완 관계를 검증.

## 샘플 우선순위
1st mock: 핵심 페르소나·TPO 기준 기능/핏 검증
2nd mock: 1차 실패 수정 + 가격대 목표 원가 검증

## 9. Pre-mortem / 리스크 · 확인 필요
{risk_text}

## 10. 검증 계획
- Persona/segment: 인터뷰·리뷰 코딩으로 JTBD와 우선순위 확인
- Pricing: {pricing.experiment if pricing and pricing.experiment else '가격점 A/B 또는 구매의향 테스트 설계'}
- Product: TPO별 착용·보호·통기·내구 acceptance test
- Journey: 상세페이지→구매→첫 사용 구간의 상위 마찰 3개 개선

## 11. Feasibility / Human feedback 반영 로그
{fb_log or '(none)'}
"""


def run_product_planning(
    approved_concepts: list[ConceptCandidate],
    *,
    research_report: ResearchReport | None = None,
    feasibility_report: FeasibilityReport | None = None,
    human_feedback: HumanFeedback | None = None,
    settings: Settings | None = None,
    dry_run: bool = False,
) -> str:
    if not approved_concepts:
        raise ValueError("No approved concepts for product planning")

    settings = settings or get_settings()
    primary = approved_concepts[0]

    if dry_run:
        plan = _dry_run_plan(
            primary,
            research_report=research_report,
            feasibility_report=feasibility_report,
            human_feedback=human_feedback,
        )
        if len(approved_concepts) > 1:
            appendix = "\n\n".join(
                f"## Appendix — {c.name}\n{c.usp_hypothesis or ''}" for c in approved_concepts[1:]
            )
            plan = f"{plan}\n\n# Appendix — additional approved concepts\n{appendix}"
        return plan

    llm = get_chat_model(settings)
    context = {
        "concept": primary.model_dump(),
        "research_report": research_report.model_dump() if research_report else {},
        "feasibility_report": feasibility_report.model_dump() if feasibility_report else {},
        "human_feedback": human_feedback.model_dump() if human_feedback else {},
        "additional_concepts": [c.model_dump() for c in approved_concepts[1:]],
    }
    user = (
        "Produce the final CQR product plan markdown for the approved concept.\n"
        "Write in Korean with every mandatory PRD, prioritization, pre-mortem, and validation "
        "section from the system prompt.\n"
        "Carry forward research personas, segments, pricing strategy, job stories, customer "
        "journey improvements, and competitive battlecard implications from Context JSON.\n"
        "Include pocket/waist/colorway tables with counts, zones, closure types.\n"
        "Never use vague specs like 'appropriate cargo pockets'.\n\n"
        f"Context JSON:\n{context}"
    )
    draft = invoke_structured(
        llm,
        with_language(PRODUCT_PLANNING_SYSTEM, settings.report_language),
        user,
        ProductPlanDraft,
    )
    return draft.markdown
