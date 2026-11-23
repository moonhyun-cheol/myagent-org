"""Google Trends in a trend study: fixed comparison basis, spikes, query conditions in the pack."""
import json
from datetime import date, timedelta

from cqr_product_pipeline.agents.evidence_pack import parse_brief, run_evidence_pack
from cqr_product_pipeline.agents.google_trends import (
    TrendsUnavailable,
    direction,
    parse_timeline,
    study_trends,
    trend_metrics,
    trends_keywords,
)

SEASON = [40, 36, 35, 28, 21, 17, 20, 23, 36, 48, 58, 54]


def _monthly(by_year: dict[int, list[int]], partial_last: bool = True, second: int | None = None) -> dict:
    points = []
    for year, values in sorted(by_year.items()):
        for month, value in enumerate(values, 1):
            row = [value] if second is None else [value, second]
            points.append({"date": f"{year}-{month:02d}-01", "values": row, "partial": False})
    points[-1]["partial"] = partial_last
    return {"resolution": "MONTH", "points": points}


def _spring_spike_series() -> dict:
    years = {2023: SEASON, 2024: [v + 2 for v in SEASON], 2025: [v + 4 for v in SEASON]}
    y2026 = [v + 6 for v in SEASON][:11]  # Jan-Nov, November partial
    y2026[3], y2026[4], y2026[5] = 100, 71, 45  # April-June: one state's spike (June: 2.4x its median 19)
    years[2026] = y2026
    return _monthly(years)


def test_years_are_compared_on_the_same_window_without_the_partial_month_or_the_spike():
    m = trend_metrics(["bomber jacket"], _spring_spike_series(), [2024, 2025, 2026])
    assert m["status"] == "ok" and m["resolution"] == "MONTH"
    assert m["window"] == "1~10월" and m["last_complete"] == "2026-10-01" and m["dropped_partial"] == 1
    assert [s["label"] for s in m["spikes"]] == ["2026-04", "2026-05", "2026-06"]
    rows = {r["year"]: r for r in m["years"]}
    assert list(rows) == [2023, 2024, 2025, 2026]
    assert rows[2023]["in_period"] is False and rows[2024]["in_period"] is True
    # Same Jan-Oct window in every year; 2026 without April-June.
    assert rows[2023]["window_avg"] == round(sum(SEASON[:10]) / 10, 1)
    kept_2026 = [v + 6 for i, v in enumerate(SEASON[:10]) if i not in (3, 4, 5)]
    assert rows[2026]["window_avg"] == round(sum(kept_2026) / len(kept_2026), 1)
    assert rows[2026]["window_avg_all"] > rows[2026]["window_avg"]
    expected = round((rows[2024]["window_avg"] / rows[2023]["window_avg"] - 1) * 100, 1)
    assert rows[2024]["yoy_pct"] == expected
    # The spike month is not the year's high; November is (complete years only get a full-year average).
    assert (rows[2025]["high_label"], rows[2026]["high_label"]) == ("11월", "10월")
    assert rows[2025]["full_avg"] is not None and rows[2026]["full_avg"] is None
    assert "눌려" in m["scale_note"]
    # The last three complete months (Aug-Oct) beside it, against the same months a year earlier.
    assert m["recent_window"] == "8~10월"
    assert rows[2025]["recent_avg"] == round(sum(v + 4 for v in SEASON[7:10]) / 3, 1)
    assert rows[2026]["recent_yoy_pct"] == round((rows[2026]["recent_avg"] / rows[2025]["recent_avg"] - 1) * 100, 1)


def test_a_long_rise_is_a_level_shift_and_stays_in_the_average():
    years = {2023: SEASON, 2024: SEASON, 2025: SEASON, 2026: [v * 2 + 20 for v in SEASON][:11]}
    m = trend_metrics(["x"], _monthly(years), [2024, 2025, 2026])
    assert m["spikes"] == [] and len(m["level_shifts"]) >= 4
    rows = {r["year"]: r for r in m["years"]}
    assert rows[2026]["window_avg"] == rows[2026]["window_avg_all"]
    assert rows[2026]["direction"] == "증가"


def test_direction_needs_five_percent_and_two_points():
    assert direction(31.0, 30.0) == "보합"  # +3.3%
    assert direction(11.5, 10.0) == "보합"  # +15% but only 1.5 points
    assert direction(33.0, 30.0) == "증가"
    assert direction(27.0, 30.0) == "감소"
    assert direction(30.0, None) == ""


def test_weekly_series_small_keyword_and_share_of_the_main_keyword():
    start = date(2023, 1, 1)
    points = []
    for week in range(150):
        day = start + timedelta(weeks=week)
        main = 30 + (day.month in (10, 11, 12)) * 20
        points.append({"date": day.isoformat(), "values": [main, 3], "partial": week == 149})
    m = trend_metrics(["bomber jacket", "mens bomber jacket"], {"resolution": "WEEK", "points": points}, [2024, 2025])
    last = date.fromisoformat(m["last_complete"])
    assert m["window"] == f"1월 1일~{last.month}월 {last.day}일"
    extra = m["keywords"][0]
    assert extra["small"] is True and extra["yoy_pct"] is None
    assert 5 < extra["ratio_pct"] < 12


def test_timeline_rows_keep_missing_data_and_the_partial_mark():
    body = {
        "default": {
            "timelineData": [
                {"time": "1672531200", "value": [40, 0], "hasData": [True, False]},
                {"time": "1675209600", "value": [36, 4], "hasData": [True, True], "isPartial": True},
            ]
        }
    }
    rows = parse_timeline(body, 2)
    assert rows == [
        {"date": "2023-01-01", "values": [40, None], "partial": False},
        {"date": "2023-02-01", "values": [36, 4], "partial": True},
    ]


def test_keywords_add_the_gendered_search():
    assert trends_keywords("Bomber  Jacket", "men") == ["bomber jacket", "mens bomber jacket"]
    assert trends_keywords("bomber jacket", "women") == ["bomber jacket", "womens bomber jacket"]
    assert trends_keywords("men's bomber jacket", "men") == ["men's bomber jacket"]
    assert trends_keywords("bomber jacket", "all") == ["bomber jacket"]
    assert trends_keywords("", "men") == []


def test_conditions_and_rules_are_recorded_and_a_refusal_is_reported():
    calls = []

    def fetcher(keywords, time_range):
        calls.append((keywords, time_range))
        return _spring_spike_series()

    ok = study_trends(["bomber jacket"], [2024, 2025, 2026], fetcher, date(2026, 11, 16))
    assert calls == [(["bomber jacket"], "2023-01-01 2026-11-16")]
    assert ok["status"] == "ok" and ok["conditions"]["resolution"] == "MONTH"
    assert ok["conditions"]["geo"] == "US" and ok["conditions"]["fetched"] == "2026-11-16"
    assert "date=2023-01-01%202026-11-16&geo=US&q=bomber%20jacket" in ok["url"]
    assert any("같은 기간" in line for line in ok["lines"]) and set(ok["rules"]) >= {"window", "spike", "direction"}

    def refused(keywords, time_range):
        raise TrendsUnavailable("HTTP 429")

    bad = study_trends(["bomber jacket"], [2024, 2025, 2026], refused, date(2026, 11, 16))
    assert (bad["status"], bad["error"]) == ("unavailable", "HTTP 429")
    assert bad["conditions"]["time"] == "2023-01-01 2026-11-16"


def _trend_brief():
    return parse_brief(
        "",
        {"product": "봄버재킷", "product_en": "bomber jacket", "period": "2024-2026", "gender": "men", "style": "military"},
    )


def _searcher(query, max_results):
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


def test_trend_pack_cites_trends_as_the_last_evidence_item(tmp_path):
    seen = []

    def fetcher(keywords, time_range):
        seen.append(keywords)
        return _spring_spike_series()

    result = run_evidence_pack(
        _trend_brief(), tmp_path, "t1", searcher=_searcher, fetcher=lambda url: "", trends_fetcher=fetcher,
        today=date(2026, 11, 16),
    )
    assert result["status"] == "ok" and seen == [["bomber jacket", "mens bomber jacket"]]
    pack = json.loads((tmp_path / "evidence_pack.json").read_text(encoding="utf-8"))
    item = pack["evidence"][-1]
    assert pack["trends"]["status"] == "ok" and pack["trends"]["evidence_id"] == item["id"]
    assert (item["source"], item["domain"], item["kind"]) == ("데이터", "trends.google.com", "market")
    assert "2025년 1~10월 평균" in item["detail"] and "전년 대비" in item["detail"]
    assert pack["stats"]["trends"] == "ok" and pack["trends"]["points"]
    md = result["markdown"]
    assert "## 검색 관심도 (Google Trends)" in md and "| 연도 | 1~10월 평균 (전년 대비) | 최근 8~10월 평균 (전년 대비) |" in md
    assert "| 2023 (비교 기준 해) |" in md and "일시적 이상치로 제외: 2026-04 100" in md


def test_a_refused_trends_call_is_named_and_the_web_pack_still_written(tmp_path):
    def refused(keywords, time_range):
        raise TrendsUnavailable("HTTP 429")

    result = run_evidence_pack(
        _trend_brief(), tmp_path, "t2", searcher=_searcher, fetcher=lambda url: "", trends_fetcher=refused,
        today=date(2026, 11, 16),
    )
    assert result["status"] == "ok"
    pack = json.loads((tmp_path / "evidence_pack.json").read_text(encoding="utf-8"))
    assert pack["trends"]["status"] == "unavailable" and pack["stats"]["trends_error"] == "HTTP 429"
    assert all(e["source"] != "데이터" for e in pack["evidence"])
    assert "조회하지 못했습니다(HTTP 429)" in result["markdown"]
    assert "검색 관심도(Google Trends): 조회 실패(HTTP 429)" in result["markdown"]


def test_product_study_and_injected_searcher_make_no_trends_call(tmp_path):
    calls = []
    product = parse_brief("", {"product": "봄버재킷", "product_en": "bomber jacket"})
    run_evidence_pack(product, tmp_path / "a", "p", searcher=_searcher, fetcher=lambda url: "",
                      trends_fetcher=lambda k, t: calls.append(k))
    run_evidence_pack(_trend_brief(), tmp_path / "b", "q", searcher=_searcher, fetcher=lambda url: "")
    assert calls == []
    assert "trends" not in json.loads((tmp_path / "b" / "evidence_pack.json").read_text(encoding="utf-8"))
