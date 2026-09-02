import csv
import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TOOLS = str(REPO / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from operator_config import resolve_listing_file  # noqa: E402

LISTING = resolve_listing_file(REPO)
if LISTING is None:
    print("SKIP: listing file not found. Set CQR_LISTING or _local/operator.json nas.alllisting")
    raise SystemExit(0)
OUT = Path(__file__).resolve().parent.parent.parent / "data" / "brand_active_report.json"

KEYWORDS = [
    "CQR", "TSLA", "TESLA", "ATIKA", "ATIKA", "TXP", "BMS", "FM", "HAREACE",
    "REALON", "NEWDERY", "COOFANDY", "MAGCOMSEN", "TACVASEN", "ROTHCO", "BALEAF",
    "AKASO", "UNDER ARMOUR", "NIKE", "ADIDAS", "AMAZON",
]


def classify(name: str) -> str:
    n = (name or "").upper()
    for kw in sorted(KEYWORDS, key=len, reverse=True):
        if kw in n:
            if kw == "TESLA":
                return "TSLA"
            return kw
    first = (name or "").split(" ", 1)[0]
    if re.match(r"^[A-Za-z][A-Za-z0-9&+\-./]{1,15}$", first):
        return first.upper()
    return "OTHER/NO-TITLE"


active = collections.Counter()
all_rows = collections.Counter()
samples = {}

with LISTING.open("r", encoding="utf-8", errors="replace", newline="") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        name = row.get("item-name", "") or ""
        brand = classify(name)
        all_rows[brand] += 1
        if (row.get("status", "") or "").lower() == "active":
            active[brand] += 1
            samples.setdefault(brand, name[:120])

report = {
    "active_total": sum(active.values()),
    "active_brands": [
        {"brand": b, "count": c, "sample": samples.get(b, "")}
        for b, c in active.most_common()
    ],
    "all_brands_top50": all_rows.most_common(50),
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
