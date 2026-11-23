"""Google Trends (US web search interest) for a market/trend study.

Web articles say what was written about a year; they cannot show how much demand moved between
years. Search interest can, as long as every year is read from one series and compared on the
same basis. A free-written merged report compared a different window for each claim (fall
average, year-end peak, Jan-Oct average) and got +1%, +15% and -2.4% for the same year, so the
basis is fixed here and written into the pack with the data.

Rules (``RULES`` has the Korean text shown to the reader):

- Query: the product's English name and, for a gendered target, ``mens …`` / ``womens …`` in one
  request (one scale), geo US, all categories, web search, from January 1 of the year before the
  period (the first year needs a previous year) to today, UTC. Google returns weekly points for
  a range up to about three years and monthly points for a longer one; the resolution is recorded.
- The point Google marks partial (the current week or month) is dropped.
- Year over year: the average of the same calendar window in every year, January 1 to the date
  of the last complete point (January-October for a run in November). A complete year also gets
  its full-year average; the high and low are read over the whole year. The last three months
  (13 weeks) before the last complete point, against the same dates a year earlier, are shown
  beside it: a year-to-date average can rise on its first months while the season is flat.
- Spike: a point at least ``SPIKE_RATIO`` times the median of the same month (weekly: the same
  week +-1) in the other years and at least ``SPIKE_MIN_POINTS`` above it. A run of such points
  up to three months long is a temporary spike, left out of averages, highs and lows; a longer
  run is a level shift and kept. Judged on the main keyword only, with at least two other years.
- Direction: up from +5%, down from -5%, flat in between or when the averages differ by less
  than 2 index points.
- A keyword averaging under 10 points gets no year-over-year change: values are integers, so
  one point is 10% or more.

The index is relative (the highest point of the request is 100): it is interest, not search
volume, sales or revenue, and it is never compared with a revenue growth rate.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Callable
from urllib.parse import quote

TRENDS_EXPLORE_URL = "https://trends.google.com/trends/api/explore"
TRENDS_MULTILINE_URL = "https://trends.google.com/trends/api/widgetdata/multiline"
TRENDS_PAGE_URL = "https://trends.google.com/trends/explore"
TRENDS_DOMAIN = "trends.google.com"
TRENDS_SOURCE = "데이터"  # Evidence.source of the Trends item (pages are 본문 / 요약문)
TRENDS_TIMEOUT = 15
TRENDS_ATTEMPTS = 3
SPIKE_RATIO = 2.0
SPIKE_MIN_POINTS = 15
SPIKE_MAX_RUN = {"MONTH": 3, "WEEK": 13}
FLAT_PCT = 5.0
FLAT_POINTS = 2.0
SMALL_AVG = 10.0

RULES = {
    "window": "연도 비교는 매년 같은 기간(1월 1일부터 마지막 완료 구간의 날짜까지) 평균만 씁니다.",
    "recent": "최근 3개월(주별이면 13주)과 전년 같은 날짜 구간의 평균을 함께 보여 줍니다(참고 기준).",
    "partial": "Google이 집계 중(partial)으로 표시한 마지막 구간은 뺍니다.",
    "spike": (
        f"다른 해 같은 달(주별이면 같은 주 ±1주) 값의 중앙값보다 {SPIKE_RATIO:g}배 이상 크고 "
        f"{SPIKE_MIN_POINTS}포인트 이상 높은 구간이 3개월 이내로 이어지면 일시적 이상치로 보고 평균·최고·최저에서 뺍니다. "
        "더 길게 이어지면 수준 변화로 보고 그대로 둡니다."
    ),
    "direction": (
        f"전년 대비 +{FLAT_PCT:g}% 이상은 증가, -{FLAT_PCT:g}% 이하는 감소, 그 사이이거나 평균 차이가 "
        f"{FLAT_POINTS:g}포인트 미만이면 보합입니다."
    ),
    "small": f"평균이 {SMALL_AVG:g} 미만인 검색어는 반올림 오차가 커서 전년 대비를 계산하지 않습니다.",
    "meaning": "검색 관심도는 조회 기간의 최고 구간을 100으로 둔 상대 지수입니다. 검색량·판매량·매출이 아닙니다.",
}

# (keywords, "YYYY-MM-DD YYYY-MM-DD") -> {"resolution": "WEEK"|"MONTH", "points": [{date, values, partial}]}
TrendsFetcher = Callable[[list[str], str], dict]


class TrendsUnavailable(RuntimeError):
    """Google refused or changed the response (429, consent page, new format)."""


def _json_body(text: str) -> dict:
    """Trends API bodies start with ``)]}'`` before the JSON."""
    start = (text or "").find("{")
    if start < 0:
        raise TrendsUnavailable("JSON이 아닌 응답")
    return json.loads(text[start:])


def _client(timeout: float):
    import primp  # shipped with ddgs (browser impersonation)

    try:
        return primp.Client(impersonate="random", impersonate_os="random", cookie_store=True, timeout=timeout)
    except TypeError:  # an older primp without these options
        return primp.Client(timeout=timeout)


def parse_timeline(body: dict, keywords: int) -> list[dict]:
    """``timelineData`` rows as ``{date, values, partial}``; a keyword without data is ``None``."""
    points = []
    for row in body.get("default", {}).get("timelineData", []):
        values = list(row.get("value") or [])[:keywords]
        has = list(row.get("hasData") or [True] * len(values))
        stamp = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc).date()
        points.append(
            {
                "date": stamp.isoformat(),
                "values": [int(v) if i < len(has) and has[i] else None for i, v in enumerate(values)],
                "partial": bool(row.get("isPartial")),
            }
        )
    return points


def fetch_trends(keywords: list[str], time_range: str, timeout: float = TRENDS_TIMEOUT) -> dict:
    """One explore request (widget token) and one multiline request. Raises ``TrendsUnavailable``."""
    req = {
        "comparisonItem": [{"keyword": k, "geo": "US", "time": time_range} for k in keywords],
        "category": 0,
        "property": "",
    }
    params = {"hl": "en-US", "tz": "0", "req": json.dumps(req, separators=(",", ":"))}
    status = None
    # Google answers a client's first request with 429 and a cookie; the same client then gets
    # the data. So the attempts share one client (its cookie store); only the last starts afresh.
    client = _client(timeout)
    for attempt in range(TRENDS_ATTEMPTS):
        if attempt == TRENDS_ATTEMPTS - 1 and attempt:
            client = _client(timeout)
        try:
            explore = client.get(TRENDS_EXPLORE_URL, params=params)
        except Exception as exc:  # noqa: BLE001 - network error: retry, then report it
            status = type(exc).__name__
            time.sleep(1.5 * (attempt + 1))
            continue
        status = explore.status_code
        if status != 200:
            time.sleep(1.5 * (attempt + 1))
            continue
        widgets = _json_body(explore.text).get("widgets", [])
        widget = next((w for w in widgets if w.get("id") == "TIMESERIES"), None)
        if not widget:
            raise TrendsUnavailable("시계열 위젯 없음")
        line = client.get(
            TRENDS_MULTILINE_URL,
            params={
                "hl": "en-US",
                "tz": "0",
                "req": json.dumps(widget["request"], separators=(",", ":")),
                "token": widget["token"],
            },
        )
        if line.status_code != 200:
            status = line.status_code
            time.sleep(1.5 * (attempt + 1))
            continue
        return {
            "resolution": str(widget["request"].get("resolution", "")),
            "points": parse_timeline(_json_body(line.text), len(keywords)),
        }
    raise TrendsUnavailable(f"HTTP {status}" if isinstance(status, int) else str(status or "응답 없음"))


def trends_keywords(product_en: str, gender: str) -> list[str]:
    """The product's English name, plus its gendered search (``mens bomber jacket``) for a gendered target."""
    base = " ".join(product_en.lower().replace("’", "'").split())
    if not base:
        return []
    words = base.split()
    if words[0] in {"men's", "mens", "men", "women's", "womens", "women"}:
        return [base]
    prefix = {"men": "mens", "women": "womens"}.get(gender)
    return [base, f"{prefix} {base}"] if prefix else [base]


def explore_url(keywords: list[str], time_range: str) -> str:
    """The Trends page showing the same query, so a reader can open and redo it."""
    q = ",".join(quote(k) for k in keywords)
    return f"{TRENDS_PAGE_URL}?date={quote(time_range)}&geo=US&q={q}&hl=en-US"


def _slot(day: date, resolution: str) -> int:
    return day.month - 1 if resolution == "MONTH" else (day.timetuple().tm_yday - 1) // 7


def _avg(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _pct(current: float | None, previous: float | None) -> float | None:
    if current is None or not previous:
        return None
    return round((current / previous - 1) * 100, 1)


def direction(current: float | None, previous: float | None) -> str:
    pct = _pct(current, previous)
    if pct is None:
        return ""
    if abs(current - previous) < FLAT_POINTS or abs(pct) < FLAT_PCT:
        return "보합"
    return "증가" if pct > 0 else "감소"


def _label(day: date, resolution: str) -> str:
    return f"{day.year}-{day.month:02d}" if resolution == "MONTH" else day.isoformat()


def find_spikes(series: list[tuple[date, int]], resolution: str) -> tuple[set[date], list[dict], list[dict]]:
    """(dates left out, spike rows, level-shift rows) for the main keyword's points in order."""
    near = 0 if resolution == "MONTH" else 1
    flagged: list[tuple[date, int, float] | None] = []
    for day, value in series:
        slot = _slot(day, resolution)
        others = [v for d, v in series if d.year != day.year and abs(_slot(d, resolution) - slot) <= near]
        years = {d.year for d, _v in series if d.year != day.year and abs(_slot(d, resolution) - slot) <= near}
        typical = median(others) if len(years) >= 2 else None
        hit = typical is not None and value >= SPIKE_RATIO * typical and value - typical >= SPIKE_MIN_POINTS
        flagged.append((day, value, typical) if hit else None)
    longest = SPIKE_MAX_RUN.get(resolution, SPIKE_MAX_RUN["WEEK"])
    excluded: set[date] = set()
    spikes: list[dict] = []
    shifts: list[dict] = []
    run: list[tuple[date, int, float]] = []
    for item in [*flagged, None]:
        if item is not None:
            run.append(item)
            continue
        if run:
            rows = [{"label": _label(d, resolution), "value": v, "typical": round(t, 1)} for d, v, t in run]
            if len(run) <= longest:
                excluded.update(d for d, _v, _t in run)
                spikes += rows
            else:
                shifts += rows
            run = []
    return excluded, spikes, shifts


def _month_label(day: date) -> str:
    return f"{day.month}월"


def _same_day(year: int, like: date) -> date:
    try:
        return date(year, like.month, like.day)
    except ValueError:  # February 29
        return date(year, like.month, 28)


RECENT_DAYS = 91  # 13 weeks; for monthly points the last three month starts


def trend_metrics(keywords: list[str], series: dict, years: list[int]) -> dict:
    """Per-year metrics on the fixed basis (see the module rules). ``years`` is the study period."""
    resolution = series.get("resolution") or "WEEK"
    raw = series.get("points") or []
    points = [(date.fromisoformat(p["date"]), p["values"]) for p in raw if not p.get("partial")]
    if not points or not keywords:
        return {"status": "empty", "resolution": resolution}
    main = [(d, v[0]) for d, v in points if v and v[0] is not None]
    if not main:
        return {"status": "empty", "resolution": resolution}
    last = points[-1][0]
    end = (last.month, last.day)
    window = f"1~{last.month}월" if resolution == "MONTH" else f"1월 1일~{last.month}월 {last.day}일"
    excluded, spikes, shifts = find_spikes(main, resolution)
    shown = sorted({d.year for d, _v in main if (years[0] - 1 if years else d.year) <= d.year})
    full_points = 12 if resolution == "MONTH" else 50
    recent_days = RECENT_DAYS if resolution != "MONTH" else 70  # Aug 1, Sep 1, Oct 1 before Oct 1 + 1

    def recent(year: int) -> list[int]:
        stop = _same_day(year, last)
        return [v for d, v in main if d not in excluded and stop - timedelta(days=recent_days) < d <= stop]

    recent_dates = [d for d, _v in main if last - timedelta(days=recent_days) < d <= last]
    first = recent_dates[0] if recent_dates else last
    recent_window = (
        f"{first.month}~{last.month}월" if resolution == "MONTH" else f"{first.month}월 {first.day}일~{last.month}월 {last.day}일"
    )

    rows = []
    previous: dict | None = None
    for year in shown:
        mine = [(d, v) for d, v in main if d.year == year]
        kept = [(d, v) for d, v in mine if d not in excluded]
        win = [v for d, v in kept if (d.month, d.day) <= end]
        win_all = [v for d, v in mine if (d.month, d.day) <= end]
        complete = year < last.year and len(mine) >= full_points
        row = {
            "year": year,
            "window_avg": _avg(win),
            "window_avg_all": _avg(win_all),
            "window_points": len(win),
            "full_avg": _avg([v for _d, v in kept]) if complete else None,
            "high": None,
            "high_label": "",
            "low": None,
            "low_label": "",
            "yoy_pct": None,
            "direction": "",
            "full_yoy_pct": None,
            "recent_avg": _avg(recent(year)),
            "recent_yoy_pct": None,
            "recent_direction": "",
            "in_period": not years or year in years,
        }
        if kept:
            high = max(kept, key=lambda dv: dv[1])
            low = min(kept, key=lambda dv: dv[1])
            row.update(high=high[1], high_label=_month_label(high[0]), low=low[1], low_label=_month_label(low[0]))
        if previous:
            row["yoy_pct"] = _pct(row["window_avg"], previous["window_avg"])
            row["direction"] = direction(row["window_avg"], previous["window_avg"])
            row["full_yoy_pct"] = _pct(row["full_avg"], previous["full_avg"])
            row["recent_yoy_pct"] = _pct(row["recent_avg"], previous["recent_avg"])
            row["recent_direction"] = direction(row["recent_avg"], previous["recent_avg"])
        rows.append(row)
        previous = row

    extra = []
    latest = last.year
    base_now = next((r["window_avg"] for r in rows if r["year"] == latest), None)
    for index, keyword in enumerate(keywords[1:], 1):
        values = [(d, v[index]) for d, v in points if len(v) > index and v[index] is not None and d not in excluded]
        by_year = {
            y: _avg([v for d, v in values if d.year == y and (d.month, d.day) <= end]) for y in shown
        }
        now = by_year.get(latest)
        before = by_year.get(latest - 1)
        small = now is None or now < SMALL_AVG or before is None or before < SMALL_AVG
        extra.append(
            {
                "keyword": keyword,
                "window_avg": by_year,
                "ratio_pct": round(now / base_now * 100, 1) if now is not None and base_now else None,
                "yoy_pct": None if small else _pct(now, before),
                "small": small,
            }
        )
    top = max((v for _d, v in main), default=0)
    return {
        "status": "ok",
        "resolution": resolution,
        "window": window,
        "recent_window": recent_window,
        "last_complete": last.isoformat(),
        "dropped_partial": sum(1 for p in raw if p.get("partial")),
        "years": rows,
        "spikes": spikes,
        "level_shifts": shifts,
        "keywords": extra,
        "scale_note": (
            "조회 기간 최고점(100)이 이상치 구간이라 나머지 값이 낮게 눌려 있습니다. 연도 간 비율(전년 대비 %)은 영향을 받지 않습니다."
            if top >= 100 and any(s["value"] >= 100 for s in spikes)
            else ""
        ),
    }


def _num(value: float | None) -> str:
    return "—" if value is None else (f"{value:.1f}" if value % 1 else str(int(value)))


def _signed(pct: float | None) -> str:
    return "" if pct is None else f"{pct:+.1f}%"


def metric_lines(trends: dict) -> list[str]:
    """The metrics as sentences: the evidence item's text, quoted by the synthesis."""
    cond = trends["conditions"]
    unit = "월별" if trends["resolution"] == "MONTH" else "주별"
    keywords = ", ".join(cond["keywords"])
    lines = [
        f"Google Trends 미국 웹 검색 관심도({unit}, 0~100 상대 지수, 검색량·판매량 아님). 검색어 {keywords}, "
        f"기간 {cond['time'].replace(' ', '~')}, 조회일 {cond['fetched']}.",
        f"연도 비교 기준(고정): 매년 같은 기간({trends['window']}) 평균, 일시적 이상치 제외.",
    ]
    for row in trends["years"]:
        text = f"{row['year']}년 {trends['window']} 평균 {_num(row['window_avg'])}"
        if row["yoy_pct"] is not None:
            text += f" (전년 대비 {_signed(row['yoy_pct'])}, {row['direction']})"
        if row["window_avg_all"] != row["window_avg"]:
            text += f", 이상치 포함 시 {_num(row['window_avg_all'])}"
        lines.append(text + ".")
    recent_rows = [r for r in trends["years"] if r["recent_avg"] is not None]
    if recent_rows:
        lines.append(
            f"최근 구간({trends['recent_window']}) 평균(참고): "
            + ", ".join(
                f"{r['year']}년 {_num(r['recent_avg'])}"
                + (f"({_signed(r['recent_yoy_pct'])}, {r['recent_direction']})" if r["recent_yoy_pct"] is not None else "")
                for r in recent_rows
            )
            + "."
        )
    full = [r for r in trends["years"] if r["full_avg"] is not None]
    if full:
        lines.append(
            "연간 평균(끝난 해, 참고): "
            + ", ".join(
                f"{r['year']}년 {_num(r['full_avg'])}" + (f"({_signed(r['full_yoy_pct'])})" if r["full_yoy_pct"] is not None else "")
                for r in full
            )
            + "."
        )
    highs = [r for r in trends["years"] if r["high"] is not None]
    if highs:
        lines.append("최고 구간: " + ", ".join(f"{r['year']}년 {r['high_label']} {r['high']}" for r in highs) + ".")
        lines.append("최저 구간: " + ", ".join(f"{r['year']}년 {r['low_label']} {r['low']}" for r in highs) + ".")
    if trends["spikes"]:
        lines.append(
            "일시적 이상치로 제외: "
            + ", ".join(f"{s['label']} {s['value']}(다른 해 같은 시기 중앙값 {_num(s['typical'])})" for s in trends["spikes"])
            + "."
        )
    if trends["level_shifts"]:
        lines.append(
            "평년보다 높은 상태가 길게 이어져 수준 변화로 보고 남긴 구간: "
            + ", ".join(f"{s['label']} {s['value']}" for s in trends["level_shifts"])
            + "."
        )
    base = cond["keywords"][0]
    latest = trends["years"][-1]["year"] if trends["years"] else None
    for k in trends["keywords"]:
        now = k["window_avg"].get(latest) if latest else None
        text = f"{k['keyword']}: {latest}년 {trends['window']} 평균 {_num(now)}"
        if k["ratio_pct"] is not None:
            text += f", {base}의 약 {_num(k['ratio_pct'])}% 수준(겹치는 검색어라 점유율이 아님)"
        text += (
            f", 평균이 {SMALL_AVG:g} 미만이라 전년 대비는 계산하지 않음"
            if k["small"]
            else f", 전년 대비 {_signed(k['yoy_pct'])}"
        )
        lines.append(text + ".")
    if trends.get("scale_note"):
        lines.append(trends["scale_note"])
    return lines


def study_trends(
    keywords: list[str], years: list[int], fetcher: TrendsFetcher, today: date | None = None
) -> dict:
    """Fetch and measure. Always returns a dict with ``status`` (ok | unavailable | empty) and the query conditions."""
    today = today or date.today()
    start = date((years[0] if years else today.year) - 1, 1, 1)
    time_range = f"{start.isoformat()} {today.isoformat()}"
    conditions = {
        "keywords": keywords,
        "geo": "US",
        "category": "전체 카테고리(0)",
        "property": "웹 검색",
        "time": time_range,
        "timezone": "UTC",
        "fetched": today.isoformat(),
    }
    out = {"source": "Google Trends", "url": explore_url(keywords, time_range), "conditions": conditions, "rules": RULES}
    if not keywords:
        return {**out, "status": "empty", "error": "검색용 영문명 없음"}
    try:
        series = fetcher(keywords, time_range)
    except Exception as exc:  # noqa: BLE001 - blocked or changed: the pack says so
        return {**out, "status": "unavailable", "error": str(exc)[:120] or type(exc).__name__}
    metrics = trend_metrics(keywords, series, years)
    conditions["resolution"] = metrics.get("resolution", "")
    result = {**out, **metrics, "points": series.get("points", [])}
    if result["status"] == "ok":
        result["lines"] = metric_lines(result)
    return result
