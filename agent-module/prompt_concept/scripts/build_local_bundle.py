"""Build paste bundles from MY_prompt.md only — no local data embeds.

Catalog and strategy facts come from product_data_base_url (future) or slash commands.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

CONCEPT_ROOT = Path(__file__).resolve().parent.parent
INJECT_PRIORITY = CONCEPT_ROOT / "cqr-inject-priority.md"
PROMPT_SRC = CONCEPT_ROOT / "MY_prompt.md"

OUT_FULL = CONCEPT_ROOT / "MY_prompt_bundle.md"
OUT_SLIM = CONCEPT_ROOT / "MY_prompt_bundle_slim.md"


def read_text(path: Path, fallback: str = "") -> str:
    if not path.exists():
        return fallback
    return path.read_text(encoding="utf-8")


def bundle_header(mode: str) -> str:
    return "\n".join(
        [
            "# Minyoung CQR Concept Concierge — BUNDLE (no embedded catalog)",
            f"# Mode: {mode.upper()} | Built: {date.today().isoformat()}",
            "# Product facts: product_data_base_url API or slash (/childasin, /모델가계도).",
            "# Do not paste old bundles with EMBEDDED sections — they are retired.",
            "",
        ]
    )


def build_bundle(mode: str) -> str:
    inject = read_text(INJECT_PRIORITY).strip()
    prompt = read_text(PROMPT_SRC)
    if not prompt.strip():
        raise SystemExit("MY_prompt.md is missing or empty")
    parts = [
        bundle_header(mode),
        inject,
        "\n\n---\n\n# CQR RULEBOOK\n\n",
        prompt,
    ]
    if mode == "slim":
        parts.append(
            "\n\n---\n\n# SLIM NOTE\n\n"
            "Slim bundle: same API/slash rules as full. No embedded MODEL ROW INDEX or catalog tables.\n"
        )
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
