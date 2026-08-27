# CQR Loadout System — Brand Manual (v3.1 / 260813)

> Source: CQR Internal Strategy v3.1 + Scene Manual loadout registry. Operational regex/line numbers live in scene manual; this embed defines **structure and intent** for briefs and `.art`.

## Design principle — loadout is not line-owned

Loadout = **mission type**, not line property. Mobile loadout is the same whether EXPEDITION or COVERT uses it. Gear carries *what mission relationship the person is in*, not line identity.

- **Global line-neutral IDs**: `LO-` + 3-letter mission character. No line prefix.
- Lines/categories **reference only**; definitions live in one registry.
- **Orthogonality**: scene selection and loadout selection can combine independently (future imagebuilder); today category still embeds loadout in scene.

## Eleven loadouts at a glance

| Global ID | Loadout | Axis | Sub-variants | Primary line refs | Alias |
|---|---|---|---|---|---|
| **LO-MOV** | mobile (이동) | field · mobility | single 100% | EXPEDITION lowland | G1 |
| **LO-OBS** | observation (관측) | field · recon | VR 45 / LS 25 / TR 15 / UR 15 | EXPEDITION midland | G2 |
| **LO-SIG** | signal (통신) | field · comms | SC + RD (RD-A/B/C/D) | EXPEDITION highland | G3 |
| **LO-CMD** | command (지휘) | decision · command | DA 28 / BO 38 / DI 34 × STATION·FIELD | COVERT STATION · LIBERATOR MODERN urban | — |
| **LO-CARE** | care (돌봄·동반) | companion · care | single ambient | EXPEDITION HUNTER flannel (in-season) | — |
| **LO-INS** | inspection (검증) | verify · oversee | INS-A / INS-C / INS-O | SAPPER pre-PAA | — |
| **LO-TRN** | training (단련·준비) | readiness | TRN-RUN / STN / GMS / SHT | tactical training activewear | — |
| **LO-HMNT** | hunt maintenance (사냥 정비) | sustain · ready | ARC / WFL / CMP / SCT / DOG / PAK / BOT | EXPEDITION HUNTER off-season warm layer | — |
| **LO-MTRB** | moto trailblaze (모토 개척) | pioneer · sustain | MNT / CMP / NAV / PAK | EXPEDITION RIDER moto | — |
| **LO-SR** | special reconnaissance (특수정찰) | infiltrate · observe · report | SR-MOV / SR-OBS / SR-SIG | LIBERATOR MODERN field | — |
| **LO-CR** | clandestine reconnaissance (은밀정찰) | recon · collect · deniable | CR-APP / CR-PRP / CR-MOV / CR-OBS | **LIBERATOR BLACK exclusive** | — |

> **v3.1:** eleven global IDs. LO-SR = MODERN field (gunshot = failure). LO-CR = BLACK exclusive exception to line-neutral rule. LO-HMNT = seasonal camp sustain. LO-MTRB = camp-anchor moto only.

Cross-line reference is allowed **except LO-CR**. New IDs (`LO-CMD` / `LO-CARE` / `LO-INS`) still carry **tier above execution**. LIBERATOR MODERN dual wing: **LO-CMD** (urban command) + **LO-SR** (field recon).

## Field trio (LO-MOV / LO-OBS / LO-SIG)

EXPEDITION-origin. One category adopts **one** of the three — **no mixing across the trio**. G1/G2/G3 remain **aliases** (60+ legacy categories keep G notation).

### LO-MOV — mobile · alias G1

**Axis**: field mobility / **Sub**: single, no branch (100%)

Lightest field loadout. Visual identity: **body-worn only, base assets ZERO** — person advances through terrain, never stationed.

- **Signature assets**: `MPU5 mesh network handset` + `wrist-mounted Garmin Foretrex tactical GPS` only.
- **Forbidden (all ZERO)**: optics (Vector, Raptar, Trionyx) / displays (Toughbook, rugged tablet) / Iridium puck / Pelican / Skydio UAV / portable SATCOM relay kit (4 types). No fixed-position gear.
- **Use**: lowland PAA Outdoor — deep forest, slot canyon, dune, etc. "First entrant (virgin terrain)" signature.

### LO-OBS — observation · alias G2

**Axis**: field recon / **Sub**: 4 variants (global standard distribution)

Stay and *watch*. Sub-variant follows observation tool type.

| sub | Name | % | Visual anchor |
|---|---|---:|---|
| **VR** | visual reconnaissance | 45 | Vectronix Vector 23 binoculars |
| **LS** | line-of-sight survey | 25 | Wilcox Raptar + carbon tabletop tripod + Pelican |
| **TR** | thermal reconnaissance | 15 | Pulsar Trionyx thermal binoculars |
| **UR** | UAV reconnaissance | 15 | Skydio X10 + matte black ground controller |

- **Common assist**: rugged tactical tablet (sub-specific rate) + MPU5 + Foretrex.
- **Tablet rates**: VR·UR **100%** (chest harness clip — ATAK terrain / UAV feed); LS·TR **50%** (Raptar·Trionyx already visual-dominant).
- **Forbidden (G3-only assets)**: Toughbook laptop 0 / portable SATCOM relay kit 4 types 0.
- **Use**: midland PAA Outdoor most / Urban Overwatch.

### LO-SIG — signal · alias G3

**Axis**: field comms / **Sub**: SC + RD always paired — **never use one alone**

Connect from a fixed point. Screen terminal (SC) and relay deployment (RD) operate as one mission.

| sub | Name | Visual anchor |
|---|---|---|
| **SC** | screen-heavy terminal | rugged Panasonic Toughbook laptop screen |
| **RD** | relay deployment | portable SATCOM·relay 4-type signature |

**RD internal distribution**:

| sub | Asset | % |
|---|---|---:|
| **RD-A** | compact portable parabolic SATCOM terminal | 30 |
| **RD-B** | portable flyaway parabolic mesh dish | 15 |
| **RD-C** | compact LEO phased-array flat-panel terminal | 30 |
| **RD-D** | portable mesh network tactical relay node | 25 |

- **Common assist**: Vector 23 (1 optic assist) + Pelican hard case (foam cutout visible) + MPU5 chest harness + Foretrex.
- **Forbidden (G2-only)**: rugged tactical tablet 0.
- **Use**: highland PAA Outdoor — summit comms post, desert-mountain ridge relay, volcano caldera rim comms, etc.

## LO-CMD — command loadout

**Axis**: decision · command / **Refs**: COVERT STATION (STATION) · LIBERATOR MODERN (FIELD)

Carries **decision-maker tier above execution**. Structure: **command mode (3)** × **environment (2)** — orthogonal.

### Shared identity (environment-agnostic)

- **Arms ZERO.** Authority via **spatial convergence on single person (P)** — everything converges on one decision point.
- Armed operators are *conceptual backdrop only* — not drawn (Principle 6: no personnel·carry description for extras).
- Gender casting = character module; STATION=female, FIELD=male per category character memo.

### Command modes (3 — same in STATION and FIELD)

| mode | Name | % | Relation | Spatial grammar |
|---|---|---:|---|---|
| **DA** | decide-alone | 28 | reads info alone, decides | display converges to P |
| **BO** | brief-out | 38 | issues deployment | open staging from P toward dais |
| **DI** | debrief-in | 34 | collects results | semicircle converging toward P |

### STATION sub-line (indoor · female)

**Line**: COVERT STATION — first COVERT split: STATION (indoor decision) / STREET (outdoor, WIP).

- **Identity**: urban-acquired intel brought to base for *analysis and self-directed operation decision*. Single tier **Mission Commander**.
- **Convergence**: display · seating · conference table.
- **Asset pool**: ruggedized secure laptop / tablet / target package folder / credential lanyard·badge (all generic — no real agency names·seals).
- **Scene mix (40-scene base)**: BO 15 / DI 14 / DA 11. Background = open hangar 20 + bright large conference room 20.

### FIELD sub-line (outdoor urban command post · male)

**Line**: LIBERATOR MODERN — **urban command wing** (field recon = **LO-SR**, not this pool). Direction: *active-duty credibility*. First [PAA] category: SWAT Field Command.

- **Identity**: on-scene incident commander — reads and controls deployed team, not the team itself. Deficit dimension = authority·command (executor → decision·control tier). Do not mix SR field assets (helmet/NVG/manpack/camo net) into CMD FIELD.
- **Convergence**: command vehicle rear command surface — MCV side awning/rear bay · BearCat rear bay/roof hatch · SUV tailgate · foldout command table — + perimeter staging (police tape·cone·staged patrol vehicles).
- **Asset pool**: **generic ruggedized command laptop** (floor plan·perimeter map·structure schematic·AO overlay) / handheld radio / folding command table or matte black Pelican hard case surface.
- **Key guardrail**: arms ZERO. **Ban field asset vocabulary** — Toughbook, rugged tactical tablet, ATAK, etc. FIELD display = generic command laptop only. Prevents command tier sliding into field operator.
- **「Incident scale = commander authority」**: authority scales with incident gravity. Background = high-density urban core where national-scale terror/disaster could occur — low-density reads as neighborhood incident, weakens authority.

### Asset pool separation

LO-CMD asset pool (STATION·FIELD generic laptop) is **fully separate** from G2 rugged tablet · G3 Toughbook field pools — no cross-detection.

## LO-CARE — care loadout

**Axis**: companion · care / **Ref**: EXPEDITION HUNTER flannel (The Grounded Guardian)

**Only loadout intentionally not defined by gear** — lightest by design.

### Philosophy — lightness is the signal

Other five loadouts define via gear; LO-CARE "care" rides mostly on **action·attitude·gaze** (delegated to §0-11-5 leadership quadrant — do not redefine here). Heavy gear reads as operator/mission and contradicts force-submerged concept — **lightness itself is signature**.

### Signature asset — one bird dog

- **Bird dog** (Brittany·setter·springer·pointer) — carries warmth (safe man) + competence (working-dog ease) + **hunting trace** (anti-Tourist).
- Dog scene auto-satisfies "minimum 1 hunting trace" — no extra hunt props required.

### Relationship prop structure (imagebuilder)

Imagebuilder synthesizes *man (wearer) only* in character prompt:
- **Man (subject)**: gear·CARE POSE = character prompt — omit from scene text.
- **Relationship props (dog·woman)**: background elements in scene; **both orient toward synthesized man**. Woman gaze = eye-level·active (equal), never `looking up at` (subordinate) — dog may look up.

### Forbidden assets

Inherit §0-11-3 (uniform·insignia·rescue scene ban) + overt firearms·tactical structure kit·plate carrier·dramatic rescue staging. Hunt weapons only as cased *context trace*, never foreground.

## LO-INS — inspection loadout

**Axis**: verify · oversee / **Ref**: SAPPER all pre-PAA categories

SAPPER's first proper loadout. Carries §0-8 self-image (field mechanic → Lead Engineer / Chief Inspector / Production Superintendent **oversee tier**; deficit = authority·recognition).

### Core — axis is action, not distance

Oversee tier splits by *action·tool type*, not distance from airframe — **inspect/verify**, not assemble. Diagnostic device must be **at arm's reach** on component — no distant bench·test cart (prevents airframe receding to background).

### Device pool (5 — digital only)

① rugged maintenance tablet ② ruggedized diagnostic laptop ③ handheld digital diagnostic unit ④ portable maintenance-aid terminal ⑤ slim digital readout screen (articulated arm).

**Physical gauges·manual aids excluded** — feeler/dial/gap-flush/coating gauge·borescope·leak rig·multimeter·inspection lamp·mirror·paper work card·physical QA stamp read as legacy field-worker tier. Digital devices carry high-tech + oversee simultaneously.

**Screen content** branches by component (engine health-monitoring / sensor·optical BIT / harness continuity / actuator·hydraulic / structural fit-check / avionics display BIT, etc.).

### Sub-variants (environment differs; device·action shared)

| sub | Environment | Categories |
|---|---|---|
| **INS-A** | aviation · natural-light hangar | F-22/F-35 · military drone · large rotorcraft (land hangar / ship bay / naval airbase) |
| **INS-C** | space · cleanroom | satellite · rocket/launch vehicle · planetary surface unit · spacecraft/station module · robot (cathedral-scale cleanroom) |
| **INS-O** | launch facility · outdoor | launch facility — outdoor GSE (swing arm·umbilical·deflector/trench·clamp) at arm's reach; separate test bench deprecated |

- **INS-A**: aviation light geometry·joined components·clean vocabulary + 1 device. Large rotorcraft includes rotorhead·swashplate·transmission·tail rotor·tilting nacelle·BFWS etc. all in joined state.
- **INS-C**: cleanroom·multi-directional light·white epoxy deck + 1 device (integration/BIT/telemetry screen).
- **INS-O**: inherits SAPPER §0-8 — not "assembler at launch pad" but *GSE·pad system integration verified via digital device* tier.

### Non-PAA exclusion

Military aviation-maintenance · energy/infrastructure · defense-equipment dev/maintenance lack §0-8 gap — LO-INS non-binding.

## LO-TRN — training loadout (v2.7)

**Axis**: readiness · training / **Ref**: tactical training categories (activewear)

Only loadout for **between missions** readiness (except LO-HMNT seasonal gear/camp prep). Gap: "man exercising → operator training with standard."

### Core (all variants)

Pen + waterproof log (sleeve pen-slot hero detail) + watch/stopwatch.

### Sub-branches

| Branch | Grammar | Notes |
|---|---|---|
| **TRN-RUN** | Course — fixed movement, load variable | RUN-BW / RUN-VST / RUN-RCK / RUN-SB |
| **TRN-STN** | Station — apparatus owns scene | CLIMB / CARRY / CRAWL / AQ |
| **TRN-GMS** | Tactical games lanes | competitive obstacle·load stages |
| **TRN-SHT** | Range / stage shooting pose layer | **only** carve-out where firearm pose may appear — still not free weapon porn |

### Guards

- **Indoor scenes: 0** across TRN (except explicitly documented exceptions)
- **Silent gear ban:** earbuds, armband, neon running accessories, bottle belt
- **Field pool ban:** optics/MPU5/Toughbook/SATCOM — training is not field LO
- **VST worn rule:** WORN in ≤1 of 4 cuts
- **QC question:** "Does this person know their split time?" — YES = training; NO = jogging

## LO-HMNT — hunt maintenance loadout (v2.6)

**Axis**: sustain · ready / **Ref**: EXPEDITION HUNTER off-season, warm layers, winter fleece

Converts "man at cabin" into **mission**: keep gear and camp alive across seasons — not leisure rest.

### Core grammar

- **Mid-repair tense**: taken apart, laid out, airing, door ajar — just stepped back from work
- **Structure anchor only** — cabin, porch, gear shed, tailgate. **No field entry**
- Body minimal; tools staged on bench/tailgate — not fistfuls of clutter
- Season: hard frost or thin first snow; deep snow 0; cold+bright light (not gloomy dusk)

### Subs (pick one narrative)

| sub | Story |
|---|---|
| ARC | Archery maintenance (replaces gun-cleaning story) |
| WFL | Waterfowl gear reinhabit next season |
| CMP | Cabin/wood/chimney sustain |
| SCT | Scout prep (optics/map/log — prepare, don't execute recon) |
| DOG | Off-duty dog care — colleague gaze same direction |
| PAK | Pack/clothing repair (repair-not-replace) |
| BOT | Boat/canoe shore maintenance |

### Weapon policy

- **Firearms = total 0** (body + cleaning kit props that summon guns)
- **Bow** = staged open-case / wall-rack OK · **no** hand hold, draw, broadheads, aiming

### Forbidden

Tactical operator kit, glamping, night/dusk/gloomy vocab, deep snow, meat processing, digital OBS terminals (paper log OK).

## LO-MTRB — moto trailblaze loadout (v2.7)

**Axis**: pioneer · sustain / **Ref**: EXPEDITION RIDER moto

First **motorcycle asset** loadout. Trailblazer: first to prove a route for those who follow. Rider gap made concrete as pathfinder.

### Core grammar

- **Camp-anchor mandatory** — product (e.g. hoodie) is not PPE: **no riding/action hero**
- Bike always side-stand — "ride is over"
- Every camp item must plausibly have arrived on that ADV bike (no car-camp scale)
- Light: sunset / late afternoon / early morning only — no night/overcast

### Subs

| sub | Focus |
|---|---|
| MNT | Field maintenance (tool roll, chain lube, pump) |
| CMP | Camp fire/cook (stone ring, pot, 1-person tent) — min 1 camp-life trace |
| NAV | Map + compact GPS + binoculars + satellite messenger puck (not SOF radio tree) |
| PAK | Pack/unpack rhythm on bike soft bags |

### Bike constants

Plain white ADV tank (solo 100%); dual rider scene may use factory livery; soft side bags + cinch drybag; baked mud waterline weathering OK.

### Forbidden

Riding-context scenes, glamping, car-camping scale, SOF comms register (MPU5 chest), night/overcast.

## LO-SR — special reconnaissance loadout (v3.1)

**Axis**: infiltrate · observe · report / **Ref**: LIBERATOR MODERN field

10th registry ID. Active-duty SOF **non-combat** mission: infiltrate → observe → report. Gunshot = failure — firearms absence is doctrine, not censorship.

### Philosophy

- Defense = remaining unseen, not armor. Pack+belt kit; **no plate carrier / chest rig** so the hero garment stays the outer layer.
- Occupation is proven by **asset pool**, not gunfight. QC: *Could this kit belong to another job?* — must be NO.

### Subs

| sub | Scene grammar | Product proof |
|---|---|---|
| **SR-MOV** | Short halt — person moves; scene holds testimony assets (staged patrol pack + map/compass / EUD+paper map / compact binos). Closed forest vs open ridge. Hiking vocab 0 | Mobility · Durability |
| **SR-OBS** | Camo net + spotting-scope tripod. **Tripod height sets pose**: chest=sit (body plate open to camera) / mid=knee / low+prone mat=prone proof cut (elbow pads). Optional paper log+EUD; folding recon quadcopter on sit axis only | Reinforcement (elbow/knee) · Access (arm-pocket draw) |
| **SR-SIG** | Ground tarp + field manpack radio + wire/directional antenna + signal log. Satellite puck ≤1. **Comms firewall:** manpack/antenna = SIG only — 0 in MOV/OBS | Capacity |

### Constants (all SR scenes)

1. Firearms and summoning props 0 (mag, holster, gun case, cleaning kit)
2. PC / chest rig 0
3. Mission anchor: high-cut helmet + NVG **staged on pack** (worn/handheld NVG 0 — worn = "in the op" tense)
4. Camo net = environment OK; face paint 0
5. Night 0. Cool autumn = hoodie alibi. Empty velcro panels
6. Era-neutral classic silhouettes (archive-depth naming — do not invent unseen "latest" kit)

## LO-CR — clandestine reconnaissance loadout (v3.1)

**Axis**: recon · collect · deniable / **Ref**: LIBERATOR BLACK field — **exclusive**

11th registry ID. Forest BLACK: approach by civilian vehicle → paper-map prep → pathless walk → distant observe. Urban Overwatch is city BLACK; LO-CR is **forest BLACK**.

### Why exclusive

Assets encode deniability (civilian SUV, target photos, Glock holster, **no** helmet/NVG/camo net/manpack). One military asset collapses MODERN/BLACK. Other lines must not reference LO-CR.

### vs LO-SR

| | LO-SR (MODERN) | LO-CR (BLACK) |
|---|---|---|
| Mission owner | Army / active SR team | None — deniable |
| Kit | Helmet+NVG on pack, camo net, manpack, obs log | Civilian SUV, paper map, target photo, compact binos |
| Weapons | Firearms 0 (gunshot = failure) | Glock pose-layer holster only; C-column 0; grip 0 |
| Target | Terrain recon (no facility) | Enemy facility — **never rendered** |
| Season | Cool autumn | Early-winter threshold |
| MOV | Short halt only | MOV-T (passing) primary + MOV-H (halt) secondary |

### Subs

| sub | Grammar |
|---|---|
| **CR-APP** | Weathered SUV at forest-edge track — **just dismounted** (tailgate + civilian daypack). No return/boarding/in-cabin cuts. Headlights off |
| **CR-PRP** | Hood/tailgate command surface — paper topo (grease-pencil route) + unnamed target photos + compact binos. **No EUD/tablet** — paper map = deniable code |
| **CR-MOV** | Pathless; `undisturbed frost ahead` mandatory. T (passing terrain owns scene, staged assets 0) primary / H (short halt, staged daypack+binos) secondary. Trail vocab 0 |
| **CR-OBS** | One compact binocular. No camo net / spotting scope / tripod / obs log. Sit primary; prone 0 |

### Constants

1. C-column firearms 0 including PRP table
2. Military assets 0 (helmet, NVG, camo net, manpack, antenna, obs log, EUD, tripod, scope)
3. Facility never shown (do not negate-name it — omission only)
4. Vehicle = APP/PRP only
5. PC/chest rig 0 · logo/badge/patch 0 · plate vocab 0 · night/sunset 0 · deep snow 0 (patchy shade snow OK)

## Operating policy

### Explicit exception (LO-CR)

LO-CR is **not** line-neutral. LIBERATOR BLACK only. Do not let COVERT / MODERN / EXPEDITION borrow CR assets (Glock, civilian infiltration SUV, unnamed target photos as primary kit).

### Gradual transition (G → LO)

Legacy G1/G2/G3 categories (~60 EXPEDITION) **keep G notation in body text**. Registry provides alias mapping only — no bulk string replace. **New categories write global `LO-` IDs only.** Full G→LO migration = separate cycle (regex·changelog impact).

### Future — orthogonal combination

Loadout as line-neutral global ID enables future "scene + loadout" orthogonal picks. Today: category embeds loadout in scene. Orthogonal combo = imagebuilder expansion backlog.

## Line ↔ loadout reference (summary)

| Line / sub-line | Loadout | Tier |
|---|---|---|
| EXPEDITION lowland | LO-MOV (G1) | execution — mobility |
| EXPEDITION midland | LO-OBS (G2) | execution — recon |
| EXPEDITION highland | LO-SIG (G3) | execution — comms |
| EXPEDITION HUNTER flannel (in-season companion) | LO-CARE | companion — care |
| EXPEDITION HUNTER off-season / warm layer | LO-HMNT | sustain — camp·gear cycle |
| EXPEDITION RIDER moto | LO-MTRB | pioneer — trailblaze at camp |
| COVERT STATION | LO-CMD (STATION) | decision — command |
| LIBERATOR MODERN urban command | LO-CMD (FIELD) | decision — command |
| LIBERATOR MODERN field | LO-SR (MOV/OBS/SIG) | execution — special recon |
| LIBERATOR BLACK field | LO-CR (APP/PRP/MOV/OBS) | deniable recon — **exclusive** |
| SAPPER pre-PAA | LO-INS (INS-A/C/O) | verify — recognition |
| Tactical training | LO-TRN (RUN/STN/GMS/SHT) | readiness — between missions |

## Brief and `.art` application rules

When writing 로드아웃과 장비 or slot props:

1. Resolve loadout ID from matched category/line (G alias OK for legacy rows).
2. Apply **only** signature + allowed assist assets for that ID and sub-variant.
3. Enforce **forbidden cross-pool** assets (MOV zero optics/displays; OBS zero Toughbook/SATCOM; SIG zero tablet; CMD FIELD zero field vocab; CARE zero heavy tactical; INS digital-only at arm's reach).
4. For LO-SIG: always pair SC + RD — never SC-only or RD-only.
5. For LO-CMD: state mode (DA/BO/DI) + environment (STATION/FIELD); arms ZERO; spatial convergence grammar.
6. For LO-CARE: bird dog as scene background prop; man gear minimal; woman/dog gaze rules.
7. For LO-INS: pick INS-A/C/O from environment; one digital device touching component; no physical gauges.
8. For LO-TRN: activewear; pen+log+watch; no field pools; indoor 0; training-not-jogging QC.
9. For LO-HMNT: structure camp only; mid-repair tense; firearms 0; bow staged-only; no leisure rest.
10. For LO-MTRB: camp-anchor + side-stand bike; no riding; gear must fit bike; no glamping/SOF radio.
11. For LO-SR: firearms 0; helmet+NVG staged on pack; empty velcro; SIG comms firewall; tripod height sets OBS pose; no PC/chest rig.
12. For LO-CR: BLACK only; C-column firearms 0 (holster pose only); no SR military kit; vehicle APP/PRP only; pathless frost; facility never rendered.
13. Do not invent loadout assets outside registry. Mark unmapped category under 확인 필요.
