"""Build structured model row table from cqr_development_direction.txt + v3.1 overlay."""

from __future__ import annotations

import re
from pathlib import Path

CONCEPT_ROOT = Path(__file__).resolve().parent.parent
DATA = CONCEPT_ROOT.parent / "data"
DEV_TXT = DATA / "cqr_development_direction.txt"
OUT = DATA / "model_row_index.txt"

MODEL_RE = re.compile(
    r"^(?:CQ[-_])?(TLP|TFP|TXP|TXS|TSP|TWP|TOK|TOL|TOS|HOK|HKJ|HKZ|HLP|HOF|HOH|HOS|WFP|WHP|BL|BT|BZ)\d{2,4}[A-Z]?$",
    re.I,
)
ASIN_RE = re.compile(r"B0[A-Z0-9]{8}", re.I)

ROW_MAP = {
    "모델명": "model",
    "라인": "line",
    "배경": "background",
    "지역": "region",
    "온도": "temp",
    "원단": "fabric",
    "원단사양": "fabric_spec",
    "목적": "purpose",
}

FABRIC_TIER = {
    "L": (
        "mesh",
        "interlock",
        "메쉬",
        "니트",
        "jersey",
        "vent",
        "cooling",
        "cn ",
        "소로나",
        "트리코트",
    ),
    "M": (
        "ripstop",
        "립스탑",
        "cargo",
        "light flex",
        "라이트플렉스",
        "combat",
        "utility",
        "ns드라이",
        "ns dry",
        "어센드",
        "트루워크",
        "고신축",
    ),
    "W": (
        "flannel",
        "twill",
        "grid fleece",
        "fleece",
        "shirt jacket",
        "항공점퍼",
        " brushed",
        "폴리스웨터",
        "lt풀오버",
        "lt플리스",
    ),
    "C": (
        "softshell",
        "sherpa",
        "winter",
        "3l",
        "insulated",
        "snow",
        "thrm",
        "thermal",
    ),
}

# Soft aliases → canon (v3.1)
LINE_NORMALIZE: dict[str, str] = {
    "lib": "Liberator-Modern",
    "lib-modern": "Liberator-Modern",
    "liberator - modern": "Liberator-Modern",
    "liberator-modern": "Liberator-Modern",
    "liberatormodern": "Liberator-Modern",
    "lib-legacy": "Liberator-Legacy",
    "lib - legacy": "Liberator-Legacy",
    "liberator - legacy": "Liberator-Legacy",
    "liberator-legacy": "Liberator-Legacy",
    "lib-black": "Liberator-Black",
    "liberator - black": "Liberator-Black",
    "liberator-black": "Liberator-Black",
    "covert": "Covert",
    "sapper": "Sapper",
    "exp-rider": "Expedition-Rider",
    "expedition-rider": "Expedition-Rider",
    "exp-hunter": "Expedition-Hunter",
    "expedition-hunter": "Expedition-Hunter",
    "expedition-alpinist": "Expedition-Alpinist",
    "exp-alpinist": "Expedition-Alpinist",
    "expedition": "Expedition-Alpinist",
}

# Per-SKU hard overrides (A+ queue + clear fixes). See CQR_LINEUP_V31_OVERLAY.md
LINE_OVERRIDE: dict[str, str] = {
    "TLP117": "Liberator-Legacy",
    "TLP125": "Liberator-Black",
    "TLP127": "Liberator-Modern",
    "TLP135": "Liberator-Black",
    "TOS101": "Liberator-Modern",
    "TOS120": "Liberator-Modern",
    "TOS121": "Liberator-Modern",
    "TOS130": "Liberator-Modern",
    "TOS230": "Liberator-Modern",
    "TOS612": "Liberator-Modern",
    "TOK002": "Liberator-Black",
    "TOK171": "Liberator-Modern",
    "TOK271": "Liberator-Modern",
    "HOK909": "Expedition-Rider",
    "HOK809": "Liberator-Modern",
    "HOK817": "Liberator-Modern",
    "HKJ001": "Liberator-Black",
    "HKJ002": "Liberator-Black",
    "HKJ003": "Liberator-Black",
    "HKJ502": "Liberator-Legacy",
    "HKJ503": "Liberator-Legacy",
    "HKZ204": "Covert",
    "HKZ210": "Covert",
    "HKZ300": "Expedition-Rider",
    "HKZ305": "Covert",
    "HOH321": "Expedition-Hunter",
    "HOH322": "Expedition-Hunter",
    "HOF110": "Expedition-Hunter",
    "HOF113": "Expedition-Hunter",
    "HOF120": "Expedition-Hunter",
    "HOF123": "Expedition-Hunter",
    "TXP441": "Expedition-Alpinist",
    "TXP406": "Covert",
    "TXP900": "Expedition-Rider",
    "TWP320": "Sapper",
    "WFP611": "Liberator-Modern",
    "WHP830": "Expedition-Alpinist",
    "HLP831": "Expedition-Alpinist",
    "HLP832": "Expedition-Alpinist",
    "HLP900": "Expedition-Alpinist",
    "HLP905": "Expedition-Alpinist",
    "HLP910": "Expedition-Alpinist",
    "HLP920": "Expedition-Alpinist",
    "HLP200": "Expedition-Alpinist",
    "HLP201": "Expedition-Alpinist",
    "HLP010": "Expedition-Alpinist",
    "HLP011": "Expedition-Alpinist",
    "HLP833": "Expedition-Alpinist",
    "HLP999": "Expedition-Alpinist",
    # Shorts_LT — sheet mainline Covert / Alpinist
    "TSP600": "Covert",
    "TSP620": "Covert",
    "TSP640": "Expedition-Alpinist",
    "TSP641": "Expedition-Alpinist",
    "TXS002": "Covert",
    "TXS201": "Covert",
    "TXS204": "Covert",
    "TXS303": "Covert",
    "TXS803": "Covert",
    "TXS804": "Covert",
    "TXS903": "Covert",
    "TXS101": "Expedition-Alpinist",
}

# Models that must not auto-pick a sub-line
AMBIGUOUS: set[str] = {
    "TLP002",
    "TLP731",
    "TXP202",
    "TXP203",
    "TOK001",
    "HKZ303",
}

# New / missing SKUs not reliably parsed from NAS extract
EXTRA_ROWS: list[dict] = [
    {
        "model": "WHP830",
        "tier": "C",
        "line": "Expedition-Alpinist",
        "temp": "cold",
        "fabric": "thermal stretch softshell",
        "region": "-",
        "background": "women cold-weather trail",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "HOH321",
        "tier": "W",
        "line": "Expedition-Hunter",
        "temp": "2~10C",
        "fabric": "LT fleece",
        "region": "-",
        "background": "off-season camp sustain LO-HMNT",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "HOH322",
        "tier": "W",
        "line": "Expedition-Hunter",
        "temp": "2~10C",
        "fabric": "LT fleece",
        "region": "-",
        "background": "off-season camp sustain LO-HMNT",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "TOS120",
        "tier": "L",
        "line": "Liberator-Modern",
        "temp": "-",
        "fabric": "인터락메쉬165",
        "region": "-",
        "background": "LO-TRN training (GO HARDER)",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "TOS121",
        "tier": "L",
        "line": "Liberator-Modern",
        "temp": "-",
        "fabric": "인터락메쉬165",
        "region": "-",
        "background": "LO-TRN training (GO HARDER)",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "TOS612",
        "tier": "M",
        "line": "Liberator-Modern",
        "temp": "-",
        "fabric": "combat shirt",
        "region": "-",
        "background": "LO-SR field (colorway)",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "HKZ305",
        "tier": "W",
        "line": "Covert",
        "temp": "-",
        "fabric": "폴리스웨터",
        "region": "-",
        "background": "3COLOR MOVE UNRESTRICTED",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "HKZ204",
        "tier": "W",
        "line": "Covert",
        "temp": "-",
        "fabric": "grid fleece",
        "region": "-",
        "background": "RAVEN grid heat management",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "WFP611",
        "tier": "M",
        "line": "Liberator-Modern",
        "temp": "-",
        "fabric": "PC고신축사",
        "region": "-",
        "background": "VANGUARD (colorway)",
        "asin": "",
        "sheet": "NEW_A+",
    },
    {
        "model": "HKJ001",
        "tier": "W",
        "line": "Liberator-Black",
        "temp": "-",
        "fabric": "항공점퍼",
        "region": "숲속",
        "background": "LO-CR / YKK reshoot",
        "asin": "",
        "sheet": "NEW_A+",
    },
]


def infer_tier(fabric: str, sheet: str, model: str) -> str:
    f = (fabric or "").lower()
    for tier, keys in FABRIC_TIER.items():
        if any(k in f for k in keys):
            return tier
    if sheet == "Shirts" or model.startswith(("TOK", "TOS", "TOL")):
        return "L"
    if "ripstop" in sheet.lower() or model.startswith(("TLP", "TFP", "WFP")):
        return "M"
    if sheet.startswith("FW_") or model.startswith(("HKJ", "HOH", "WHP")):
        return "W" if not model.startswith("WHP") else "C"
    if model.startswith("WHP"):
        return "C"
    return "M"


def sanitize(text: str, limit: int = 80) -> str:
    if not text:
        return "-"
    text = re.sub(r"\s+", " ", text).strip()
    for bad in (
        "fbi",
        "csi:",
        "camp peary",
        "lenco",
        "military-camp",
        "교관",
        "스파이",
        "⚔️",
        "🏛️",
        "🕵️",
    ):
        text = re.sub(re.escape(bad), "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if text else "-"


def normalize_line(raw: str, model: str) -> str:
    if model in AMBIGUOUS:
        return f"확인필요({sanitize(raw, 24)})"
    if model in LINE_OVERRIDE:
        return LINE_OVERRIDE[model]

    cleaned = sanitize(raw, 40)
    key = cleaned.lower().replace("–", "-").replace("—", "-")
    key = re.sub(r"\s+", " ", key).strip()

    # fabric-as-line garbage
    if any(x in key for x in ("나일론", "립스탑", "겹바지", "원단")) or key in {
        "라인",
        "-",
        "",
    }:
        return "확인필요(라인미지정)"

    if key in LINE_NORMALIZE:
        return LINE_NORMALIZE[key]

    # partial contains
    if "legacy" in key:
        return "Liberator-Legacy"
    if "black" in key and "modern" in key:
        return f"확인필요({cleaned})"
    if "black" in key:
        return "Liberator-Black"
    if "modern" in key:
        return "Liberator-Modern"
    if "alpinist" in key and "hunt" in key:
        return f"확인필요({cleaned})"
    if "alpinist" in key:
        return "Expedition-Alpinist"
    if "rider" in key:
        return "Expedition-Rider"
    if "hunter" in key or "hunting" in key:
        return "Expedition-Hunter"
    if "covert" in key:
        return "Covert"
    if "sapper" in key:
        return "Sapper"
    if key.startswith("lib"):
        return "Liberator-Modern"

    return cleaned


def extract_models_from_block(block_lines: list[str]) -> list[str]:
    models: list[str] = []
    collecting = False
    for ln in block_lines:
        if "|" not in ln:
            continue
        parts = [p.strip() for p in ln.split("|")]
        key = parts[0]
        if key == "모델명":
            collecting = True
            for p in parts[1:]:
                # TOS120/121 → both
                for chunk in re.split(r"[/,]", p):
                    token = chunk.split("(")[0].strip().upper().replace("CQ-", "")
                    if MODEL_RE.match(token):
                        models.append(token)
            continue
        if collecting:
            if key in ROW_MAP:
                collecting = False
            else:
                for p in parts:
                    for chunk in re.split(r"[/,]", p):
                        token = chunk.split("(")[0].strip().upper().replace("CQ-", "")
                        if MODEL_RE.match(token) and token not in models:
                            models.append(token)
    return models


def parse_dev(text: str) -> list[dict]:
    lines = text.splitlines()
    rows: list[dict] = []
    seen: set[str] = set()

    i = 0
    while i < len(lines):
        if not lines[i].startswith("## "):
            i += 1
            continue
        sheet = lines[i][3:].strip()
        i += 1
        block_lines: list[str] = []
        while i < len(lines) and not lines[i].startswith("## "):
            block_lines.append(lines[i])
            i += 1

        block: dict[str, list[str]] = {}
        for ln in block_lines:
            if "|" not in ln:
                continue
            parts = [p.strip() for p in ln.split("|")]
            key = parts[0]
            if key in ROW_MAP:
                block[ROW_MAP[key]] = parts[1:]

        models = extract_models_from_block(block_lines)
        if not models:
            continue

        asins: list[str] = []
        for ln in block_lines[:20]:
            asins.extend(ASIN_RE.findall(ln.upper()))

        for idx, token in enumerate(models):
            if token in seen:
                continue
            seen.add(token)

            def col(field: str) -> str:
                vals = block.get(field, [])
                if idx < len(vals):
                    return vals[idx]
                if vals:
                    return vals[min(idx, len(vals) - 1)]
                return ""

            fabric = col("fabric_spec") or col("fabric")
            entry = {
                "model": token,
                "sheet": sheet,
                "line": normalize_line(col("line"), token),
                "background": sanitize(col("background"), 70),
                "region": sanitize(col("region"), 60),
                "temp": sanitize(col("temp"), 30),
                "fabric": sanitize(fabric, 50),
                "tier": infer_tier(fabric, sheet, token),
                "asin": (
                    asins[idx]
                    if idx < len(asins)
                    else (asins[0] if len(asins) == 1 else "")
                ),
            }
            rows.append(entry)

    for extra in EXTRA_ROWS:
        if extra["model"] in seen:
            # still apply line override on existing
            for r in rows:
                if r["model"] == extra["model"]:
                    r["line"] = LINE_OVERRIDE.get(extra["model"], r["line"])
                    if extra.get("background") and r["background"] in {"-", ""}:
                        r["background"] = extra["background"]
            continue
        seen.add(extra["model"])
        rows.append(dict(extra))

    priority = {
        "Pants_ripstop": 0,
        "Pants_LT": 1,
        "Shirts": 2,
        "FW_Jacket": 3,
        "Sapper": 4,
        "NEW_A+": 5,
    }
    rows.sort(key=lambda r: (priority.get(r["sheet"], 9), r["model"]))
    return rows


def render_table(rows: list[dict], limit: int = 120) -> str:
    ambiguous_n = sum(1 for r in rows if r["line"].startswith("확인필요"))
    out = [
        "# Model row index (structured)",
        "",
        "Use for model matching, Garment-TPO Gate, and scene brief. Prefer this over raw sheet scan.",
        "Line names normalized to Strategy v3.1 canon. See `data/CQR_LINEUP_V31_OVERLAY.md`.",
        "",
        "model | tier | line | temp | fabric | region | background | asin | sheet",
        "--- | --- | --- | --- | --- | --- | --- | --- | ---",
    ]
    for r in rows[:limit]:
        out.append(
            " | ".join(
                [
                    r["model"],
                    r["tier"],
                    r["line"],
                    r["temp"],
                    r["fabric"],
                    r["region"],
                    r["background"],
                    r["asin"],
                    r["sheet"],
                ]
            )
        )
    out.append("")
    out.append(
        f"Total rows parsed: {len(rows)}. Showing {min(limit, len(rows))}. "
        f"Ambiguous (확인필요): {ambiguous_n}."
    )
    return "\n".join(out)


def main() -> None:
    if not DEV_TXT.exists():
        OUT.write_text(
            "# Model row index\n\nMISSING cqr_development_direction.txt",
            encoding="utf-8",
        )
        print("Missing", DEV_TXT)
        return
    text = DEV_TXT.read_text(encoding="utf-8")
    rows = parse_dev(text)
    OUT.write_text(render_table(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to", OUT)
    amb = [r["model"] for r in rows if r["line"].startswith("확인필요")]
    if amb:
        print("Ambiguous:", ", ".join(amb))


if __name__ == "__main__":
    main()
