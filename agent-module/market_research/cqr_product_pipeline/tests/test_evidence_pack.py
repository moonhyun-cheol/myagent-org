"""Evidence-pack research: structured brief, on-topic evidence only, no template fill."""
import json
import sys

import pytest

from cqr_product_pipeline.agents.evidence_pack import (
    brief_gate,
    build_queries,
    collect_evidence,
    parse_brief,
    render_markdown,
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


def _korean(text):
    return any("가" <= ch <= "힣" for ch in text)


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
    brief = parse_brief(
        "",
        {
            "category": "아웃도어",
            "product_en": "outdoor apparel",
            "competitors": "Columbia, Patagonia",
            "price_band": "$60-150",
        },
    )
    assert brief_gate(brief) is None
    assert brief.product == "" and brief.category == "아웃도어"
    queries = [q for q, _ in build_queries(brief)]
    assert any(q.startswith("Columbia outdoor apparel") for q in queries)
    assert any("$60-150" in q for q in queries)


def test_queries_target_the_us_market_in_english():
    brief = parse_brief(
        "품목: 작업화 / 영문명: work boots / 시즌: 겨울 / 초점: waterproof, 착화감 / 가격: 미드~미드하이 / 경쟁사: Keen, 케이투"
    )
    assert brief_gate(brief) is None
    queries = [q for q, _ in build_queries(brief)]
    assert queries and not any(_korean(q) for q in queries)
    assert "work boots waterproof complaints" in queries
    assert "Keen work boots review price" in queries
    assert "work boots US market trends winter" in queries
    md = render_markdown(brief, [], {}, build_queries(brief), "s", dry_run=True)
    assert "대상 시장: 미국" in md
    # Korean values are reported as left out, not searched.
    for left_out in ("초점 `착화감`", "가격대 `미드~미드하이`", "경쟁사 `케이투`"):
        assert left_out in md
    assert "시즌 `겨울`" not in md  # translated to winter, so it was searched


def test_season_codes_are_spelled_out_for_english_queries():
    queries = [q for q, _ in build_queries(parse_brief("품목: 스키바지 / 영문명: ski pants / 시즌: 2027 FW"))]
    assert "ski pants US market trends 2027 fall winter" in queries


@pytest.mark.parametrize(
    "text",
    ["품목: 텀블러", "카테고리: 아웃도어 / 경쟁사: Columbia, Patagonia", "품목: 텀블러 / 영문명: 텀블러"],
)
def test_korean_name_without_an_english_name_is_not_searched(text):
    brief = parse_brief(text)
    assert brief_gate(brief) == "no_english_name"
    assert build_queries(brief) == []


def test_rule_dictionary_supplies_the_english_name():
    brief = parse_brief("품목: 스키바지")
    assert brief_gate(brief) is None
    assert "ski" in brief.search_term and not _korean(brief.search_term)


def test_sources_outside_the_us_market_are_dropped():
    def searcher(query, max_results):
        return [
            {"title": "Ski pants review", "url": "https://gear.example/us", "snippet": "ski pants leaked at the seat"},
            {"title": "스키바지 후기 단점 정리", "url": "https://blog.naver.com/x/1", "snippet": "스키바지 ski pants 솔직 후기입니다"},
            {"title": "Best ski pants UK", "url": "https://www.snowmag.co.uk/ski-pants", "snippet": "ski pants from £120"},
            {"title": "Ski pants guide", "url": "https://shop.example.kr/ski", "snippet": "ski pants sizing"},
            {"title": "Ski pants thread", "url": "https://forum.example.io/t/2", "snippet": "my ski pants ripped"},
        ]

    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    evidence, stats = collect_evidence(brief, searcher, lambda url: "")
    assert {e.url for e in evidence} == {"https://gear.example/us", "https://forum.example.io/t/2"}
    assert stats["off_market_dropped"] == 3
    assert stats["off_market_domains"] == ["blog.naver.com", "shop.example.kr", "snowmag.co.uk"]
    assert stats["results"] == 5


def test_country_editions_of_a_site_are_not_us_sources():
    def searcher(query, max_results):
        return [
            {"title": "Ski pants pin", "url": "https://ca.pinterest.com/pin/1", "snippet": "ski pants outfit"},
            {"title": "Ski pants guide", "url": "https://en-gb.example.com/ski", "snippet": "ski pants guide"},
            {"title": "Ski pants board", "url": "https://kr.pinterest.com/pin/2", "snippet": "ski pants"},
            # Not a country edition: investor relations, a language label, a city label, the US locale.
            {"title": "Ski pants annual report", "url": "https://ir.example.com/report", "snippet": "ski pants sales grew"},
            {"title": "Ski pants article", "url": "https://en.wikipedia.org/wiki/Ski_pants", "snippet": "ski pants are trousers"},
            {"title": "Ski pants deals", "url": "https://ny.example.com/deals", "snippet": "ski pants in NYC"},
            {"title": "Ski pants US store", "url": "https://en-us.example.com/ski", "snippet": "ski pants US"},
        ]

    evidence, stats = collect_evidence(parse_brief("품목: 스키바지 / 영문명: ski pants"), searcher, lambda url: "")
    assert stats["off_market_domains"] == ["ca.pinterest.com", "en-gb.example.com", "kr.pinterest.com"]
    assert {e.domain for e in evidence} == {"ir.example.com", "en.wikipedia.org", "ny.example.com", "en-us.example.com"}


def test_amazon_product_lists_are_dropped_but_products_and_reviews_are_kept(tmp_path):
    def searcher(query, max_results):
        return [
            {
                "title": "Amazon.com: Ski Pants",
                "url": "https://www.amazon.com/ski-pants/s?k=ski+pants",
                "snippet": "Results. Check each product page for other buying options. ski pants",
            },
            {"title": "Amazon.com: Burton ski pants", "url": "https://www.amazon.com/b?node=123", "snippet": "ski pants"},
            {"title": "Burton ski pants", "url": "https://www.amazon.com/Burton-Pants/dp/B07X2GG8BX", "snippet": "ski pants $199"},
            {
                "title": "Customer reviews: ski pants",
                "url": "https://www.amazon.com/Ski-Pants/product-reviews/B000GC7GVS",
                "snippet": "my ski pants leaked at the seat",
            },
            {"title": "Best ski pants review", "url": "https://gear.example/ski-pants", "snippet": "ski pants tested"},
        ]

    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    result = run_evidence_pack(brief, tmp_path, "s5", searcher=searcher, fetcher=lambda url: "")
    assert result["status"] == "ok"
    assert result["stats"]["listing_dropped"] == 2 and result["stats"]["results"] == 5
    pack = json.loads((tmp_path / "evidence_pack.json").read_text(encoding="utf-8"))
    assert {e["url"] for e in pack["evidence"]} == {
        "https://www.amazon.com/Burton-Pants/dp/B07X2GG8BX",
        "https://www.amazon.com/Ski-Pants/product-reviews/B000GC7GVS",
        "https://gear.example/ski-pants",
    }
    assert "Amazon 상품 목록 페이지라 제외 2건" in (tmp_path / "research_report.md").read_text(encoding="utf-8")


SHARE_BRIEF = "품목: 스키바지 / 영문명: ski pants / 경쟁사: Burton, Patagonia / 가격: $90-280"


def _share_searcher(market_rows=6):
    """Distinct on-topic rows for every query; each domain names its kind (review0-1.example, market6-0.example)."""
    kinds = dict(build_queries(parse_brief(SHARE_BRIEF)))
    order = {query: n for n, query in enumerate(kinds)}

    def searcher(query, max_results):
        kind = kinds[query]
        return [
            {
                "title": f"ski pants {kind} {r}",
                "url": f"https://{kind}{order[query]}-{r}.example/p",
                "snippet": f"ski pants {kind} note {r}",
            }
            for r in range(market_rows if kind == "market" else max_results)
        ]

    return searcher


def test_every_evidence_kind_gets_its_share():
    from cqr_product_pipeline.agents.evidence_pack import FETCH_QUOTA, KIND_QUOTA, MAX_EVIDENCE, MAX_FETCH

    brief = parse_brief(SHARE_BRIEF)
    # One market query after six review/competitor ones: by rank alone it got 2 of 18 slots.
    assert [k for _q, k in build_queries(brief)].count("market") == 1
    fetched: list[str] = []

    def fetcher(url):
        fetched.append(url.split("//")[1].split("-")[0].rstrip("0123456789"))
        return ""

    evidence, stats = collect_evidence(brief, _share_searcher(), fetcher)
    assert {kind: sum(1 for e in evidence if e.kind == kind) for kind in KIND_QUOTA} == KIND_QUOTA
    assert stats["evidence_by_kind"] == KIND_QUOTA and len(evidence) == MAX_EVIDENCE
    assert {kind: fetched.count(kind) for kind in FETCH_QUOTA} == FETCH_QUOTA and len(fetched) == MAX_FETCH
    # Ids run in the order the pack lists its sections.
    assert [e.id for e in evidence] == [f"E{n}" for n in range(1, MAX_EVIDENCE + 1)]
    sections = ["review", "competitor", "market"]
    assert [e.kind for e in evidence] == sorted((e.kind for e in evidence), key=sections.index)


def test_a_kind_short_of_results_hands_its_slots_to_the_others(tmp_path):
    from cqr_product_pipeline.agents.evidence_pack import MAX_EVIDENCE

    result = run_evidence_pack(
        parse_brief(SHARE_BRIEF), tmp_path, "s4", searcher=_share_searcher(market_rows=1), fetcher=lambda url: ""
    )
    by_kind = result["stats"]["evidence_by_kind"]
    assert by_kind["market"] == 1 and sum(by_kind.values()) == MAX_EVIDENCE
    md = (tmp_path / "research_report.md").read_text(encoding="utf-8")
    assert "시장·트렌드 근거: 할당 4건 중 1건만 확보" in md
    assert "종류별 채택 건수(할당): 리뷰·불만 근거 9(8), 경쟁사·가격 근거 8(6), 시장·트렌드 근거 1(4)" in md


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


# Reduced copies of the two layouts search.yahoo.com serves (structure taken from saved live pages).
# Result blocks are nested the way the parsed live pages are: the next result sits inside the previous one.
YAHOO_DESKTOP = """
<div id="web"><ol><li>
<div class="dd fst algo algo-sr relsrch richAlgo">
  <div class="compTitle options-toggle">
    <a class="d-ib" href="https://r.search.yahoo.com/_ylt=A;_ylu=B/RV=2/RE=1/RO=10/RU=https%3a%2f%2fgear.example%2fski-pants%3fa%3d1/RK=2/RS=x-">
      <div class="d-ib"><span><span class="d-b">Gear Example</span></span></div>
      <h3 class="title"><span class="d-b">Best ski pants review</span></h3>
    </a>
  </div>
  <div class="compText aAbs"><p><span>Jan 2, 2026</span> We tested ski pants for two seasons.</p></div>
  <div class="dd algo algo-sr relsrch Sr">
    <div class="compTitle options-toggle">
      <a href="https://r.search.yahoo.com/_ylt=C;_ylu=D/RV=2/RE=1/RO=10/RU=https%3a%2f%2fforum.example%2ft%2f1/RK=2/RS=y-">
        <div><span><span>Forum Example</span></span></div>
        <h3 class="title"><span>Ski pants leaking thread</span></h3>
      </a>
    </div>
    <div class="dd lst algo algo-sr relsrch richAlgo">
      <div class="compTitle options-toggle">
        <a href="https://shop.example/burton"><h3 class="title"><span>Burton ski pants price</span></h3></a>
      </div>
      <div class="compTitle"><h2 class="title"><span>Searches related to ski pants</span></h2></div>
      <div class="compText aAbs"><p>related: ski bibs</p></div>
    </div>
  </div>
</div>
</li></ol></div>
"""
YAHOO_MOBILE = """
<section class="dd fst algo s-algo algo-sr richAlgo">
  <div class="compTitle p-r">
    <h3 class="title d-ib">
      <a class="s-title fz-m" aria-label="Best ski pants review"
         href="https://r.search.yahoo.com/_ylt=A;_ylu=B/RV=2/RE=1/RO=10/RU=https%3a%2f%2fgear.example%2fski-pants/RK=2/RS=x-">
        <span><span class="fz-13">Gear Example</span><span class="fc-battleship"> \u203a ski-pants</span></span>
      </a>
    </h3>
    <div><a class="thmb algo-favicon" href="https://r.search.yahoo.com/_ylt=Z/RU=https%3a%2f%2fgear.example%2f/RK=2"><img></a></div>
  </div>
  <div class="compText"><p class="s-desc">We tested ski pants for two seasons.</p></div>
  <section class="dd lst algo s-algo algo-sr Sr">
    <div class="compTitle p-r">
      <h3 class="title d-ib">
        <a class="s-title fz-m" aria-label="Ski pants leaking thread" href="https://forum.example/t/1"><span>Forum</span></a>
      </h3>
    </div>
    <div class="compText"><p class="s-desc">my ski pants leak at the seat</p></div>
    <div class="compTitle u-plrEdges s-header"><h3 class="title"><span class="s-title">Related searches</span></h3></div>
  </section>
</section>
"""


def test_yahoo_parser_reads_the_desktop_layout_without_gluing_titles():
    pytest.importorskip("lxml")
    from cqr_product_pipeline.agents.evidence_pack import parse_yahoo_results

    rows = parse_yahoo_results(YAHOO_DESKTOP)
    assert [r["title"] for r in rows] == [
        "Best ski pants review",
        "Ski pants leaking thread",
        "Burton ski pants price",
    ]
    # Redirect links are decoded to the real URL.
    assert [r["url"] for r in rows] == [
        "https://gear.example/ski-pants?a=1",
        "https://forum.example/t/1",
        "https://shop.example/burton",
    ]
    assert rows[0]["snippet"] == "Jan 2, 2026 We tested ski pants for two seasons."
    # A result without its own text gets none: the "related searches" text is not borrowed.
    assert rows[1]["snippet"] == "" and rows[2]["snippet"] == ""


def test_yahoo_parser_reads_the_mobile_layout_ddgs_returns_nothing_for():
    pytest.importorskip("lxml")
    from cqr_product_pipeline.agents.evidence_pack import parse_yahoo_results

    rows = parse_yahoo_results(YAHOO_MOBILE)
    assert [(r["title"], r["url"], r["snippet"]) for r in rows] == [
        ("Best ski pants review", "https://gear.example/ski-pants", "We tested ski pants for two seasons."),
        ("Ski pants leaking thread", "https://forum.example/t/1", "my ski pants leak at the seat"),
    ]
    assert parse_yahoo_results("<html><body><p>consent page</p></body></html>") == []


def test_search_uses_yahoo_first_and_falls_back_to_the_library(monkeypatch):
    from cqr_product_pipeline.agents import evidence_pack

    monkeypatch.setattr(evidence_pack, "SEARCH_SPACING", 0)
    monkeypatch.setattr(
        evidence_pack, "yahoo_search", lambda q, n: [{"title": "t", "url": "https://a.example/1", "snippet": "s"}]
    )
    assert evidence_pack.ddg_search("ski pants", 6) == [
        {"title": "t", "url": "https://a.example/1", "snippet": "s", "via": "yahoo"}
    ]

    class _Library:
        def __init__(self, **_kwargs):
            pass

        def text(self, query, **_kwargs):
            return [{"title": "lib", "href": "https://b.example/2", "body": "from library"}]

    def _broken(query, max_results):
        raise RuntimeError("markup changed")

    import ddgs

    monkeypatch.setattr(ddgs, "DDGS", _Library)
    for failing in (_broken, lambda q, n: []):
        monkeypatch.setattr(evidence_pack, "yahoo_search", failing)
        assert evidence_pack.ddg_search("ski pants", 6) == [
            {"title": "lib", "url": "https://b.example/2", "snippet": "from library", "via": "ddgs"}
        ]


def test_unreadable_hosts_keep_their_snippet_and_use_no_fetch_slot():
    fetched: list[str] = []

    def searcher(query, max_results):
        return [
            {"title": "Ski pants thread", "url": "https://www.reddit.com/r/skiing/comments/1/", "snippet": "my ski pants ripped", "via": "yahoo"},
            {"title": "Ski pants", "url": "https://www.amazon.com/dp/B0", "snippet": "ski pants $89", "via": "yahoo"},
            {"title": "Best ski pants review", "url": "https://gear.example/ski-pants", "snippet": "ski pants tested", "via": "yahoo"},
        ]

    def fetcher(url):
        fetched.append(url)
        return SKI_BODY

    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    evidence, stats = collect_evidence(brief, searcher, fetcher)
    assert fetched == ["https://gear.example/ski-pants"]
    assert stats["fetch_attempted"] == 1 and stats["fetch_ok"] == 1
    sources = {e.domain: e.source for e in evidence}
    assert sources == {"reddit.com": "요약문", "amazon.com": "요약문", "gear.example": "본문"}
    # Every query was answered by the same path; the pack reports it.
    assert stats["search_via"] == {"yahoo": stats["queries"]}
    md = render_markdown(brief, evidence, stats, build_queries(brief), "s")
    assert f"검색 경로: Yahoo 직접 조회 {stats['queries']}회" in md


def test_report_has_excerpts_and_no_template_sections(tmp_path):
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants / 경쟁사: Burton, Arcteryx")
    result = run_evidence_pack(brief, tmp_path, "s1", searcher=_searcher, fetcher=_fetcher)
    assert result["status"] == "ok"
    md = (tmp_path / "research_report.md").read_text(encoding="utf-8")
    assert "브리프 해석" in md and "https://gear.example/ski-pants" in md
    assert "대상 시장: 미국" in md and "미국 외 출처라 제외 0건" in md
    assert "경쟁사 `Arcteryx`: 이 브랜드를 언급한 근거 0건" in md
    assert "경쟁사 `Burton`" not in md
    for template in ("페르소나 1", "TAM", "컨셉 후보 A", "template_pad", "템플릿 폴백"):
        assert template not in md
    pack = json.loads((tmp_path / "evidence_pack.json").read_text(encoding="utf-8"))
    assert pack["schema"].startswith("cqr.market_research.evidence_pack/")
    assert pack["market"] == "US"
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
