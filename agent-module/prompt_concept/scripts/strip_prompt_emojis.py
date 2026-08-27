"""Remove emoji from prompt sources — label-aware, spacing-safe."""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONCEPT_ROOT = Path(__file__).resolve().parent.parent
MANAGER_ROOT = CONCEPT_ROOT.parent
DATA = MANAGER_ROOT / "data"

EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002700-\U000027bf"
    "\U00002600-\U000026ff"
    "\U00002300-\U000023ff"
    "]+",
    flags=re.UNICODE,
)
VARIATION_RE = re.compile(r"[\uFE0F\u200D]")

# Replace known multi-emoji packs before generic strip
SEQUENCE_REPLACEMENTS = [
    ("📽️📺🎭🖼️", "무드 참고, 매체 DNA, 배우 3티어, 디테일 컷시트"),
    ("📺🎭🖼️", "매체 DNA, 배우 3티어, 디테일 컷시트"),
    ("🎯·🌍", "mission·place"),
]

POLICY_REPLACEMENTS = [
    (
        "no prose emoji in body prose; titles and headers start with topic-fit emoji",
        "no emoji anywhere in user-visible output; section titles are plain Korean topic headings only",
    ),
    ("emoji only on structure", "plain-text section headings only — no emoji"),
    ("with emoji-led titles", "with plain-text titles"),
    ("a. emoji title.", "a. plain-text title."),
    ("Use these 5 emoji-led sections", "Use these 5 labeled sections"),
    ("Use these emoji-led sections", "Use these labeled sections"),
    ("Emoji-led sections in order", "Labeled sections in order"),
    ("use clear emoji headers", "use clear plain-text section headers"),
]

SOURCE_FILES = [
    CONCEPT_ROOT / "MY_prompt.md",
    CONCEPT_ROOT / "cqr-inject-priority.md",
    DATA / "model_row_index.txt",
    DATA / "PRODUCT_DEV_SPEC_ENGINE.md",
    DATA / "COLOR_CODE.md",
    DATA / "GOLDEN_EXAMPLE.md",
    DATA / "codex" / "CQR_BRAND_CONCEPT.md",
    DATA / "CQR_INTERNAL_STRATEGY_v3.1.md",
    DATA / "CQR_LOADOUT_SYSTEM.md",
    DATA / "SCENE_BRIEF_ENGINE.md",
    DATA / "SLOGAN_VOICE.md",
    DATA / "CQR_IMAGE_MODEL_CAST.md",
    DATA / "CQR_VISUAL_DNA.md",
    DATA / "CQR_PROMPT_GENERATION_PROTOCOL.md",
    DATA / "CQR_BRAND_IMAGE_PLAYBOOK.md",
    DATA / "CQR_FILM_MOOD_REF.md",
    DATA / "cqr_development_direction.txt",
]


def strip_emojis(text: str) -> str:
    for old, new in SEQUENCE_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in POLICY_REPLACEMENTS:
        text = text.replace(old, new)
    text = VARIATION_RE.sub("", text)
    text = EMOJI_RE.sub("", text)
    # tidy double spaces on each line (preserve newlines)
    lines = [re.sub(r"  +", " ", line.rstrip()) for line in text.splitlines()]
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def process_file(path: Path) -> bool:
    if not path.exists():
        print(f"SKIP {path}")
        return False
    original = path.read_text(encoding="utf-8")
    updated = strip_emojis(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    before = len(EMOJI_RE.findall(original))
    after = len(EMOJI_RE.findall(updated))
    print(f"OK {path.relative_to(MANAGER_ROOT)} ({before} -> {after} emoji runs)")
    return True


def main() -> int:
    changed = sum(process_file(p) for p in SOURCE_FILES)
    print(f"Updated {changed} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
