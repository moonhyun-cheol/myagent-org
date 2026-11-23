"""Evidence-pack research: structured brief -> web evidence -> validated excerpts.

No LLM and no templates. Every line of the output is one of: the brief as the
user gave it, a counted statistic, or a verbatim excerpt with its URL. Market
gaps, personas, sizing and pricing conclusions are deliberately not produced
here; a section without evidence is reported as missing instead of being filled.

The target market is the United States (CQR is a US brand). Queries are English;
results on another country's domain or country edition, in a non-Latin script,
priced only in another currency, or on a page that declares another country's
locale are dropped and counted. A brief whose product or category has no
English name is not searched at all.

Search goes to search.yahoo.com first (see ``yahoo_search``): in the runtime the
host uses, Yahoo is the only ddgs text engine that answers, it ignores the
region parameter, and ddgs reads only one of the two page layouts Yahoo serves,
so most ddgs calls came back empty. ddgs stays as the fallback.

Each evidence item carries a short ``excerpt`` (shown in the pack) and a longer
``detail`` (more on-topic passages, and on competitor pages the lines that state
a price) for the host's synthesis step, which must cite evidence ids and may only
quote amounts that appear in the cited items.

A market/trend study (``study: trend``, or any brief with a ``period``) searches each
year of the period, gives most slots to market evidence, and records the date a page
was published and last updated so the synthesis can tell what was said about which year.
A page whose content date is older than the period (and that names no year of it) is
marked ``before_period`` and only used when nothing newer fills the slot. A page without a
date is dated from its URL when it can be (``/2018/05/``, ``…-in-2022``, a Reddit post id):
an SEO page keeps its original year in the URL while the title is moved to this year. One
that stays without a date and names no year of the period is marked ``undated`` and comes
after dated pages.

The brief's target customer (``gender``, ``style``) shapes the queries: men's bomber
jacket, best men's military bomber jacket. A result whose title is for the other gender
is dropped. The CLI fills a brief without one with CQR's customer (``TARGET_DEFAULTS``).
Market-size queries do not name the gender (reports rarely split by it); their results are
marked ``all_genders`` so the synthesis does not compare their brands and prices with the
target customer's products.

On a market page the lines that state a market figure (USD 41.07 Billion, CAGR) are kept
even when they do not repeat the product name: a US outerwear report gave a 127-character
excerpt without them.

A trend study also reads Google Trends (US web search interest) for the product's English
name and its gendered search, from the year before the period to today (``google_trends``).
It is the one series that compares years on one scale, so it is measured on a fixed basis
(the same calendar window every year, partial point dropped, temporary spikes left out) and
the query conditions and rules go into the pack with the numbers. It becomes the last evidence
item (source ``데이터``) so the synthesis can cite it; when Google refuses, the pack says so.

Reddit pages refuse unauthenticated fetches, so a Reddit hit normally keeps its snippet only.
When Reddit API credentials are configured (``reddit_api.reddit_from_env``), the pack also
searches Reddit for review threads and reads each thread's post and top comments through the
official API. Reddit evidence is labelled ``소비자 발언``: it is what users wrote, for complaints
and use cases, not a price or market figure.

Review evidence also comes from pages a plain fetch can read: retailer review pages that print
their reviews in the HTML (Zappos, store review pages) and forum threads. A review-query page
whose markup shows consumer posts (``consumer_posts``: several schema.org Review items, review
marks such as "Verified Buyer" / "out of 5 stars", or forum post markers such as "Joined" /
"Messages" / "… said:") is labelled ``소비자 발언`` with ``voice_from`` 리뷰 or 포럼. An editor's
review (one Review item, first-person prose) is not. A consumer post more than
``OLD_POST_YEARS`` old is marked ``old_post``: forum threads are often a decade old.

Every page fetch that fails records why (HTTP status, timeout, empty or script-only body), so
the pack can say which sources were blocked instead of only "13/16 read".
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import unquote_plus, urlsplit

from .google_trends import (
    TRENDS_DOMAIN,
    TRENDS_SOURCE,
    TrendsFetcher,
    fetch_trends,
    study_trends,
    trends_keywords,
)
from .reddit_api import RedditClient, reddit_from_env

PACK_SCHEMA = "cqr.market_research.evidence_pack/1"
MIN_EVIDENCE = 3
MAX_QUERIES = 10
# Market queries are planned last but never cut: they get these slots out of MAX_QUERIES.
MARKET_QUERIES = 2
RESULTS_PER_QUERY = 6
MAX_FETCH = 16
MAX_EVIDENCE = 18
# Evidence and fetch slots per kind, taken in rank order. A kind that cannot fill its
# share hands the rest to the others, so the totals stay MAX_EVIDENCE / MAX_FETCH.
# Without shares the review queries (3-4 of 8) used the slots up before the single
# market query's second and third hits were reached.
KIND_QUOTA = {"review": 8, "competitor": 6, "market": 4}
FETCH_QUOTA = {"review": 7, "competitor": 5, "market": 4}
# A market/trend study asks how the market moved, so market evidence takes most slots.
STUDY_TREND = "trend"
STUDY_PRODUCT = "product"
TREND_KIND_QUOTA = {"review": 3, "competitor": 5, "market": 10}
TREND_FETCH_QUOTA = {"review": 2, "competitor": 4, "market": 10}
TREND_DEFAULT_YEARS = 3  # a trend study without a period looks at the last 3 years
MAX_PERIOD_YEARS = 4  # one query per year; older years of a longer period are left out
MAX_PER_DOMAIN = 3
MIN_BODY_CHARS = 400
EXCERPT_CHARS = 720
DETAIL_CHARS = 2400
PRICE_LINES = 6
FIGURE_LINES = 4
PRICE_LINE_MARK = "[가격 표기 줄]"
FIGURE_LINE_MARK = "[시장 수치 줄]"
# CQR's customer, used by the CLI when a brief names no target: menswear in military and
# workwear styles. ``성별: 전체`` / ``스타일: 전체`` turns either off for one study.
TARGET_DEFAULTS = {"gender": "men", "style": "military, workwear"}
FROM_DEFAULT = "CQR 기본 타깃"
GENDER_LABELS = {"men": "남성", "women": "여성", "unisex": "공용", "all": "전체(성별 무관)"}
_GENDER_VALUES = {
    **dict.fromkeys(("men", "men's", "mens", "male", "남성", "남자", "남성용"), "men"),
    **dict.fromkeys(("women", "women's", "womens", "female", "여성", "여자", "여성용"), "women"),
    **dict.fromkeys(("unisex", "공용", "남녀공용", "유니섹스"), "unisex"),
    **dict.fromkeys(("all", "any", "none", "전체", "무관", "상관없음", "없음"), "all"),
}
_ALL_VALUES = frozenset({"all", "any", "none", "전체", "무관", "상관없음", "없음"})
# Style values as English search words (밀리터리 -> military).
_STYLE_EN = {
    "밀리터리": "military",
    "워크웨어": "workwear",
    "워킹": "workwear",
    "작업복": "workwear",
    "택티컬": "tactical",
    "아웃도어": "outdoor",
    "헤리티지": "heritage",
}
# Gender named in the sentence or in the product name (여성 봄버재킷, men's dress slacks).
_GENDER_TEXT = (
    (re.compile(r"남녀\s?공용|유니섹스|\bunisex\b", re.IGNORECASE), "unisex"),
    (re.compile(r"(?<![가-힣])(?:여성|여자)|\b(?:women|womens|ladies)\b", re.IGNORECASE), "women"),
    (re.compile(r"(?<![가-힣])(?:남성|남자)|\b(?:men['’]s|mens)\b", re.IGNORECASE), "men"),
)
# A result title written for one gender. "men" inside "women" is not a word boundary.
_TITLE_GENDER = {
    "women": re.compile(r"\b(?:women|womens|woman|ladies|female)(?:['’]s)?\b", re.IGNORECASE),
    "men": re.compile(r"\b(?:men|mens|male|unisex)(?:['’]s)?\b", re.IGNORECASE),
}
# A market figure: USD 41.07 Billion, $17.9 billion, US$2.5 bn, CAGR.
_MARKET_FIGURE_RE = re.compile(
    r"(?:US\$|\bUSD\s?|\$)\s?\d[\d.,]*\s?(?:billion|million|trillion|bn|mn)\b|\bCAGR\b", re.IGNORECASE
)
SEARCH_SPACING = 0.8  # seconds between live queries; back-to-back calls get throttled
SEARCH_RETRY_DELAY = 2.0
SEARCH_TIMEOUT = 10
YAHOO_SEARCH_URL = "https://search.yahoo.com/search"
# Search-engine redirect / ad links are not sources.
_NON_SOURCE_HOSTS = ("bing.com", "duckduckgo.com", "google.com", "search.yahoo.com")
# Hosts whose pages never gave a readable body in measured runs (login wall /
# bot page). Their search snippet is still used; no fetch slot is spent on them.
_NO_FETCH_HOSTS = ("reddit.com", "amazon.com")
REDDIT_HOSTS = ("reddit.com",)
VOICE_LABEL = "소비자 발언"
VOICE_REVIEW = "리뷰"
VOICE_FORUM = "포럼"
OLD_POST_YEARS = 3  # a consumer post older than this is marked old: products and complaints change
# Consumer posts on a page (measured on MA-1 review and forum results, 2026-11). An editor's
# review has one schema.org Review item and first-person prose, so neither counts alone.
_LD_REVIEW_RE = re.compile(r"\"@type\"\s*:\s*\"Review\"")
_REVIEW_MARK_RE = re.compile(
    r"verified (?:buyer|purchase|reviewer|owner)|out of 5 stars|(?<![\d.])\d(?:\.\d)? out of 5\b"
    r"|was this review helpful|reviewed in the united states",
    re.IGNORECASE,
)
# XenForo / vBulletin / phpBB post furniture: "Joined: Mar 5, 2012", "Messages: 1,204", "Bob said:".
_FORUM_MARK_RE = re.compile(r"\b(?:Joined|Messages|Reaction score)\b|\b(?:said|wrote):")
_FORUM_PATH_RE = re.compile(r"/(?:threads?|forums?|topic|t|community|discussion)/|showthread|viewtopic", re.IGNORECASE)
_BLOCKED_STATUSES = frozenset({"HTTP 401", "HTTP 403", "HTTP 429", "HTTP 503"})
EMPTY_BODY = "본문 없음(스크립트로 그리는 페이지 등)"
REDDIT_RESULTS = 8  # threads per Reddit API search
REDDIT_MAX_THREADS = 8  # threads read through the API per run
_SENTENCE_END_RE = re.compile(r"[.!?…](?:\s|$)")
MARKET = "US"
MARKET_LABEL = "미국"
SEARCH_REGION = "us-en"
# Two-letter TLDs used as generic ones, not as another country's market.
_GENERIC_CC_TLDS = frozenset({"us", "co", "io", "ai", "me", "tv", "cc", "gg", "ly", "to", "fm"})
# ISO 3166-1 alpha-2 codes (+ "uk"). A first host label like ca. / uk. / en-gb. is that
# country's edition of a site (ca.pinterest.com), so it is not a US source.
_COUNTRY_CODES = frozenset(
    (
        "ad ae af ag ai al am ao aq ar as at au aw ax az ba bb bd be bf bg bh bi bj bl bm bn bo bq br bs bt bv bw "
        "by bz ca cc cd cf cg ch ci ck cl cm cn co cr cu cv cw cx cy cz de dj dk dm do dz ec ee eg eh er es et fi "
        "fj fk fm fo fr ga gb gd ge gf gg gh gi gl gm gn gp gq gr gs gt gu gw gy hk hm hn hr ht hu id ie il im in "
        "io iq ir is it je jm jo jp ke kg kh ki km kn kp kr kw ky kz la lb lc li lk lr ls lt lu lv ly ma mc md me "
        "mf mg mh mk ml mm mn mo mp mq mr ms mt mu mv mw mx my mz na nc ne nf ng ni nl no np nr nu nz om pa pe pf "
        "pg ph pk pl pm pn pr ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si sj sk sl sm sn so sr ss st sv "
        "sx sy sz tc td tf tg th tj tk tl tm tn to tr tt tv tw tz ua ug um us uy uz va vc ve vg vi vn vu wf ws ye "
        "yt za zm zw uk"
    ).split()
)
# First labels that are the US or a US territory, or that sites use for a function rather
# than a country: ir. investor relations, my. account, hr. careers, id. login.
_NOT_A_COUNTRY_EDITION = frozenset({"us", "pr", "gu", "vi", "as", "mp", "um", "ir", "my", "hr", "id"}) | _GENERIC_CC_TLDS
_EDITION_LABEL_RE = re.compile(r"^(?:[a-z]{2}-)?([a-z]{2})$")  # ca / en-gb / fr-ca
_US_REGIONS = frozenset({"us", "pr", "gu", "vi", "as", "mp", "um"})
# Retailer pages about one item: a product page or its reviews. Anything else on the
# retailer's main host (search /s?k=…, category /b?node=… /browse/ /c/, stores, best-seller
# lists) is a product list whose snippet is shop navigation, not a review or a price for
# one product. Matched on the exact host, so corporate.target.com and the like are kept.
_RETAIL_ITEM_PATHS = {
    "amazon.com": re.compile(r"/(?:dp|gp/product|gp/aw/d|product-reviews|gp/customer-reviews)/"),
    "walmart.com": re.compile(r"/(?:ip|reviews/product)/"),
    "target.com": re.compile(r"/p/"),
}
# Money written in another currency. A result priced only this way is not a US listing.
_FOREIGN_CURRENCY_RE = re.compile(
    r"[£€₹]\s?\d|\d\s?€|(?<![A-Za-z])(?:CA|AU|NZ|HK|SG|C|A|S)\$\s?\d"
    r"|\b(?:GBP|EUR|CAD|AUD|NZD|INR)\s?\d|\d\s?(?:GBP|EUR|CAD|AUD|NZD|INR)\b"
)
_USD_RE = re.compile(r"(?:(?<=US)|(?<![A-Za-z]))\$\s?\d|\bUSD\b")
_HTML_LANG_RE = re.compile(r"<html\b[^>]*?\blang\s*=\s*[\"']?([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*)", re.IGNORECASE)
_OG_LOCALE_RE = re.compile(r"<meta\b[^>]*?(?:property|name)\s*=\s*[\"']og:locale[\"'][^>]*>", re.IGNORECASE)
_CONTENT_RE = re.compile(r"\bcontent\s*=\s*[\"']([^\"']+)", re.IGNORECASE)
# Structured product price: schema.org Offer in JSON-LD, or a product:price meta tag.
# Product pages often render the visible price with script, so it is not in the text.
_LD_JSON_RE = re.compile(
    r"<script\b[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL
)
_META_PRICE_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:product:price:amount|og:price:amount)[\"'][^>]*>",
    re.IGNORECASE,
)
_META_CURRENCY_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:product:price:currency|og:price:currency)[\"'][^>]*>",
    re.IGNORECASE,
)
# Status codes a browser-like client sometimes gets past (bot walls, rate limits).
_RETRY_IMPERSONATED = frozenset({401, 403, 429, 503})
OFF_MARKET_LABELS = {
    "domain": "국가 도메인",
    "edition": "국가판 서브도메인",
    "script": "비라틴 문자",
    "currency": "외화로만 적힌 가격",
    "locale": "페이지가 선언한 언어·지역",
}
_KOREAN_RE = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]")
# Season wording for an English query.
_SEASON_EN = {
    "봄": "spring",
    "여름": "summer",
    "가을": "fall",
    "겨울": "winter",
    "봄여름": "spring summer",
    "가을겨울": "fall winter",
    "SS": "spring summer",
    "FW": "fall winter",
}

Searcher = Callable[[str, int], list[dict]]
Fetcher = Callable[[str], str]

# field -> accepted keys in an inline ``키: 값`` brief (longest key wins).
FIELD_KEYS: dict[str, tuple[str, ...]] = {
    "product": ("품목", "제품", "product", "item"),
    "product_en": ("영문명", "영문", "검색어", "product_en", "english"),
    "category": ("카테고리", "category"),
    "season": ("시즌", "season"),
    "channel": ("채널", "channel"),
    "price_band": ("가격대", "가격", "price_band", "price"),
    "competitors": ("경쟁사", "competitors", "competitor"),
    "focus": ("초점", "포커스", "focus"),
    "study": ("조사유형", "조사 유형", "study"),
    "period": ("기간", "period"),
    "gender": ("성별", "gender"),
    "style": ("스타일", "세그먼트", "style", "segment"),
}
FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("product", "품목"),
    ("product_en", "검색용 영문명"),
    ("category", "카테고리"),
    ("season", "시즌"),
    ("channel", "채널"),
    ("price_band", "가격대"),
    ("competitors", "경쟁사"),
    ("focus", "초점"),
    ("study", "조사 유형"),
    ("period", "기간"),
    ("gender", "성별 타깃"),
    ("style", "스타일 타깃"),
)
STUDY_LABELS = {STUDY_TREND: "시장·트렌드 추이", STUDY_PRODUCT: "제품 조사(불만·경쟁·시장)"}
# Accepted ``조사유형:`` values (lower case).
_STUDY_VALUES = {
    "trend": STUDY_TREND,
    "trends": STUDY_TREND,
    "market": STUDY_TREND,
    "market trend": STUDY_TREND,
    "트렌드": STUDY_TREND,
    "추이": STUDY_TREND,
    "시장": STUDY_TREND,
    "시장·트렌드": STUDY_TREND,
    "product": STUDY_PRODUCT,
    "제품": STUDY_PRODUCT,
}
KIND_LABELS: tuple[tuple[str, str], ...] = (
    ("review", "리뷰·불만 근거"),
    ("competitor", "경쟁사·가격 근거"),
    ("market", "시장·트렌드 근거"),
)
FROM_FIELD = "입력 필드"
FROM_TEXT = "문장 해석(규칙)"
FIELD_EXAMPLE = (
    "/심층리서치 품목: 스키바지 / 영문명: ski pants / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280"
)

_KEY_TO_FIELD = {key.lower(): name for name, keys in FIELD_KEYS.items() for key in keys}
_FIELD_RE = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(k) for k in sorted(_KEY_TO_FIELD, key=len, reverse=True))
    + r")\s*[:=]\s*",
    re.IGNORECASE,
)
_PRICE_BAND_RE = re.compile(r"\$\s?\d{1,4}(?:\s?[-–~]\s?\$?\d{1,4})?")
# A US-dollar price: $89, $9.99, $1,299. Not CA$/A$ amounts, and not a figure with a
# magnitude ($17.9 billion, $2.5M, $100k), which is a market size rather than a price.
_PRICE_RE = re.compile(
    r"(?:(?<=US)|(?<![A-Za-z]))\$\s?(?:\d{1,3}(?:,\d{3})+|\d{1,5})(?:\.\d{1,2})?"
    r"(?!\d|[.,]\d)(?!\s?(?:[mb]illion|trillion|bn|mn|[mbk])\b)",
    re.IGNORECASE,
)
_SEASON_CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?:(20\d\d)\s*)?(FW|F/W|SS|S/S)(?![A-Za-z])", re.IGNORECASE)
# 「봄버재킷」「살펴봄」 must not read as spring: the word has to stand alone.
_SEASON_KO_RE = re.compile(r"(?<![가-힣])(봄|여름|가을|겨울)(?:용|철|에|시즌)?(?![가-힣])")
_SEASON_EN_RE = re.compile(r"\b(winter|summer)\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(20[2-4]\d)(?!\d)")
# A period: 2024-2026 / 2024년~2026년, or a relative one: 최근 3년 / 지난 2개년 / last 3 years.
_PERIOD_RANGE_RE = re.compile(r"(?<!\d)(20\d\d)\s*년?\s*[-–~]\s*(20\d\d)(?!\d)\s*년?")
_RECENT_YEARS_RE = re.compile(r"(?:최근|지난)\s*(\d{1,2})\s*개?년|\b(?:last|past)\s+(\d{1,2})\s+years\b", re.IGNORECASE)
# Publication date a page declares, and the date Yahoo prints before a snippet ("Mar 5, 2025 · …").
_PUBLISHED_META_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:article:published_time|og:published_time|"
    r"datePublished|publish[-_]?date|pubdate|parsely-pub-date|sailthru\.date|date)[\"'][^>]*>",
    re.IGNORECASE,
)
_LD_PUBLISHED_RE = re.compile(r"\"datePublished\"\s*:\s*\"([^\"]{8,40})\"")
# Last-modified date. Updated guides keep their first publication date (Esquire's "best
# bomber jackets for 2026" says 2016-08-25 and dateModified 2026-01-20).
_MODIFIED_META_RE = re.compile(
    r"<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*[\"'](?:article:modified_time|og:updated_time|"
    r"dateModified|last-modified|modified[-_]?date|parsely-updated)[\"'][^>]*>",
    re.IGNORECASE,
)
_LD_MODIFIED_RE = re.compile(r"\"dateModified\"\s*:\s*\"([^\"]{8,40})\"")
_ISO_DATE_RE = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)")
_MONTHS = {m: n for n, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
_SNIPPET_DATE_RE = re.compile(r"^\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(20\d\d)\b")
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


@dataclass
class ResearchBrief:
    raw: str = ""
    product: str = ""
    product_en: str = ""
    category: str = ""
    season: str = ""
    channel: str = ""
    price_band: str = ""
    competitors: list[str] = field(default_factory=list)
    focus: str = ""
    study: str = ""  # STUDY_TREND | STUDY_PRODUCT | "" (product study)
    period: str = ""  # "2024-2026" / "2025"
    gender: str = ""  # men | women | unisex | all | "" (not stated)
    style: str = ""  # "military, workwear" (English search words)
    origin: dict[str, str] = field(default_factory=dict)

    @property
    def scope(self) -> str:
        return self.product or self.category

    @property
    def search_term(self) -> str:
        """English name the US-market queries are built on ('' when the brief has none)."""
        for value in (self.product_en, self.product, self.category):
            if value and not _has_korean(value):
                return value
        return ""


@dataclass
class Evidence:
    id: str
    kind: str
    title: str
    url: str
    domain: str
    source: str  # "본문" (page body read) | "요약문" (search snippet only)
    excerpt: str
    prices: list[str]
    query: str
    # Longer on-topic passages (+ price lines on competitor pages) for the synthesis step.
    detail: str = ""
    # USD prices from the page's structured product data or its price lines.
    page_prices: list[str] = field(default_factory=list)
    # Publication date the page declares, or the date in front of the search snippet (YYYY-MM-DD).
    published: str = ""
    # Last-modified date the page declares, when it is after ``published``.
    updated: str = ""
    # Trend study: the content date is before the period and the text names no year of it.
    before_period: bool = False
    # Trend study: no date found (page, snippet or URL) and the text names no year of the period.
    undated: bool = False
    # Found by a query without the target gender (market size): may cover every gender.
    all_genders: bool = False
    # "소비자 발언" for forum/community posts (Reddit): complaints and use cases, not prices.
    voice: str = ""
    # Where a consumer post came from: "reddit" | "리뷰" (review page) | "포럼" (forum thread).
    voice_from: str = ""
    # Consumer post older than OLD_POST_YEARS (year in ``post_year``).
    old_post: bool = False
    post_year: int = 0


def content_date(item: Evidence) -> str:
    """Date of the version that was read: the update date, else the publication date."""
    return item.updated or item.published


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text or ""))


def _english(value: str) -> str:
    return "" if _has_korean(value) else value


def _parts(value: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,/·]", value or "") if p.strip()]


def _season_words(season: str) -> list[str]:
    return [_SEASON_EN.get(w.upper() if w.isascii() else w, w) for w in (season or "").split()]


def _season_en(season: str) -> str:
    """Season for an English query: 겨울 -> winter, FW -> fall winter; untranslatable words are left out."""
    return " ".join(w for w in _season_words(season) if not _has_korean(w))


def _unsearchable(brief: ResearchBrief) -> list[str]:
    """Brief values left out of the English queries because they are written in Korean."""
    left_out = [f"경쟁사 `{c}`" for c in brief.competitors if _has_korean(c)]
    left_out += [f"초점 `{p}`" for p in _parts(brief.focus) if _has_korean(p)]
    for label, value in (("채널", brief.channel), ("가격대", brief.price_band)):
        if _has_korean(value):
            left_out.append(f"{label} `{value}`")
    if any(_has_korean(w) for w in _season_words(brief.season)):
        left_out.append(f"시즌 `{brief.season}`")
    left_out += [f"스타일 `{p}`" for p in _parts(brief.style) if _has_korean(p)]
    return left_out


def _gender_value(value: str) -> str:
    return _GENDER_VALUES.get(_clean(value).lower(), "")


def _style_value(value: str) -> str:
    """English style words: 밀리터리, 워크웨어 -> military, workwear. '' for 전체 / all."""
    if _clean(value).lower() in _ALL_VALUES:
        return ""
    return ", ".join(dict.fromkeys(_STYLE_EN.get(p, _STYLE_EN.get(p.lower(), p)) for p in _parts(value)))


def _gender_from_text(text: str) -> str:
    found = {gender for pattern, gender in _GENDER_TEXT if pattern.search(text)}
    return "" if not found else found.pop() if len(found) == 1 else "all"


def _season_from_text(text: str) -> str:
    code = _SEASON_CODE_RE.search(text)
    if code:
        return " ".join(x for x in (code.group(1), code.group(2).upper().replace("/", "")) if x)
    word = _SEASON_KO_RE.search(text) or _SEASON_EN_RE.search(text)
    year = _YEAR_RE.search(text)
    return " ".join(x for x in (year.group(1) if year else "", word.group(1) if word else "") if x)


def _study_value(value: str) -> str:
    return _STUDY_VALUES.get(_clean(value).lower(), "")


def period_years(period: str, current_year: int | None = None) -> list[int]:
    """Years a period covers, oldest first. Future years are left out, and of a long period
    only the last MAX_PERIOD_YEARS are kept (one search per year)."""
    now = current_year or date.today().year
    text = period or ""
    if match := _PERIOD_RANGE_RE.search(text):
        first, last = sorted((int(match.group(1)), int(match.group(2))))
        years = list(range(first, last + 1))
    elif match := _RECENT_YEARS_RE.search(text):
        count = int(match.group(1) or match.group(2))
        years = list(range(now - count + 1, now + 1)) if count > 0 else []
    else:
        years = sorted({int(y) for y in _YEAR_RE.findall(text)})
    return [y for y in years if y <= now][-MAX_PERIOD_YEARS:]


def study_years(brief: ResearchBrief, current_year: int | None = None) -> list[int]:
    """Years a trend study searches: the period's, else the last TREND_DEFAULT_YEARS."""
    years = period_years(brief.period, current_year)
    if years:
        return years
    now = current_year or date.today().year
    return list(range(now - TREND_DEFAULT_YEARS + 1, now + 1))


def _period_text(years: list[int]) -> str:
    return "" if not years else str(years[0]) if len(years) == 1 else f"{years[0]}-{years[-1]}"


def _period_from_text(text: str) -> str:
    """A period written in the sentence (최근 3년, 2024~2026) as "2024-2026"; a lone year is a season, not a period."""
    if _PERIOD_RANGE_RE.search(text) or _RECENT_YEARS_RE.search(text):
        return _period_text(period_years(text))
    return ""


def page_published(html: str) -> str:
    """Publication date a page declares (article:published_time, JSON-LD datePublished, …) as YYYY-MM-DD."""
    head = html[:300_000]
    values = [c.group(1) for tag in _PUBLISHED_META_RE.findall(head) if (c := _CONTENT_RE.search(tag))]
    values += _LD_PUBLISHED_RE.findall(head)
    for value in values:
        if match := _ISO_DATE_RE.search(value):
            return "-".join(match.groups())
    return ""


def page_updated(html: str) -> str:
    """Latest last-modified date a page declares (article:modified_time, JSON-LD dateModified) as
    YYYY-MM-DD; '' when there is none after the publication date."""
    head = html[:300_000]
    values = [c.group(1) for tag in _MODIFIED_META_RE.findall(head) if (c := _CONTENT_RE.search(tag))]
    values += _LD_MODIFIED_RE.findall(head)
    dates = sorted("-".join(m.groups()) for value in values if (m := _ISO_DATE_RE.search(value)))
    latest = dates[-1] if dates else ""
    return latest if latest > page_published(html) else ""


def snippet_published(snippet: str) -> str:
    """The date a search engine prints in front of a snippet ("Mar 5, 2025 · …") as YYYY-MM-DD."""
    match = _SNIPPET_DATE_RE.match(snippet or "")
    if not match:
        return ""
    return f"{match.group(3)}-{_MONTHS[match.group(1)]:02d}-{int(match.group(2)):02d}"


def _rule_product(text: str) -> tuple[str, str]:
    """Product phrase read from free text by the legacy rule parser (fallback only)."""
    try:
        from cqr_product_pipeline.agents.deep_research import (
            _parse_brief_hints,
            brief_needs_clarification,
        )
    except Exception:  # noqa: BLE001 - legacy parser needs the LLM stack
        return "", ""
    hints = _parse_brief_hints(text, None)
    if brief_needs_clarification(hints):
        return "", ""
    product = _clean(hints.get("product_brief"))  # phrase as written in the brief
    english = _clean(hints.get("garment"))  # English search label
    if not english.isascii():
        english = product if product.isascii() else ""
    return product, english


def parse_brief(
    raw: str, overrides: dict[str, str] | None = None, defaults: dict[str, str] | None = None
) -> ResearchBrief:
    """Explicit fields are used verbatim; only what is missing is read from the sentence.

    ``defaults`` fills a target the brief does not state (the CLI passes ``TARGET_DEFAULTS``).
    """
    raw = (raw or "").strip()
    values: dict[str, str] = {}
    origin: dict[str, str] = {}
    matches = list(_FIELD_RE.finditer(raw))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        value = raw[match.end() : end].strip(" \t\r\n,;/|·—-")
        name = _KEY_TO_FIELD[match.group(1).lower()]
        if value and name not in values:
            values[name], origin[name] = value, FROM_FIELD
    for name, value in (overrides or {}).items():
        if name in FIELD_KEYS and value and value.strip():
            values[name], origin[name] = value.strip(), FROM_FIELD
    free = raw[: matches[0].start()].strip() if matches else raw

    if "period" not in values and (period := _period_from_text(free)):
        values["period"], origin["period"] = period, FROM_TEXT
    elif values.get("period") and (years := period_years(values["period"])):
        values["period"] = _period_text(years)  # 최근 3년 -> 2024-2026
    # A period (최근 3년, 2024-2026) is not a season year.
    season_text = _RECENT_YEARS_RE.sub(" ", _PERIOD_RANGE_RE.sub(" ", free))
    if "season" not in values and (season := _season_from_text(season_text)):
        values["season"], origin["season"] = season, FROM_TEXT
    if study := _study_value(values.get("study", "")):
        values["study"] = study
    else:
        values.pop("study", None)
        origin.pop("study", None)
        if period_years(values.get("period", "")):
            values["study"], origin["study"] = STUDY_TREND, "기간에서 추론"
    if "price_band" not in values and (price := _PRICE_BAND_RE.search(free)):
        values["price_band"], origin["price_band"] = _clean(price.group(0)), FROM_TEXT
    if not values.get("product") and values.get("product_en") and not values.get("category"):
        values["product"], origin["product"] = values["product_en"], origin["product_en"]
    if not values.get("product") and not values.get("category") and free:
        product, english = _rule_product(free)
        if product:
            values["product"], origin["product"] = product, FROM_TEXT
            if english and "product_en" not in values:
                values["product_en"], origin["product_en"] = english, FROM_TEXT
    if values.get("product") and "product_en" not in values:
        if values["product"].isascii():
            values["product_en"], origin["product_en"] = values["product"], origin["product"]
        else:
            _same, english = _rule_product(values["product"])
            if english:
                values["product_en"], origin["product_en"] = english, "규칙 사전"

    # Target customer: the field, else a gender the sentence or product name states, else the default.
    defaults = defaults or {}
    gender = _gender_value(values.get("gender", ""))
    if not gender:
        origin.pop("gender", None)
        # Not the category: it names the market-size segment (men's outerwear), not the customer.
        named = " ".join((free, values.get("product", ""), values.get("product_en", "")))
        if gender := _gender_from_text(named):
            origin["gender"] = FROM_TEXT
        elif gender := _gender_value(defaults.get("gender", "")):
            origin["gender"] = FROM_DEFAULT
    if "style" in values:
        style = _style_value(values["style"])  # '' for 전체: the field still says so
    elif style := _style_value(defaults.get("style", "")):
        origin["style"] = FROM_DEFAULT

    competitors = [
        c
        for c in (_clean(x) for x in re.split(r",|·|/|;|\band\b|및", values.get("competitors", "")))
        if c
    ]
    return ResearchBrief(
        raw=raw,
        product=values.get("product", ""),
        product_en=values.get("product_en", ""),
        category=values.get("category", ""),
        season=values.get("season", ""),
        channel=values.get("channel", ""),
        price_band=values.get("price_band", ""),
        competitors=competitors,
        focus=values.get("focus", ""),
        study=values.get("study", ""),
        period=values.get("period", ""),
        gender=gender,
        style=style,
        origin=origin,
    )


def brief_gate(brief: ResearchBrief) -> str | None:
    """Reason code when the brief cannot be researched, else None."""
    if not brief.scope:
        return "no_scope"
    if not brief.search_term:
        return "no_english_name"  # nothing to search the US market with
    return None


def _for_target(brief: ResearchBrief, term: str, style: str = "") -> str:
    """The term for the brief's customer: men's bomber jacket, men's military bomber jacket."""
    words = set(_tokens(term))
    if style and not set(_tokens(style)) <= words:
        term = f"{style} {term}"
    prefix = {"men": "men's", "women": "women's"}.get(brief.gender, "")
    if prefix and not words & {"men", "women", "unisex"}:
        term = f"{prefix} {term}"
    return term


def _off_target(gender: str, title: str) -> bool:
    """A result titled for the other gender only ("Best Bomber Jackets for Women" in a men's study)."""
    other = {"men": "women", "women": "men"}.get(gender)
    if not other:
        return False
    return bool(_TITLE_GENDER[other].search(title)) and not _TITLE_GENDER[gender].search(title)


def build_queries(brief: ResearchBrief) -> list[tuple[str, str]]:
    """English, US-market search plan built only from brief values (no seeded brands or price bands).

    Review, trend and brand queries name the target customer (men's …); market-size queries do
    not, since market reports rarely split by gender. Each target style adds one brand query.
    """
    term = brief.search_term
    queries: list[tuple[str, str]] = []
    if not term:
        return queries
    who = _for_target(brief, term)
    styles = [s for s in _parts(brief.style) if not _has_korean(s)][:2]
    styled = [_for_target(brief, term, s) for s in styles]

    def add(text: str, kind: str) -> None:
        text = _clean(text)
        if text and text not in {q for q, _ in queries}:
            queries.append((text, kind))

    # Korean values would only pull Korean pages into a US study; see _unsearchable().
    focus = " ".join(p for p in _parts(brief.focus) if not _has_korean(p))
    channel = _english(brief.channel) or "amazon"
    price = _english(brief.price_band)
    competitors = [c for c in brief.competitors if not _has_korean(c)]
    if brief.study == STUDY_TREND:
        # How the market moved: one query per year, market size, then a few brand and review queries.
        years = study_years(brief)
        for year in years:
            add(f"{who} trend {year}", "market")
        category = _english(brief.category)
        add(f"{term} market size growth", "market")
        if category and category.lower() != term.lower():
            add(f"{category} US market size growth", "market")
        for name in competitors[:2]:
            add(f"{name} {term} {years[-1]}", "competitor")
        add(f"best {who} brands {years[-1]}", "competitor")
        add(f"{who} review complaints problems", "review")
        for target in styled:
            add(f"best {target} {years[-1]}", "competitor")
        return queries[:MAX_QUERIES]
    if brief.product:
        add(f"{who} review complaints problems", "review")
        add(f"{who} reddit issues worth it", "review")
        # Forum threads and owners' reviews (measured: heritage forums and store review pages
        # print their posts in the HTML; see consumer_posts).
        add(f"{term} review forum", "review")
        if focus:
            add(f"{who} {focus} complaints", "review")
        add(f"{who} {channel} customer reviews 1 star", "review")
        add(f"{who} product specifications materials fit", "competitor")
        for name in competitors[:4]:
            add(f"{name} {term} review price", "competitor")
        if not competitors:
            add(f"best {who} comparison price", "competitor")
        if price:
            add(f"{who} {price} best value", "competitor")
        for target in styled:
            add(f"best {target} brands", "competitor")
    else:
        for name in competitors[:5]:
            add(f"{name} {term} review complaints quality", "review")
        add(f"{who} brands customer complaints reddit", "review")
        add(f"{term} review forum", "review")
        add(f"{who} brands price comparison {price}", "competitor")
        for target in styled:
            add(f"best {target} brands", "competitor")
    queries = queries[: MAX_QUERIES - MARKET_QUERIES]
    # A narrow product name rarely appears in market reports ("slacks US market trends winter"
    # returned winter-wear reports only), so the second market query asks for size and growth
    # without the season, at the brief's category level when one is given in English.
    category = _english(brief.category) if brief.product else ""
    add(f"{who} US market trends {_season_en(brief.season)}", "market")
    if category and category.lower() != term.lower():
        add(f"{category} US market size growth", "market")
    else:
        add(f"{term} market size growth", "market")
    return queries


def scope_terms(brief: ResearchBrief, kind: str = "") -> list[str]:
    """Terms a kept result must mention. Korean terms are left out: kept pages are English.

    A market result may name the brief's category instead of the product: a market report
    covers the category (men's dress pants), not one product name in it (slacks).
    """
    if brief.product:
        terms = [brief.product, brief.product_en]
        if kind == "market":
            terms.append(brief.category)
    else:
        terms = [brief.category, brief.product_en, *brief.competitors]
    return list(dict.fromkeys(t for t in terms if t and not _has_korean(t)))


def _token_pairs(term: str) -> list[tuple[str, str]]:
    """(word as written, stem) per word: pants -> pant. 'ss' / 'us' / 'is' endings are not plurals."""
    out = []
    for tok in re.findall(r"[a-z0-9]+|[가-힣]+", re.sub(r"['’]s\b", "", term.lower())):  # men's -> men
        stem = tok
        if tok.isascii() and len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
            stem = tok[:-1]  # pants ~ pant
        out.append((tok, stem))
    return out


def _tokens(term: str) -> list[str]:
    return [stem for _word, stem in _token_pairs(term)]


def _token_hit(tok: str, low_text: str) -> bool:
    """A modifier word with a regular ending: ski ~ skiing / skier, men ~ men's, work ~ workers.

    Not a bare prefix: "men" must not match "mention", nor "work" "workflow".
    """
    if tok.isascii():
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?:s|es|['’]s|ing|ers?|ly)?(?![a-z0-9])", low_text))
    return tok in low_text


def _noun_hit(stem: str, low_text: str, plural_only: str = "") -> bool:
    """The head noun as a whole word, singular or plural: pant / pants, not panther or bootcut."""
    if not stem.isascii():
        return stem in low_text
    word = re.escape(plural_only) if plural_only else re.escape(stem) + r"(?:s|es)?"
    return bool(re.search(r"(?<![a-z0-9])" + word + r"(?![a-z0-9])", low_text))


def _term_hit(term: str, low_text: str) -> bool:
    """The term's last word (the noun: pants, boots, apparel) and at least half of the words before it.

    ``tactical cargo pants`` matches a page about cargo pants or tactical pants; ``ski pants``
    and ``work boots`` still need both words. Requiring every word dropped most cargo-pants pages.

    The singular of a plural noun counts only next to another word of the term: "Peak Cargo
    Pant" is a cargo pants page, but "Slack" alone is the chat app, not slacks.
    """
    pairs = _token_pairs(term)
    if not pairs:
        return False
    *modifiers, (head_word, head) = pairs
    if not _noun_hit(head, low_text):
        return False
    hits = sum(1 for _word, stem in modifiers if _token_hit(stem, low_text))
    if hits * 2 < len(modifiers):
        return False
    if head_word != head and not hits:
        return _noun_hit(head, low_text, plural_only=head_word)
    return True


def on_topic(terms: list[str], text: str) -> bool:
    low = text.lower()
    return any(_term_hit(term, low) for term in terms)


def _off_market_reason(domain: str, text: str) -> str:
    """Why a search result is not a US source ('' when it may be one); keys of OFF_MARKET_LABELS."""
    labels = domain.split(".")
    tld = labels[-1]
    if len(tld) == 2 and tld.isalpha() and tld not in _GENERIC_CC_TLDS:
        return "domain"
    edition = _EDITION_LABEL_RE.match(labels[0]) if len(labels) >= 3 else None
    if edition and edition.group(1) in _COUNTRY_CODES and edition.group(1) not in _NOT_A_COUNTRY_EDITION:
        return "edition"
    letters = [ch for ch in text if ch.isalpha()]
    if sum(1 for ch in letters if ord(ch) > 0x24F) * 10 > len(letters) * 3:
        return "script"
    if _FOREIGN_CURRENCY_RE.search(text) and not _USD_RE.search(text):
        return "currency"
    return ""


def page_locales(html: str) -> tuple[str, ...]:
    """Language tags a page declares in ``<html lang>`` and ``og:locale`` (lower case, ``-`` separated)."""
    head = html[:60_000]
    found: list[str] = []
    if match := _HTML_LANG_RE.search(head):
        found.append(match.group(1))
    for tag in _OG_LOCALE_RE.findall(head):
        if content := _CONTENT_RE.search(tag):
            found.append(content.group(1))
    return tuple(dict.fromkeys(tag.strip().lower().replace("_", "-") for tag in found if tag.strip()))


def foreign_locale(locales: tuple[str, ...] | list[str]) -> bool:
    """A declared locale of another country (en-gb, en_CA) or another language without the US (de, fr-fr)."""
    for tag in locales:
        parts = tag.strip().lower().replace("_", "-").split("-")
        lang = parts[0]
        region = next((p for p in parts[1:] if len(p) == 2 and p.isalpha()), "")
        if region:
            if region in _COUNTRY_CODES and region not in _US_REGIONS:
                return True
        elif lang != "en" and 2 <= len(lang) <= 3 and lang.isalpha():
            return True
    return False


class Page(str):
    """Page text that also carries what the markup said: declared locales (``page_locales``),
    structured USD prices (``structured_prices``) and how it was fetched (``via``)."""

    locales: tuple[str, ...] = ()
    offers: tuple[str, ...] = ()
    via: str = "urllib"
    published: str = ""
    updated: str = ""
    consumer: str = ""  # VOICE_REVIEW / VOICE_FORUM when the page shows consumer posts


def consumer_posts(html: str, text: str, url: str = "") -> str:
    """``리뷰`` / ``포럼`` when the page carries posts consumers wrote, else ''.

    Reviews: two or more schema.org Review items, or two or more review marks (Verified Buyer,
    out of 5 stars, "Was this review helpful"). Forum: three or more post markers (Joined,
    Messages, "… said:"), or one on a thread URL. An editor's review is neither.
    """
    if len(_LD_REVIEW_RE.findall(html or "")) >= 2 or len(_REVIEW_MARK_RE.findall(text or "")) >= 2:
        return VOICE_REVIEW
    marks = len(_FORUM_MARK_RE.findall(text or ""))
    if marks >= 3 or (marks and _FORUM_PATH_RE.search(urlsplit(url or "").path + "?" + urlsplit(url or "").query)):
        return VOICE_FORUM
    return ""


def fetch_failure(exc: BaseException) -> str:
    """Short reason a page fetch failed: ``HTTP 403``, ``시간 초과``, or the error type."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError):
        return "시간 초과"
    if (message := _clean(str(exc))).startswith("HTTP "):
        return message[:12]
    return type(exc).__name__


def _usd(value: object) -> str:
    try:
        amount = float(str(value).replace(",", "").strip())
    except ValueError:
        return ""
    if not 0 < amount < 100_000:
        return ""
    return f"${int(amount):,}" if amount == int(amount) else f"${amount:,.2f}"


def structured_prices(html: str) -> tuple[str, ...]:
    """USD prices a page states in schema.org Offer data (JSON-LD) or product:price meta tags."""
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("@type")
        kinds = " ".join(kind) if isinstance(kind, list) else str(kind or "")
        if "Offer" in kinds or "priceCurrency" in node:
            if str(node.get("priceCurrency") or "USD").upper() == "USD":
                for key in ("price", "lowPrice", "highPrice"):
                    if isinstance(node.get(key), (int, float, str)) and (amount := _usd(node[key])):
                        found.append(amount)
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for block in _LD_JSON_RE.findall(html):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    currency_tag = _META_CURRENCY_RE.search(html[:200_000])
    currency = _CONTENT_RE.search(currency_tag.group(0)) if currency_tag else None
    if (currency.group(1) if currency else "USD").strip().upper() == "USD":
        for tag in _META_PRICE_RE.findall(html[:200_000]):
            if (content := _CONTENT_RE.search(tag)) and (amount := _usd(content.group(1))):
                found.append(amount)
    return tuple(dict.fromkeys(found))[:6]


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "form", "iframe"}
    _BREAK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_data(self, data):  # noqa: ANN001
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed markup: keep what was parsed
        pass
    # One block per line, so excerpts can tell prose from menus and link lists.
    lines = (_clean(line) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


def _fetch_urllib(url: str, timeout: float) -> str | None:
    """Raw HTML, or None when the response is not HTML."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - http(s) only
        if "html" not in (response.headers.get("Content-Type") or "").lower():
            return None
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read(800_000)
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _fetch_impersonated(url: str, timeout: float) -> str:
    """Raw HTML through the browser-impersonating client ddgs ships (primp). Raises when it fails too."""
    from ddgs.http_client import HttpClient

    response = HttpClient(timeout=max(1, int(timeout))).get(url)
    if response.status_code >= 400:
        raise OSError(f"HTTP {response.status_code}")
    html = (response.text or "")[:800_000]
    return html if "<html" in html[:5000].lower() or "<body" in html.lower() else ""


def fetch_text(url: str, timeout: float = 8.0) -> str:
    """Page body as plain text. Raises on network errors; '' for non-HTML.

    A 403 / 429 / 503 or a dropped connection is retried once with a browser-like client:
    some review and retail sites refuse a plain urllib request but serve a browser.
    """
    via = "urllib"
    try:
        html = _fetch_urllib(url, timeout)
    except urllib.error.HTTPError as exc:
        if exc.code not in _RETRY_IMPERSONATED:
            raise
        html, via = _fetch_impersonated(url, timeout), "impersonated"
    except (urllib.error.URLError, ConnectionError) as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            raise  # a slow page is not retried: it would only double the wait
        html, via = _fetch_impersonated(url, timeout), "impersonated"
    if html is None:
        return ""
    page = Page(html_to_text(html))
    page.locales = page_locales(html)
    page.offers = structured_prices(html)
    page.published = page_published(html)
    page.updated = page_updated(html)
    page.via = via
    page.consumer = consumer_posts(html, page, url)
    return page


_last_search = 0.0


def _host_in(domain: str, hosts: tuple[str, ...]) -> bool:
    return any(domain == host or domain.endswith("." + host) for host in hosts)


def _listing_page(domain: str, path: str) -> bool:
    """A retailer's search, category or store page (see _RETAIL_ITEM_PATHS)."""
    item_path = _RETAIL_ITEM_PATHS.get(domain)
    return bool(item_path) and not item_path.search(path + "/")


def _allocate(
    rows: list[dict], candidates: list[int], quota: dict[str, int], total: int, per_domain: int = 0
) -> list[int]:
    """Row indexes picked in candidate (rank) order: each kind up to its quota first, then any kind up to ``total``.

    ``per_domain`` > 0 caps how many picks a single domain may take.
    """
    picked: list[int] = []
    taken: set[int] = set()
    kinds: dict[str, int] = {}
    domains: dict[str, int] = {}
    for within_quota in (True, False):
        for index in candidates:
            if len(picked) >= total:
                return picked
            row = rows[index]
            if index in taken:
                continue
            if within_quota and kinds.get(row["kind"], 0) >= quota.get(row["kind"], 0):
                continue
            if per_domain and domains.get(row["domain"], 0) >= per_domain:
                continue
            taken.add(index)
            picked.append(index)
            kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
            domains[row["domain"]] = domains.get(row["domain"], 0) + 1
    return picked


def _yahoo_target(href: str) -> str:
    """Real URL behind a r.search.yahoo.com redirect link."""
    if "/RU=" not in href:
        return href
    target = href.split("/RU=", 1)[1]
    return unquote_plus(target.split("/RK=", 1)[0].split("/RS=", 1)[0])


def parse_yahoo_results(page: str) -> list[dict]:
    """Organic results from a Yahoo result page, in page order.

    Yahoo serves a desktop and a mobile layout depending on the browser profile,
    and result blocks sit inside one another in the parsed tree. Reading every
    title under a block therefore glues the next result's title onto it. Each
    result has exactly one linked title, so titles and bodies are walked in
    document order instead: a body belongs to the linked title right before it.
    """
    from lxml import html as lxml_html

    tree = lxml_html.fromstring(page)
    nodes = tree.xpath(
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' algo-sr ')]"
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' compTitle ')"
        " or contains(concat(' ', normalize-space(@class), ' '), ' compText ')]"
    )
    rows: list[dict] = []
    open_row: dict | None = None  # last linked title still waiting for its body
    for node in nodes:
        classes = f" {node.get('class', '')} "
        if " compTitle " in classes:
            open_row = None  # a heading without a link ("Related searches") ends the result
            heading = node.xpath(".//h3[1]")
            if not heading:
                continue
            # desktop: <a><h3>title</h3></a>; mobile: <h3><a aria-label="title">site › crumbs</a></h3>
            link = heading[0].xpath("ancestor::a[1]") or heading[0].xpath(".//a[@href][1]")
            if not link or not link[0].get("href"):
                continue
            title = link[0].get("aria-label") or heading[0].text_content()
            open_row = {"title": _clean(title), "url": _yahoo_target(link[0].get("href")), "snippet": ""}
            rows.append(open_row)
        elif open_row is not None:
            open_row["snippet"] = _clean(node.text_content())
            open_row = None
    return [row for row in rows if row["title"] and row["url"].startswith("http")]


def yahoo_search(query: str, max_results: int) -> list[dict]:
    """One request to search.yahoo.com through the HTTP client ddgs ships (browser impersonation)."""
    from ddgs.http_client import HttpClient

    response = HttpClient(timeout=SEARCH_TIMEOUT).get(YAHOO_SEARCH_URL, params={"p": query})
    if response.status_code != 200:
        return []
    return parse_yahoo_results(response.text or "")[:max_results]


def ddg_search(query: str, max_results: int) -> list[dict]:
    """Search rows tagged with the path that produced them (``via``: ``yahoo`` or ``ddgs``)."""
    global _last_search
    wait = _last_search + SEARCH_SPACING - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    try:
        try:
            rows = yahoo_search(query, max_results)
        except Exception:  # noqa: BLE001 - markup or client changed: use the library path
            rows = []
        if rows:
            return [{**row, "via": "yahoo"} for row in rows]
        from ddgs import DDGS

        found = DDGS(timeout=SEARCH_TIMEOUT).text(query, max_results=max_results, region=SEARCH_REGION)
    finally:
        _last_search = time.monotonic()
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", ""), "via": "ddgs"}
        for r in found or []
    ]


def _search(searcher: Searcher, query: str) -> list[dict]:
    try:
        return searcher(query, RESULTS_PER_QUERY)
    except Exception:  # noqa: BLE001 - throttled or flaky backend: one more try
        time.sleep(SEARCH_RETRY_DELAY)
        return searcher(query, RESULTS_PER_QUERY)


def _unmerge(found: list[dict]) -> list[dict]:
    """Normalize rows and cut back a row that a backend glued together from its neighbours.

    Some backends return the first hit with the titles and snippets of the next
    hits appended. Left alone, a sentence from one page is quoted under another URL.
    """
    rows = [
        {"title": _clean(r.get("title")), "snippet": _clean(r.get("snippet")), "url": _clean(r.get("url"))}
        for r in found or []
    ]
    for row in rows:
        for other in rows:
            if other is row:
                continue
            for key, size in (("title", 12), ("snippet", 40)):
                probe = other[key][:80]
                cut = row[key].find(probe) if len(probe) >= size else -1
                if cut > 0:
                    row[key] = row[key][:cut].strip()
    return rows


def _price_lines(text: str, limit: int = PRICE_LINES) -> list[str]:
    """Lines of a page that state a US-dollar price, with the line before when the price stands alone.

    Product tiles and spec tables put the price on its own short line under the name.
    """
    lines = text.split("\n")
    out: list[str] = []
    for index, line in enumerate(lines):
        if len(line) > 240 or not _PRICE_RE.search(line) or _FOREIGN_CURRENCY_RE.search(line):
            continue
        if len(line) < 40 and index:
            line = f"{lines[index - 1][:160]} {line}"
        if line not in out:
            out.append(line.strip())
        if len(out) >= limit:
            break
    return out


def _figure_lines(text: str, limit: int = FIGURE_LINES, width: int = 400) -> list[str]:
    """Lines of a market page that state a market figure (USD 41.07 Billion, CAGR), with the line
    before when the figure stands alone ("Base year 2024" / "USD 41.07 Billion")."""
    lines = text.split("\n")
    out: list[str] = []
    for index, line in enumerate(lines):
        match = _MARKET_FIGURE_RE.search(line)
        if not match:
            continue
        if len(line) > width:
            begin = max(0, match.start() - width // 3)
            line = line[begin : begin + width]
        elif len(line) < 40 and index and not _MARKET_FIGURE_RE.search(lines[index - 1]):
            # The label line ("Base year 2024"), unless it is itself a figure line already kept.
            line = f"{lines[index - 1][:160]} {line}"
        if (line := line.strip()) not in out:
            out.append(line)
        if len(out) >= limit:
            break
    return out


def _years_named(text: str, years: list[int]) -> bool:
    return any(re.search(rf"(?<!\d){y}(?!\d)", text) for y in years)


_URL_YEAR_RE = re.compile(r"(?<![0-9])(20[0-9]{2})(?![0-9])")
_REDDIT_POST_RE = re.compile(r"/comments/([0-9a-z]{5,8})(?:/|$)", re.IGNORECASE)
# First Reddit post id of each January (base 36, approximate to a month or two). Ids are
# sequential, so an id gives the year it was posted: 4p3ji0 is 2016, 9d6xqk is 2018.
_REDDIT_YEAR_START = (
    (2016, "3z0000"),
    (2017, "5l0000"),
    (2018, "7n0000"),
    (2019, "ab0000"),
    (2020, "eh0000"),
    (2021, "kn0000"),
    (2022, "rs0000"),
    (2023, "1000000"),
    (2024, "18v0000"),
    (2025, "1hq0000"),
)


def url_year(url: str, current_year: int | None = None) -> int:
    """Year a URL dates its page to: a Reddit post id, else a year in the path. 0 when none.

    A Reddit id newer than the last table entry gives 0: its year is not known.
    """
    parts = urlsplit(url or "")
    if match := _REDDIT_POST_RE.search(parts.path):
        post = int(match.group(1).lower(), 36)
        found = 0
        for year, start in _REDDIT_YEAR_START:
            if post < int(start, 36):
                return found or year - 1
            found = year
        return 0
    latest = (current_year or date.today().year) + 1
    years = [int(y) for y in _URL_YEAR_RE.findall(parts.path) if 2000 <= int(y) <= latest]
    return min(years) if years else 0


def _gender_named(text: str) -> bool:
    return bool(re.search(r"\b(?:men|mens|women|womens|unisex)\b", re.sub(r"['’]s\b", "", text.lower())))


def _excerpt(text: str, terms: list[str], width: int = 340, windows: int = 2) -> str:
    """Up to ``windows`` on-topic passages, in page order. Blocks without a sentence are skipped."""
    scored: list[tuple[int, int, int, str]] = []
    for index, block in enumerate(text.split("\n")):
        if len(block) < 60:
            continue
        low = block.lower()
        hits = sum(1 for term in terms if _term_hit(term, low))
        sentences = len(_SENTENCE_END_RE.findall(block))
        if hits and sentences:
            scored.append((hits, min(sentences, 6), -index, block))
    chunks: list[str] = []
    for _hits, _sentences, _order, block in sorted(sorted(scored, reverse=True)[:windows], key=lambda s: -s[2]):
        if len(block) > width:
            low = block.lower()
            found = [p for p in (low.find(tok) for term in terms for tok in _tokens(term)[-1:]) if p >= 0]
            begin = max(0, min(found) - 110) if found else 0
            if begin:  # start on a word boundary, not mid-word
                begin = block.find(" ", begin) + 1
            block = block[begin : begin + width]
        chunks.append(block.strip())
    return " … ".join(chunks)


def collect_evidence(
    brief: ResearchBrief,
    searcher: Searcher | None = None,
    fetcher: Fetcher | None = None,
    reddit: RedditClient | None = None,
    today: date | None = None,
) -> tuple[list[Evidence], dict]:
    """``reddit``: an API client (``reddit_api``); with one, Reddit threads are searched and read."""
    searcher = searcher or ddg_search
    fetcher = fetcher or fetch_text
    current_year = (today or date.today()).year
    queries = build_queries(brief)
    rows: list[dict] = []
    seen: set[str] = set()
    search_errors: list[str] = []
    empty_queries: list[str] = []
    off_market: list[str] = []
    off_market_by: dict[str, int] = {}
    listing: list[str] = []
    off_target: list[str] = []
    search_via: dict[str, int] = {}  # queries answered per search path

    def _drop_off_market(domain: str, reason: str) -> None:
        off_market.append(domain)
        off_market_by[reason] = off_market_by.get(reason, 0) + 1

    def _take(row: dict, rank: int, kind: str, query: str) -> None:
        parts = urlsplit(row["url"])
        domain = parts.netloc.lower().removeprefix("www.")
        key = (parts.netloc.lower() + parts.path).rstrip("/")
        if parts.scheme not in {"http", "https"} or key in seen or _host_in(domain, _NON_SOURCE_HOSTS):
            return
        seen.add(key)
        if reason := _off_market_reason(domain, f"{row['title']} {row['snippet']}"):
            _drop_off_market(domain, reason)
            return
        if _listing_page(domain, parts.path):
            listing.append(row["url"])
            return
        if _off_target(brief.gender, row["title"]):
            off_target.append(row["url"])
            return
        rows.append({**row, "domain": domain, "kind": kind, "query": query, "rank": rank})

    for query, kind in queries:
        try:
            found = _search(searcher, query)
        except Exception as exc:  # noqa: BLE001 - one failed query must not end the run
            search_errors.append(f"{query} ({type(exc).__name__}: {_clean(str(exc))[:60]})")
            continue
        if not found:
            empty_queries.append(query)
        if found and found[0].get("via"):
            search_via[found[0]["via"]] = search_via.get(found[0]["via"], 0) + 1
        for rank, row in enumerate(_unmerge(found)):
            _take(row, rank, kind, query)
    reddit_queries_run: list[str] = []
    if reddit is not None:
        for query in reddit_queries(brief):
            reddit_queries_run.append(query)
            for rank, row in enumerate(reddit.search(query, REDDIT_RESULTS)):
                _take(row, rank, "review", f"Reddit API: {query}")
    results = len(rows) + len(off_market) + len(listing) + len(off_target)
    # Rank order across queries: every query's first hit, then every second hit, …
    rows.sort(key=lambda r: r["rank"])

    failures: dict[str, str] = {}  # url -> why its body was not read

    def _body(row: dict) -> str:
        try:
            body = fetcher(row["url"])
        except Exception as exc:  # noqa: BLE001 - blocked/slow page: fall back to the snippet
            failures[row["url"]] = fetch_failure(exc)
            return ""
        if len(body or "") < MIN_BODY_CHARS:
            failures[row["url"]] = EMPTY_BODY
        return body or ""

    # Fetch slots go to pages that can be read, shared out per kind; the rest keep their snippet.
    trend = brief.study == STUDY_TREND
    kind_quota, fetch_quota = (TREND_KIND_QUOTA, TREND_FETCH_QUOTA) if trend else (KIND_QUOTA, FETCH_QUOTA)
    readable = [i for i, row in enumerate(rows) if not _host_in(row["domain"], _NO_FETCH_HOSTS)]
    to_fetch = _allocate(rows, readable, fetch_quota, MAX_FETCH)
    bodies = [""] * len(rows)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, body in zip(to_fetch, pool.map(_body, [rows[i] for i in to_fetch])):
            bodies[index] = body
    # Reddit threads are read through the API (one call each, spaced), outside the fetch slots.
    reddit_read: list[int] = []
    if reddit is not None:
        threads = [i for i, row in enumerate(rows) if _host_in(row["domain"], REDDIT_HOSTS) and _is_thread(row["url"])]
        for index in threads[:REDDIT_MAX_THREADS]:
            reddit_read.append(index)
            thread = reddit.thread(rows[index]["url"])
            if thread.get("text"):
                page = Page(thread["text"])
                page.published = thread.get("published", "")
                page.via = "reddit_api"
                bodies[index] = page

    terms = scope_terms(brief)
    market_terms = scope_terms(brief, "market")
    excerpt_terms = [t for t in _parts(brief.focus) if not _has_korean(t)] + terms
    usable: list[int] = []
    excerpts: dict[int, tuple[str, str]] = {}
    figures: dict[int, list[str]] = {}
    dates: dict[int, tuple[str, str]] = {}  # (published, updated)
    stale: set[int] = set()
    undated: set[int] = set()
    years = study_years(brief) if trend else []
    off_topic = 0
    for index, (row, body) in enumerate(zip(rows, bodies)):
        if foreign_locale(getattr(body, "locales", ())):
            _drop_off_market(row["domain"], "locale")  # e.g. a UK or Canadian site on a .com domain
            continue
        row_terms = market_terms if row["kind"] == "market" else terms
        head_ok = on_topic(row_terms, f"{row['title']} {row['snippet']}")
        body_ok = len(body) >= MIN_BODY_CHARS and on_topic(row_terms, body)
        from_body = _excerpt(body, excerpt_terms + row_terms[len(terms):]) if body_ok else ""
        if body_ok and row["kind"] == "market" and (found := _figure_lines(body)):
            # A market report states its figures without repeating the product name.
            figures[index] = found
            if not _MARKET_FIGURE_RE.search(from_body):
                from_body = " … ".join([found[0], from_body] if from_body else found[:2])
        if not from_body and not head_ok:
            off_topic += 1
            continue
        if excerpt := from_body or row["snippet"]:
            usable.append(index)
            excerpts[index] = (excerpt, "본문" if from_body else "요약문")
            published = (
                getattr(body, "published", "") or row.get("published", "") or snippet_published(row["snippet"])
            )
            dates[index] = (published, getattr(body, "updated", ""))
            when = dates[index][1] or published
            if years:
                named = _years_named(f"{row['title']} {row['snippet']} {excerpt}", years)
                if when:
                    if int(when[:4]) < years[0] and not named:
                        stale.add(index)
                elif year := url_year(row["url"]):
                    # The URL keeps the year an SEO page was written; its title may name this year.
                    if year < years[0]:
                        stale.add(index)
                elif not named:
                    undated.add(index)
    # A trend study reads an undated page after dated ones, an older page only when nothing
    # from the period fills the slot.
    usable.sort(key=lambda i: (i in stale, i in undated))
    kind_order = {kind: n for n, (kind, _label) in enumerate(KIND_LABELS)}
    chosen = sorted(
        _allocate(rows, usable, kind_quota, MAX_EVIDENCE, MAX_PER_DOMAIN),
        key=lambda i: (kind_order.get(rows[i]["kind"], len(kind_order)), i),
    )
    evidence: list[Evidence] = []
    for number, index in enumerate(chosen, 1):  # numbered in the order the pack lists them
        row = rows[index]
        excerpt, source = excerpts[index]
        body = bodies[index]
        detail, page_prices = excerpt, list(getattr(body, "offers", ()) or ())
        if source == "본문":
            row_terms = market_terms if row["kind"] == "market" else terms
            detail = _excerpt(body, excerpt_terms + row_terms[len(terms):], width=600, windows=4) or excerpt
            # Marked lines go after the cut, so a long body cannot push them out.
            detail = detail[:DETAIL_CHARS]
            if row["kind"] == "competitor":
                lines = _price_lines(body)
                if lines:
                    detail += f"\n{PRICE_LINE_MARK} " + " | ".join(lines)
                page_prices += [p for line in lines for p in _PRICE_RE.findall(line)]
            if index in figures:
                detail += f"\n{FIGURE_LINE_MARK} " + " | ".join(figures[index])
        published, updated = dates[index]
        if _host_in(row["domain"], REDDIT_HOSTS):
            voice_from = "reddit"
        elif row["kind"] == "review" and source == "본문":
            voice_from = getattr(body, "consumer", "")
        else:
            voice_from = ""
        post_year = 0
        if voice_from:
            when = updated or published
            post_year = int(when[:4]) if when[:4].isdigit() else url_year(row["url"], current_year)
        evidence.append(
            Evidence(
                id=f"E{number}",
                kind=row["kind"],
                title=row["title"][:140],
                url=row["url"],
                domain=row["domain"],
                source=source,
                excerpt=excerpt[:EXCERPT_CHARS],
                prices=list(dict.fromkeys(_clean(p) for p in _PRICE_RE.findall(excerpt)))[:5],
                query=row["query"],
                detail=detail,
                page_prices=list(dict.fromkeys(_clean(p) for p in page_prices))[:8],
                published=published,
                updated=updated,
                before_period=index in stale,
                undated=index in undated,
                all_genders=brief.gender in {"men", "women"} and not _gender_named(row["query"]),
                voice=VOICE_LABEL if voice_from else "",
                voice_from=voice_from,
                old_post=bool(post_year) and current_year - post_year > OLD_POST_YEARS,
                post_year=post_year,
            )
        )
    review_fetched = [i for i in to_fetch if rows[i]["kind"] == "review"]
    failure_counts: dict[str, int] = {}
    for index in to_fetch:
        if reason := failures.get(rows[index]["url"]):
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
    stats = {
        "queries": len(queries),
        "search_errors": search_errors,
        "empty_queries": empty_queries,
        "search_via": search_via,
        "results": results,
        "off_market_dropped": len(off_market),
        "off_market_domains": sorted(set(off_market)),
        "off_market_by": off_market_by,
        "listing_dropped": len(listing),
        "off_target_dropped": len(off_target),
        "fetch_attempted": len(to_fetch),
        "fetch_ok": sum(1 for i in to_fetch if len(bodies[i]) >= MIN_BODY_CHARS),
        "fetch_impersonated_ok": sum(
            1 for i in to_fetch if len(bodies[i]) >= MIN_BODY_CHARS and getattr(bodies[i], "via", "") == "impersonated"
        ),
        "fetch_failures": dict(sorted(failure_counts.items(), key=lambda kv: -kv[1])),
        "review_pages": {
            "attempted": len(review_fetched),
            "ok": sum(1 for i in review_fetched if len(bodies[i]) >= MIN_BODY_CHARS),
            "consumer": sum(
                1 for i in review_fetched if len(bodies[i]) >= MIN_BODY_CHARS and getattr(bodies[i], "consumer", "")
            ),
            "blocked": sum(1 for i in review_fetched if failures.get(rows[i]["url"]) in _BLOCKED_STATUSES),
            "evidence": sum(1 for e in evidence if e.voice_from in {VOICE_REVIEW, VOICE_FORUM}),
            "old_posts": sum(1 for e in evidence if e.old_post and e.voice_from in {VOICE_REVIEW, VOICE_FORUM}),
        },
        "off_topic_dropped": off_topic,
        "evidence": len(evidence),
        "evidence_body": sum(1 for e in evidence if e.source == "본문"),
        "kind_quota": dict(kind_quota),
        "evidence_by_kind": {kind: sum(1 for e in evidence if e.kind == kind) for kind, _label in KIND_LABELS},
        "reddit_api": (
            {
                "enabled": True,
                "searches": reddit_queries_run,
                "threads_attempted": len(reddit_read),
                "threads_ok": sum(1 for i in reddit_read if len(bodies[i]) >= MIN_BODY_CHARS),
                "evidence": sum(1 for e in evidence if e.voice_from == "reddit" and e.source == "본문"),
                "errors": list(reddit.errors),
            }
            if reddit is not None
            else {"enabled": False}
        ),
    }
    if trend:
        stats["years"] = years
        stats["evidence_by_year"] = {str(y): sum(1 for e in evidence if about_year(e, y)) for y in years}
        stats["before_period_found"] = len(stale)
        stats["before_period_kept"] = sum(1 for e in evidence if e.before_period)
        stats["undated_kept"] = sum(1 for e in evidence if e.undated)
    return evidence, stats


def about_year(item: Evidence, year: int) -> bool:
    """The version read is from that year (update date, else publication date), or the text names the year."""
    if content_date(item).startswith(str(year)):
        return True
    return bool(re.search(rf"(?<!\d){year}(?!\d)", f"{item.title} {item.excerpt} {item.detail}"))


def _is_thread(url: str) -> bool:
    return bool(_REDDIT_POST_RE.search(urlsplit(url or "").path))


def reddit_queries(brief: ResearchBrief) -> list[str]:
    """Reddit API searches: the English product name, and with the brief's English focus.

    Reddit search matches post titles and text, so the long web review queries (``… review
    complaints problems``) find little there; the bare product name finds the threads.
    """
    term = brief.search_term
    if not term:
        return []
    focus = " ".join(p for p in _parts(brief.focus) if not _has_korean(p))
    out = [term]
    if focus:
        out.append(f"{term} {focus}")
    return out


def _cell(text: str) -> str:
    return _clean(text).replace("|", "\\|")


def _brief_table(brief: ResearchBrief) -> list[str]:
    lines = ["| 항목 | 값 | 출처 |", "|---|---|---|"]
    for name, label in FIELD_LABELS:
        value = getattr(brief, name)
        value = ", ".join(value) if isinstance(value, list) else value
        if name == "study":
            value = STUDY_LABELS.get(value, value)
        elif name == "gender":
            value = GENDER_LABELS.get(value, value)
        elif name == "style" and not value and name in brief.origin:
            value = "전체(스타일 무관)"
        lines.append(f"| {label} | {_cell(value) or '미지정'} | {brief.origin.get(name, '-') if value else '-'} |")
    if FROM_DEFAULT in (brief.origin.get("gender"), brief.origin.get("style")):
        lines += [
            "",
            "성별·스타일을 적지 않아 CQR 기본 타깃으로 검색했습니다. 다른 타깃이면 "
            "`성별: 여성`, `성별: 전체`, `스타일: 전체`처럼 지정하세요.",
        ]
    if left_out := _unsearchable(brief):
        lines += [
            "",
            "한국어로 적혀 미국 시장 검색에 쓰지 않은 값: " + ", ".join(left_out) + ". 영어로 적으면 검색에 반영됩니다.",
        ]
    if brief.study == STUDY_TREND:
        years = ", ".join(str(y) for y in study_years(brief))
        default = "" if period_years(brief.period) else f" (기간을 지정하지 않아 최근 {TREND_DEFAULT_YEARS}년)"
        lines += ["", f"연도별로 검색한 해: {years}{default}"]
    lines += ["", f"해석이 틀렸거나 항목을 더 지정하려면 필드로 다시 요청하세요: `{FIELD_EXAMPLE}`"]
    return lines


def render_markdown(
    brief: ResearchBrief,
    evidence: list[Evidence],
    stats: dict,
    queries: list[tuple[str, str]],
    session_id: str,
    dry_run: bool = False,
    trends: dict | None = None,
) -> str:
    out = [
        f"# 시장조사 근거 팩 — {brief.scope}",
        "",
        f"- 세션: `{session_id}`",
        f"- 대상 시장: {MARKET_LABEL} (영어 검색어 · 다른 나라 도메인과 한글 등 비라틴 문자 페이지 제외)",
    ]
    if brief.raw:
        out.append(f"- 요청 원문: {_clean(brief.raw)}")
    out += ["", "## 브리프 해석", "", *_brief_table(brief), ""]
    if dry_run:
        out += [
            "> DRY RUN — 검색을 실행하지 않았습니다. 아래는 실행 예정 검색어이며 조사 결과가 아닙니다.",
            "",
            "## 실행 예정 검색어",
            "",
            *[f"- `{q}`" for q, _ in queries],
            "",
        ]
        return "\n".join(out)

    dropped_from = f"({', '.join(stats['off_market_domains'][:8])})" if stats["off_market_domains"] else ""
    out += [
        "> 웹에서 수집해 브리프 주제와 맞는지 확인한 근거 모음입니다. 발췌는 원문 그대로입니다. "
        "시장 공백·페르소나·시장 규모·가격 전략 같은 종합 결론은 이 문서에 없습니다.",
        "",
        "## 수집 요약",
        "",
        f"- 검색 {stats['queries']}회, 결과 {stats['results']}건, "
        f"미국 외 출처라 제외 {stats['off_market_dropped']}건{dropped_from}, "
        f"소매처(Amazon·Walmart·Target) 상품 목록 페이지라 제외 {stats.get('listing_dropped', 0)}건, "
        + (
            f"제목이 다른 성별 대상이라 제외 {stats['off_target_dropped']}건, "
            if brief.gender in {"men", "women"} and "off_target_dropped" in stats
            else ""
        )
        + f"주제와 무관해 제외 {stats['off_topic_dropped']}건",
    ]
    if by := stats.get("off_market_by"):
        out.append(
            "- 미국 외 출처로 본 이유: "
            + ", ".join(f"{OFF_MARKET_LABELS.get(k, k)} {n}건" for k, n in sorted(by.items(), key=lambda kv: -kv[1]))
        )
    fallback = stats.get("fetch_impersonated_ok", 0)
    out += [
        f"- 본문 수집 {stats['fetch_ok']}/{stats['fetch_attempted']}건"
        + (f" (일반 요청이 막혀 브라우저형 요청으로 읽은 {fallback}건 포함)" if fallback else "")
        + (
            " — 못 읽은 이유: " + ", ".join(f"{reason} {n}건" for reason, n in failed.items())
            if (failed := stats.get("fetch_failures"))
            else ""
        ),
        f"- 채택 근거 {stats['evidence']}건 (본문 {stats['evidence_body']}건, "
        f"검색 요약문만 {stats['evidence'] - stats['evidence_body']}건)",
    ]
    if (pages := stats.get("review_pages")) and pages.get("attempted"):
        line = (
            f"- 리뷰·포럼 페이지(Reddit 제외): 본문 수집 {pages['ok']}/{pages['attempted']}건, "
            f"소비자 리뷰·포럼 글로 판정 {pages['consumer']}건, 채택 {pages['evidence']}건 "
            f"({VOICE_LABEL} — 불만·사용 사례 근거, 가격·시장 수치 근거 아님)"
        )
        if pages.get("blocked"):
            line += f", 차단 {pages['blocked']}건"
        if pages.get("old_posts"):
            line += f", {OLD_POST_YEARS}년 넘은 글 {pages['old_posts']}건(근거에 `오래된 글` 표시)"
        out.append(line)
    quota = stats.get("kind_quota") or {}
    by_kind = stats.get("evidence_by_kind") or {}
    if quota:
        out.append(
            "- 종류별 채택 건수(할당): "
            + ", ".join(f"{label} {by_kind.get(kind, 0)}({quota.get(kind, 0)})" for kind, label in KIND_LABELS)
            + ". 할당을 못 채운 종류의 남은 자리는 다른 종류가 씁니다."
        )
    by_year = stats.get("evidence_by_year") or {}
    if by_year:
        out.append(
            "- 연도별 근거(게시일이 그해이거나 내용에 그해가 나온 근거): "
            + ", ".join(f"{year}년 {n}건" for year, n in by_year.items())
        )
    if found := stats.get("before_period_found"):
        out.append(
            f"- 조사 기간 이전에 게시·수정된 페이지 {found}건은 기간 안의 근거가 모자랄 때만 썼습니다 "
            f"(채택 {stats.get('before_period_kept', 0)}건)"
        )
    if undated_kept := stats.get("undated_kept"):
        out.append(f"- 게시일을 확인하지 못한 페이지 {undated_kept}건은 날짜가 확인된 근거 뒤에 채택했습니다")
    if via := stats.get("search_via"):
        labels = {"yahoo": "Yahoo 직접 조회", "ddgs": "ddgs 라이브러리(대체 경로)"}
        out.append("- 검색 경로: " + ", ".join(f"{labels.get(k, k)} {n}회" for k, n in sorted(via.items())))
    reddit = stats.get("reddit_api") or {}
    if reddit.get("enabled"):
        line = (
            f"- Reddit 공식 API: 검색 {len(reddit.get('searches', []))}회, "
            f"스레드 본문·댓글 수집 {reddit.get('threads_ok', 0)}/{reddit.get('threads_attempted', 0)}건, "
            f"채택 {reddit.get('evidence', 0)}건 ({VOICE_LABEL} — 불만·사용 사례 근거, 가격·시장 수치 근거 아님)"
        )
        if errors := reddit.get("errors"):
            line += f". 실패 {len(errors)}회: " + "; ".join(errors[:5])
        out.append(line)
    elif "reddit_api" in stats:
        out.append(
            "- Reddit 공식 API: 설정 안 됨 — Reddit 결과는 검색 요약문만 사용 "
            "(`REDDIT_CLIENT_ID`·`REDDIT_CLIENT_SECRET` 설정 시 스레드 본문과 댓글을 읽습니다)"
        )
    if stats["search_errors"]:
        out.append(f"- 실패한 검색 {len(stats['search_errors'])}회: " + "; ".join(stats["search_errors"]))
    if empty := stats.get("empty_queries"):
        out.append(f"- 결과가 없던 검색 {len(empty)}회: " + "; ".join(f"`{q}`" for q in empty))
    out.append("")

    missing: list[str] = []
    for kind, label in KIND_LABELS:
        items = [e for e in evidence if e.kind == kind]
        if not items:
            missing.append(f"{label}: 0건")
            continue
        if len(items) < quota.get(kind, 0):
            missing.append(f"{label}: 할당 {quota[kind]}건 중 {len(items)}건만 확보")
        out += [f"## {label} ({len(items)}건)", ""]
        for item in items:
            published = f" · 게시일 {item.published}" if item.published else ""
            if item.updated:
                published += f" · 수정일 {item.updated}"
            if item.before_period:
                published += " · 조사 기간 이전 글"
            if item.undated:
                published += " · 게시일 확인 불가"
            if item.all_genders:
                published += " · 성별 구분 없는 검색 결과"
            voice = f" · {item.voice}" if item.voice else ""
            if item.voice_from in {VOICE_REVIEW, VOICE_FORUM}:
                voice += f"({item.voice_from})"
            if item.old_post:
                published += f" · 오래된 글({item.post_year}년)"
            out += [
                f"### {item.id}. {item.title}",
                "",
                f"- 출처: {item.domain}{voice} · {item.source}{published} · 검색어 `{item.query}`",
            ]
            if item.prices:
                out.append(f"- 발췌 안 가격 표기: {', '.join(item.prices)}")
            if extra := [p for p in item.page_prices if p not in item.prices]:
                out.append(f"- 페이지의 상품 정보·가격 줄에 적힌 가격: {', '.join(extra)}")
            out += [f"- {item.url}", "", f"> {item.excerpt}", ""]
    for name in brief.competitors:
        low = name.lower()
        if not any(low in f"{e.title} {e.excerpt}".lower() for e in evidence):
            missing.append(f"경쟁사 `{name}`: 이 브랜드를 언급한 근거 0건")
    missing += [f"{year}년: 그해를 다룬 근거 0건" for year, n in by_year.items() if not n]
    if trends is not None:
        out += ["## 검색 관심도 (Google Trends)", ""]
        if trends.get("status") == "ok":
            cond = trends["conditions"]
            out += [
                f"- 근거 번호: {trends.get('evidence_id', '-')} · {trends['url']}",
                f"- 조회 조건: 검색어 {', '.join(f'`{k}`' for k in cond['keywords'])} · 미국 · {cond['category']} · "
                f"{cond['property']} · {cond['time'].replace(' ', '~')} · "
                f"{'월별' if trends['resolution'] == 'MONTH' else '주별'} · 시간대 {cond['timezone']} · 조회일 {cond['fetched']}",
                "",
                f"| 연도 | {trends['window']} 평균 (전년 대비) | 최근 {trends['recent_window']} 평균 (전년 대비) "
                "| 연간 평균(끝난 해) | 최고 | 최저 |",
                "|---|---|---|---|---|---|",
            ]

            def _avg_cell(avg, pct, way) -> str:
                if avg is None:
                    return "—"
                return f"{avg:g}" + (f" ({pct:+.1f}%, {way})" if pct is not None else "")

            for row in trends["years"]:
                full = "—" if row["full_avg"] is None else f"{row['full_avg']:g}"
                high = f"{row['high_label']} {row['high']}" if row["high"] is not None else "—"
                low = f"{row['low_label']} {row['low']}" if row["low"] is not None else "—"
                avg = _avg_cell(row["window_avg"], row["yoy_pct"], row["direction"])
                recent = _avg_cell(row["recent_avg"], row["recent_yoy_pct"], row["recent_direction"])
                label = f"{row['year']}" + ("" if row["in_period"] else " (비교 기준 해)")
                out.append(f"| {label} | {avg} | {recent} | {full} | {high} | {low} |")
            # Lines after the per-year ones: the other bases, spikes, keywords, scale.
            out += ["", *[f"- {line}" for line in trends["lines"][2 + len(trends["years"]):]]]
            out += ["", "규칙:", *[f"- {rule}" for rule in trends["rules"].values()], ""]
        else:
            out += [
                f"- 조회하지 못했습니다({trends.get('error') or trends.get('status')}). 연도별 수요 변화를 비교할 수치 근거가 없습니다.",
                f"- 같은 조회: {trends['url']}",
                "",
            ]
            missing.append(f"검색 관심도(Google Trends): 조회 실패({trends.get('error') or trends.get('status')})")
    missing.append("시장 규모·페르소나·세그먼트·가격 전략·컨셉 후보: 이 파이프라인은 산출하지 않습니다(종합 단계 없음)")
    out += ["## 근거가 없는 항목", "", *[f"- {m}" for m in missing], ""]
    out += ["## 실행한 검색어", "", *[f"- `{q}`" for q, _ in queries], ""]
    return "\n".join(out)


def run_evidence_pack(
    brief: ResearchBrief,
    output_dir: Path,
    session_id: str,
    dry_run: bool = False,
    searcher: Searcher | None = None,
    fetcher: Fetcher | None = None,
    trends_fetcher: TrendsFetcher | None = None,
    today: date | None = None,
    reddit: RedditClient | None = None,
) -> dict:
    """Write the pack. ``status`` is ``ok`` or ``insufficient_evidence`` (no report written).

    A trend study reads Google Trends with ``trends_fetcher``; a live run (no injected
    ``searcher``) uses ``fetch_trends``, a test that injects a searcher gets no Trends call
    unless it injects a trends fetcher too.

    Reddit threads are read through the API with ``reddit``; a live run uses the client
    ``reddit_from_env`` builds when credentials are configured (none otherwise).
    """
    queries = build_queries(brief)
    evidence: list[Evidence] = []
    stats: dict = {"queries": len(queries)}
    trends: dict | None = None
    if not dry_run:
        if reddit is None and searcher is None:
            reddit = reddit_from_env()
        evidence, stats = collect_evidence(brief, searcher, fetcher, reddit, today)
        fetch = trends_fetcher or (fetch_trends if searcher is None else None)
        if brief.study == STUDY_TREND and fetch is not None:
            keywords = trends_keywords(brief.search_term, brief.gender)
            trends = study_trends(keywords, study_years(brief), fetch, today)
            stats["trends"] = trends["status"]
            if trends["status"] == "ok":
                trends["evidence_id"] = f"E{len(evidence) + 1}"
                evidence.append(trends_evidence(trends))
                stats["evidence_data"] = 1
            elif trends.get("error"):
                stats["trends_error"] = trends["error"]
    web_evidence = sum(1 for e in evidence if e.source != TRENDS_SOURCE)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evidence_pack.json").write_text(
        json.dumps(
            {
                "schema": PACK_SCHEMA,
                "market": MARKET,
                "session_id": session_id,
                "dry_run": dry_run,
                "brief": asdict(brief),
                "queries": [{"query": q, "kind": k} for q, k in queries],
                "stats": stats,
                "evidence": [asdict(e) for e in evidence],
                **({"trends": trends} if trends is not None else {}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    result = {"status": "ok", "evidence_count": len(evidence), "stats": stats, "dry_run": dry_run}
    if not dry_run and web_evidence < MIN_EVIDENCE:
        result["status"] = "insufficient_evidence"
        return result
    markdown = render_markdown(brief, evidence, stats, queries, session_id, dry_run, trends)
    (output_dir / "research_report.md").write_text(markdown, encoding="utf-8")
    result["markdown"] = markdown
    return result


def trends_evidence(trends: dict) -> Evidence:
    """The Trends metrics as an evidence item, so the synthesis cites them like any other source."""
    cond = trends["conditions"]
    lines = trends["lines"]
    return Evidence(
        id=trends["evidence_id"],
        kind="market",
        title=(
            f"Google Trends 미국 검색 관심도 — {', '.join(cond['keywords'])} "
            f"({cond['time'].replace(' ', '~')}, {'월별' if trends['resolution'] == 'MONTH' else '주별'})"
        ),
        url=trends["url"],
        domain=TRENDS_DOMAIN,
        source=TRENDS_SOURCE,
        excerpt=" ".join(lines[: 2 + len(trends["years"])])[:EXCERPT_CHARS],
        prices=[],
        query=", ".join(cond["keywords"]),
        detail="\n".join(lines),
        # No publication date: the lines name every year they measure (and the day it was read).
    )
