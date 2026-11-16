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
    assert "상품 목록 페이지라 제외 2건" in (tmp_path / "research_report.md").read_text(encoding="utf-8")


def test_walmart_and_target_product_lists_are_dropped_too():
    def searcher(query, max_results):
        return [
            {"title": "Ski pants - Walmart.com", "url": "https://www.walmart.com/search?q=ski+pants", "snippet": "ski pants"},
            {"title": "Ski pants - Walmart", "url": "https://www.walmart.com/browse/clothing/ski-pants/5438", "snippet": "ski pants"},
            {"title": "Arctix ski pants", "url": "https://www.walmart.com/ip/Arctix-Ski-Pants/123", "snippet": "ski pants $39"},
            {"title": "Ski pants : Target", "url": "https://www.target.com/s?searchTerm=ski+pants", "snippet": "ski pants"},
            {"title": "All in Motion ski pants", "url": "https://www.target.com/p/ski-pants/-/A-1", "snippet": "ski pants $45"},
            # Not the shop: a press page on a subdomain is a possible market source.
            {"title": "Target ski pants sales", "url": "https://corporate.target.com/news/ski", "snippet": "ski pants sales"},
        ]

    evidence, stats = collect_evidence(parse_brief("품목: 스키바지 / 영문명: ski pants"), searcher, lambda url: "")
    assert stats["listing_dropped"] == 3
    assert {e.url for e in evidence} == {
        "https://www.walmart.com/ip/Arctix-Ski-Pants/123",
        "https://www.target.com/p/ski-pants/-/A-1",
        "https://corporate.target.com/news/ski",
    }


def test_topic_needs_the_noun_and_half_of_the_words_before_it():
    from cqr_product_pipeline.agents.evidence_pack import on_topic, scope_terms

    brief = parse_brief("품목: 카고바지 / 영문명: tactical cargo pants")
    # The Korean name never appears on an English page, so it is not a topic term.
    assert scope_terms(brief) == ["tactical cargo pants"]
    terms = scope_terms(brief)
    for text in ("Best cargo pants for work", "These tactical pants ripped", "tactical cargo pant review"):
        assert on_topic(terms, text), text
    for text in ("cargo shorts review", "work pants that last", "tactical cargo vest"):
        assert not on_topic(terms, text), text
    # Two-word names still need both words.
    assert on_topic(["ski pants"], "pants for skiing")
    assert not on_topic(["ski pants"], "ski jacket review")
    assert not on_topic(["work boots"], "hiking boots review")


def test_prices_are_us_dollar_amounts_not_market_sizes():
    from cqr_product_pipeline.agents.evidence_pack import _PRICE_RE

    text = (
        "The market will reach $17.9 billion by 2030 ($2.5M last year, $100k grants). "
        "Boots run $1,299 or $89.99, CA$129 in Canada, US$45 imported, and the cheapest is $17."
    )
    assert _PRICE_RE.findall(text) == ["$1,299", "$89.99", "$45", "$17"]


def test_foreign_prices_and_declared_locales_mark_non_us_pages():
    from cqr_product_pipeline.agents.evidence_pack import Page, foreign_locale, page_locales

    html = (
        '<html lang="en-GB"><head><meta property="og:locale" content="en_GB"/>'
        '<meta property="og:locale:alternate" content="fr_FR"/></head><body>x</body></html>'
    )
    assert page_locales(html) == ("en-gb",)
    assert [foreign_locale(t) for t in (("en-gb",), ("en-ca",), ("de",), ("en",), ("en-us",), ("es-us",), ())] == [
        True, True, True, False, False, False, False,
    ]

    def page(locale):
        body = Page(SKI_BODY)
        body.locales = (locale,)
        return body

    def searcher(query, max_results):
        return [
            {"title": "Ski pants review", "url": "https://uksnow.example.com/r", "snippet": "ski pants from £120"},
            {"title": "Ski pants deals", "url": "https://deals.example/a", "snippet": "ski pants C$129 or $99 in the US"},
            {"title": "Ski pants tested", "url": "https://gear-uk.example/t", "snippet": "ski pants tested"},
            {"title": "Ski pants tested", "url": "https://gear-us.example/t", "snippet": "ski pants tested"},
        ]

    bodies = {"https://gear-uk.example/t": page("en-gb"), "https://gear-us.example/t": page("en-us")}
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    evidence, stats = collect_evidence(brief, searcher, lambda url: bodies.get(url, ""))
    assert {e.url for e in evidence} == {"https://deals.example/a", "https://gear-us.example/t"}
    assert stats["off_market_by"] == {"currency": 1, "locale": 1}
    assert stats["off_market_domains"] == ["gear-uk.example", "uksnow.example.com"]
    md = render_markdown(brief, evidence, stats, build_queries(brief), "s")
    assert "미국 외 출처로 본 이유: 외화로만 적힌 가격 1건, 페이지가 선언한 언어·지역 1건" in md


def test_queries_without_results_are_counted():
    brief = parse_brief("품목: 스키바지 / 영문명: ski pants")
    quiet = build_queries(brief)[0][0]
    evidence, stats = collect_evidence(brief, lambda q, n: [] if q == quiet else _searcher(q, n), _fetcher)
    assert stats["empty_queries"] == [quiet]
    md = render_markdown(brief, evidence, stats, build_queries(brief), "s")
    assert f"결과가 없던 검색 1회: `{quiet}`" in md


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
    # Market queries come after six review/competitor ones: by rank alone they got 2 of 18 slots.
    assert [k for _q, k in build_queries(brief)].count("market") == 2
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
    assert by_kind["market"] == 2 and sum(by_kind.values()) == MAX_EVIDENCE
    md = (tmp_path / "research_report.md").read_text(encoding="utf-8")
    assert "시장·트렌드 근거: 할당 4건 중 2건만 확보" in md
    assert (
        f"종류별 채택 건수(할당): 리뷰·불만 근거 {by_kind['review']}(8), "
        f"경쟁사·가격 근거 {by_kind['competitor']}(6), 시장·트렌드 근거 2(4)"
    ) in md
    assert by_kind["review"] > 8 or by_kind["competitor"] > 6


def test_a_singular_noun_alone_is_another_word():
    from cqr_product_pipeline.agents.evidence_pack import on_topic

    # "Slack" the chat app filled 3 of 8 review slots of a slacks brief.
    assert not on_topic(["slacks"], "Slack Reviews | Slack takes my money every month")
    assert on_topic(["slacks"], "The best dress slacks for the office")
    assert not on_topic(["men's dress slacks"], "Slack mentioned members of the workspace")
    assert on_topic(["men's dress slacks"], "Men's slacks that survive a commute")
    # Next to another word of the term the singular is the product: "Peak Cargo Pant".
    assert on_topic(["tactical cargo pants"], "5.11 Peak Cargo Pant")
    # Whole words: no bootcut for boots, no workflow for work.
    assert not on_topic(["work boots"], "bootcut jeans for work")
    assert not on_topic(["work boots"], "workflow boots")
    assert on_topic(["work boots"], "Workers review their boots")


def test_market_queries_are_kept_and_may_name_the_category():
    brief = parse_brief(
        "품목: 슬랙스 / 영문명: dress slacks / 카테고리: men's dress pants / 시즌: 겨울 / "
        "경쟁사: Bonobos, Haggar, Dockers, Banana Republic / 가격: $40-90 / 초점: stretch, wrinkle"
    )
    queries = build_queries(brief)
    assert len(queries) <= 10
    assert [q for q, k in queries if k == "market"] == [
        "dress slacks US market trends winter",
        "men's dress pants US market size growth",
    ]

    def searcher(query, max_results):
        if "market" not in query:
            return [{"title": f"dress slacks {query}", "url": f"https://r.example/{len(query)}", "snippet": "dress slacks"}]
        return [
            {"title": "Men's Dress Pants Market Size 2030", "url": "https://m.example/a", "snippet": "men's dress pants grew 4%"},
            {"title": "Winter Wear Market", "url": "https://m.example/b", "snippet": "winter wear reached $600 billion"},
        ]

    evidence, _stats = collect_evidence(brief, searcher, lambda url: "")
    market = [e.url for e in evidence if e.kind == "market"]
    assert market == ["https://m.example/a"]  # the category counts for market rows only


def test_structured_prices_come_from_offer_data():
    from cqr_product_pipeline.agents.evidence_pack import structured_prices

    html = (
        '<html><head><script type="application/ld+json">{"@type":"Product","name":"Peak Cargo Pant",'
        '"offers":{"@type":"Offer","price":"89.49","priceCurrency":"USD"}}</script>'
        '<script type="application/ld+json">[{"@type":"Offer","price":120,"priceCurrency":"CAD"}]</script>'
        '<meta property="product:price:amount" content="99.00"/></head><body>x</body></html>'
    )
    assert structured_prices(html) == ("$89.49", "$99")
    assert structured_prices('<meta property="og:price:currency" content="EUR"><meta property="og:price:amount" content="10">') == ()


def test_competitor_pages_keep_their_price_lines_for_synthesis():
    from cqr_product_pipeline.agents.evidence_pack import Page

    body = Page(
        "5.11 Peak Cargo Pant\n$89.49\nThe tactical cargo pants we wore for a season held up well, "
        "though the cargo pockets sagged when loaded. " * 6 + "\nShipping over $50 is free."
    )
    body.offers = ("$99",)

    def searcher(query, max_results):
        host = f"shop{len(query)}.example"  # one domain per query: at most 3 items per domain
        return [{"title": "5.11 tactical cargo pants", "url": f"https://{host}/p", "snippet": "tactical cargo pants"}]

    brief = parse_brief("품목: 카고바지 / 영문명: tactical cargo pants / 경쟁사: 5.11")
    evidence, _stats = collect_evidence(brief, searcher, lambda url: body)
    item = next(e for e in evidence if e.kind == "competitor")
    assert item.source == "본문"
    assert item.page_prices[:2] == ["$99", "$89.49"]
    assert "[가격 표기 줄] 5.11 Peak Cargo Pant $89.49" in item.detail
    assert len(item.detail) > len(item.excerpt) or item.detail.startswith(item.excerpt[:40])


def test_a_refused_fetch_is_retried_with_a_browser_like_client(monkeypatch):
    import urllib.error

    from cqr_product_pipeline.agents import evidence_pack as ep

    def refused(url, timeout):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(ep, "_fetch_urllib", refused)
    monkeypatch.setattr(
        ep,
        "_fetch_impersonated",
        lambda url, timeout: '<html lang="en-US"><body><p>Ski pants review. They leaked.</p>'
        '<script type="application/ld+json">{"@type":"Offer","price":"199","priceCurrency":"USD"}</script></body></html>',
    )
    page = ep.fetch_text("https://blocked.example/review")
    assert "Ski pants review." in page and page.via == "impersonated"
    assert page.locales == ("en-us",) and page.offers == ("$199",)

    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(ep, "_fetch_urllib", not_found)
    with pytest.raises(urllib.error.HTTPError):
        ep.fetch_text("https://gone.example/x")


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


# --- Market/trend study: period, one search per year, publication dates ---


def test_period_years_are_absolute_and_never_in_the_future():
    from cqr_product_pipeline.agents.evidence_pack import period_years

    assert period_years("최근 3년", 2026) == [2024, 2025, 2026]
    assert period_years("last 2 years", 2026) == [2025, 2026]
    assert period_years("2025~2027", 2026) == [2025, 2026]
    assert period_years("2020-2026", 2026) == [2023, 2024, 2025, 2026]  # one search per year, at most 4
    assert period_years("", 2026) == []


def test_a_period_makes_a_trend_study_and_is_not_a_season():
    from datetime import date

    now = date.today().year
    brief = parse_brief("품목: 봄버재킷 / 영문명: bomber jacket / 기간: 최근 2년")
    assert (brief.study, brief.period, brief.season) == ("trend", f"{now - 1}-{now}", "")
    assert brief.origin["study"] == "기간에서 추론"
    sentence = parse_brief("2022~2024 시장 추이 품목: 봄버재킷 / 영문명: bomber jacket")
    assert (sentence.period, sentence.season, sentence.study) == ("2022-2024", "", "trend")
    # The user can keep a product study for a period.
    product = parse_brief("품목: 봄버재킷 / 영문명: bomber jacket / 기간: 2022-2024 / 조사유형: 제품")
    assert product.study == "product"
    assert "bomber jacket review complaints problems" in [q for q, _ in build_queries(product)]
    assert not any(q.endswith("2022") for q, _ in build_queries(product))


def test_trend_study_queries_each_year_then_market_size_brands_and_reviews():
    from cqr_product_pipeline.agents.evidence_pack import MAX_QUERIES

    brief = parse_brief(
        "", {"product": "봄버재킷", "product_en": "bomber jacket", "period": "2022-2024", "category": "men's outerwear"}
    )
    queries = build_queries(brief)
    assert queries == [
        ("bomber jacket trend 2022", "market"),
        ("bomber jacket trend 2023", "market"),
        ("bomber jacket trend 2024", "market"),
        ("bomber jacket market size growth", "market"),
        ("men's outerwear US market size growth", "market"),
        ("best bomber jacket brands 2024", "competitor"),
        ("bomber jacket review complaints problems", "review"),
    ]
    assert len(queries) <= MAX_QUERIES
    md = render_markdown(brief, [], {}, queries, "s", dry_run=True)
    assert "| 조사 유형 | 시장·트렌드 추이 | 기간에서 추론 |" in md
    assert "연도별로 검색한 해: 2022, 2023, 2024" in md


def test_trend_study_gives_market_evidence_most_slots_and_dates_it():
    from cqr_product_pipeline.agents.evidence_pack import TREND_KIND_QUOTA

    brief = parse_brief(
        "", {"product": "봄버재킷", "product_en": "bomber jacket", "period": "2022-2024", "category": "men's outerwear"}
    )

    def searcher(query, max_results):
        year = query.rsplit(" ", 1)[-1] if query[-4:].isdigit() else ""
        slug = query.replace(" ", "-").replace("'", "")
        return [
            {
                "title": f"Bomber jacket trends {year}".strip(),
                "url": f"https://{slug}-{n}.example/a",
                "snippet": (f"Mar 5, {year} · " if year and n == 0 else "") + f"Bomber jackets look {n} ways.",
            }
            for n in range(3)
        ]

    evidence, stats = collect_evidence(brief, searcher, lambda url: "")
    assert stats["kind_quota"] == TREND_KIND_QUOTA
    assert stats["evidence_by_kind"] == {"review": 3, "competitor": 3, "market": 12}
    assert stats["years"] == [2022, 2023, 2024]
    assert all(n > 0 for n in stats["evidence_by_year"].values())
    assert {e.published for e in evidence if e.published} == {"2022-03-05", "2023-03-05", "2024-03-05"}
    md = render_markdown(brief, evidence, stats, build_queries(brief), "s")
    assert "- 연도별 근거(" in md and "게시일 2022-03-05" in md


def test_publication_date_is_read_from_the_page_and_the_snippet():
    from cqr_product_pipeline.agents.evidence_pack import page_published, snippet_published

    assert page_published('<meta property="article:published_time" content="2025-03-04T10:00:00Z">') == "2025-03-04"
    assert (
        page_published('<script type="application/ld+json">{"datePublished": "2024-11-02T08:00:00-05:00"}</script>')
        == "2024-11-02"
    )
    assert page_published("<html><body>no date here</body></html>") == ""
    assert snippet_published("Mar 5, 2025 · Bomber jackets are back") == "2025-03-05"
    assert snippet_published("Bomber jackets are back in 2025") == ""


# --- Target customer (gender, style), update dates, market figures ---

BOMBER = {"product": "봄버재킷", "product_en": "bomber jacket"}


def test_cqr_customer_is_the_default_target_and_shapes_the_queries():
    from cqr_product_pipeline.agents.evidence_pack import FROM_DEFAULT, MAX_QUERIES, TARGET_DEFAULTS

    brief = parse_brief("", {**BOMBER, "period": "2022-2024", "category": "outerwear jackets"}, defaults=TARGET_DEFAULTS)
    assert (brief.gender, brief.style) == ("men", "military, workwear")
    assert brief.origin["gender"] == brief.origin["style"] == FROM_DEFAULT
    queries = build_queries(brief)
    assert queries[:3] == [(f"men's bomber jacket trend {y}", "market") for y in (2022, 2023, 2024)]
    texts = [q for q, _ in queries]
    assert "bomber jacket market size growth" in texts  # market reports are not split by gender
    assert "best men's military bomber jacket 2024" in texts and "best men's workwear bomber jacket 2024" in texts
    assert len(queries) <= MAX_QUERIES
    md = render_markdown(brief, [], {}, queries, "s", dry_run=True)
    assert "| 성별 타깃 | 남성 | CQR 기본 타깃 |" in md and "CQR 기본 타깃으로 검색했습니다" in md

    # A gender the user states wins; 전체 turns the target off.
    women = parse_brief("여성 봄버재킷 품목: 봄버재킷 / 영문명: bomber jacket", defaults=TARGET_DEFAULTS)
    assert women.gender == "women" and women.origin["gender"] == "문장 해석(규칙)"
    assert "women's bomber jacket review complaints problems" in [q for q, _ in build_queries(women)]
    off = parse_brief("품목: 봄버재킷 / 영문명: bomber jacket / 성별: 전체 / 스타일: 전체", defaults=TARGET_DEFAULTS)
    assert (off.gender, off.style) == ("all", "")
    off_queries = [q for q, _ in build_queries(off)]
    assert "bomber jacket review complaints problems" in off_queries
    assert not any("men's" in q or "military" in q for q in off_queries)
    assert "| 스타일 타깃 | 전체(스타일 무관) | 입력 필드 |" in render_markdown(off, [], {}, [], "s", dry_run=True)
    # Korean style words are translated or reported as not searched; a gendered name is not doubled.
    styled = parse_brief("품목: 봄버재킷 / 영문명: bomber jacket / 스타일: 밀리터리, 캠핑", defaults=TARGET_DEFAULTS)
    assert styled.style == "military, 캠핑"
    assert "스타일 `캠핑`" in render_markdown(styled, [], {}, build_queries(styled), "s", dry_run=True)
    slacks = parse_brief("", {"product": "슬랙스", "product_en": "men's dress slacks"}, defaults=TARGET_DEFAULTS)
    assert slacks.gender == "men"
    assert not any("men's men's" in q for q, _ in build_queries(slacks))


def test_cli_researches_for_the_cqr_customer_by_default(tmp_path, monkeypatch):
    from cqr_product_pipeline.cli import run_research

    seen = {}

    def fake_pack(brief, output_dir, session_id, dry_run=False):
        seen["brief"] = brief
        return {"status": "insufficient_evidence", "evidence_count": 0, "stats": {}}

    monkeypatch.setattr(run_research, "run_evidence_pack", fake_pack)
    monkeypatch.setattr(
        sys, "argv", ["run_research", "--brief", "품목: 스키바지 / 영문명: ski pants", "--output-dir", str(tmp_path)]
    )
    with pytest.raises(SystemExit):
        run_research.main()
    assert (seen["brief"].gender, seen["brief"].style) == ("men", "military, workwear")


def test_results_titled_for_the_other_gender_are_dropped():
    def searcher(query, max_results):
        return [
            {"title": "23 Best Bomber Jackets for Women in 2024", "url": "https://w.example/a", "snippet": "bomber jackets"},
            {"title": "Best Bomber Jackets for Men and Women", "url": "https://mw.example/b", "snippet": "bomber jackets"},
            {"title": "Bomber jacket review", "url": "https://r.example/c", "snippet": "my bomber jacket ripped"},
        ]

    brief = parse_brief("", {**BOMBER, "gender": "남성"})
    evidence, stats = collect_evidence(brief, searcher, lambda url: "")
    urls = {e.url for e in evidence}
    assert "https://w.example/a" not in urls
    assert {"https://mw.example/b", "https://r.example/c"} <= urls
    assert stats["off_target_dropped"] == 1
    md = render_markdown(brief, evidence, stats, build_queries(brief), "s")
    assert "제목이 다른 성별 대상이라 제외 1건" in md


def test_update_date_is_the_content_date():
    from cqr_product_pipeline.agents.evidence_pack import Page, about_year, page_updated

    html = (
        '<meta content="2016-08-25T23:17:00Z" property="article:published_time">'
        '<script type="application/ld+json">{"datePublished":"2016-08-25","dateModified":"2026-01-20T15:52:00-05:00"}'
        "</script>"
    )
    assert page_updated(html) == "2026-01-20"
    assert page_updated('<meta property="article:published_time" content="2025-03-04">') == ""

    page = Page("short")
    page.published, page.updated = "2016-08-25", "2023-05-01"
    brief = parse_brief("", {**BOMBER, "period": "2022-2024"})

    def searcher(query, max_results):
        return [{"title": "Best bomber jackets", "url": "https://upd.example/b", "snippet": "bomber jackets tested"}]

    evidence, stats = collect_evidence(brief, searcher, lambda url: page)
    (item,) = evidence
    assert (item.published, item.updated, item.before_period) == ("2016-08-25", "2023-05-01", False)
    assert about_year(item, 2023) and not about_year(item, 2022)
    assert stats["evidence_by_year"]["2023"] == 1
    assert "게시일 2016-08-25 · 수정일 2023-05-01" in render_markdown(brief, evidence, stats, [], "s")


def test_trend_study_uses_pages_older_than_the_period_last():
    from cqr_product_pipeline.agents.evidence_pack import MAX_EVIDENCE

    old = {"title": "Bomber jacket review", "url": "https://old.example/a", "snippet": "Dec 8, 2010 · bomber jacket notes"}
    rows = [old] + [
        {"title": f"Bomber jacket guide {n}", "url": f"https://new{n}.example/x", "snippet": f"bomber jacket {n}"}
        for n in range(MAX_EVIDENCE + 2)
    ]
    brief = parse_brief("", {**BOMBER, "period": "2022-2024"})
    evidence, stats = collect_evidence(brief, lambda q, n: rows, lambda url: "")
    assert len(evidence) == MAX_EVIDENCE
    assert "https://old.example/a" not in {e.url for e in evidence}  # rank 0, but older than the period
    assert (stats["before_period_found"], stats["before_period_kept"]) == (1, 0)

    # With room to spare it is kept and marked.
    evidence, stats = collect_evidence(brief, lambda q, n: rows[:3], lambda url: "")
    kept = next(e for e in evidence if e.url == old["url"])
    assert kept.before_period and stats["before_period_kept"] == 1
    assert "조사 기간 이전 글" in render_markdown(brief, evidence, stats, [], "s")


def test_market_figure_lines_are_kept_on_market_pages():
    body = "\n".join(
        [
            "United States Outerwear Market Report",
            "Explore potential revenue opportunities across the outerwear jackets segmentation landscape, "
            "including Jackets, Men, Synthetics.",
            "Base year 2024",
            "USD 41.07 Billion",
            "Based on Deep Market Insights findings, the United States Outerwear Market reached USD 41.07 Billion "
            "in 2024 and is estimated to attain USD 54.91 Billion by 2033.",
            "Forecast CAGR 3.37%",
        ]
        + ["Our analysts cover apparel demand across regions and channels every quarter."] * 8
    )
    brief = parse_brief("", {**BOMBER, "category": "outerwear jackets"})

    def searcher(query, max_results):
        if "market" not in query:
            return []
        return [{"title": "United States Outerwear Market Size Report", "url": "https://m.example/us", "snippet": "report"}]

    evidence, _stats = collect_evidence(brief, searcher, lambda url: body)
    (item,) = evidence
    assert item.kind == "market" and item.source == "본문"
    assert "USD 41.07 Billion" in item.excerpt
    assert "[시장 수치 줄]" in item.detail and "CAGR 3.37%" in item.detail
