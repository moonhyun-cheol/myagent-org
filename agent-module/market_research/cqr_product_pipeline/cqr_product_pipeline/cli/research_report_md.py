"""Format ResearchReport as chat-friendly markdown (Korean by default)."""

from __future__ import annotations

import re

from cqr_product_pipeline.schemas.models import ResearchReport

LABELS: dict[str, dict[str, str]] = {
    "ko": {
        "title": "# 심층리서치 리포트",
        "session": "세션",
        "meta": "## 리포트 메타",
        "quality_banner": (
            "> **품질 배너 · 템플릿 폴백**\n"
            "> LLM 근거 종합에 실패했거나 웹 스니펫이 부족합니다. 아래 공백·페인·페르소나는 "
            "**카테고리 골격**이며 확정 시장조사로 쓰지 마세요.\n"
            "> 재실행: 품목·시즌을 명확히 한 brief로 다시 `/심층리서치` 하세요."
        ),
        "gaps": "## 시장 공백 (가설)",
        "gaps_empty": "_시장 공백을 추출하지 못했습니다 (품질 게이트 실패 — 카테고리·시즌을 명확히 해서 재실행하세요)._",
        "pains": "## 소비자 페인 포인트 (가설)",
        "freq": "**추정 테마 빈도 (템플릿):**",
        "sentiment_limits": "**감성·표본 해석:**",
        "competitors": "## 경쟁사 시드 (검증 전)",
        "sizing": "## 시장 규모 (TAM / SAM / SOM)",
        "market_definition": "시장 정의",
        "top_down": "Top-down",
        "bottom_up": "Bottom-up",
        "assumptions": "핵심 가정",
        "confidence": "신뢰도",
        "personas": "## 핵심 페르소나 (JTBD · 가설)",
        "segments": "## 시장·사용자 세그먼트 (가설)",
        "pricing": "## 가격 전략",
        "battlecards": "## 경쟁 배틀카드",
        "job_stories": "## Job Stories",
        "journeys": "## 고객 여정",
        "qual": "## 정성 테마",
        "concepts": "## 컨셉 후보 (GO/KILL 판정 아님 · 가설)",
        "concept": "컨셉",
        "line": "라인",
        "garment": "품목",
        "tpo": "TPO",
        "usp": "USP 가설",
        "sources": "## 출처 (관련 스니펫만)",
        "sources_empty": "_품목에 맞는 웹 출처를 남기지 못했습니다 (무관·저품질 URL 필터링)._ ",
        "next": "_다음: 원할 때만 **타당성** 또는 **기획서** 요청. 기본 워크플로는 `/심층리서치` 여기서 종료._",
    },
    "en": {
        "title": "# Deep Research Report",
        "session": "Session",
        "meta": "## Report meta",
        "quality_banner": (
            "> **Quality banner · template fallback**\n"
            "> LLM synthesis failed or web evidence is thin. Sections below are **category skeleton** — not a final study.\n"
            "> Re-run `/심층리서치` with a clearer product + season brief."
        ),
        "gaps": "## Market gaps (hypotheses)",
        "gaps_empty": "_No market gaps extracted (quality gate failed — re-run with a clearer category/season brief)._",
        "pains": "## Consumer pain points (hypotheses)",
        "freq": "**Estimated theme frequency (template):**",
        "sentiment_limits": "**Sentiment and sample limits:**",
        "competitors": "## Competitor seeds (unverified)",
        "sizing": "## Market sizing (TAM / SAM / SOM)",
        "market_definition": "Market definition",
        "top_down": "Top-down",
        "bottom_up": "Bottom-up",
        "assumptions": "Key assumptions",
        "confidence": "Confidence",
        "personas": "## Core personas (JTBD · hypotheses)",
        "segments": "## Market and user segments (hypotheses)",
        "pricing": "## Pricing strategy",
        "battlecards": "## Competitive battlecards",
        "job_stories": "## Job stories",
        "journeys": "## Customer journey",
        "qual": "## Qualitative themes",
        "concepts": "## Concept candidates (not yet GO/KILL · hypotheses)",
        "concept": "Concept",
        "line": "Line",
        "garment": "Garment",
        "tpo": "TPO",
        "usp": "USP hypothesis",
        "sources": "## Sources (topic-filtered)",
        "sources_empty": "_No on-topic sources retained after quality filter._",
        "next": "_Next: request **타당성** or **기획서** only when you want it. Default workflow ends here._",
    },
}


def _clean(text: str) -> str:
    return re.sub(r"^[\s\-•*]+", "", str(text or "")).strip()


def _bullet(text: str) -> str:
    cleaned = _clean(text)
    return f"- {cleaned}" if cleaned else ""


def _is_template_fallback(report: ResearchReport) -> bool:
    note = (report.quant_signals.review_rating_notes or "") + " " + " ".join(report.qual_themes or [])
    needles = (
        "템플릿",
        "template",
        "폴백",
        "fallback",
        "LLM 종합 실패",
        "웹 검색 근거 0건",
        "드라이런",
        "insufficient_evidence",
    )
    low = note.lower()
    if any(n.lower() in low for n in needles):
        return True
    if report.pricing_strategy.confidence == "insufficient_evidence" and not report.sources:
        return True
    return bool(report.pricing_strategy.confidence == "insufficient_evidence" and "템플릿" in note)


def format_research_report_md(
    report: ResearchReport,
    *,
    session_id: str = "",
    lang: str = "ko",
    brief_lock: dict | None = None,
) -> str:
    labels = LABELS["en"] if str(lang).lower().startswith("en") else LABELS["ko"]
    is_ko = not str(lang).lower().startswith("en")
    is_tpl = _is_template_fallback(report)

    # Prefer brief_lock KO phrase for product lock line
    product_hint = ""
    season_hint = ""
    family_hint = ""
    if brief_lock:
        pb = str(brief_lock.get("product_brief") or "").strip()
        g = str(brief_lock.get("garment") or "").strip()
        product_hint = pb or g
        season_hint = str(brief_lock.get("season") or "").strip()
        family_hint = str(brief_lock.get("product_family") or brief_lock.get("category_key") or "").strip()
    if not product_hint and report.concepts:
        product_hint = _clean(report.concepts[0].garment_type or report.concepts[0].name or "")

    lines = [labels["title"]]
    if session_id:
        lines.append(f"{labels['session']}: `{session_id}`")
    lines.append("")

    if is_tpl:
        lines.append(labels["quality_banner"])
        lines.append("")

    # Scope always shown when lock available (readable report header).
    if product_hint or season_hint or family_hint:
        lines.append("## 조사 범위" if is_ko else "## Study scope")
        if product_hint:
            lines.append(f"- {'품목' if is_ko else 'product'}: **{product_hint}**")
            g_en = (brief_lock or {}).get("garment") if brief_lock else None
            if g_en and str(g_en) != product_hint:
                lines.append(f"- {'검색 라벨' if is_ko else 'search label'}: `{g_en}`")
        if season_hint:
            lines.append(f"- {'시즌/TPO' if is_ko else 'season'}: {season_hint}")
        if family_hint:
            lines.append(f"- {'패밀리' if is_ko else 'family'}: `{family_hint}`")
        if brief_lock and brief_lock.get("competitors"):
            lines.append(f"- {'경쟁 시드' if is_ko else 'competitor seeds'}: {brief_lock['competitors']}")
        if is_tpl:
            lines.append(
                f"- {'품질 게이트' if is_ko else 'quality gate'}: **template_fallback** "
                f"({report.pricing_strategy.confidence})"
            )
        elif report.pricing_strategy.confidence:
            lines.append(
                f"- {'신뢰도' if is_ko else 'confidence'}: {report.pricing_strategy.confidence}"
            )
        lines.append("")
    elif is_tpl:
        lines.append(labels["meta"])
        lines.append(
            f"- {'신뢰도' if is_ko else 'confidence'}: **{report.pricing_strategy.confidence}**"
        )
        if report.quant_signals.review_rating_notes:
            lines.append(f"- note: {report.quant_signals.review_rating_notes}")
        lines.append("")

    lines.append(
        labels["gaps"]
        if is_tpl
        else ("## 시장 공백 (Market gaps)" if is_ko else "## Market gaps")
    )
    if report.market_gaps:
        for i, gap in enumerate(report.market_gaps, start=1):
            cleaned = _clean(gap)
            if cleaned:
                lines.append(f"{i}. {cleaned}")
    else:
        lines.append(labels["gaps_empty"])
    lines.append("")

    if report.consumer_pain_points:
        lines.append(
            labels["pains"]
            if is_tpl
            else ("## 소비자 페인 포인트" if is_ko else "## Consumer pain points")
        )
        for p in report.consumer_pain_points:
            bullet = _bullet(p)
            if bullet:
                lines.append(bullet)
        if report.quant_signals.pain_theme_frequencies:
            lines.append("")
            lines.append(labels["freq"] if is_tpl else ("**추정 테마 빈도:**" if is_ko else "**Estimated theme frequency:**"))
            for theme, freq in report.quant_signals.pain_theme_frequencies.items():
                lines.append(f"- {theme}: {freq:.0%}")
        if report.quant_signals.review_rating_notes and not is_tpl:
            lines.append("")
            lines.append(f"{labels['sentiment_limits']} {report.quant_signals.review_rating_notes}")
        # Real reports with quant notes should always show sentiment line when present.
        if report.quant_signals.review_rating_notes and is_tpl is False:
            pass  # already above
        lines.append("")

    # Fix: for non-template, also surface sentiment when we skipped earlier due to empty pains
    if (
        not report.consumer_pain_points
        and report.quant_signals.review_rating_notes
        and not is_tpl
    ):
        lines.append(f"{labels['sentiment_limits']} {report.quant_signals.review_rating_notes}")
        lines.append("")

    if report.competitor_moves:
        lines.append(
            labels["competitors"]
            if is_tpl
            else ("## 경쟁사 프로필 및 차별화 기회" if is_ko else "## Competitor profiles and differentiation openings")
        )
        for c in report.competitor_moves:
            bullet = _bullet(c)
            if bullet:
                lines.append(bullet)
        lines.append("")

    sizing = report.market_sizing
    if any((sizing.tam, sizing.sam, sizing.som, sizing.top_down_method, sizing.bottom_up_method)):
        lines.append(labels["sizing"])
        if sizing.market_definition:
            lines.append(f"- {labels['market_definition']}: {sizing.market_definition}")
        lines.append(f"- TAM: {sizing.tam or '확인 필요'}")
        lines.append(f"- SAM: {sizing.sam or '확인 필요'}")
        lines.append(f"- SOM: {sizing.som or '확인 필요'}")
        if sizing.top_down_method:
            lines.append(f"- {labels['top_down']}: {sizing.top_down_method}")
        if sizing.bottom_up_method:
            lines.append(f"- {labels['bottom_up']}: {sizing.bottom_up_method}")
        if sizing.assumptions:
            lines.append(f"- {labels['assumptions']}: {'; '.join(sizing.assumptions)}")
        lines.append(f"- {labels['confidence']}: {sizing.confidence}")
        lines.append("")

    if report.personas:
        lines.append(labels["personas"])
        for persona in report.personas:
            lines.append(f"### {persona.name} (`{persona.persona_id}`)")
            lines.append(f"- {'세그먼트' if is_ko else 'segment'}: {persona.segment}")
            lines.append(f"- {'상황' if is_ko else 'context'}: {persona.context}")
            lines.append(f"- JTBD: {persona.job_to_be_done}")
            if persona.pains:
                lines.append(f"- Pains: {'; '.join(persona.pains)}")
            if persona.gains:
                lines.append(f"- Gains: {'; '.join(persona.gains)}")
            if persona.buying_triggers:
                lines.append(
                    f"- {'구매 트리거' if is_ko else 'triggers'}: {'; '.join(persona.buying_triggers)}"
                )
            if persona.unexpected_insight:
                lines.append(
                    f"- {'비정형 인사이트' if is_ko else 'insight'}: {persona.unexpected_insight}"
                )
            lines.append("")

    if report.market_segments:
        lines.append(labels["segments"])
        lines.append("| Segment | Need / TPO | WTP | 경쟁 | 우선순위 |")
        lines.append("|---|---|---|---|---|")
        for segment in report.market_segments:
            need_tpo = f"{segment.defining_need} / {segment.behavior_and_tpo}"
            lines.append(
                f"| {segment.name} | {need_tpo} | {segment.willingness_to_pay or '확인 필요'} "
                f"| {segment.competitive_intensity} | {segment.priority} |"
            )
        lines.append("")

    pricing = report.pricing_strategy
    if any(
        (
            pricing.target_price_band,
            pricing.recommended_price,
            pricing.competitor_benchmarks,
            pricing.pricing_gap,
            pricing.experiment,
        )
    ):
        lines.append(labels["pricing"])
        if pricing.value_metric:
            lines.append(f"- {'가치 기준' if is_ko else 'value metric'}: {pricing.value_metric}")
        lines.append(f"- {'목표 밴드' if is_ko else 'band'}: {pricing.target_price_band or '확인 필요'}")
        lines.append(
            f"- {'권장 가격' if is_ko else 'recommended'}: {pricing.recommended_price or '확인 필요'}"
        )
        if pricing.pricing_gap:
            lines.append(f"- {'가격 공백' if is_ko else 'gap'}: {pricing.pricing_gap}")
        if pricing.competitor_benchmarks:
            lines.append(
                f"- {'경쟁 벤치마크' if is_ko else 'benchmarks'}: {'; '.join(pricing.competitor_benchmarks)}"
            )
        if pricing.rationale:
            lines.append(f"- {'근거' if is_ko else 'rationale'}: {pricing.rationale}")
        if pricing.experiment:
            lines.append(f"- {'검증 실험' if is_ko else 'experiment'}: {pricing.experiment}")
        lines.append(f"- {labels['confidence']}: {pricing.confidence}")
        lines.append("")

    if report.competitive_battlecards:
        lines.append(labels["battlecards"])
        for card in report.competitive_battlecards:
            lines.append(f"### vs {card.competitor}")
            if card.strengths:
                lines.append(f"- {'상대 강점' if is_ko else 'strengths'}: {'; '.join(card.strengths)}")
            if card.weaknesses:
                lines.append(f"- {'상대 약점' if is_ko else 'weaknesses'}: {'; '.join(card.weaknesses)}")
            if card.our_advantages:
                lines.append(f"- {'대응 우위' if is_ko else 'advantages'}: {'; '.join(card.our_advantages)}")
            if card.objection:
                lines.append(f"- {'예상 이의' if is_ko else 'objection'}: {card.objection}")
            if card.response:
                lines.append(f"- {'답변' if is_ko else 'response'}: {card.response}")
            if card.avoid_claims:
                lines.append(f"- {'금지 주장' if is_ko else 'avoid'}: {'; '.join(card.avoid_claims)}")
            lines.append("")

    if report.job_stories:
        lines.append(labels["job_stories"])
        for story in report.job_stories:
            lines.append(
                f"- **When** {story.when}, **I want** {story.want}, **so that** {story.so_that}."
            )
        lines.append("")

    if report.customer_journeys:
        lines.append(labels["journeys"])
        for journey in report.customer_journeys:
            lines.append(f"### {journey.journey_name} (`{journey.persona_id}`)")
            lines.append("| Stage | Goal | Pain | Emotion | Opportunity |")
            lines.append("|---|---|---|---|---|")
            for stage in journey.stages:
                lines.append(
                    f"| {stage.stage} | {stage.goal} | {'; '.join(stage.pain_points) or '-'} "
                    f"| {stage.emotion or '-'} | {'; '.join(stage.opportunities) or '-'} |"
                )
            if journey.priority_improvements:
                lines.append(
                    f"- {'우선 개선' if is_ko else 'priority'}: {'; '.join(journey.priority_improvements)}"
                )
            lines.append("")

    if report.qual_themes:
        lines.append(labels["qual"])
        for t in report.qual_themes:
            bullet = _bullet(t)
            if bullet:
                lines.append(bullet)
        lines.append("")

    if report.concepts:
        lines.append(labels["concepts"])
        for c in report.concepts:
            lines.append(f"### {labels['concept']} {c.concept_id}: {c.name}")
            if c.line_recommendation:
                lines.append(f"- {labels['line']}: {c.line_recommendation}")
            if c.garment_type:
                lines.append(f"- {labels['garment']}: {c.garment_type}")
            if c.target_tpo:
                lines.append(f"- {labels['tpo']}: {c.target_tpo}")
            if c.usp_hypothesis:
                lines.append(f"- {labels['usp']}: {c.usp_hypothesis}")
            lines.append("")

    sources_usable = [
        s
        for s in (report.sources or [])
        if s.url and "example.com/dry-run" not in s.url
    ]
    lines.append(labels["sources"])
    if sources_usable:
        for s in sources_usable:
            title = f" — {s.title}" if s.title else ""
            lines.append(f"- [{s.url}]({s.url}){title}")
    else:
        lines.append(labels["sources_empty"])
    lines.append("")

    lines.append(labels["next"])
    return "\n".join(lines)
