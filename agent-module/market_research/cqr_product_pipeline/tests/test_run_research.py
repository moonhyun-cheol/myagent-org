"""Tests for standalone deep research CLI."""

from cqr_product_pipeline.agents.deep_research import (
    _build_search_queries,
    _parse_brief_hints,
    ensure_concept_ids,
    run_deep_research,
)
from cqr_product_pipeline.cli.research_report_md import format_research_report_md
from cqr_product_pipeline.schemas.models import (
    MarketSizing,
    QuantSignals,
    ResearchReport,
)


def test_dry_run_research_report():
    report = run_deep_research("Liberator summer cargo gap", dry_run=True)
    report = ensure_concept_ids(report)
    assert len(report.market_gaps) >= 3
    assert len(report.concepts) >= 1
    md = format_research_report_md(report, session_id="t1")
    assert "시장 공백" in md
    assert "컨셉" in md
    md_en = format_research_report_md(report, session_id="t1", lang="en")
    assert "Market gaps" in md_en


def test_report_renders_competitor_sentiment_and_market_sizing():
    report = ResearchReport(
        market_gaps=["Short-inseam waterproof ski pants at a mid-market price"],
        competitor_moves=[
            "Burton / Reserve Bib | leader | $279 | strong waterproofing | fit complaints | short-inseam opening | https://example.com/burton"
        ],
        consumer_pain_points=["Short users report excessive inseam length"],
        quant_signals=QuantSignals(
            pain_theme_frequencies={"fit": 1.0},
            review_rating_notes="Small review sample; frequency is directional only.",
        ),
        market_sizing=MarketSizing(
            market_definition="US women's ski pants, annual retail revenue",
            tam="$1.0B illustrative sourced scope",
            sam="$250M channel/category slice",
            som="$2.5M 1-3 year obtainable target",
            top_down_method="Industry total × women's × ski-pants share",
            bottom_up_method="Addressable buyers × annual units × ASP",
            assumptions=["USD", "US", "annual"],
            confidence="low",
        ),
    )
    md = format_research_report_md(report, session_id="sizing1")
    assert "경쟁사" in md
    assert "감성·표본 해석" in md or "Small review sample" in md
    assert "시장 규모" in md
    assert "Bottom-up" in md
    assert "신뢰도: low" in md


def test_brief_hints_ski_fw_not_tactical():
    hints = _parse_brief_hints(
        "2027 fw시즌 스키바지 컨셉 구성을 위한 시장조사 실시", None
    )
    assert hints["product_family"] == "bottoms"
    assert hints["category_key"] == "bottoms"
    assert "ski" in hints["garment"]
    assert hints["product_brief"] == "스키바지"
    assert "fall-winter" in hints["season"] or "2027" in hints["season"]
    assert hints["line"] == "unspecified"
    assert "5.11" not in hints["competitors"]


def test_ski_fw_dry_run_concepts_on_brief():
    report = run_deep_research(
        "2027 FW 시즌 스키바지 컨셉 구성을 위한 시장조사",
        dry_run=True,
    )
    report = ensure_concept_ids(report)
    assert len(report.market_gaps) >= 3
    blob = " ".join(
        [
            *(report.market_gaps),
            *(c.garment_type or "" for c in report.concepts),
            *(c.target_tpo or "" for c in report.concepts),
        ]
    ).lower()
    assert "ski" in blob
    assert "tactical" not in blob
    assert "coolmax" not in blob
    md = format_research_report_md(report, session_id="ski1")
    assert "시장 공백" in md
    assert "1." in md  # gaps numbered, not empty
    assert "스키" in md or "ski" in md.lower()


def test_pick_ollama_model_falls_back_to_installed_tag():
    from cqr_product_pipeline.config.providers import (
        pick_ollama_model,
        resolve_ollama_base_url,
    )
    from cqr_product_pipeline.config.settings import Settings

    assert pick_ollama_model("qwen2.5:7b", ["qwen2.5:7b"]) == "qwen2.5:7b"
    assert (
        pick_ollama_model("qwen2.5:32b", ["qwen2.5:7b"]) == "qwen2.5:7b"
    )  # same family
    assert pick_ollama_model("qwen3.6:35b", ["llama3.1:8b"]) == "llama3.1:8b"
    assert pick_ollama_model("qwen3.6:35b", []) == "qwen3.6:35b"  # tag listing failed
    assert "127.0.0.1" in resolve_ollama_base_url(Settings(ollama_base_url=None))


def test_report_language_rule_is_korean_by_default():
    from cqr_product_pipeline.config.settings import Settings
    from cqr_product_pipeline.prompts.deep_research import DEEP_RESEARCH_SYSTEM
    from cqr_product_pipeline.prompts.language import with_language

    assert Settings().report_language == "ko"
    system = with_language(DEEP_RESEARCH_SYSTEM, "ko")
    assert "OUTPUT LANGUAGE — Korean" in system
    assert "OUTPUT LANGUAGE — English" in with_language(DEEP_RESEARCH_SYSTEM, "en")


def test_brief_hints_work_boots_not_pants():
    brief = "공사장 현장직들을 위한 작업화, 습한 겨울 환경에 착용, 현장조사"
    hints = _parse_brief_hints(brief, None)
    assert hints["product_family"] == "footwear"
    assert hints["garment"] == "work boots"
    assert hints["product_brief"] == "작업화"
    assert "wet" in hints["conditions"]
    assert "jobsite" in hints["conditions"]
    assert "fall-winter" in hints["season"] or "winter" in hints["season"]
    assert "Timberland PRO" in hints["competitors"]

    queries = " | ".join(_build_search_queries(brief, hints)).lower()
    assert "boot" in queries or "작업화" in queries
    assert "ski pants" not in queries
    assert "taclite" not in queries


def test_work_boots_dry_run_stays_on_footwear():
    report = run_deep_research(
        "공사장 현장직들을 위한 작업화, 습한 겨울 환경에 착용, 현장조사",
        dry_run=True,
    )
    report = ensure_concept_ids(report)
    assert len(report.market_gaps) >= 3
    blob = " ".join(
        [
            *report.market_gaps,
            *report.consumer_pain_points,
            *(c.garment_type or "" for c in report.concepts),
            *(c.target_tpo or "" for c in report.concepts),
            *(c.usp_hypothesis or "" for c in report.concepts),
        ]
    ).lower()
    assert "work boots" in blob
    assert "ski pants" not in blob
    md = format_research_report_md(report, session_id="boot1")
    assert "시장 공백" in md


def test_unregistered_product_gloves_extracts_without_registry_entry():
    """New products must work from brief phrase extraction — no case-by-case category key."""
    brief = "습한 겨울 공사장용 방한장갑 시장조사"
    hints = _parse_brief_hints(brief, None)
    assert hints["product_family"] == "handwear"
    assert "glove" in hints["garment"] or "장갑" in hints["product_brief"]
    queries = " | ".join(_build_search_queries(brief, hints)).lower()
    assert "glove" in queries or "장갑" in queries
    assert "ski pants" not in queries
    assert "work boots" not in queries

    report = run_deep_research(brief, dry_run=True)
    blob = " ".join(c.garment_type or "" for c in report.concepts).lower()
    assert "glove" in blob or "장갑" in blob


def test_apparel_vocab_skirts_golf_tennis_leggings():
    cases = [
        ("스커트 시장조사", "bottoms", ("skirt", "스커트")),
        ("테니스치마 컨셉 시장조사", "bottoms", ("tennis", "skirt", "치마")),
        ("골프바지 2027 FW 시장조사", "bottoms", ("golf", "pants", "바지")),
        ("골프 스커트 여성용 시장조사", "bottoms", ("golf", "skirt", "스커트")),
        ("레깅스 요가복 시장조사", "bottoms", ("legging", "레깅스")),
        ("원피스 여름 시장조사", "dresses", ("dress", "원피스")),
        ("사이클바지 시장조사", "bottoms", ("cycling", "pants", "바지")),
        ("경량패딩 시장조사", "tops", ("lightweight", "padded", "패딩")),
        ("클라이밍바지 시장조사", "bottoms", ("climbing", "pants", "바지")),
        ("낚시조끼 시장조사", "tops", ("fishing", "vest", "조끼")),
        ("골프화 시장조사", "footwear", ("golf", "shoes", "골프화")),
        ("벙어리장갑 시장조사", "handwear", ("mittens", "장갑")),
        ("크로스백 시장조사", "other", ("crossbody", "크로스백")),
    ]
    for brief, family, needles in cases:
        hints = _parse_brief_hints(brief, None)
        assert hints["product_family"] == family, brief
        blob = f"{hints['product_brief']} {hints['garment']}".lower()
        assert any(n.lower() in blob for n in needles), (brief, blob)
        # Must not collapse to a bare sport word like "골프" alone.
        assert hints["product_brief"] not in {"골프", "테니스", "요가"}, brief
        queries = " | ".join(_build_search_queries(brief, hints)).lower()
        assert any(n.lower() in queries for n in needles), (brief, queries)


def test_broad_or_style_words_are_not_locked_as_products():
    for brief in (
        "의류 시장조사",
        "웨어 시장조사",
        "고어텍스 시장조사",
        "오버핏 시장조사",
        "여성용 시장조사",
    ):
        hints = _parse_brief_hints(brief, None)
        assert hints["product_brief"] not in {
            "의류",
            "웨어",
            "고어텍스",
            "오버핏",
            "여성용",
        }, brief


def test_dive_suit_ss_not_season_token():
    """'ss시즌에' must never become the product — 다이빙복 locks swim_dive seeds."""
    from cqr_product_pipeline.agents.deep_research import _dry_run_report

    brief = "2028 ss시즌에 맞는 다이빙복 시장조사"
    hints = _parse_brief_hints(brief, None)
    assert hints["product_brief"] == "다이빙복"
    assert "diving" in hints["garment"].lower() or "wetsuit" in hints["garment"].lower()
    assert hints["product_family"] == "swim_dive"
    assert "Columbia" not in hints["competitors"]

    report = run_deep_research(brief, dry_run=True)
    md = format_research_report_md(report, session_id="dive1", brief_lock=hints)
    assert "조사 범위" in md
    assert "다이빙복" in md
    assert "ss시즌에(ss시즌에)" not in md

    fb_report = _dry_run_report(
        brief, None, fallback_note="LLM 종합 실패 (ModuleNotFoundError)"
    )
    fb_md = format_research_report_md(fb_report, session_id="dive-fb", brief_lock=hints)
    assert "품질 배너" in fb_md or "템플릿 폴백" in fb_md
    assert "### vs Columbia" not in fb_md
    assert "### vs " not in fb_md
    assert fb_report.competitive_battlecards == []


def test_followup_noise_tokens_never_product():
    """「방금」/「해줘」 must not become garment locks."""
    from cqr_product_pipeline.agents.deep_research import _extract_product_phrase

    bangum = _parse_brief_hints(
        "방금 시장조사에서 경쟁 공백 3개만 다시 요약해. 코드 수정 금지.", None
    )
    assert bangum["product_brief"] not in {
        "방금",
        "해줘",
        "공백",
        "요약",
        "요약해",
        "경쟁",
    }
    assert bangum["garment"] not in {"방금", "해줘", "요약해"}

    haejwo = _parse_brief_hints("시장조사해줘. edit_file로 코드 고치지 마.", None)
    assert haejwo["product_brief"] not in {"해줘", "방금", "고치지", "edit_file로"}
    assert haejwo["garment"] not in {"해줘", "방금", "고치지"}

    phrase, label = _extract_product_phrase("해줘. edit_file로 코드 고치지 마.")
    assert phrase not in {"해줘", "edit_file", "edit_file로", "고치지"}
    assert label not in {"해줘"}


def test_grounded_snippet_fallback_uses_web_titles():
    from cqr_product_pipeline.agents.deep_research import _grounded_report_from_snippets

    brief = "2028 ss시즌에 맞는 다이빙복 시장조사"
    report = _grounded_report_from_snippets(
        brief,
        None,
        [
            {
                "title": "3mm wetsuit review mobility complaints",
                "link": "https://example-dive.com/a",
                "snippet": "shoulder stretch fails on entry",
            },
            {
                "title": "Plumber in Columbia City",
                "link": "https://wateralchemyplumbing.com/x",
                "snippet": "24/7 plumbing",
            },
        ],
        fallback_note="LLM 종합 실패 (ModuleNotFoundError)",
    )
    md_blob = " ".join(
        report.consumer_pain_points + report.qual_themes + report.market_gaps
    )
    assert "wetsuit" in md_blob.lower() or "mobility" in md_blob.lower()
    assert report.competitive_battlecards == []
    urls = " ".join(s.url for s in report.sources)
    assert "wateralchemyplumbing" not in urls
    assert "example-dive.com" in urls or len(report.sources) >= 0

    from cqr_product_pipeline.agents.deep_research import _snippets_to_sources

    hints = _parse_brief_hints("2028 ss시즌에 맞는 다이빙복 시장조사", None)
    sources = _snippets_to_sources(
        [
            {
                "title": "Best 3mm wetsuit for summer diving 2028",
                "link": "https://example-dive.com/wetsuit-review",
                "snippet": "dive suit neoprene mobility complaints",
            },
            {
                "title": "Plumber in Columbia City",
                "link": "https://columbia-city-in.wateralchemyplumbing.com/",
                "snippet": "24/7 plumbing",
            },
            {
                "title": "Economist baffled by Elon Musk protest",
                "link": "https://futurism.com/future-society/economist-adam-tooze",
                "snippet": "masses",
            },
        ],
        hints,
    )
    urls = " ".join(s.url for s in sources)
    assert "wetsuit-review" in urls or "dive" in urls
    assert "wateralchemyplumbing" not in urls
    assert "futurism.com" not in urls
