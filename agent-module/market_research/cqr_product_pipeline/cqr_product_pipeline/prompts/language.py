"""Report output-language rules shared by all pipeline agents."""

from __future__ import annotations

KOREAN_OUTPUT_RULE = """
OUTPUT LANGUAGE — Korean (ko-KR). Hard requirement.
- Write every narrative field in Korean: market_gaps, consumer_pain_points, competitor_moves,
  qual_themes, personas, market_segments, pricing_strategy, competitive_battlecards,
  job_stories, customer_journeys, concept name / target_tpo / usp_hypothesis,
  review_rating_notes, priority rationale, pre_mortem, summary, blockers, data_gaps.
- Keep as-is (do not translate): brand names (Burton, Patagonia, 5.11), model codes, fabric and
  spec terms (GORE-TEX, 2.5L, ripstop, denier), sizes, price bands ($120-$180), URLs.
- pain_theme_frequencies keys stay ASCII snake_case machine keys; values stay numeric.
- garment_type stays a short English category label (e.g. "ski pants") for downstream matching.
- When quoting a review, keep a short original quote, then add a Korean paraphrase.
- Never emit English sentences or English paragraphs for report prose.
""".strip()

ENGLISH_OUTPUT_RULE = """
OUTPUT LANGUAGE — English. Write all narrative fields in English.
""".strip()


def language_rule(lang: str = "ko") -> str:
    return ENGLISH_OUTPUT_RULE if str(lang).lower().startswith("en") else KOREAN_OUTPUT_RULE


def with_language(system_prompt: str, lang: str = "ko") -> str:
    """Append the output-language contract to a system prompt."""
    return f"{system_prompt}\n\n{language_rule(lang)}"
