import csv
import collections
import json
import re
from pathlib import Path

LISTING = Path(r"\\Nas\공용_시장조사팀\06_amazon.com\06_alllisting\20260612_KR_alllisting_051024.txt")
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
