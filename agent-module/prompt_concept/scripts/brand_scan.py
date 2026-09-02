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
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TITLE_BRAND_RE = re.compile(
    r"^([A-Z0-9][A-Z0-9&+\-./]{1,20}?)\s+"
    r"(?:Men['']s|Women['']s|Unisex|Kids|Boy['']s|Girl['']s|Mens|Womens|Baby|Youth|"
    r"Big|Little|Infant|Toddler|Junior|Adult|Classic|Premium|Pro|Ultra|Super|"
    r"Outdoor|Tactical|Quick|Flex|Thermal|Compression|Sports|Athletic|Work|Hiking|"
    r"Cargo|Convertible|Long|Short|Lightweight|Water|Stretch|Ripstop|100%|UPF|Cool|Dry|"
    r"Running|Swim|Yoga|Golf|Casual|Everyday|Warm|Fleece|Flannel|Polo|Button|Zip|"
    r"Pack|Set|Multi|Active|Performance|Winter|Summer|Mesh|Cotton|Leather|Genuine|"
    r"Baselayer|Workout|Training|Gym|Fitness|Military|Travel|Business|Standard|"
    r"Deluxe|Basic|Essential|Relaxed|Loose|Slim|Regular|Utility|Field|Duty|Operator|"
    r"Rash|Guard|Snow|Rain|Wind|Sun|UV|Disc|Frisbee|Pickleball|Boxing|Weightlifting|"
    r"Crossfit|Triathlon|Marathon|Walk|Trail|Mountain|Beach|Pool|Vacation|School|"
    r"Team|Club|Elite|Champion|Safety|Protection|Defense|Shield|Armor|Cover|Case|"
    r"Bag|Pouch|Box|Holder|Stand|Mount|Belt|Buckle|Hook|Loop|Strap|Rope|Cord|"
    r"Round|Flat|Wide|Narrow|High|Low|Mid|Full|Half|Front|Back|Side|Top|Under|Over|"
    r"Inner|Outer|Cold|Hot|Wet|Dry|Soft|Hard|Heavy|Light|Dark|Bright|New|Old|"
    r"Modern|Vintage|Retro|Plus|Max|Mini|Micro|Macro|Slim|Skinny|Straight|Bootcut|"
    r"Fitted|Tight|Loose|Relaxed|Comfort|Everyday|Daily|Weekly|Monthly|Annual|"
    r"Professional|Recreational|Competitive|Amateur|Elite|Premium|Budget|Value|"
    r"Economy|Luxury|Deluxe|Standard|Basic|Essential|Advanced|Expert|Beginner|"
    r"Intermediate|Master|Legend|Hero|Icon|Star|Gold|Silver|Bronze|Platinum|"
    r"Diamond|Crystal|Glass|Metal|Wood|Stone|Plastic|Rubber|Silicone|Nylon|"
    r"Polyester|Spandex|Lycra|Elastic|Stretchy|Breathable|Waterproof|Windproof|"
    r"Snowproof|Fireproof|Flame|Heat|Cold|Warm|Cool|Fresh|Clean|Dirty|New|Used|"
    r"Refurbished|Renewed|Open|Closed|Sealed|Unsealed|Original|Generic|Compatible|"
    r"Replacement|Spare|Backup|Emergency|Portable|Fixed|Mobile|Stationary|Static|"
    r"Dynamic|Automatic|Manual|Digital|Analog|Smart|Dumb|Simple|Complex|Easy|Hard|"
    r"Fast|Slow|Quick|Instant|Delayed|Immediate|Future|Past|Present|Current|"
    r"Previous|Next|First|Last|Middle|Center|Edge|Corner|Border|Frame|Panel|"
    r"Sheet|Layer|Level|Stage|Phase|Step|Part|Piece|Unit|Item|Product|Goods|"
    r"Merchandise|Stock|Inventory|Supply|Order|Purchase|Sale|Deal|Offer|Discount|"
    r"Coupon|Promo|Promotion|Campaign|Event|Launch|Release|Update|Upgrade|Renewal|"
    r"Replacement|Repair|Maintenance|Service|Support|Help|Guide|Manual|Handbook|"
    r"Book|Journal|Notebook|Planner|Calendar|Schedule|Agenda|List|Checklist|"
    r"Template|Sample|Example|Demo|Trial|Test|Review|Rating|Score|Rank|Level|"
    r"Grade|Class|Category|Type|Kind|Sort|Style|Model|Version|Edition|Series|"
    r"Collection|Line|Range|Set|Bundle|Kit|Package|Box|Case|Bag|Pouch|Pack|"
    r"Roll|Sheet|Pad|Block|Cube|Sphere|Cylinder|Cone|Pyramid|Prism|Polygon|"
    r"Circle|Square|Rectangle|Triangle|Oval|Round|Flat|Curved|Bent|Angled|"
    r"Straight|Diagonal|Horizontal|Vertical|Parallel|Perpendicular|Cross|Overlap|"
    r"Merge|Split|Join|Separate|Connect|Disconnect|Attach|Detach|Remove|Install|"
    r"Setup|Assembly|Build|Construct|Create|Make|Form|Shape|Mold|Cast|Forge|"
    r"Weld|Solder|Glue|Tape|Stitch|Sew|Knit|Weave|Braid|Twist|Bend|Fold|Cut|"
    r"Slice|Chop|Dice|Grind|Crush|Pound|Hammer|Nail|Screw|Bolt|Rivet|Clamp|Pin|"
    r"Clip|Hook|Latch|Lock|Unlock|Open|Close|Seal|Fill|Empty|Pour|Spill|Collect|"
    r"Gather|Scatter|Spread|Apply|Wipe|Clean|Wash|Rinse|Dry|Soak|Cook|Bake|Roast|"
    r"Grill|Fry|Boil|Simmer|Steam|Smoke|Cure|Preserve|Store|Keep|Hold|Retain|"
    r"Sustain|Bear|Carry|Lift|Lower|Raise|Drop|Catch|Throw|Roll|Slide|Glide|"
    r"Float|Sink|Dive|Surface|Emerge|Appear|Disappear|Exist|Live|Die|Born|Age|"
    r"Mature|Decline|Renew|Refresh|Revive|Restore|Recover|Heal|Hurt|Injure|Damage|"
    r"Destroy|Ruin|Spoil|Rot|Decay|Recycle|Reuse|Repurpose|Discard|Dispose|Waste|"
    r"Conserve|Protect|Maintain|Continue|Persist|Endure|Last|Remain|Stay|Leave|"
    r"Depart|Arrive|Reach|Achieve|Attain|Obtain|Get|Give|Take|Receive|Send|"
    r"Deliver|Return|Come|Go|Move|Travel|Run|Walk|Stand|Sit|Lie|Sleep|Wake|Eat|"
    r"Drink|Breathe)",
    re.I,
)

KNOWN_IN_TITLE = [
    "CQR", "TSLA", "TESLA", "TXP401", "TXP", "BMS", "FM", "HAREACE", "REALON",
    "NEWDERY", "COOFANDY", "GAYHAY", "LAVENTO", "SANTINY", "MAGCOMSEN",
    "FREE SOLDIER", "TBMPOY", "KINGOLD", "SILENART", "QLOVEA", "SOLOCOTE",
    "GGRSUP", "UANE", "AKARMY", "ANTARCTIC", "DOBEN", "EKOUAER", "FLYHAWK",
    "GOLDTOE", "HANES", "JERACOL", "KAYDEN", "LAVIUR", "LOMON", "NORTHYARD",
    "PROCLUB", "ROTHCO", "TACVASEN", "TAC9", "TELALNT", "TIAFLY", "VAYAGER",
    "WULFUL", "YOGALICIOUS", "ZITY", "33000FT", "33,000FT", "AKASO", "BALEAF",
    "BENNYS", "BONCERLY", "BURLEBO", "CAMEL", "CANMISS", "CCTK", "CHARTOU",
    "CLARAGEN", "CRZ", "CYT", "DANISH", "ELESOL", "FISOUL", "FOOTJOY", "GEEKER",
    "GRECERELLE", "HODIS", "HUMBLE", "HYDRO", "INNAV", "JINSHI", "JOGAL",
    "KOLILI", "KORAMAN", "LELINTA", "LEON", "LOOG", "LUPO", "MAGNIVIT",
    "MEROKEETY", "MIER", "MINTLIMIT", "MOERD", "MUMANA", "NUBWO", "OAKLEY",
    "PAGK", "SCRUBS", "SPOSULEI", "UNDER ARMOUR", "NIKE", "ADIDAS", "REEBOK",
    "COLUMBIA", "CARHARTT", "DICKIES", "5.11", "5.11 TACTICAL", "THE NORTH FACE",
]


def normalize_brand(raw: str) -> str:
    raw = (raw or "").strip().upper().replace("'", "").replace(".", "")
    aliases = {
        "TESLA": "TSLA",
        "AMAZONFOUND": "AMAZON.FOUND",
        "AMAZON": "AMAZON.FOUND",
        "33000FT": "33,000FT",
    }
    return aliases.get(raw, raw)


def extract_brand(name: str, sku: str) -> str:
    name = name or ""
    sku = sku or ""
    m = TITLE_BRAND_RE.match(name)
    if m:
        return normalize_brand(m.group(1))
    lower = name.lower()
    for token in sorted(KNOWN_IN_TITLE, key=len, reverse=True):
        if token.lower() in lower:
            return normalize_brand(token)
    sm = re.match(r"^([A-Za-z][A-Za-z0-9]{1,12})", sku or "")
    if sm:
        return normalize_brand(sm.group(1))
    first = name.split(" ", 1)[0] if name else ""
    if first and re.match(r"^[A-Z0-9][A-Z0-9&+\-./]{1,20}$", first, re.I):
        return normalize_brand(first)
    return "UNKNOWN"


def family_key(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    if not name:
        return "EMPTY"
    return name.split(",")[0].strip()[:100]


rows = 0
brand_ctr = collections.Counter()
family_by_brand = collections.defaultdict(collections.Counter)
samples = {}
status_ctr = collections.Counter()
active_only = collections.Counter()

with LISTING.open("r", encoding="utf-8", errors="replace", newline="") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        rows += 1
        name = row.get("item-name", "") or ""
        sku = row.get("seller-sku", "") or ""
        status = row.get("status", "") or ""
        brand = extract_brand(name, sku)
        status_ctr[status] += 1
        brand_ctr[brand] += 1
        family_by_brand[brand][family_key(name)] += 1
        if brand not in samples:
            samples[brand] = {
                "item_name": name[:140],
                "seller_sku": sku[:80],
                "asin": row.get("asin1", ""),
                "price": row.get("price", ""),
                "status": status,
            }
        if status.lower() == "active":
            active_only[brand] += 1

report = {
    "source_file": str(LISTING),
    "snapshot_date": "2026-06-12",
    "row_count": rows,
    "status_breakdown": dict(status_ctr),
    "brand_count": len(brand_ctr),
    "brands": [],
}

for brand, count in brand_ctr.most_common():
    report["brands"].append(
        {
            "brand": brand,
            "listing_count": count,
            "active_count": active_only.get(brand, 0),
            "sample": samples.get(brand, {}),
            "top_families": [
                {"family": fam, "count": fam_count}
                for fam, fam_count in family_by_brand[brand].most_common(12)
            ],
        }
    )

(OUT_DIR / "brand_catalog_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)

lines = [
    f"rows={rows}",
    f"unique_brands={len(brand_ctr)}",
    f"status={dict(status_ctr)}",
    "",
]
for brand, count in brand_ctr.most_common(80):
    sample = samples[brand]
    lines.append(
        f"{count}\t{active_only.get(brand, 0)}\t{brand}\t{sample.get('asin', '')}\t{sample.get('item_name', '')[:90]}"
    )
(OUT_DIR / "brand_catalog_report.txt").write_text("\n".join(lines), encoding="utf-8")

codex_dir = OUT_DIR / "codex"
codex_dir.mkdir(exist_ok=True)
for item in report["brands"]:
    if item["listing_count"] < 50 and item["brand"] not in {"CQR", "TSLA"}:
        continue
    body = [
        f"# {item['brand']} Codex Seed",
        "",
        f"Source: {LISTING.name}",
        f"Listings: {item['listing_count']} (active {item['active_count']})",
        "",
        "## Product Identity",
        f"Sample ASIN: {item['sample'].get('asin', '')}",
        f"Sample title: {item['sample'].get('item_name', '')}",
        "",
        "## Top Product Families",
    ]
    for fam in item["top_families"]:
        body.append(f"- {fam['family']} ({fam['count']})")
    body.extend(
        [
            "",
            "## Open Gaps",
            "- Size chart unverified",
            "- Warranty/return terms unverified",
            "- Materials by ASIN unverified",
            "- Live stock/price unverified",
        ]
    )
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", item["brand"])[:40]
    (codex_dir / f"{safe}.md").write_text("\n".join(body), encoding="utf-8")

print("DONE")
print("rows", rows)
print("brands", len(brand_ctr))
for b, c in brand_ctr.most_common(25):
    print(c, active_only.get(b, 0), b)
