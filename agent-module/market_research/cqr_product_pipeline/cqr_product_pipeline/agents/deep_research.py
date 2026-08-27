"""Deep Research agent — multi-query web search + structured synthesis."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from cqr_product_pipeline.config.providers import get_chat_model, get_search_tool
from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.prompts.deep_research import (
    DEEP_RESEARCH_SYSTEM,
    PAIN_EXTRACTION_SYSTEM,
)
from cqr_product_pipeline.prompts.language import with_language
from cqr_product_pipeline.schemas.models import (
    CompetitiveBattlecard,
    ConceptCandidate,
    CustomerJourney,
    JobStory,
    JourneyStage,
    MarketSegmentProfile,
    PersonaProfile,
    PricingStrategy,
    QuantSignals,
    ResearchReport,
    SourceRef,
)
from cqr_product_pipeline.utils.llm import invoke_structured

logger = logging.getLogger(__name__)

LINE_HINTS = ("Covert", "Liberator", "Expedition", "Sapper")

# Soft competitor seeds by *product family* only — never a closed product registry.
# Search queries always lock to the extracted product phrase from the brief.
FAMILY_COMPETITOR_SEEDS: dict[str, tuple[str, ...]] = {
    "footwear": (
        "Timberland PRO",
        "KEEN Utility",
        "Red Wing",
        "Wolverine",
        "Merrell",
        "Sorel",
    ),
    "bottoms": (
        "Columbia",
        "Patagonia",
        "The North Face",
        "Outdoor Research",
        "Carhartt",
        "Dickies",
    ),
    "dresses": ("Reformation", "J.Crew", "Everlane", "Uniqlo", "Aritzia"),
    "tops": ("Columbia", "Patagonia", "The North Face", "Arc'teryx", "Carhartt"),
    "handwear": ("Outdoor Research", "Black Diamond", "Hestra", "Mechanix", "Carhartt"),
    "headwear": ("Outdoor Research", "Carhartt", "The North Face", "Patagonia"),
    # Dive / swim — never seed Columbia/Carhartt outdoor apparel defaults here.
    "swim_dive": (
        "O'Neill",
        "Billabong",
        "Cressi",
        "Bare",
        "Mares",
        "Scubapro",
        "Patagonia",
    ),
    "other": ("Columbia", "Patagonia", "The North Face", "Carhartt"),
}

FAMILY_PRICE_BAND: dict[str, str] = {
    "footwear": "$80–$250",
    "bottoms": "$40–$220",
    "dresses": "$40–$200",
    "tops": "$50–$350",
    "handwear": "$20–$120",
    "headwear": "$20–$80",
    "swim_dive": "$80–$450",
    "other": "$40–$200",
}

# Cross-family drift tokens: a footwear brief answered with pants/jackets = fail.
FAMILY_DRIFT_TOKENS: dict[str, tuple[str, ...]] = {
    "footwear": ("pants", "바지", "팬츠", "skirt", "치마", "스커트", "jacket", "재킷"),
    "bottoms": (
        "boot",
        "부츠",
        "작업화",
        "안전화",
        "신발",
        "outsole",
        "midsole",
        "dress",
        "원피스",
    ),
    "dresses": ("boot", "부츠", "pants", "바지", "outsole", "작업화"),
    "tops": ("boot", "부츠", "작업화", "skirt", "치마", "스커트", "outsole"),
    "handwear": ("pants", "바지", "boot", "부츠", "작업화", "skirt", "치마"),
    "headwear": ("pants", "바지", "boot", "부츠", "작업화", "skirt", "치마"),
    "swim_dive": (
        "boot",
        "부츠",
        "작업화",
        "outsole",
        "midsole",
        "cargo pants",
        "카고바지",
    ),
}

# Optional exact phrase gloss (quality boost only). Unknown products still work via
# suffix/stem tables below — this is NOT a closed category registry.
_PRODUCT_GLOSS: dict[str, str] = {
    "스키바지": "ski pants",
    "스키 바지": "ski pants",
    "스키팬츠": "ski pants",
    "보드바지": "snowboard pants",
    "스노보드바지": "snowboard pants",
    "전술바지": "tactical pants",
    "카고바지": "cargo pants",
    "작업바지": "work pants",
    "등산바지": "hiking pants",
    "골프바지": "golf pants",
    "골프 바지": "golf pants",
    "테니스치마": "tennis skirt",
    "테니스 치마": "tennis skirt",
    "테니스스커트": "tennis skirt",
    "골프치마": "golf skirt",
    "골프 치마": "golf skirt",
    "골프스커트": "golf skirt",
    "골프 스커트": "golf skirt",
    "작업화": "work boots",
    "안전화": "safety boots",
    "등산화": "hiking boots",
    "방한화": "winter boots",
    "방한부츠": "winter boots",
    "겨울부츠": "winter boots",
    "작업장갑": "work gloves",
    "방한장갑": "winter gloves",
    "스키장갑": "ski gloves",
    "다이빙복": "diving suit",
    "잠수복": "wetsuit",
    "웨트수트": "wetsuit",
    "웨트슈트": "wetsuit",
    "드라이수트": "drysuit",
    "드라이슈트": "drysuit",
    "다이빙수트": "diving suit",
    "다이빙슈트": "diving suit",
    "수영복": "swimwear",
    "래시가드": "rash guard",
    "비키니": "bikini",
    "보드숏": "board shorts",
    "보드쇼츠": "board shorts",
}

# Modifier stem → English (for unregistered compounds like 사이클바지 → cycling pants).
_STEM_EN: dict[str, str] = {
    "스키": "ski",
    "보드": "snowboard",
    "스노보드": "snowboard",
    "전술": "tactical",
    "카고": "cargo",
    "작업": "work",
    "등산": "hiking",
    "하이킹": "hiking",
    "골프": "golf",
    "테니스": "tennis",
    "요가": "yoga",
    "러닝": "running",
    "조깅": "jogging",
    "사이클": "cycling",
    "바이크": "bike",
    "방한": "winter",
    "겨울": "winter",
    "레인": "rain",
    "플리스": "fleece",
    "소프트셸": "softshell",
    "하드셸": "hardshell",
    "안전": "safety",
    "클라이밍": "climbing",
    "낚시": "fishing",
    "피싱": "fishing",
    "헌팅": "hunting",
    "사냥": "hunting",
    "캠핑": "camping",
    "서핑": "surfing",
    "풋살": "futsal",
    "축구": "soccer",
    "야구": "baseball",
    "농구": "basketball",
    "배구": "volleyball",
    "배드민턴": "badminton",
    "스쿼시": "squash",
    "탁구": "table tennis",
    "마라톤": "marathon",
    "트레일": "trail",
    "트레킹": "trekking",
    "볼링": "bowling",
    "피트니스": "fitness",
    "헬스": "gym",
    "필라테스": "pilates",
    "크로스핏": "crossfit",
    "댄스": "dance",
    "발레": "ballet",
    "라이딩": "riding",
    "수영": "swim",
    "다이빙": "diving",
    "스쿠버": "scuba",
    "방수": "waterproof",
    "발수": "water-repellent",
    "방풍": "windproof",
    "투습": "breathable",
    "통기": "breathable",
    "흡한속건": "moisture-wicking",
    "속건": "quick-dry",
    "냉감": "cooling",
    "쿨링": "cooling",
    "발열": "heated",
    "기모": "fleece-lined",
    "방염": "flame-resistant",
    "난연": "flame-resistant",
    "전열": "heated",
    "방진": "dust-resistant",
    "제전": "anti-static",
    "반사": "reflective",
    "리플렉티브": "reflective",
    "자외선차단": "UV-protective",
    "방충": "insect-repellent",
    "스트레치": "stretch",
    "스판": "stretch",
    "경량": "lightweight",
    "초경량": "ultralight",
    "방오": "stain-resistant",
    "택티컬": "tactical",
    "정비": "mechanic",
    "용접": "welding",
    "경비": "security",
    "경호": "security",
    "소방": "firefighter",
    "경찰": "police",
    "군용": "military",
    "밀리터리": "military",
    "건설": "construction",
    "배달": "delivery",
    "라이더": "rider",
    "목수": "carpenter",
    "농업": "farming",
    "원예": "gardening",
    "조리": "kitchen",
    "의료": "medical",
    "간호": "nursing",
    "수술": "surgical",
    "방역": "protective",
    "롱": "long",
    "숏": "short",
    "미니": "mini",
    "와이드": "wide-leg",
}

# Product-form suffixes — the generalization surface for apparel vocabulary.
# New garments work when they end with one of these (optional modifier stem in front).
_FORM_SUFFIXES: tuple[tuple[str, str, str], ...] = (
    # (ko_suffix, en_label, family) — longest first matters for matching
    ("작업화", "work boots", "footwear"),
    ("안전화", "safety boots", "footwear"),
    ("등산화", "hiking boots", "footwear"),
    ("방한화", "winter boots", "footwear"),
    ("현장화", "work boots", "footwear"),
    ("워크부츠", "work boots", "footwear"),
    ("스니커즈", "sneakers", "footwear"),
    ("운동화", "sneakers", "footwear"),
    ("단화", "loafers", "footwear"),
    ("로퍼", "loafers", "footwear"),
    ("구두", "dress shoes", "footwear"),
    ("샌들", "sandals", "footwear"),
    ("슬리퍼", "slippers", "footwear"),
    ("쪼리", "flip-flops", "footwear"),
    ("플립플랍", "flip-flops", "footwear"),
    ("뮬", "mules", "footwear"),
    ("블로퍼", "backless loafers", "footwear"),
    ("장화", "rain boots", "footwear"),
    ("레인부츠", "rain boots", "footwear"),
    ("트레킹화", "trekking shoes", "footwear"),
    ("런닝화", "running shoes", "footwear"),
    ("러닝화", "running shoes", "footwear"),
    ("축구화", "soccer cleats", "footwear"),
    ("풋살화", "futsal shoes", "footwear"),
    ("족구화", "jokgu shoes", "footwear"),
    ("볼링화", "bowling shoes", "footwear"),
    ("골프화", "golf shoes", "footwear"),
    ("테니스화", "tennis shoes", "footwear"),
    ("전술화", "tactical boots", "footwear"),
    ("군화", "combat boots", "footwear"),
    ("원피스", "dress", "dresses"),
    ("드레스", "dress", "dresses"),
    ("점프수트", "jumpsuit", "dresses"),
    ("점프슈트", "jumpsuit", "dresses"),
    ("뷔스티에", "bustier", "dresses"),
    ("레깅스", "leggings", "bottoms"),
    ("타이즈", "tights", "bottoms"),
    ("타이츠", "tights", "bottoms"),
    ("스커트", "skirt", "bottoms"),
    ("치마", "skirt", "bottoms"),
    ("슬랙스", "slacks", "bottoms"),
    ("조거", "joggers", "bottoms"),
    ("쇼츠", "shorts", "bottoms"),
    ("바지", "pants", "bottoms"),
    ("팬츠", "pants", "bottoms"),
    ("청바지", "jeans", "bottoms"),
    ("데님팬츠", "denim pants", "bottoms"),
    ("반바지", "shorts", "bottoms"),
    ("치마바지", "skort", "bottoms"),
    ("스코트", "skort", "bottoms"),
    ("멜빵바지", "overalls", "bottoms"),
    ("오버롤", "overalls", "bottoms"),
    ("오버롤즈", "overalls", "bottoms"),
    ("티셔츠", "t-shirt", "tops"),
    ("블라우스", "blouse", "tops"),
    ("가디건", "cardigan", "tops"),
    ("스웨터", "sweater", "tops"),
    ("후디", "hoodie", "tops"),
    ("후드", "hoodie", "tops"),
    ("셔츠", "shirt", "tops"),
    ("폴로", "polo", "tops"),
    ("니트", "knit", "tops"),
    ("재킷", "jacket", "tops"),
    ("자켓", "jacket", "tops"),
    ("점퍼", "jumper", "tops"),
    ("코트", "coat", "tops"),
    ("조끼", "vest", "tops"),
    ("베스트", "vest", "tops"),
    ("맨투맨", "sweatshirt", "tops"),
    ("스웨트셔츠", "sweatshirt", "tops"),
    ("짚업", "zip-up", "tops"),
    ("집업", "zip-up", "tops"),
    ("아노락", "anorak", "tops"),
    ("윈드브레이커", "windbreaker", "tops"),
    ("바람막이", "windbreaker", "tops"),
    ("패딩", "padded jacket", "tops"),
    ("다운", "down jacket", "tops"),
    ("야상", "field jacket", "tops"),
    ("집업후드", "zip-up hoodie", "tops"),
    ("후드집업", "zip-up hoodie", "tops"),
    ("튜닉", "tunic", "tops"),
    ("나시", "sleeveless top", "tops"),
    ("민소매", "sleeveless top", "tops"),
    ("민소매티", "sleeveless t-shirt", "tops"),
    ("슬리브리스", "sleeveless top", "tops"),
    ("탱크탑", "tank top", "tops"),
    ("장갑", "gloves", "handwear"),
    ("손장갑", "gloves", "handwear"),
    ("손가락장갑", "finger gloves", "handwear"),
    ("벙어리장갑", "mittens", "handwear"),
    ("손목보호대", "wrist guard", "handwear"),
    ("모자", "hat", "headwear"),
    ("헬멧", "helmet", "headwear"),
    ("비니", "beanie", "headwear"),
    ("캡", "cap", "headwear"),
    ("볼캡", "baseball cap", "headwear"),
    ("벙거지", "bucket hat", "headwear"),
    ("버킷햇", "bucket hat", "headwear"),
    ("선캡", "sun visor", "headwear"),
    ("썬캡", "sun visor", "headwear"),
    ("바이저", "visor", "headwear"),
    ("군모", "patrol cap", "headwear"),
    ("양말", "socks", "other"),
    ("벨트", "belt", "other"),
    ("가방", "bag", "other"),
    ("백팩", "backpack", "other"),
    ("넥워머", "neck warmer", "other"),
    ("목토시", "neck gaiter", "other"),
    ("팔토시", "arm sleeves", "other"),
    ("쿨토시", "cooling arm sleeves", "other"),
    ("발토시", "leg warmers", "other"),
    ("레그워머", "leg warmers", "other"),
    ("머플러", "muffler", "other"),
    ("스카프", "scarf", "other"),
    ("크로스백", "crossbody bag", "other"),
    ("숄더백", "shoulder bag", "other"),
    ("토트백", "tote bag", "other"),
    ("메신저백", "messenger bag", "other"),
    ("웨이스트백", "waist bag", "other"),
    ("힙색", "fanny pack", "other"),
    ("보스턴백", "boston bag", "other"),
    ("파우치", "pouch", "other"),
    ("부츠", "boots", "footwear"),
    ("신발", "shoes", "footwear"),
    # Swim / dive (must beat last-resort season tokens like "ss시즌에")
    ("드라이수트", "drysuit", "swim_dive"),
    ("드라이슈트", "drysuit", "swim_dive"),
    ("웨트수트", "wetsuit", "swim_dive"),
    ("웨트슈트", "wetsuit", "swim_dive"),
    ("다이빙수트", "diving suit", "swim_dive"),
    ("다이빙슈트", "diving suit", "swim_dive"),
    ("다이빙복", "diving suit", "swim_dive"),
    ("잠수복", "wetsuit", "swim_dive"),
    ("수영복", "swimwear", "swim_dive"),
    ("비키니", "bikini", "swim_dive"),
    ("래시가드", "rash guard", "swim_dive"),
    ("보드숏", "board shorts", "swim_dive"),
    ("보드쇼츠", "board shorts", "swim_dive"),
)

_FORM_SUFFIX_EN = {ko: en for ko, en, _fam in _FORM_SUFFIXES}
_FORM_SUFFIX_FAMILY = {ko: fam for ko, _en, fam in _FORM_SUFFIXES}

# Standalone forms (no modifier required): 스커트, 치마, 레깅스, 원피스…
_STANDALONE_FORMS = frozenset(ko for ko, _en, _fam in _FORM_SUFFIXES if len(ko) >= 2)

_KO_SUFFIX_ALT = "|".join(
    re.escape(ko)
    for ko, _en, _fam in sorted(_FORM_SUFFIXES, key=lambda x: len(x[0]), reverse=True)
)
# Compact compound: 테니스치마 / 골프바지 / 방한장갑
_KO_PRODUCT_RE = re.compile(rf"([가-힣A-Za-z0-9]{{0,12}}(?:{_KO_SUFFIX_ALT}))")
# Spaced compound: 골프 스커트 / 테니스 치마 / 요가 레깅스
_KO_SPACED_PRODUCT_RE = re.compile(rf"([가-힣A-Za-z0-9]{{1,12}})\s+({_KO_SUFFIX_ALT})")
_EN_PRODUCT_RE = re.compile(
    r"\b((?:ski|snowboard|tactical|cargo|work|hiking|winter|safety|rain|golf|tennis|yoga|"
    r"running|cycling|softshell|hard\s*shell)\s+"
    r"(?:pants?|trousers|bibs?|boots?|shoes?|gloves?|jackets?|parkas?|shells?|skirts?|dresses?|"
    r"leggings?|shorts?|polos?)|"
    r"(?:diving\s+suits?|dive\s+suits?|wet\s*suits?|wetsuits?|dry\s*suits?|drysuits?|"
    r"swim\s*wear|swimsuits?|rash\s*guards?|board\s*shorts?)|"
    r"(?:boots?|shoes?|gloves?|jackets?|parkas?|helmets?|beanies?|skirts?|dresses?|leggings?|"
    r"shorts?|slacks?|joggers?))\b",
    re.IGNORECASE,
)
_STOP_BRIEF = {
    "위한",
    "위한,",
    "맞는",
    "대해",
    "대한",
    "관련",
    "시장조사",
    "현장조사",
    "심층리서치",
    "딥리서치",
    "컨셉",
    "구성을",
    "구성",
    "실시",
    "착용",
    "환경에",
    "환경",
    "시즌",
    "시즌에",
    "ss시즌",
    "fw시즌",
    "ss시즌에",
    "fw시즌에",
    "s/s",
    "f/w",
    "여성용",
    "남성용",
    "남녀",
    "market",
    "research",
    "concept",
    # Discourse / polite leftovers — never product locks
    "방금",
    "아까",
    "이전",
    "다시",
    "요약",
    "공백",
    "개만",
    "해줘",
    "해주세요",
    "주세요",
    "부탁",
    "에서",
    "위",
    "해당",
    "코드",
    "수정",
    "금지",
    "edit_file",
    "edit_file로",
    "apply_patch",
    "write_file",
    "시장조사에서",
    "경쟁",
    "3개만",
    "개만",
    # Never accept these broad/style/material words as the product itself.
    "화",
    "복",
    "용",
    "모",
    "의",
    "착",
    "관",
    "백",
    "핏",
    "라인",
    "셋",
    "세트",
    "스타일",
    "타입",
    "룩",
    "컷",
    "패션",
    "디자인",
    "컬렉션",
    "패턴",
    "웨어",
    "복장",
    "의류",
    "의복",
    "용품",
    "기어",
    "잡화",
    "장비",
    "아이템",
    "악세서리",
    "액세서리",
    "면",
    "나일론",
    "폴리",
    "린넨",
    "울",
    "캐시미어",
    "가죽",
    "레더",
    "고어텍스",
    "캔버스",
    "메시",
    "메쉬",
    "공용",
    "남성",
    "여성",
    "키즈",
    "주니어",
    "아동",
    "빅사이즈",
    "오버핏",
    "프리",
    "슬림",
    "타이트",
}


class PainExtraction(BaseModel):
    consumer_pain_points: list[str] = Field(
        min_length=3,
        description="Verbatim-style pain themes from reviews/articles",
    )
    pain_theme_frequencies: dict[str, float] = Field(
        description="Theme -> estimated share 0-1, must sum to ~1.0",
    )
    qual_themes: list[str] = Field(default_factory=list)
    review_rating_notes: str | None = None


def _normalize_plain_bullets(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in items:
        text = re.sub(r"^[\s\-•*]+", "", str(raw or "")).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _detect_product_family(label: str) -> str:
    t = label.lower()
    # Exact suffix family first (치마/스커트/원피스 before vague token checks).
    for ko, _en, fam in sorted(_FORM_SUFFIXES, key=lambda x: len(x[0]), reverse=True):
        if ko in t:
            return fam
    if any(
        k in t
        for k in (
            "boot",
            "shoe",
            "footwear",
            "부츠",
            "신발",
            "작업화",
            "안전화",
            "등산화",
            "방한화",
            "현장화",
        )
    ):
        return "footwear"
    if any(k in t for k in ("glove", "mitten", "장갑")):
        return "handwear"
    if any(
        k in t
        for k in (
            "wetsuit",
            "drysuit",
            "diving suit",
            "dive suit",
            "swimwear",
            "swimsuit",
            "rash guard",
            "board short",
            "다이빙복",
            "잠수복",
            "웨트수트",
            "웨트슈트",
            "드라이수트",
            "수영복",
            "래시가드",
            "비키니",
            "scuba",
            "diving",
        )
    ):
        return "swim_dive"
    if any(k in t for k in ("hat", "beanie", "helmet", "모자", "헬멧", "비니")):
        return "headwear"
    if any(k in t for k in ("dress", "원피스", "드레스")):
        return "dresses"
    if any(
        k in t
        for k in (
            "jacket",
            "parka",
            "shell",
            "hoodie",
            "shirt",
            "sweater",
            "cardigan",
            "blouse",
            "polo",
            "재킷",
            "자켓",
            "점퍼",
            "코트",
            "조끼",
            "후드",
            "셔츠",
            "니트",
            "스웨터",
            "가디건",
            "블라우스",
            "폴로",
        )
    ):
        return "tops"
    if any(
        k in t
        for k in (
            "pant",
            "trouser",
            "bib",
            "short",
            "skirt",
            "legging",
            "jogger",
            "slack",
            "바지",
            "팬츠",
            "쇼츠",
            "치마",
            "스커트",
            "레깅스",
            "조거",
            "슬랙스",
        )
    ):
        return "bottoms"
    return "other"


def _gloss_en(phrase: str) -> str:
    p = phrase.strip()
    if p in _PRODUCT_GLOSS:
        return _PRODUCT_GLOSS[p]
    low = p.lower()
    for ko, en in sorted(_PRODUCT_GLOSS.items(), key=lambda x: len(x[0]), reverse=True):
        if ko in p or ko.lower() in low:
            return en

    # Spaced "골프 스커트" already joined elsewhere; handle compound suffix+stem.
    for ko, en, _fam in sorted(_FORM_SUFFIXES, key=lambda x: len(x[0]), reverse=True):
        if p == ko or p.endswith(ko):
            stem = p[: -len(ko)].strip() if p != ko else ""
            if not stem:
                return en
            stem_en = _STEM_EN.get(stem, stem)
            # Prefer English search label when stem is mapped; else keep KO compound.
            if stem in _STEM_EN:
                return f"{stem_en} {en}"
            if re.search(r"[A-Za-z]", stem):
                return f"{stem} {en}"
            return p  # keep Korean compound for search
    if re.search(r"[A-Za-z]", p):
        return p
    return p


def _is_noise_product_token(token: str) -> bool:
    """Reject season/meta tokens so last-resort lock never becomes 'ss시즌에'."""
    t = token.strip().strip(".,!?;:\"'()[]")
    if not t or len(t) < 2:
        return True
    low = t.lower()
    if low in _STOP_BRIEF or t in _STOP_BRIEF:
        return True
    if re.fullmatch(r"20\d{2}", t):
        return True
    if re.fullmatch(r"(?:ss|fw|s/?s|f/?w)(?:시즌)?(?:에)?", low):
        return True
    if "시즌" in t:
        return True
    if re.fullmatch(r"[\W_]+", t):
        return True
    return False


def _strip_brief_discourse_noise(text: str) -> str:
    """Remove polite imperatives / tool disclaimers before product lock extraction."""
    t = text
    t = re.sub(r"edit_file[^\s]*", " ", t, flags=re.I)
    t = re.sub(r"(?:apply_patch|write_file)[^\s]*", " ", t, flags=re.I)
    t = re.sub(r"코드\s*수정\s*금지[^\n]*", " ", t)
    t = re.sub(r"파일\s*수정\s*금지[^\n]*", " ", t)
    t = re.sub(
        r"(?:시장조사|심층리서치|딥리서치|현장조사)(?:에서|의|를|을|에)?", " ", t
    )
    t = re.sub(r"(해줘|해주세요|주세요|부탁합니다?)\s*[.!]?", " ", t)
    t = re.sub(r"\b(?:방금|아까|이전|다시|요약|공백|개만|경쟁)\b", " ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def _extract_product_phrase(text: str) -> tuple[str, str]:
    """Return (brief_lock_phrase, search_label) from free-form brief text."""
    text = _strip_brief_discourse_noise(text)
    # Prefer exact gloss hits (longest first) so 스키바지 beats bare 바지.
    for ko in sorted(_PRODUCT_GLOSS, key=len, reverse=True):
        if ko in text:
            return ko, _PRODUCT_GLOSS[ko]

    en = _EN_PRODUCT_RE.search(text)
    if en:
        phrase = re.sub(r"\s+", " ", en.group(1)).strip().lower()
        return phrase, phrase

    # Spaced compound before compact: "골프 스커트" must not fall to bare "골프".
    spaced = _KO_SPACED_PRODUCT_RE.search(text)
    if spaced:
        stem, form = spaced.group(1).strip(), spaced.group(2).strip()
        if stem.lower() not in _STOP_BRIEF and form in _STANDALONE_FORMS:
            spaced_phrase = f"{stem} {form}"
            compact = f"{stem}{form}"
            if spaced_phrase in _PRODUCT_GLOSS:
                return spaced_phrase, _PRODUCT_GLOSS[spaced_phrase]
            if compact in _PRODUCT_GLOSS:
                return compact, _PRODUCT_GLOSS[compact]
            return spaced_phrase, _gloss_en(compact)

    # Compact compound. Reject matches where the suffix is buried inside a
    # larger Hangul word (모자이크→모자, 니트로→니트, 다운로드→다운): if the
    # char right after the match is another Hangul syllable, it is not a
    # product boundary.
    for ko in _KO_PRODUCT_RE.finditer(text):
        phrase = ko.group(1).strip()
        if not phrase or phrase in _STOP_BRIEF:
            continue
        tail = text[ko.end() : ko.end() + 1]
        if tail and "\uac00" <= tail <= "\ud7a3":
            continue
        return phrase, _gloss_en(phrase)

    # Standalone form token (스커트 / 레깅스 / 원피스) anywhere in brief.
    for tok in re.split(r"[\s,./|]+", text):
        t = tok.strip().strip(".,!?;:\"'()[]")
        if t in _STANDALONE_FORMS:
            return t, _gloss_en(t)

    # Last resort: only product-shaped tokens (form suffix / latin), never verbs.
    for tok in re.split(r"[\s,./|]+", text):
        t = tok.strip().strip(".,!?;:\"'()[]")
        if _is_noise_product_token(t):
            continue
        if t.lower() in ("fw", "ss", "f/w", "s/s"):
            continue
        if any(t.endswith(ko) for ko, _en, _fam in _FORM_SUFFIXES):
            return t, _gloss_en(t)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9][A-Za-z0-9\s\-]{1,40}", t):
            return t.lower(), t.lower()
        continue

    return "product", "product"


def _product_lock_tokens(brief_phrase: str, search_label: str) -> list[str]:
    tokens: list[str] = []
    for raw in (brief_phrase, search_label):
        for part in re.split(r"[\s/_-]+", raw):
            p = part.strip().lower()
            if len(p) >= 2 and p not in tokens and p not in _STOP_BRIEF:
                tokens.append(p)
    return tokens[:8]


def _detect_season(text: str) -> str:
    t = text.lower()
    year = ""
    ym = re.search(r"(20\d{2})", text)
    if ym:
        year = ym.group(1)

    fw = any(
        k in t
        for k in (
            "fw",
            "f/w",
            "fall-winter",
            "fall winter",
            "autumn",
            "winter",
            "가을",
            "겨울",
            "스키시즌",
            "ski season",
        )
    )
    ss = any(
        k in t
        for k in (
            "ss",
            "s/s",
            "spring-summer",
            "spring summer",
            "summer",
            "봄",
            "여름",
            "hot weather",
            "lightweight summer",
        )
    )

    if fw and not ss:
        season = "fall-winter"
    elif ss and not fw:
        season = "spring-summer"
    elif any(k in t for k in ("summer", "hot", "humid")):
        season = "summer"
    elif any(k in t for k in ("winter", "cold", "snow")):
        season = "winter"
    else:
        season = "all-season"

    return f"{year} {season}".strip() if year else season


def _detect_conditions(text: str) -> str:
    t = text.lower()
    found = []
    if any(
        k in t
        for k in (
            "습한",
            "습기",
            "젖은",
            "wet",
            "humid",
            "rain",
            "slush",
            "진흙",
            "mud",
        )
    ):
        found.append("wet")
    if any(
        k in t
        for k in ("추운", "혹한", "영하", "cold", "freezing", "subzero", "눈", "snow")
    ):
        found.append("cold")
    if any(
        k in t
        for k in ("공사장", "현장", "jobsite", "construction", "산업", "industrial")
    ):
        found.append("jobsite")
    return "+".join(found) or "unspecified"


def _parse_brief_hints(user_brief: str, target_category: str | None) -> dict[str, str]:
    """Extract product/season/TPO from free-form brief — no closed category registry."""
    text = f"{user_brief} {target_category or ''}".strip()
    source = (target_category or "").strip() or text
    brief_phrase, search_label = _extract_product_phrase(source)
    # If CLI category is set, prefer it for the lock phrase.
    if target_category and target_category.strip():
        brief_phrase, search_label = _extract_product_phrase(target_category)

    family = _detect_product_family(f"{brief_phrase} {search_label}")
    line_hit = next((name for name in LINE_HINTS if name.lower() in text.lower()), None)
    season = _detect_season(text)
    conditions = _detect_conditions(text)
    price_band = FAMILY_PRICE_BAND.get(family, FAMILY_PRICE_BAND["other"])
    seeds = FAMILY_COMPETITOR_SEEDS.get(family, FAMILY_COMPETITOR_SEEDS["other"])

    channel = "Amazon US"
    if any(k in text.lower() for k in ("rei", "backcountry", "evo", "dick's")):
        channel = "US outdoor retail + Amazon"
    if family == "footwear" and "jobsite" in conditions:
        channel = "Amazon US + US work/safety retail"

    return {
        "line": line_hit or "unspecified",
        "garment": search_label,
        "product_brief": brief_phrase,
        "product_family": family,
        # Keep category_key as family for backward-compatible callers/tests.
        "category_key": family,
        "season": season,
        "conditions": conditions,
        "price_band": price_band,
        "channel": channel,
        "competitors": ", ".join(seeds[:6]),
        "lock_tokens": "|".join(_product_lock_tokens(brief_phrase, search_label)),
    }


def _amazon_and_review_queries(hints: dict[str, str]) -> list[str]:
    """Product-locked generic queries — works for any extracted garment, not a registry."""
    g = hints["garment"]
    brief_g = hints.get("product_brief") or g
    season = hints["season"]
    conditions = hints.get("conditions") or "unspecified"
    brands = [b.strip() for b in hints["competitors"].split(",") if b.strip()]
    b0, b1 = (brands + ["Columbia", "Patagonia"])[:2]
    cond_q = conditions.replace("+", " ") if conditions != "unspecified" else ""

    queries = [
        f"{g} amazon 1 star 2 star review complaints",
        (
            f"{brief_g} 리뷰 불만 단점"
            if brief_g != g
            else f"{g} review sizing durability"
        ),
        f"{b0} {g} review complaints",
        f"{b1} {g} review fit durability price",
        f"reddit {g} {season} {cond_q} complaints pain points".strip(),
        f"site:amazon.com {g} bad reviews",
        f"best {g} {season} review comparison price",
        f"{g} {season} {cond_q} market gap white space".strip(),
    ]
    if "wet" in conditions or "cold" in conditions:
        queries.append(f"{g} waterproof insulated {cond_q} review".strip())
    if hints.get("product_family") == "footwear":
        queries.append(f"{g} slip resistance break-in width fatigue review")
    return queries


def _competitor_and_trend_queries(hints: dict[str, str], user_brief: str) -> list[str]:
    g = hints["garment"]
    season = hints["season"]
    brands = [b.strip() for b in hints["competitors"].split(",") if b.strip()]
    b0 = brands[0] if brands else "competitor"
    line_q = (
        f"{hints['line']} {g} competitor price {hints['price_band']} {hints['channel']}"
        if hints["line"] != "unspecified"
        else f"{g} competitor price {hints['price_band']} {hints['channel']} {season}"
    )
    return [
        line_q,
        f"{b0} {g} comparison review pain points {season}",
        f"{g} {season} trend white space market gap",
        f"{user_brief[:100]} market gap white space",
    ]


def _build_search_queries(user_brief: str, hints: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    # Always lead with the raw brief so search tracks user intent.
    seed = user_brief.strip()[:120]
    if seed:
        ordered.append(seed)
        seen.add(seed.lower())
    for q in _amazon_and_review_queries(hints) + _competitor_and_trend_queries(
        hints, user_brief
    ):
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            ordered.append(q)
    return ordered


def _run_search_loop(
    queries: list[str],
    search_tool: BaseTool | None,
    *,
    max_calls: int,
) -> list[dict[str, Any]]:
    if not search_tool:
        return []

    snippets: list[dict[str, Any]] = []
    for query in queries[:max_calls]:
        try:
            raw = search_tool.invoke({"query": query})
        except TypeError:
            raw = search_tool.invoke(query)
        except Exception as exc:
            logger.warning("search failed for %r: %s", query, exc)
            continue

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            item.setdefault("_query", query)
                    snippets.extend(parsed)
                    continue
            except json.JSONDecodeError:
                snippets.append(
                    {"title": query, "snippet": raw, "link": "", "_query": query}
                )
                continue
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    item.setdefault("_query", query)
            snippets.extend(raw)
        elif isinstance(raw, dict):
            raw.setdefault("_query", query)
            snippets.append(raw)
    return snippets


def _snippets_to_sources(
    snippets: list[dict[str, Any]], hints: dict[str, str]
) -> list[SourceRef]:
    lock_tokens = [t for t in (hints.get("lock_tokens") or "").split("|") if t]
    if not lock_tokens:
        lock_tokens = _product_lock_tokens(
            hints.get("product_brief") or "", hints.get("garment") or ""
        )
    garment = (hints.get("garment") or "").lower()
    brief_g = (hints.get("product_brief") or "").lower()
    family = hints.get("product_family") or "other"

    # Tokens that count as on-topic for this brief (product + family cues).
    topical: list[str] = [t.lower() for t in lock_tokens if len(t) >= 2]
    for extra in (garment, brief_g):
        if extra and extra not in topical:
            topical.append(extra)
    for part in re.split(r"[\s/_-]+", f"{garment} {brief_g}"):
        p = part.strip().lower()
        if len(p) >= 3 and p not in topical:
            topical.append(p)
    family_cues: dict[str, tuple[str, ...]] = {
        "swim_dive": (
            "wetsuit",
            "drysuit",
            "dive",
            "diving",
            "scuba",
            "swim",
            "neoprene",
            "다이빙",
            "잠수",
            "수트",
            "수영",
            "슈트",
        ),
        "footwear": ("boot", "shoe", "footwear", "outsole", "부츠", "신발", "작업화"),
        "bottoms": ("pant", "skirt", "legging", "바지", "치마", "스커트"),
        "handwear": ("glove", "mitten", "장갑"),
        "tops": ("jacket", "hoodie", "parka", "재킷", "패딩"),
    }
    topical.extend(family_cues.get(family, ()))

    hard_neg = (
        "plumber",
        "mistfall hunter",
        "elon musk",
        "fake review",
        "1-star rating with no review",
        "trump",
        "matchmaking not working",
        "wateralchemyplumbing",
    )

    scored: list[tuple[int, SourceRef]] = []
    seen_urls: set[str] = set()
    for item in snippets:
        url = str(item.get("link") or item.get("url") or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(item.get("title") or "")[:200]
        snippet = str(
            item.get("snippet") or item.get("body") or item.get("content") or ""
        )[:400]
        blob = f"{title} {snippet} {url}".lower()
        score = 0
        for tok in topical:
            if tok and tok in blob:
                score += 2 if tok in {brief_g, garment} or tok in lock_tokens else 1
        if any(n in blob for n in hard_neg):
            score -= 8
        if any(
            k in url.lower()
            for k in ("amazon.", "rei.com", "backcountry", "reddit.com")
        ):
            score += 1

        if score <= 0:
            continue

        lower = url.lower()
        if "amazon" in lower or "review" in lower:
            stype = "review_aggregate"
        elif "reddit" in lower or "forum" in lower:
            stype = "forum"
        else:
            stype = "other"
        scored.append(
            (
                score,
                SourceRef(
                    url=url,
                    title=title or None,
                    source_type=stype,
                ),
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:12]]


def _dry_run_report(
    user_brief: str,
    target_category: str | None,
    *,
    fallback_note: str | None = None,
) -> ResearchReport:
    hints = _parse_brief_hints(user_brief, target_category)
    line = hints["line"]
    garment = hints["garment"]
    brief_g = hints.get("product_brief") or garment
    season = hints["season"]
    conditions = hints.get("conditions") or "unspecified"
    family = hints.get("product_family") or hints.get("category_key") or "other"
    cond_note = f", 조건={conditions}" if conditions != "unspecified" else ""

    # Prefer Hangul product brief for narrative (다이빙복), keep EN garment for locks.
    if re.search(r"[\uac00-\ud7a3]", brief_g or ""):
        display_g = brief_g
    elif brief_g == garment:
        display_g = garment
    else:
        display_g = f"{brief_g} ({garment})" if brief_g else garment
    concept_name = f"{display_g} 컨셉 ({season})"

    gaps = [
        f"{hints['price_band']} {display_g} 구간에서 {season}{cond_note} TPO 수요가 충족되지 않음",
        f"경쟁사 스펙이 유사해 차별화된 {display_g} 형제 SKU가 과소 편성됨",
        f"목표 가격대에서 핏·내구성·사용 조건 서술이 명확한 {display_g} 화이트 스페이스 존재",
    ]
    competitors_seed = [
        f"카테고리 주요 경쟁사(시드): {hints['competitors']}",
        f"{hints['channel']} 기준 가격 집중 구간 {hints['price_band']}",
    ]
    pains = [
        f"{display_g}의 핏·사이즈 편차",
        "고마모 부위 내구성 불만",
        "편안함 대비 기능 과잉(부피) 트레이드오프",
        f"{season} 사용 시 날씨 보호력과 통기성의 불일치",
        "가격 대비 성능 불만",
    ]
    freqs = {
        "fit": 0.28,
        "durability": 0.24,
        "comfort": 0.2,
        "weather": 0.16,
        "price": 0.12,
    }
    themes = [
        f"구매자는 브랜드 충성보다 {display_g}의 시즌·용도 적합성으로 판단함",
        "기후·TPO를 무시한 기능 구성은 신뢰를 빠르게 잃음",
    ]
    if family == "swim_dive":
        pains = [
            f"{display_g}: 수온·두께(mm) 미스매치로 한기 또는 과열",
            "네오프렌 품질·솔기 내구성 및 지퍼 고장",
            "어깨·겨드랑이 가동 범위 제한",
            "사이즈 표기 브랜드 간 편차",
            "입문·렌탈 대비 구매 가성비 판단 어려움",
        ]
        freqs = {
            "thermal_fit": 0.26,
            "durability_seams": 0.22,
            "mobility": 0.2,
            "sizing": 0.18,
            "price_value": 0.14,
        }
        themes = [
            f"구매자는 {display_g}를 패션·아웃도어 재킷과 같은 카테고리로 보지 않음 — 수온·잠수/입수 TPO가 우선",
            "두께·솔기·지퍼가 후기 페인의 핵심이며 일반 의류 브랜드 벤치마크는 부적절",
        ]
        job_mobility = "수온 변화에 맞게 보온과 움직임을 유지하고 싶다"
    else:
        job_mobility = "날씨 변화에도 활동을 중단하지 않고 편안하게 움직이고 싶다"
    if family == "footwear":
        pains = [
            f"{garment}: 습한 환경에서 방수 성능이 한 시즌을 못 버티는 봉합·굴곡부 누수",
            "보온과 땀 배출의 트레이드오프",
            "젖은 노면 미끄러짐",
            "종일 착용 시 발 피로",
            "발볼·사이즈 편차",
        ]
        freqs = {
            "waterproof_durability": 0.26,
            "warmth_vs_sweat": 0.22,
            "slip_resistance": 0.2,
            "fit_width_sizing": 0.16,
            "weight_fatigue": 0.16,
        }
    concepts = [
        ConceptCandidate(
            concept_id="A",
            name=concept_name,
            line_recommendation=None if line == "unspecified" else line,
            garment_type=garment,
            target_tpo=f"{season}{cond_note} 주 사용 상황",
            usp_hypothesis=f"{hints['price_band']} 가격대에서 상위 페인을 해소하는 {display_g}",
            keywords=[garment, brief_g, season, "gap", "pain"],
            evidence_refs=["gap-1"],
        ),
        ConceptCandidate(
            concept_id="B",
            name=f"{display_g} 대체 TPO",
            line_recommendation=None if line == "unspecified" else line,
            garment_type=garment,
            target_tpo=f"{season} 보조 사용 상황",
            usp_hypothesis="기능을 덜어낸 구성과 명확한 시즌·조건 포지셔닝",
            keywords=[garment, season, "seasonal"],
            evidence_refs=["gap-2"],
        ),
        ConceptCandidate(
            concept_id="C",
            name=f"가성비 {display_g}",
            line_recommendation=None if line == "unspecified" else line,
            garment_type=garment,
            target_tpo=f"{season} 입문·중급",
            usp_hypothesis=f"핵심 페인만 남긴 엔트리 {hints['price_band']} 구성",
            keywords=[garment, season, "value"],
            evidence_refs=["gap-1", "gap-3"],
        ),
    ]

    personas = [
        PersonaProfile(
            persona_id="P1",
            name="기능 우선 주사용자",
            segment="성능·신뢰성 우선",
            context=f"{season} {display_g} 주기 사용자",
            job_to_be_done=job_mobility,
            pains=pains[:3],
            gains=(
                ["보호력과 통기성의 균형", "일관된 핏과 내구성"]
                if family != "swim_dive"
                else ["수온 적중 두께", "솔기·지퍼 내구성", "가동 범위"]
            ),
            buying_triggers=["기존 제품 마모", "시즌 시작", "기능 업그레이드"],
            unexpected_insight="기능 수보다 상황에 맞는 조절성과 실패 없는 핵심 사양을 우선한다",
            evidence_refs=["pain-1", "gap-1"],
        ),
        PersonaProfile(
            persona_id="P2",
            name="가치 검증형 입문자",
            segment="가격·후기 검증 우선",
            context=f"{season} {display_g} 입문·간헐 구매 사용자",
            job_to_be_done="과투자 없이 필수 기능을 갖춘 실패 없는 첫 제품을 사고 싶다",
            pains=[pains[-1], pains[0]],
            gains=["명확한 성능 수치", "쉬운 사이즈 선택", "가격 대비 핵심 기능"],
            buying_triggers=["첫 여행·활동 예약", "프로모션", "후기 비교 완료"],
            unexpected_insight="최저가보다 반품 위험과 기능 누락을 줄이는 설명을 가치로 본다",
            evidence_refs=["gap-1", "pain-price"],
        ),
    ]
    market_segments = [
        MarketSegmentProfile(
            segment_id="S1",
            name="성능 중심 반복 사용자",
            size_signal="검증 필요",
            defining_need="날씨 보호·활동성·내구성의 균형",
            behavior_and_tpo=f"{season} 고빈도 핵심 TPO",
            willingness_to_pay=hints["price_band"],
            competitive_intensity="high",
            priority="invest",
            rationale="페인 강도와 반복 사용 빈도가 높아 차별화 가치가 큼",
            evidence_refs=["gap-1", "pain-1"],
        ),
        MarketSegmentProfile(
            segment_id="S2",
            name="가격 민감 입문 사용자",
            size_signal="검증 필요",
            defining_need="필수 기능과 쉬운 구매 판단",
            behavior_and_tpo=f"{season} 저빈도·입문 TPO",
            willingness_to_pay=hints["price_band"],
            competitive_intensity="high",
            priority="validate",
            rationale="볼륨 가능성은 있으나 가격 탄력성과 반품률 검증이 필요",
            evidence_refs=["gap-1", "pain-price"],
        ),
        MarketSegmentProfile(
            segment_id="S3",
            name="핏 미충족 사용자",
            size_signal="검증 필요",
            defining_need="인심·라이즈·사이즈 선택지 개선",
            behavior_and_tpo=f"{season} 표준 핏이 맞지 않는 사용자",
            willingness_to_pay=None,
            competitive_intensity="medium",
            priority="validate",
            rationale="명확한 공백이 있으나 수요 규모와 SKU 복잡도 검증이 선행돼야 함",
            evidence_refs=["gap-3", "pain-fit"],
        ),
    ]
    competitor_names = [
        x.strip() for x in hints["competitors"].split(",") if x.strip()
    ][:3]
    battlecards = [
        CompetitiveBattlecard(
            competitor=name,
            target_customer=f"{display_g} 구매자",
            strengths=(
                ["카테고리 브랜드 인지 또는 구색"]
                if family != "swim_dive"
                else ["다이빙/수영 장비 전문 구색"]
            ),
            weaknesses=["실제 웹 근거로 확인 필요"],
            our_advantages=["핵심 페인에 집중한 TPO 명확성"],
            objection=f"왜 {name} 대신 신규 제안을 선택해야 하는가?",
            response="가격·핵심 사양·핏의 비교 근거를 확보한 뒤 답변",
            avoid_claims=["근거 없는 성능 우위", "근거 없는 가격 우위"],
            source_urls=[],
        )
        for name in competitor_names
    ]
    job_stories = [
        JobStory(
            when=f"{season} 활동 중 날씨와 체온이 변할 때",
            want="보호력과 통풍을 즉시 조절하고 싶다",
            so_that="활동을 멈추거나 옷을 갈아입지 않고 편안함을 유지할 수 있다",
            evidence_refs=["pain-weather", "gap-1"],
        ),
        JobStory(
            when=f"{display_g}를 온라인으로 비교할 때",
            want="핏·핵심 사양·한계를 빠르게 확인하고 싶다",
            so_that="반품과 잘못된 구매 위험을 줄일 수 있다",
            evidence_refs=["pain-fit", "pain-price"],
        ),
        JobStory(
            when="고마모 부위가 반복적으로 손상될 때",
            want="필요 부위만 보강된 제품을 선택하고 싶다",
            so_that="불필요한 무게 없이 사용 수명을 늘릴 수 있다",
            evidence_refs=["pain-durability"],
        ),
    ]
    journeys = [
        CustomerJourney(
            persona_id="P1",
            journey_name=f"{season} {display_g} 탐색부터 반복 사용",
            stages=[
                JourneyStage(
                    stage="문제 인식",
                    goal="기존 제품 실패 원인 파악",
                    actions=["마모·불편 확인", "다음 활동 일정 확인"],
                    touchpoints=["기존 제품", "커뮤니티"],
                    pain_points=pains[:2],
                    emotion="불편·경계",
                    opportunities=["페인 기반 진단 가이드"],
                ),
                JourneyStage(
                    stage="비교",
                    goal="후보와 사양 압축",
                    actions=["후기·가격·핏 비교"],
                    touchpoints=["검색", "리뷰", "상세페이지"],
                    pain_points=["성능 주장과 실제 후기 불일치"],
                    emotion="의심",
                    opportunities=["근거가 보이는 비교표", "핏 가이드"],
                ),
                JourneyStage(
                    stage="구매·첫 사용",
                    goal="핏과 핵심 기능 검증",
                    actions=["착용", "현장 테스트"],
                    touchpoints=["배송", "패키지", "제품"],
                    pain_points=["첫 착용 시 조절법 불명확"],
                    emotion="기대·검증",
                    opportunities=["첫 사용 체크리스트"],
                ),
                JourneyStage(
                    stage="반복·추천",
                    goal="신뢰할 수 있는 주력 제품 확정",
                    actions=["장기 사용", "후기 공유"],
                    touchpoints=["리뷰", "재구매"],
                    pain_points=["장기 내구성 불확실"],
                    emotion="신뢰 또는 이탈",
                    opportunities=["마모 보증·관리 안내"],
                ),
            ],
            priority_improvements=[
                "근거 기반 비교표",
                "핏·사이즈 안내",
                "첫 사용 및 관리 가이드",
            ],
        )
    ]

    notes = "드라이런 템플릿 — 실제 웹 근거 종합 결과로 대체 필요"
    if fallback_note:
        notes = f"{fallback_note} — 아래 내용은 카테고리 템플릿이며 실제 근거 종합이 아닙니다."
        themes = [
            f"⚠ {fallback_note} — 템플릿 폴백 결과이므로 확정 조사로 쓰지 마세요.",
            *themes,
        ]
        # Template fallback must NOT look like a finished competitive deck.
        battlecards = []
        journeys = []
        job_stories = job_stories[:2]
        sources_out: list[SourceRef] = []
    else:
        sources_out = [
            SourceRef(
                url="https://example.com/dry-run",
                title="드라이런 종합 (웹·LLM 미사용)",
                source_type="industry_report",
            )
        ]

    return ResearchReport(
        market_gaps=gaps,
        competitor_moves=competitors_seed,
        consumer_pain_points=pains,
        quant_signals=QuantSignals(
            pain_theme_frequencies=freqs,
            price_band_notes=hints["price_band"],
            review_rating_notes=notes,
        ),
        personas=personas,
        market_segments=market_segments,
        pricing_strategy=PricingStrategy(
            value_metric=(
                "수온 적중 보온·가동·솔기 내구성"
                if family == "swim_dive"
                else "핵심 TPO에서 실패 없이 사용할 수 있는 보호·조절 성능"
            ),
            target_price_band=hints["price_band"],
            recommended_price=None,
            competitor_benchmarks=[
                f"{name}: 실제 가격 확인 필요" for name in competitor_names
            ],
            pricing_gap=f"{hints['price_band']} 내 기능·핏 공백",
            rationale="웹 가격·수요 근거가 없으므로 권장 가격은 잠금하지 않음",
            experiment="두 가격점 상세페이지에서 클릭→구매 전환 및 반품 의향 비교",
            assumptions=[hints["channel"], season, "실제 경쟁 가격·마진 확인 필요"],
            confidence="insufficient_evidence",
        ),
        competitive_battlecards=battlecards,
        job_stories=job_stories,
        customer_journeys=journeys,
        qual_themes=themes,
        sources=sources_out,
        concepts=concepts,
    )


def _synthesize_from_snippets(
    user_brief: str,
    target_category: str | None,
    snippets: list[dict[str, Any]],
    settings: Settings,
) -> ResearchReport:
    hints = _parse_brief_hints(user_brief, target_category)
    llm = get_chat_model(settings)
    evidence = json.dumps(snippets[:30], ensure_ascii=False, indent=2)
    user = (
        f"User brief: {user_brief}\n"
        f"Target category: {target_category or 'n/a'}\n"
        f"Parsed hints (LOCK THESE): {json.dumps(hints, ensure_ascii=False)}\n\n"
        f"Web evidence snippets ({len(snippets)} hits):\n{evidence}\n\n"
        "Requirements:\n"
        "- BRIEF FIDELITY: garment_type MUST equal Parsed hints.garment (or product_brief); "
        "season/TPO/conditions/concepts MUST stay on that product — never swap product families\n"
        "- market_gaps: minimum 3 non-empty items\n"
        "- consumer_pain_points: minimum 5 items grounded in snippets (plain text)\n"
        "- quant_signals.pain_theme_frequencies: at least 3 themes with numeric estimates\n"
        "- competitor_moves: brands relevant to the locked product; include price band when visible\n"
        "- personas: 2-3 behavioral/JTBD personas grounded in evidence; no invented demographics\n"
        "- market_segments: 3-5 distinct need/behavior segments with priority and rationale\n"
        "- pricing_strategy: benchmarks, gap, experiment, assumptions, confidence; no unsupported price\n"
        "- competitive_battlecards: up to 3 direct competitors with source URLs and claims to avoid\n"
        "- job_stories: 3-5 evidence-backed When/I want/so that stories\n"
        "- customer_journeys: highest-priority persona, 4-6 stages, 2-3 priority improvements\n"
        "- concepts: 2-3 with garment_type locked to hints.garment, target_tpo, usp_hypothesis filled\n"
        "- Do not invent an unrelated product category (e.g. pants when brief is boots, or boots when brief is gloves)\n"
        f"- Write all narrative text in {'English' if settings.report_language == 'en' else 'Korean'}"
        " (garment_type stays the locked product label from hints)\n"
        "Return ResearchReport JSON."
    )
    report = invoke_structured(
        llm,
        with_language(DEEP_RESEARCH_SYSTEM, settings.report_language),
        user,
        ResearchReport,
    )
    return _sanitize_report(report)


def _extract_pain_from_snippets(
    snippets: list[dict[str, Any]],
    settings: Settings,
    hints: dict[str, str],
) -> PainExtraction | None:
    if not snippets:
        return None
    llm = get_chat_model(settings)
    evidence = json.dumps(snippets[:30], ensure_ascii=False, indent=2)
    user = (
        f"Brief garment/season lock: {hints['garment']} / {hints['season']} ({hints['category_key']})\n"
        "Extract consumer pain themes ONLY from the evidence below.\n"
        "If Amazon review text is not verbatim in snippets, infer themes cautiously and say so in review_rating_notes.\n"
        f"Write pain points and themes in {'English' if settings.report_language == 'en' else 'Korean'}.\n\n"
        f"{evidence}"
    )
    try:
        pain = invoke_structured(
            llm,
            with_language(PAIN_EXTRACTION_SYSTEM, settings.report_language),
            user,
            PainExtraction,
        )
        pain.consumer_pain_points = _normalize_plain_bullets(pain.consumer_pain_points)
        pain.qual_themes = _normalize_plain_bullets(pain.qual_themes)
        return pain
    except Exception as exc:
        logger.warning("pain extraction failed: %s", exc)
        return None


def _sanitize_report(report: ResearchReport) -> ResearchReport:
    return report.model_copy(
        update={
            "market_gaps": _normalize_plain_bullets(report.market_gaps),
            "competitor_moves": _normalize_plain_bullets(report.competitor_moves),
            "consumer_pain_points": _normalize_plain_bullets(
                report.consumer_pain_points
            ),
            "qual_themes": _normalize_plain_bullets(report.qual_themes),
        }
    )


def _merge_pain_into_report(
    report: ResearchReport, pain: PainExtraction
) -> ResearchReport:
    qs = report.quant_signals.model_copy()
    if len(report.consumer_pain_points) < 3:
        report = report.model_copy(
            update={"consumer_pain_points": pain.consumer_pain_points}
        )
    if not qs.pain_theme_frequencies:
        qs = qs.model_copy(
            update={"pain_theme_frequencies": pain.pain_theme_frequencies}
        )
    if pain.review_rating_notes and not qs.review_rating_notes:
        qs = qs.model_copy(update={"review_rating_notes": pain.review_rating_notes})
    if not report.qual_themes and pain.qual_themes:
        report = report.model_copy(update={"qual_themes": pain.qual_themes})
    return report.model_copy(update={"quant_signals": qs})


def _report_needs_pain_backfill(report: ResearchReport) -> bool:
    return (
        len(report.consumer_pain_points) < 3
        or len(report.quant_signals.pain_theme_frequencies) < 2
    )


def _report_needs_gap_backfill(report: ResearchReport) -> bool:
    return len(report.market_gaps) < 3


def _enforce_brief_fidelity(
    report: ResearchReport, hints: dict[str, str]
) -> ResearchReport:
    """Soft repair when synthesis drifts off the brief's product phrase/family."""
    garment = hints["garment"]
    brief_g = hints.get("product_brief") or garment
    season = hints["season"]
    family = hints.get("product_family") or hints.get("category_key") or "other"
    lock_tokens = [t for t in (hints.get("lock_tokens") or "").split("|") if t]
    if not lock_tokens:
        lock_tokens = _product_lock_tokens(brief_g, garment)
    forbidden = FAMILY_DRIFT_TOKENS.get(family, ())
    report = _sanitize_report(report)

    if _report_needs_gap_backfill(report):
        template = _dry_run_report(f"{brief_g} {season}", None)
        report = report.model_copy(update={"market_gaps": template.market_gaps})

    drift = 0
    for c in report.concepts:
        blob = " ".join(
            [
                c.name or "",
                c.garment_type or "",
                c.target_tpo or "",
                c.usp_hypothesis or "",
            ]
        ).lower()
        if any(x in blob for x in forbidden):
            drift += 1
        if not any(tok.lower() in blob for tok in lock_tokens):
            drift += 1
    if drift >= max(1, len(report.concepts) // 2) or not report.concepts:
        template = _dry_run_report(f"{brief_g} {season}", None)
        report = report.model_copy(update={"concepts": template.concepts})
        if not report.competitor_moves:
            report = report.model_copy(
                update={"competitor_moves": template.competitor_moves}
            )

    return report


def _snippet_evidence_lines(
    snippets: list[dict[str, Any]], *, limit: int = 8
) -> list[str]:
    """Plain evidence strings from search hits (title + short body)."""
    lines: list[str] = []
    seen: set[str] = set()
    for item in snippets:
        title = str(item.get("title") or "").strip()
        body = str(
            item.get("snippet") or item.get("body") or item.get("content") or ""
        ).strip()
        body = re.sub(r"\s+", " ", body)[:180]
        if not title and not body:
            continue
        key = (title or body)[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        if title and body:
            lines.append(f"{title} — {body}")
        else:
            lines.append(title or body)
        if len(lines) >= limit:
            break
    return lines


def _grounded_report_from_snippets(
    user_brief: str,
    target_category: str | None,
    snippets: list[dict[str, Any]],
    *,
    fallback_note: str,
) -> ResearchReport:
    """When LLM synthesis fails but search returned hits, stay evidence-first.

    Prefer titled web snippets as pains / qual themes over pure invented template
    copy. Still mark confidence insufficient and omit fake per-brand battlecards.
    """
    hints = _parse_brief_hints(user_brief, target_category)
    evidence = _snippet_evidence_lines(snippets, limit=10)
    base = _dry_run_report(
        user_brief,
        target_category,
        fallback_note=fallback_note,
    )
    if not evidence:
        base.sources = _snippets_to_sources(snippets, hints) or base.sources
        return base

    display = hints.get("product_brief") or hints["garment"]
    season = hints["season"]
    pains = [f"웹 발췌: {e}" for e in evidence[:5]]
    # Pad with on-family template pains only if search lines are thin.
    for p in base.consumer_pain_points:
        if len(pains) >= 5:
            break
        if p not in pains:
            pains.append(p)

    gaps = [
        f"{display} · {season}: 검색 근거 상 확인된 고민 구간 (합성 실패 — 제목·스니펫 기반)",
        f"상위 검색 신호: {evidence[0][:160]}" if evidence else base.market_gaps[0],
        (
            f"출처 {min(len(snippets), 12)}건 확보 · LLM 구조화 실패로 정성 합성 미완료 — 재실행 권장"
        ),
    ]

    themes = [
        f"⚠ {fallback_note} — 검색 스니펫 발췌 모드 (LLM 종합 아님). 확정 조사 금지.",
        *[f"근거: {e[:200]}" for e in evidence[:4]],
    ]

    sources = _snippets_to_sources(snippets, hints)
    return base.model_copy(
        update={
            "market_gaps": gaps,
            "consumer_pain_points": pains,
            "qual_themes": themes,
            "sources": sources or base.sources,
            "competitive_battlecards": [],
            "customer_journeys": [],
            "quant_signals": base.quant_signals.model_copy(
                update={
                    "review_rating_notes": (
                        f"{fallback_note} — 웹 스니펫 {len(evidence)}건 발췌; "
                        "LLM 구조화 불가로 템플릿·발췌 혼합. 확정 조사 금지."
                    ),
                    "pain_theme_frequencies": {
                        "web_snippet_signal": 0.5,
                        "template_pad": 0.3,
                        "unverified": 0.2,
                    },
                }
            ),
        }
    )


def run_deep_research(
    user_brief: str,
    *,
    target_category: str | None = None,
    settings: Settings | None = None,
    dry_run: bool = False,
    extra_research_note: str | None = None,
) -> ResearchReport:
    settings = settings or get_settings()
    brief = user_brief
    if extra_research_note:
        brief = f"{user_brief}\n\nAdditional research request: {extra_research_note}"

    if dry_run:
        return _dry_run_report(brief, target_category)

    hints = _parse_brief_hints(brief, target_category)
    queries = _build_search_queries(brief, hints)
    search_tool = get_search_tool(settings)
    snippets = _run_search_loop(
        queries, search_tool, max_calls=settings.max_research_tool_calls
    )

    if snippets:
        try:
            report = _synthesize_from_snippets(
                brief, target_category, snippets, settings
            )
        except Exception as exc:  # LLM down / missing dep / schema refusal
            logger.warning("synthesis failed, grounding from snippets: %s", exc)
            report = _grounded_report_from_snippets(
                brief,
                target_category,
                snippets,
                fallback_note=f"LLM 종합 실패 ({type(exc).__name__}: {str(exc)[:160]})",
            )
            return report
        if _report_needs_pain_backfill(report):
            pain = _extract_pain_from_snippets(snippets, settings, hints)
            if pain:
                report = _merge_pain_into_report(report, pain)
        report.sources = _snippets_to_sources(snippets, hints) or report.sources
        return _enforce_brief_fidelity(report, hints)

    return _dry_run_report(
        brief,
        target_category,
        fallback_note="웹 검색 근거 0건",
    )


def ensure_concept_ids(report: ResearchReport) -> ResearchReport:
    for idx, concept in enumerate(report.concepts):
        if not concept.concept_id:
            slug = re.sub(r"[^A-Z0-9]+", "-", concept.name.upper()).strip("-")[:24]
            concept.concept_id = slug or chr(ord("A") + idx)
        if not concept.keywords:
            concept.keywords = _tokenize(
                f"{concept.name} {concept.line_recommendation} {concept.garment_type}"
            )
    return report


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", text) if len(t) > 2][:12]


def merge_research_request(report: ResearchReport, note: str) -> ResearchReport:
    report.market_gaps.append(f"Human-requested follow-up: {note}")
    for concept in report.concepts:
        concept.keywords.extend(_tokenize(note))
    return report
