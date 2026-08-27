"""Human-readable feasibility review summary for HITL (Korean)."""

from __future__ import annotations

from cqr_product_pipeline.schemas.models import FeasibilityReport, ResearchReport


def format_resume_hints(*, session_id: str, concept_ids: list[str]) -> list[str]:
    if len(concept_ids) >= 2:
        c1, c2 = concept_ids[0], concept_ids[1]
        examples = [
            '둘 다 승인해줘',
            f'{c2} 승인, {c1} 거절',
            '01 승인, 02 거절  (컨셉 순서 기준)',
        ]
    elif len(concept_ids) == 1:
        examples = [f'{concept_ids[0]} 승인', "승인해줘"]
    else:
        examples = ["A 승인, B 거절", "둘 다 승인해줘"]

    lines = [
        "재개 (한 줄만 실행 — 채팅 설명을 PowerShell에 붙여넣지 마세요):",
        f'  .\\scripts\\run.ps1 pipeline approve "{examples[0]}"',
    ]
    for ex in examples[1:]:
        lines.append(f'  .\\scripts\\run.ps1 pipeline approve "{ex}"')
    lines.append(
        "  참고: run.ps1 사용 — `python -m cqr_product_pipeline...` 직접 실행은 venv·패키지 경로가 필요합니다."
    )
    return lines


def format_feasibility_review_md(
    *,
    session_id: str,
    research_report: ResearchReport,
    feasibility_report: FeasibilityReport,
) -> str:
    lines = [
        f"# 타당성 리뷰 — 세션 {session_id}",
        "",
        "## 리서치 요약",
        f"- 시장 공백 수: {len(research_report.market_gaps)}",
        f"- 검토 대상 컨셉: {len(research_report.concepts)}",
        "",
    ]

    sizing = research_report.market_sizing
    lines.extend(
        [
            "## 시장 규모 검증",
            f"- 시장 정의: {sizing.market_definition or '확인 필요'}",
            f"- TAM: {sizing.tam or '확인 필요'}",
            f"- SAM: {sizing.sam or '확인 필요'}",
            f"- SOM (1–3년): {sizing.som or '확인 필요'}",
            f"- Top-down 근거: {sizing.top_down_method or '확인 필요'}",
            f"- Bottom-up 교차검증: {sizing.bottom_up_method or '확인 필요'}",
            f"- 신뢰도: {sizing.confidence}",
        ]
    )
    if sizing.assumptions:
        lines.append(f"- 핵심 가정: {'; '.join(sizing.assumptions)}")
    if sizing.confidence == "insufficient_evidence":
        lines.append("- 판정 제한: 시장규모 근거가 부족하므로 TAM/SAM/SOM을 GO 근거로 사용하지 않음")
    lines.append("")

    concept_lookup = {c.concept_id: c for c in research_report.concepts}

    for result in feasibility_report.concepts:
        concept = concept_lookup.get(result.concept_id)
        line = concept.line_recommendation if concept else "해당 없음"
        lines.extend(
            [
                f"## 컨셉 {result.concept_id}: {result.name}",
                f"- 라인: {line}",
                f"- 브랜드 적합 리스크: {result.brand_alignment_score}",
                f"- 생산·SCM 리스크: {result.manufacturing_score}",
                f"- 자기잠식 리스크: {result.cannibalization_score}",
                f"- **판정: {result.verdict.value}**",
            ]
        )
        if result.blockers:
            lines.append(f"- 블로커: {'; '.join(result.blockers)}")
        if result.data_gaps:
            lines.append(f"- 데이터 공백: {'; '.join(result.data_gaps)}")
        priority = result.priority
        lines.append(
            "- RICE: "
            f"reach={priority.reach if priority.reach is not None else '확인 필요'}, "
            f"impact={priority.impact if priority.impact is not None else '확인 필요'}, "
            f"confidence={priority.confidence if priority.confidence is not None else '확인 필요'}, "
            f"effort={priority.effort if priority.effort is not None else '확인 필요'}, "
            f"score={priority.rice_score if priority.rice_score is not None else '잠금 안 함'}"
        )
        if priority.rationale:
            lines.append(f"- 우선순위 근거: {priority.rationale}")
        if result.pre_mortem:
            lines.append("- Pre-mortem:")
            for risk in result.pre_mortem:
                lines.append(
                    f"  - [{risk.likelihood}/{risk.impact}] {risk.failure_scenario} — "
                    f"조기 신호: {risk.early_warning or '확인 필요'}; 대응: {risk.mitigation}; "
                    f"담당: {risk.owner or '확인 필요'}"
                )
        if result.summary:
            lines.append(f"- 요약: {result.summary}")
        lines.append("")

    concept_ids = [r.concept_id for r in feasibility_report.concepts]
    lines.extend(["", "## 재개 (PowerShell)"])
    lines.extend(format_resume_hints(session_id=session_id, concept_ids=concept_ids))
    lines.extend(
        [
            "",
            "또는 `feedback.json` 을 만들어 `cqr_product_pipeline/` 폴더에서 run.ps1 / 파이프라인 CLI로 재개하세요.",
        ]
    )
    return "\n".join(lines)
