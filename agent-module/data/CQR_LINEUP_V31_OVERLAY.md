# CQR Lineup Overlay — Strategy v3.1 (2026-08-13)

> Operational map for CONCEPT_RA / A+ / `.dev`. Does **not** replace NAS `00_NEW_상품라인업.xlsx`.  
> Source of truth for philosophy: `CQR_INTERNAL_STRATEGY_v3.1.md`.  
> Applied into `model_row_index.txt` via `prompt_concept/scripts/build_model_rows.py`.

## Line name canon (use these strings)

| Canon | Accept aliases |
|---|---|
| Liberator-Legacy | Lib-Legacy, Liberator - Legacy, Lib - Legacy |
| Liberator-Modern | Lib-Modern, Liberator - Modern, Lib |
| Liberator-Black | Lib-Black, Liberator - Black |
| Covert | Covert |
| Expedition-Alpinist | Exp-Alpinist, Expedition-Alpinist / hunting *(split if hunting-only)* |
| Expedition-Rider | Exp-Rider |
| Expedition-Hunter | Exp-Hunter |
| Sapper | Sapper |

Never leave line as fabric name (`나일론겹바지`, `립스탑겹바지`) or bare `라인`.

## Default loadout by sub-line (brief / 🎒)

| Sub-line | Default LO | Notes |
|---|---|---|
| Liberator-Legacy | LO-TRN or LO-MOV | Mix-match / Freeform → TRN; cargo field → MOV |
| Liberator-Modern field | **LO-SR** | Empty velcro; firearms 0 |
| Liberator-Modern urban command | LO-CMD FIELD | Generic command laptop only |
| Liberator-Black field | **LO-CR** | BLACK exclusive |
| Covert street | LO-MOV / LO-OBS | 100% civilian; no 요원/스파이 copy |
| Covert STATION | LO-CMD STATION | Decision room |
| Expedition-Alpinist | LO-MOV / LO-OBS / LO-SIG | Functional gap TBD — do not invent |
| Expedition-Rider | **LO-MTRB** | Camp-anchor only |
| Expedition-Hunter in-season | LO-CARE | Bird dog ambient |
| Expedition-Hunter off-season / warm | **LO-HMNT** | Cabin sustain, not leisure |
| Sapper | LO-INS | Oversee digital only |

## A+ queue — new / priority SKUs (2026-08~09)

| Model | Canon line | Loadout | Status | Note |
|---|---|---|---|---|
| **WHP830** | Expedition-Alpinist | LO-MOV | **NEW** | Women thermal pant · `COLD WIND. FEARLESS` |
| **HOH321** | Expedition-Hunter | LO-HMNT | **NEW** | LT fleece Rover |
| **HOH322** | Expedition-Hunter | LO-HMNT | **NEW** | LT fleece Falcon |
| **TOS120** | Liberator-Modern | LO-TRN | training 전환 | `GO HARDER` — not TOS230 slogan |
| **TOS121** | Liberator-Modern | LO-TRN | training 전환 | pair with 120 |
| **TOS130** | Liberator-Modern | LO-SR | A+ | mesh / field shirt |
| **TOS230** | Liberator-Modern | LO-SR | A+ | `ARMOR BREATHES` |
| **TOS612** | Liberator-Modern | LO-SR | 컬추 | combat shirt · color only OK |
| **HKZ305** | Covert | LO-MOV | 3COLOR | APEX — keep separate from HKZ204 grid story |
| **HKZ204** | Covert | LO-MOV | A+ | RAVEN grid · not APEX copy |
| **WFP611** | Liberator-Modern | LO-SR | 컬추 | VANGUARD |
| **HOK909** | Expedition-Rider | LO-MTRB | A+ | camp-anchor moto |
| **HLP900** | Expedition-Alpinist | LO-MOV | A+ | winter warmth · was fabric-as-line |
| **HLP910** | Expedition-Alpinist | LO-MOV | A+ | Kodiak |
| **HLP905** | Expedition-Alpinist | LO-MOV | A+ | with 920 unit |
| **HLP920** | Expedition-Alpinist | LO-MOV | A+ | |
| **HLP831** | Expedition-Alpinist | LO-MOV | 컬추 | Teton |
| **HLP832** | Expedition-Alpinist | LO-MOV | 컬추 | |
| **TXP441** | Expedition-Alpinist | LO-MOV | 재촬영 | Advance Off-Trail |
| **TXP406** | Covert | LO-MOV | 재촬영 | Ridgeline Ranger |
| **HKJ001** | Liberator-Black | LO-CR | YKK 재촬영 | 확인 필요 if urban-only |
| **HKJ003** | Liberator-Black | LO-CR | YKK 재촬영 | pair 001 |
| **TSP600/620** | Covert | LO-MOV | shorts | urban utility |
| **TSP640/641** | Expedition-Alpinist | LO-MOV | shorts | hiking cargo |
| **TXS002/201/204/303/803/804/903** | Covert | LO-MOV | shorts | casual utility |
| **TXS101** | Expedition-Alpinist | LO-MOV | shorts | hiking |

## Ambiguous — leave 확인 필요 until owner picks

| Model | Was | Problem | Suggested ask |
|---|---|---|---|
| **TLP002** | Liberator - | empty sub-line | Legacy vs Modern? |
| **TLP731** | Black/Modern | dual tag illegal in v3.1 | Black (zip transform) or Modern (SR)? |
| **TXP202** | 라인 | blank | Alpinist vs Covert? |
| **TXP203** | Alpinist / hunting | two lines | Alpinist OR Hunter — not both |
| **TOK001** | Lib + Rider BG | line/scene conflict | Liberator-Modern field or Rider? |
| **HLP010/011/200/201/833/999** | fabric-as-line | winter pant family | Confirm Alpinist vs Black warmth lane |
| **HKZ303** | Lib-Legacy + Hunter BG | scene vs line | Legacy freeform or Hunter LO-HMNT? |

## Copy / scene leaks to ignore in NAS extract

When `cqr_development_direction.txt` still says these, **do not copy into briefs**:

- 교관 / instructor → use active-duty SOF / LO-SR or LO-CMD
- 요원 / 스파이 / CSI → Covert = urban observer only
- 홀스터 as hero prop → ban except LO-CR pose-layer / TRN-SHT carve-out
- smiling hiker / leisure for Expedition

## Rebuild

```powershell
cd prompt_concept
python scripts/build_model_rows.py
python scripts/build_local_bundle.py
# CQR_PA:
npm run sync:skills
```
