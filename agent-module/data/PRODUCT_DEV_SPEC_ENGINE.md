# Product Development Spec Engine

Purpose: recommend **concrete, spec-level** decisions for CQR new product development — pockets, waistband, colorways, hardware, construction — anchored to verified development notes and sibling models.

Purpose Above All: every spec choice must serve a task, not decoration.

## Product data source (not in git)

Structured indexes (`product_spec_index`, `model_catalog`, `model_row_index`, `color_code_index`, `po_color_index`, PR/PO indexes) are **generated from NAS** and served from **`product_data_base_url`** (see root `manifest.json`). They are written locally to `agent-module/data/` by `_local/info-update/update.py --only indexes` and pulled by the app at runtime — same pattern as `brand_manual_url`.

If an index file is missing locally, use brand/catalog markdown in git plus mark spec fields **확인 필요** until data sync completes.

## When to activate

- 신제품 / 신규모델 / 개발 / 스펙 / spec / tech pack / 도식화 / 기획안
- `.dev` command
- pocket / 주머니 / 허리 / waist / drawstring / 끈 / colorway / 컬러way / 플랩 / 지퍼
- "TLP126 개발 방향", "이 라인 신규 바지 스펙"

## Workflow

1. Clarify intent: **new model** / **refresh of existing** / **colorway-only extension** / **competitor-led spec**
2. Match anchor model from MODEL ROW INDEX + development-direction ISSUE rows
3. Run Garment-TPO Gate for line, tier, temp band
4. Compare 1–3 sibling models in same line (e.g. TLP125 vs TFP500 vs TLP760)
5. Output NEW_PRODUCT_DEV_SPEC_FORMAT — **every checklist field must be addressed** with Recommend / Alternative / Do-not / 확인 필요
6. Never invent PO-verified mm counts. Use verified ISSUE notes, sibling inference, or mark 확인 필요
7. If user supplied competitor ref or sketch, map features to CQR line grammar

## Verified CQR construction notes (from development direction)

Use as hard constraints when applicable:

- **Gusset:** 6cm unified (7cm deprecated)
- **Cargo inner bartack:** 2 added; pocket position micro-adjust (legacy cargo refresh)
- **Back pocket inner pocket:** do NOT add on rip flex variants — sweat complaint (2026-05-07 note)
- **Side seam:** vent perforation discussed for heat; confirm before spec lock
- **Mac pocket vs standard cargo:** mac cargo / mac pocket 1pc / basic cargo / breacher / captain variants exist in Liberator matrix
- **Knee pad pocket:** D3O P12 reviewed for TFP571/572; TLP760 knee pad deferred then required by phase — confirm per model
- **Gusset diamond:** maintain on legacy refresh paths
- **Heavy fabric + large pocket stack:** heat risk (헝리 원단 포켓 덥다) — reduce pocket volume or vent when fabric is dense
- **Fit blocks referenced:** Regular / Relaxed / Straight (Beyond-style refs in ripstop family)

## Pocket decision matrix (mandatory)

For **each proposed pocket**, output one row with all columns filled:

| Field | Must specify |
|-------|----------------|
| Pocket ID | P1, P2, … |
| Zone | left thigh / right thigh / hip / seat / front slash / back / chest / sleeve / calf |
| Side | left / right / bilateral / asymmetric |
| Type | cargo / mac / welt / slash / patch / jetted / hidden / phone / knee-pad insert |
| Closure | open / flap+snap / flap+velcro / coil zip #5 / #8 / magnet (avoid unless verified) |
| Flap shape | rectangular / angled / double-layer / none |
| Volume | flat / box pleat / accordion / expandable |
| Size target | W×D cm or S/M/L vs sibling |
| Vertical position | above knee / at knee line / below knee / belt-line |
| Opening direction | vertical / horizontal / angled |
| Bartack | count and corner positions |
| Symmetry rule | mirror / tool-side only / dominant-hand bias |
| Covert vs overt | low-signature vs readable tactical |
| Purpose | phone / glove / mag-shape utility / knee pad / EDC / general cargo |
| Recommend | primary spec |
| Alternative | one fallback |
| Do-not | explicit rejection with reason |
| Confidence | confirmed / inferred from sibling / 확인 필요 |

### Pocket count guidance by line (default starting point — override with user intent)

| Line | Typical total | Notes |
|------|---------------|-------|
| Covert | 4–6 low-profile | fewer visible cargo; hidden slash + minimal thigh |
| Liberator | 8–12 | cargo stack readable; mac pocket optional 1pc |
| Expedition-Alpinist | 6–8 | thigh cargo + hip + back; tool loops optional |
| Expedition-Hunter | 4–6 | chest/back focus on shirts; pant simpler |
| Sapper | 6–10 | tool pocket density; durability over fashion |

## Waistband & closure matrix (mandatory)

| Field | Must specify |
|-------|----------------|
| Rise | low / regular / mid / high |
| Waist construction | fixed / partial elastic back / full comfort flex |
| Belt loop count | exact count |
| Belt loop width | mm |
| Belt loop placement | even spacing; front center double or not |
| Drawstring | none / internal flat / external tubular |
| Drawstring count | 1 or 2 exit points |
| Drawstring diameter | mm or flat tape width mm |
| Drawstring exit | center front / side / inside waistband |
| Waist adjuster | none / side tab / elastic cinch |
| Fly | zip length cm approx / button count |
| Top closure | hook-bar + button / snap / velcro (work pant only if verified) |
| Recommend / Alternative / Do-not / Confidence | per field group |

## Colorway strategy matrix (mandatory)

| Field | Must specify |
|-------|----------------|
| Launch core colors | list codes + human names |
| Seasonal colors | list or "none at launch" |
| Color-specific TPO | per COLOR_CODE + development row when present |
| Spec same across colors? | yes / no — if no, list delta per color |
| Contrast elements | stitch / zip tape / grommet / label — same or diff per color |
| Listing hero color | which SKU leads thumbnail test |
| Avoid pairs | colors that duplicate existing live SKU cannibalization |
| Recommend / Alternative / Do-not / Confidence | |

Known development color-TPO hints (genericize in output):
- SGN → sage / green-zone motor pool, desert bench
- BLK → urban transit, covert station
- KHK → desert FOB warm side
- ONV → harbor, olive urban
- CHC → mountain FOB cool side

## Hardware & construction matrix

| Field | Must specify |
|-------|----------------|
| Main fabric | from 원단 row or confirmed user input |
| Fabric tier | L/M/W/C |
| Panel mix | body / gusset / knee / pocket fabric split |
| Gusset cm | default 6 unless verified exception |
| Knee articulation | none / dart / ripstop overlay / pad pocket |
| Seam type | flat / topstitch rows / double-needle |
| Zipper gauge | #5 / #8 per location |
| D-ring / carabiner loop | count and zone |
| Reinforcement | seat seam / pocket corner / knife clip point |

## Output quality rules

- No vague "enough pockets" — give **counts, zones, closure types**
- Every Recommend must cite **why** in one clause (task + line + sibling or ISSUE note)
- Include **최소 1 explicit Do-not** per major category (pocket / waist / color)
- If sibling model exists, include **Spec delta vs [sibling]** section
- End with prioritized **Sample request list** for factory (what to mock up first)

## NEW_PRODUCT_DEV_SPEC_FORMAT

Use emoji-led Korean sections in order:

- 개발 목적과 Purpose Above All
- 앵커 모델과 벤치마크 (sibling + confidence)
- Garment-TPO 잠금 (tier · temp · activity)
- 실루엣·핏·rise
- 주머니 스펙表 (full matrix — one block per pocket)
- 허리·끈·벨트루프·플라이
- 컬러way 전략表
- 원단·부자재·공정
- vs 기존 모델 차이 (delta table)
- 샘플 우선순위 (1st / 2nd mock)
- 확인 필요

Forbidden: generic advice like "cargo appropriate for tactical" without counts and closure types.

## Example density (structure only)

Bad: Liberator pant needs many cargo pockets, flap preferred.

Good: P1–P2 bilateral thigh cargo 18×20cm box pleat flap+snap angled; P3 right hip phone slash zip #5 vertical; P4 seat welt no inner pocket (sweat rule); total 8 pockets; vs TLP125 add mac pocket 1pc only on left thigh; belt loop 7×25mm; drawstring none (belt-led Liberator); core SGN+BLK launch, ONV phase 2; do-not back inner pocket on rip flex.
