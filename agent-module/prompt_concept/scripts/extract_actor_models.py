"""Extract CQR actor/model casting rows from NAS options.db."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

CONCEPT_ROOT = Path(__file__).resolve().parent.parent
DATA = CONCEPT_ROOT.parent / "data"
DB = DATA / "options.db"
OUT = DATA / "CQR_IMAGE_MODEL_CAST.txt"

NAMES = [
    "Mads",
    "Ryan",
    "Sam",
    "Sven",
    "Tyler",
    "Viggo",
    "Carter",
    "David",
    "Erik",
    "Jaxon",
    "Logan",
]


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"Missing {DB}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    lines = [f"# options.db extract", f"Tables: {', '.join(tables)}", ""]

    for table in tables:
        try:
            rows = cur.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.Error:
            continue
        hits: list[sqlite3.Row] = []
        for row in rows:
            text = " | ".join(str(row[k]) for k in row.keys() if row[k] is not None)
            low = text.lower()
            if any(n.lower() in low for n in NAMES) or "[model]" in text or "188cm" in text:
                hits.append(row)
        if hits:
            lines.append(f"## {table} ({len(hits)} hits)")
            for row in hits[:40]:
                payload = {k: row[k] for k in row.keys()}
                lines.append(json.dumps(payload, ensure_ascii=False))
            lines.append("")

    model_rows = cur.execute(
        "SELECT sort_order, item_value FROM field_options "
        "WHERE field_label = '[Model]' ORDER BY sort_order"
    ).fetchall()
    lines.append(f"## [Model] field_options ({len(model_rows)} rows)")
    for sort_order, item_value in model_rows:
        lines.append(f"{sort_order} | {item_value}")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} lines)")
    print(f"[Model] rows: {len(model_rows)}")
    con.close()


if __name__ == "__main__":
    main()
