"""Build single-file local prompts from MY_prompt.md + data/*. No NAS required."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

CONCEPT_ROOT = Path(__file__).resolve().parent.parent
MANAGER_ROOT = CONCEPT_ROOT.parent
DATA = MANAGER_ROOT / "data"
SCRIPTS = CONCEPT_ROOT / "scripts"
INJECT_PRIORITY = CONCEPT_ROOT / "cqr-inject-priority.md"
PROMPT_SRC = CONCEPT_ROOT / "MY_prompt.md"

OUT_FULL = CONCEPT_ROOT / "MY_prompt_bundle.md"
OUT_SLIM = CONCEPT_ROOT / "MY_prompt_bundle_slim.md"

NAS_RE = re.compile(r"\\\\Nas\\[^\s|]+|\\\\nas\\[^\s|]+", re.I)


def read_text(path: Path, fallback: str = "") -> str:
    if not path.exists():
        return fallback
    return path.read_text(encoding="utf-8")


def strip_nas(text: str) -> str:
    text = NAS_RE.sub("[local-source]", text)
    for old, new in [
        ("attached knowledge files", "embedded knowledge in this document"),
        ("attached files", "embedded sections in this document"),
        ("attached PO or size extracts", "embedded PO or size extracts if present"),
        ("attached catalog knowledge", "embedded catalog summary"),
        ("attached catalog titles", "embedded development and catalog knowledge"),
    ]:
        text = text.replace(old, new)
    return text


def knowledge_pack_block(mode: str) -> str:
    if mode == "slim":
        return """[KNOWLEDGE PACK]

All knowledge is embedded below in this same document. Search in this order:
1. EMBEDDED: INTERNAL STRATEGY v3.1
2. EMBEDDED: MODEL ROW INDEX
3. EMBEDDED: PRODUCT DEV SPEC ENGINE
4. EMBEDDED: COLOR CODE
5. EMBEDDED: GOLDEN EXAMPLE
6. EMBEDDED: BRAND CONCEPT
7. EMBEDDED: LOADOUT SYSTEM
8. EMBEDDED: SCENE BRIEF ENGINE
9. EMBEDDED: SLOGAN VOICE
10. EMBEDDED: IMAGE MODEL CAST
11. EMBEDDED: VISUAL DNA
12. EMBEDDED: PROMPT GENERATION PROTOCOL
13. EMBEDDED: BRAND IMAGE PLAYBOOK
14. EMBEDDED: FILM MOOD REF

Full development rows are not embedded in slim mode. If model matching fails, ask for model code, color code, ASIN, or exact title. Do not invent a row.

If knowledge and user input conflict, prefer the newest user-supplied material, then embedded MODEL ROW INDEX, then embedded knowledge."""
    return """[KNOWLEDGE PACK]

All knowledge is embedded below in this same document. Search in this order:
1. EMBEDDED: INTERNAL STRATEGY v3.1
2. EMBEDDED: MODEL ROW INDEX
3. EMBEDDED: PRODUCT DEV SPEC ENGINE
4. EMBEDDED: COLOR CODE
5. EMBEDDED: DEVELOPMENT DIRECTION
6. EMBEDDED: BRAND CONCEPT
7. EMBEDDED: LOADOUT SYSTEM
8. EMBEDDED: SCENE BRIEF ENGINE
9. EMBEDDED: SLOGAN VOICE
10. EMBEDDED: IMAGE MODEL CAST
11. EMBEDDED: VISUAL DNA
12. EMBEDDED: PROMPT GENERATION PROTOCOL
13. EMBEDDED: BRAND IMAGE PLAYBOOK
14. EMBEDDED: FILM MOOD REF
15. EMBEDDED: GOLDEN EXAMPLE
16. EMBEDDED: CATALOG SUMMARY

If knowledge and user input conflict, prefer the newest user-supplied material, then MODEL ROW INDEX, then development-direction embed."""


def replace_knowledge_pack(prompt: str, mode: str) -> str:
    start = prompt.find("[KNOWLEDGE PACK]")
    end = prompt.find("[MENU RULES]")
    if start == -1 or end == -1:
        raise ValueError(
            "Could not find [KNOWLEDGE PACK] or [MENU RULES] in MY_prompt.md"
        )
    return prompt[:start] + knowledge_pack_block(mode) + "\n\n" + prompt[end:]


def patch_prompt_header(prompt: str) -> str:
    prompt = prompt.replace(
        "A-4. Knowledge Truth: use only attached knowledge files and user-supplied material in the current session. Never cite NAS paths, internal folder paths, or file system locations in user-visible answers.",
        "A-4. Knowledge Truth: use only embedded knowledge in this document and user-supplied material in the current session. Never cite internal archive paths or file system locations in user-visible answers.",
    )
    prompt = prompt.replace(
        "C-8. Never mention NAS, internal archive paths, or file system locations to the user.",
        "C-8. Never mention internal archive paths or file system locations to the user.",
    )
    return prompt


def catalog_summary() -> str:
    report = read_text(DATA / "brand_catalog_report.json")
    active = read_text(DATA / "brand_active_report.json")
    lines = [
        "# Catalog summary (local snapshot)",
        f"Generated: {date.today().isoformat()}",
        "",
        "Amazon US active listing snapshot (counts only; no live price/stock claims).",
        "",
        "- CQR: primary hero brand",
        "- TSLA: secondary athletic lane",
        "- ATIKA: tertiary women's lane",
        "",
    ]
    if active:
        lines.append("## Active counts")
        lines.append(strip_nas(active))
    lines.extend(
        [
            "",
            "## Title-bridge rule",
            "Use MODEL ROW INDEX and development direction for concept. Never invent listing facts.",
        ]
    )
    return strip_nas("\n".join(lines))


def ensure_model_rows() -> None:
    script = SCRIPTS / "build_model_rows.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], check=False, cwd=CONCEPT_ROOT)


def section(title: str, body: str) -> str:
    return f"\n\n---\n\n# EMBEDDED: {title}\n\n{body.strip()}\n"


def build_bundle(mode: str) -> str:
    ensure_model_rows()
    inject = read_text(INJECT_PRIORITY).strip()
    prompt_body = patch_prompt_header(
        replace_knowledge_pack(read_text(PROMPT_SRC), mode)
    )
    # Inject priority wins on format conflicts; MY_prompt also embeds OUTPUT CONTRACT for standalone edit.
    prompt = inject + "\n\n---\n\n# CQR RULEBOOK\n\n" + prompt_body
    model_rows = strip_nas(
        read_text(
            DATA / "model_row_index.txt", "MISSING: run scripts/build_model_rows.py"
        )
    )
    product_dev = strip_nas(read_text(DATA / "PRODUCT_DEV_SPEC_ENGINE.md"))
    color_code = strip_nas(read_text(DATA / "COLOR_CODE.md"))
    golden = strip_nas(read_text(DATA / "GOLDEN_EXAMPLE.md"))
    brand = strip_nas(read_text(DATA / "codex" / "CQR_BRAND_CONCEPT.md"))
    strategy = strip_nas(read_text(DATA / "CQR_INTERNAL_STRATEGY_v3.1.md"))
    loadout = strip_nas(read_text(DATA / "CQR_LOADOUT_SYSTEM.md"))
    scene = strip_nas(read_text(DATA / "SCENE_BRIEF_ENGINE.md"))
    slogan_voice = strip_nas(read_text(DATA / "SLOGAN_VOICE.md"))
    image_model_cast = strip_nas(read_text(DATA / "CQR_IMAGE_MODEL_CAST.md"))
    visual = strip_nas(read_text(DATA / "CQR_VISUAL_DNA.md"))
    protocol = strip_nas(read_text(DATA / "CQR_PROMPT_GENERATION_PROTOCOL.md"))
    playbook = strip_nas(read_text(DATA / "CQR_BRAND_IMAGE_PLAYBOOK.md"))
    film_mood = strip_nas(read_text(DATA / "CQR_FILM_MOOD_REF.md"))
    dev = strip_nas(read_text(DATA / "cqr_development_direction.txt"))

    header = [
        "# Minyoung CQR Concept Concierge — LOCAL BUNDLE",
        f"# Mode: {mode.upper()} | Built: {date.today().isoformat()}",
        "# Paste this entire file as system instructions. No external attachments required.",
        "",
    ]

    parts = ["".join(line + "\n" for line in header), prompt]
    parts.append(section("MODEL ROW INDEX", model_rows))
    parts.append(section("PRODUCT DEV SPEC ENGINE", product_dev))
    parts.append(section("COLOR CODE", color_code))

    if mode == "full":
        if not dev or dev.startswith("MISSING"):
            dev = "MISSING: place xlsx in data/source/ and run python scripts/extract_nas_docs.py"
        parts.append(section("DEVELOPMENT DIRECTION", dev))
        parts.append(section("CATALOG SUMMARY", catalog_summary()))

    parts.append(section("BRAND CONCEPT", brand))
    parts.append(
        section(
            "INTERNAL STRATEGY v3.1",
            strategy or "MISSING: data/CQR_INTERNAL_STRATEGY_v3.1.md",
        )
    )
    parts.append(section("LOADOUT SYSTEM", loadout))
    parts.append(section("SCENE BRIEF ENGINE", scene))
    parts.append(section("SLOGAN VOICE", slogan_voice))
    parts.append(section("IMAGE MODEL CAST", image_model_cast or "MISSING"))
    parts.append(section("VISUAL DNA", visual or "MISSING"))
    parts.append(section("PROMPT GENERATION PROTOCOL", protocol or "MISSING"))
    parts.append(section("BRAND IMAGE PLAYBOOK", playbook or "MISSING"))
    parts.append(section("FILM MOOD REF", film_mood or "MISSING"))
    parts.append(section("GOLDEN EXAMPLE", golden))

    return "".join(parts)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def main() -> None:
    full = build_bundle("full")
    slim = build_bundle("slim")
    OUT_FULL.write_text(full, encoding="utf-8")
    OUT_SLIM.write_text(slim, encoding="utf-8")
    print(
        f"Wrote {OUT_FULL.name}: {len(full):,} chars (~{estimate_tokens(full):,} tokens)"
    )
    print(
        f"Wrote {OUT_SLIM.name}: {len(slim):,} chars (~{estimate_tokens(slim):,} tokens)"
    )


if __name__ == "__main__":
    main()
