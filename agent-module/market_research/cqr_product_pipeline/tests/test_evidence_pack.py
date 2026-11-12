"""Evidence-pack research: structured brief, on-topic evidence only, no template fill."""
import json
import sys

import pytest

from cqr_product_pipeline.agents.evidence_pack import (
    brief_gate,
    build_queries,
    collect_evidence,
    parse_brief,
    run_evidence_pack,
)

SKI_BODY = (
    "We tested ski pants for two seasons. The Burton ski pants at $199 leaked at the seat "
    "after three days and the vents were too short. " + "Ski pants sizing ran long in the inseam. " * 12
)


def _searcher(query, max_results):
    return [
        {"title": "Best ski pants review", "url": "https://gear.example/ski-pants", "snippet": "ski pants tested"},
        {"title": "Ski pants leaking thread", "url": "https://forum.example/t/1", "snippet": "my ski pants leak"},
        {"title": "Burton ski pants price", "url": "https://shop.example/burton", "snippet": "Burton ski pants $199"},
        {"title": "Goodyear all-season tires", "url": "https://tires.example/x", "snippet": "Good for a year"},
    ]


def _fetcher(url):
    if "gear.example" in url:
        return SKI_BODY
    if "tires.example" in url:
        return "tire tread wear warranty " * 60
    raise OSError("blocked")


def test_inline_fields_are_used_verbatim():
    brief = parse_brief("품목: 스키바지 / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280 / 영문명: ski pants")
    assert (brief.product, brief.product_en, brief.season, brief.price_band) == (
        "스키바지",
        "ski pants",
        "2027 FW",
        "$90-280",
    )
    assert brief.competitors == ["Burton", "Patagonia"]
    assert set(brief.origin.values()) == {"입력 필드"}
    queries = " | ".join(q for q, _ in build_queries(brief))
    assert "Burton ski pants" in queries and "Patagonia ski pants" in queries and "$90-280" in queries
    # Nothing the brief did not name: no seeded brands or price bands.
    for seeded in ("Columbia", "Carhartt", "$40", "$220"):
        assert seeded not in queries


def test_flag_overrides_and_category_brief():
    brief = parse_brief("", {"category": "아웃도어", "competitors": "Columbia, Patagonia", "price_band": "미드~미드하이"})
    assert brief_gate(brief) is None
    assert brief.product == "" and brief.category == "아웃도어"
    queries = [q for q, _ in build_queries(brief)]
    assert any("Columbia" in q for q in queries) and any("미드~미드하이" in q for q in queries)


def test_season_words_must_stand_alone():
    assert parse_brief("봄버재킷 시장조사").season == ""
    assert parse_brief("겨울 슬랙스 시장조사").season == "겨울"
    assert parse_brief("2027 fw시즌 스키바지 시장조사").season == "2027 FW"


@pytest.mark.parametrize("text", ["음? 리포트 형식으로 줘", "한눈에 정리해줘", ""])
def test_no_scope_needs_brief(text):
    assert brief_gate(parse_brief(text)) == "no_scope"


def test_only_on_topic_sources_become_evidence():
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants / 경쟁사: Burton")
    evidence, stats = collect_evidence(brief, _searcher, _fetcher)
    urls = [e.url for e in evidence]
    assert "https://tires.example/x" not in urls
    assert stats["off_topic_dropped"] == 1
    by_url = {e.url: e for e in evidence}
    body = by_url["https://gear.example/ski-pants"]
    assert body.source == "본문"
    # Excerpts are verbatim slices of the page text, never rewritten.
    assert all(chunk in " ".join(SKI_BODY.split()) for chunk in body.excerpt.split(" … "))
    assert "$199" in body.prices
    # Blocked page: kept on the strength of its on-topic snippet, labelled as such.
    assert by_url["https://forum.example/t/1"].source == "요약문"


def test_glued_search_rows_and_ad_links_do_not_become_evidence():
    def searcher(query, max_results):
        return [
            {
                "title": "Skiing pants : r/skiingWhich ski pants would you choose and why?",
                "url": "https://forum.example/a",
                "snippet": "Looking at ski pants under $170. I own a pair of 686 ski pants and they fell apart in one season.",
            },
            {
                "title": "Which ski pants would you choose and why?",
                "url": "https://forum.example/b",
                "snippet": "I own a pair of 686 ski pants and they fell apart in one season.",
            },
            {"title": "Ski pants sale", "url": "https://www.bing.com/aclick?ld=x", "snippet": "ski pants deals"},
        ]

    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    evidence, _stats = collect_evidence(brief, searcher, lambda url: "")
    by_url = {e.url: e for e in evidence}
    assert set(by_url) == {"https://forum.example/a", "https://forum.example/b"}
    first = by_url["https://forum.example/a"]
    # The neighbour's title and sentence are cut off the first row.
    assert first.title == "Skiing pants : r/skiing"
    assert first.excerpt == "Looking at ski pants under $170."


def test_menu_blocks_are_not_quoted():
    from cqr_product_pipeline.agents.evidence_pack import html_to_text

    html = (
        "<nav><a>Ski pants</a><a>Jackets</a></nav>"
        "<div>Home Ski pants Jackets Gloves Boots Helmets Goggles Sale Stores Account Cart Search Menu</div>"
        "<p>These ski pants leaked at the seat after three days. The vents were too short to dump heat.</p>"
        + "<p>filler paragraph about nothing in particular.</p>" * 12
    )
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    evidence, _stats = collect_evidence(
        brief,
        lambda q, n: [{"title": "Ski pants review", "url": "https://gear.example/r", "snippet": "ski pants"}],
        lambda url: html_to_text(html),
    )
    assert evidence[0].source == "본문"
    assert evidence[0].excerpt.startswith("These ski pants leaked")
    assert "Helmets Goggles" not in evidence[0].excerpt


def test_report_has_excerpts_and_no_template_sections(tmp_path):
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants / 경쟁사: Burton, Arcteryx")
    result = run_evidence_pack(brief, tmp_path, "s1", searcher=_searcher, fetcher=_fetcher)
    assert result["status"] == "ok"
    md = (tmp_path / "research_report.md").read_text(encoding="utf-8")
    assert "브리프 해석" in md and "https://gear.example/ski-pants" in md
    assert "경쟁사 `Arcteryx`: 이 브랜드를 언급한 근거 0건" in md
    assert "경쟁사 `Burton`" not in md
    for template in ("페르소나 1", "TAM", "컨셉 후보 A", "template_pad", "템플릿 폴백"):
        assert template not in md
    pack = json.loads((tmp_path / "evidence_pack.json").read_text(encoding="utf-8"))
    assert pack["schema"].startswith("cqr.market_research.evidence_pack/")
    assert len(pack["evidence"]) == result["evidence_count"]


def test_too_little_evidence_writes_no_report(tmp_path):
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    result = run_evidence_pack(
        brief, tmp_path, "s2", searcher=lambda q, n: _searcher(q, n)[3:], fetcher=_fetcher
    )
    assert result["status"] == "insufficient_evidence"
    assert not (tmp_path / "research_report.md").exists()


def test_dry_run_is_a_plan_not_a_result(tmp_path):
    def _boom(*_a):
        raise AssertionError("dry run must not touch the network")

    result = run_evidence_pack(
        parse_brief("품목: 스키바지 / 영문명: ski pants"), tmp_path, "s3", dry_run=True, searcher=_boom, fetcher=_boom
    )
    assert result["status"] == "ok"
    md = (tmp_path / "research_report.md").read_text(encoding="utf-8")
    assert "DRY RUN" in md and "실행 예정 검색어" in md and "근거 (" not in md


def test_cli_insufficient_evidence_exit(tmp_path, monkeypatch, capsys):
    from cqr_product_pipeline.agents import evidence_pack
    from cqr_product_pipeline.cli import run_research

    monkeypatch.setattr(evidence_pack, "ddg_search", lambda q, n: [])
    monkeypatch.setattr(
        sys, "argv", ["run_research", "--brief", "품목: 스키바지 / 영문명: ski pants", "--output-dir", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as exc:
        run_research.main()
    assert exc.value.code == run_research.INSUFFICIENT_EVIDENCE_EXIT
    assert "insufficient_evidence" in capsys.readouterr().out
    assert not (tmp_path / "research_report.md").exists()
