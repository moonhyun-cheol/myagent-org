#!/usr/bin/env python3
"""Organization-module size guide pipeline — preset list + measurement match."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SIZE_GUIDE_DIR = MODULE_ROOT / "tools" / "size_guide"
PRESETS_DIR = SIZE_GUIDE_DIR / "presets"


def _load_match_fn():
    spec = importlib.util.spec_from_file_location(
        "size_guide_match", SIZE_GUIDE_DIR / "match_size.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("match_size.py not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_chart, mod.match


def cmd_list_presets() -> dict:
    presets = []
    if PRESETS_DIR.is_dir():
        for path in sorted(PRESETS_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            presets.append(
                {
                    "id": path.stem,
                    "brand": data.get("brand"),
                    "category": data.get("category"),
                    "scheme": data.get("scheme"),
                    "source_url": data.get("source_url"),
                    "verified_at": data.get("verified_at"),
                }
            )
    return {"ok": True, "pipeline": "size_guide", "presets": presets}


def cmd_match(args: argparse.Namespace) -> dict:
    load_chart, match = _load_match_fn()
    if args.preset:
        chart_path = PRESETS_DIR / f"{args.preset}.json"
    elif args.chart:
        chart_path = Path(args.chart)
    else:
        return {
            "ok": False,
            "error": "provide --preset ID or --chart PATH",
            "presets": [p.stem for p in PRESETS_DIR.glob("*.json")],
        }

    if not chart_path.is_file():
        return {"ok": False, "error": f"chart not found: {chart_path}"}

    chart = load_chart(chart_path)
    result = match(chart, args.waist, args.inseam, args.layering)
    return {
        "ok": bool(result.get("recommended")),
        "pipeline": "size_guide",
        "preset": args.preset or chart_path.stem,
        "match": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Size guide pipeline")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List bundled size chart presets")

    match_p = sub.add_parser("match", help="Match body measurements to a chart")
    match_p.add_argument("--preset", help="Preset id (filename without .json)")
    match_p.add_argument("--chart", help="Path to chart JSON")
    match_p.add_argument("--waist", type=float, default=None)
    match_p.add_argument("--inseam", type=float, default=None)
    match_p.add_argument("--unit", choices=("inch", "cm"), default="inch")
    match_p.add_argument("--layering", action="store_true")

    args = parser.parse_args()
    if args.command == "list":
        payload = cmd_list_presets()
    elif args.command == "match":
        payload = cmd_match(args)
    else:
        payload = {
            "ok": True,
            "pipeline": "size_guide",
            "status": "entry",
            "message": "Use: size_guide.py list | size_guide.py match --preset ufpro_over_pants --waist 35",
            "argv": sys.argv[1:],
        }

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
