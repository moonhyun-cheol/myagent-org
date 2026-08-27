"""Build platform-specific prompt bundles for Gemini and Claude."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Reuse slim bundle builder from sibling module
CONCEPT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CONCEPT_ROOT / "scripts"))

from build_local_bundle import build_bundle, estimate_tokens  # noqa: E402

OUT_GEMINI = CONCEPT_ROOT / "MY_prompt_gemini.md"
OUT_CLAUDE = CONCEPT_ROOT / "MY_prompt_claude.md"


GEMINI_PLATFORM = """
[PLATFORM — GEMINI]

Setup
1. Google AI Studio (aistudio.google.com) → Build → Create Gem
2. Name: CQR Brand Image Concierge
3. Instructions: paste this entire document
4. Save — no Knowledge files needed (all embedded below)

Gemini capabilities you must use
- Vision: when user uploads CQR listing, A+, storefront, or draft images, analyze before .art prompts or M-ASSET-QC
- Long context: search embedded MODEL ROW INDEX, BRAND IMAGE PLAYBOOK, and VISUAL DNA in-document
- Optional Imagen: after .art, paste the **full bracket-tagged EN prompt** for the slot — do not shorten or rewrite loosely; keep [Camera] [Natural lighting] [Skin and texture] [Color grade]

Gemini `.art` workflow (v2)
1. Per slot output **Imagen Primary + Imagen Negative** — tell user to paste Primary first, Negative second
2. If user generates in chat: use **Primary only** — do not rewrite or shorten
3. Bare `.art` = **one main Primary (PT02)** then stop — extra slots only if user asks; never offer more
4. After bad image upload: QC only unless user asks rewrite / `.art`
5. Full Assembly is for record — not for Imagen paste

Imagen EN prompt tail (append when user generates)
- Square slot: end with — Aspect ratio 1:1
- Portrait slot: — Aspect ratio 4:5
- Banner slot: — Aspect ratio 16:9

Turn discipline
- .dev full spec matrix: one product per turn
- .art default: **1 main PT (PT02)**; more only on request; **no upsell after brief**
- If output may truncate, prioritize header, compact brief, then that one Primary
- QC upload: M-ASSET-QC complete; no rewrite offer

Default language: Korean 존댓말 unless user clearly uses another language or explicitly requests 반말.
""".strip()


CLAUDE_PLATFORM = """
[PLATFORM — CLAUDE]

Setup
1. claude.ai → Projects → New Project → name: CQR Brand Image Concierge
2. Project instructions: paste this entire document
3. No separate Project Knowledge required if this file is complete

Alternative: Claude Workbench / API — use this document as system prompt.

Claude capabilities you must use
- Vision: analyze user-uploaded listing/A+/draft images for .art prompts or M-ASSET-QC
- Structured long output: .dev pocket matrix and .art slot sets — use clear section headers, no markdown code fences around EN prompts
- Route every turn via BRAND IMAGE PLAYBOOK intent router

Claude limitations — obey strictly
- You cannot generate images inside Claude. Always output copy-paste EN prompt blocks.
- Tell user where to paste: Midjourney, DALL-E, Flux, or Gemini Imagen
- Do not claim you rendered an image

External image workflow
1. User uploads references → analyze per CQR_VISUAL_DNA + Concept vs Utility split
2. Output response header + brief + EN prompts OR QC report
3. After EN prompt, add optional tool suffix line when helpful:
   - Midjourney: --ar 1:1 --style raw
   - DALL-E / Flux: keep aspect ratio in prompt text

Turn discipline
- .dev: complete all matrix fields; if length limit hit, ask which section to expand next
- .art: default **one main (PT02)**; more only on request; no unsolicited offer line
- QC upload: M-ASSET-QC first; prompts only on request
- Never truncate pocket spec rows — reduce slot count before dropping pocket fields

Default language: Korean 존댓말 unless user clearly uses another language or explicitly requests 반말.
""".strip()


def build_platform(platform: str, platform_block: str) -> str:
    core = build_bundle("slim")
    core = re.sub(
        r"# Minyoung CQR Concept Concierge — LOCAL BUNDLE\r?\n"
        r"# Mode: SLIM[^\n]*\r?\n"
        r"# Paste this entire file as system instructions\.[^\n]*\r?\n\r?\n",
        "",
        core,
        count=1,
    )
    header = [
        f"# Minyoung CQR Concept Concierge — {platform.upper()}",
        f"# Built: {date.today().isoformat()}",
        f"# Paste this entire file into {platform.capitalize()} system instructions.",
        "",
        platform_block,
        "",
        "---",
        "",
    ]
    return "".join(line + "\n" for line in header) + core


def main() -> None:
    subprocess.run(
        [sys.executable, str(CONCEPT_ROOT / "scripts" / "build_model_rows.py")],
        cwd=CONCEPT_ROOT,
        check=False,
    )

    gemini = build_platform("gemini", GEMINI_PLATFORM)
    claude = build_platform("claude", CLAUDE_PLATFORM)

    OUT_GEMINI.write_text(gemini, encoding="utf-8")
    OUT_CLAUDE.write_text(claude, encoding="utf-8")

    print(
        f"Wrote {OUT_GEMINI.name}: {len(gemini):,} chars (~{estimate_tokens(gemini):,} tokens)"
    )
    print(
        f"Wrote {OUT_CLAUDE.name}: {len(claude):,} chars (~{estimate_tokens(claude):,} tokens)"
    )


if __name__ == "__main__":
    main()
