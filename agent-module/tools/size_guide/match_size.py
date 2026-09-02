#!/usr/bin/env python3
"""Match body measurements against an extracted size-chart JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_chart(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def score_row(
    row: dict, waist: float | None, inseam: float | None
) -> tuple[int, list[str], bool]:
    notes: list[str] = []
    score = 0
    waist_ok = True
    inseam_ok = True

    if waist is not None:
        lo, hi = row.get("waist_min"), row.get("waist_max")
        if lo is not None and hi is not None:
            if lo <= waist <= hi:
                score += 2
                margin = min(waist - lo, hi - waist)
                if margin < 0.5:
                    notes.append(f'waist borderline ({margin:.2f}" from edge)')
            else:
                waist_ok = False
                notes.append(f"waist {waist} outside {lo}-{hi}")

    if inseam is not None:
        lo, hi = row.get("inseam_min"), row.get("inseam_max")
        if lo is not None and hi is not None:
            if lo <= inseam <= hi:
                score += 1
                margin = min(inseam - lo, hi - inseam)
                if margin < 0.5:
                    notes.append(f'inseam borderline ({margin:.2f}" from edge)')
            else:
                inseam_ok = False
                notes.append(f"inseam {inseam} outside {lo}-{hi}")

    if waist is not None and not waist_ok:
        return (-1, notes, False)

    return (score, notes, waist_ok and inseam_ok)


def match(
    chart: dict, waist: float | None, inseam: float | None, layering: bool
) -> dict:
    rows = chart.get("rows") or []
    ranked: list[tuple[int, dict, list[str], bool]] = []

    for row in rows:
        s, notes, full_fit = score_row(row, waist, inseam)
        if s >= 0:
            ranked.append((s, row, notes, full_fit))

    ranked.sort(key=lambda x: x[0], reverse=True)

    if not ranked:
        return {
            "recommended": None,
            "confidence": "low",
            "notes": ["No row matched measurements"],
            "layering_warning": layering,
        }

    best_score, best_row, best_notes, full_fit = ranked[0]
    if full_fit and best_score >= 3 and not best_notes:
        confidence = "high"
    elif best_score >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "recommended": best_row.get("size"),
        "confidence": confidence,
        "score": best_score,
        "notes": best_notes,
        "alternatives": [r[1].get("size") for r in ranked[1:3]],
        "source_url": chart.get("source_url"),
        "category": chart.get("category"),
        "unit": chart.get("unit"),
    }
    if layering:
        result["layering_warning"] = (
            "Measure with layers; consider sizing up if borderline."
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Match measurements to size chart JSON"
    )
    parser.add_argument("chart", type=Path, help="Path to chart JSON")
    parser.add_argument("--waist", type=float, default=None)
    parser.add_argument("--inseam", type=float, default=None)
    parser.add_argument("--unit", choices=("inch", "cm"), default="inch")
    parser.add_argument("--layering", action="store_true")
    args = parser.parse_args()

    chart = load_chart(args.chart)
    if chart.get("unit") and chart["unit"] != args.unit:
        print(
            f"warning: chart unit={chart['unit']} input unit={args.unit}",
            file=sys.stderr,
        )

    result = match(chart, args.waist, args.inseam, args.layering)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("recommended") else 1


if __name__ == "__main__":
    raise SystemExit(main())
