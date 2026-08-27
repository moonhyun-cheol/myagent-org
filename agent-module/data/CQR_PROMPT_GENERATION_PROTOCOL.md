# CQR Prompt Generation Protocol v2 — Dual Output + Shot DNA

Purpose: fix Imagen/MJ drift when **long bracket assembly is ignored**.
v1 (10-block assembly) is **documentation only**. v2 adds **Imagen Primary** — short, priority-ordered, what the image model actually reads.

---

## Why v1 still failed (QC diagnosis)

| Symptom | Root cause |
|---------|------------|
| gantry port, armory | free location words in brief/EN — whitelist not enforced early enough |
| EDC table flat lay | **not in whitelist AND not in ban list** — AI default tactical staging |
| golden hour stock | lighting preset too cinematic; Imagen weights mood over task |
| hood up bobblehead | hood rule buried in block 4 of 10 |
| CQR logo but fake scene | hero garment OK but **task = knolling not motion** |
| long EN ignored | Imagen reads **first ~200 words** — anatomy/location must be first |

**Conclusion:** one long assembled prompt is not enough. Need **Lock → Shot DNA → Pre-flight → Imagen Primary (+ Negative separate) → Full Assembly (archive)**.

---

## v2 method (MANDATORY for `.art` / `.img`)

### Per slot — 8 steps

| Step | Output | Rule |
|------|--------|------|
| 1 | Match + TPO + lane–garment + **actor lock** | global header |
| 2 | **Constraint Lock** | scale + **L-code** + **T-code** + **S-code** + bans |
| 3 | **Pre-flight ** | 8-item checklist — all before any EN |
| 4 | Korean fields | from locked codes only — no new nouns |
| 5 | ** Imagen Primary** | **150–220 words max** — user pastes THIS to Imagen |
| 6 | ** Imagen Negative** | separate block — never inline only |
| 7 | ** EN Full Assembly** | 10 bracket tags — archive / Midjourney / audit |
| 8 | **Brief sync** | compact brief must cite same L/T/S codes — no cinematic override |

**Imagen rule:** user generates from ** Imagen Primary** + ** Imagen Negative**. Full Assembly is not the default paste target.

---

## Step 2 — Constraint Lock Card (FIRST per slot)

```
 Constraint Lock
- Scale: mundane listing | subject __% | slot PT0_
- Actor: [ID] | H __cm W __kg | anti-frail ON | rotation: user-fixed / auto-rotated
- L-code: L-___-__ | place: [whitelist name only]
- T-code: T-___ | task: [verb + object + contact from T table]
- S-code: S-PT0_-__ | composition preset from S table
- Hero: [model + color + fabric] | lane: OK / flagged
- Banned: [explicit list for this slot]
```

---

## L-code — location whitelist (pick ONE)

Same as v1. **Never invent.** User says port/harbor/epic → **L-COV-02** dock edge.

Covert: L-COV-01 parking P2 · L-COV-02 inbound dock · L-COV-03 bay door · L-COV-04 transit · L-COV-05 rooftop
Liberator: L-LIB-01 desert bench · L-LIB-02 tire check yard · L-LIB-03 range berm path · L-LIB-04 tailgate pocket
Sapper: L-SAP-01 hangar floor chock · L-SAP-02 maint cart wheel · L-SAP-03 crane yard · L-SAP-04 robotics bench
Alpinist: L-ALP-01 switchback · L-ALP-02 bridge · L-ALP-03 boulder tread

---

## T-code — task whitelist (pick ONE — motion required)

**Forbidden T-codes (never default):** T-BAN-tablet-only · T-BAN-gear-knoll · T-BAN-walk-to-camera · T-BAN-look-at-layout

| Code | Task (must show motion + contact) |
|------|-------------------------------------|
| T-SCAN | scanning **pallet/crate label** — hand on **crate corner** |
| T-KNEEL | **kneeling tire tread check** — hand on **rubber tread** |
| T-POCKET | **pulling cargo pocket flap** open — fingers on **fabric flap** |
| T-STRIDE | **mid-stride** trail/yard walk — **pole plant** or **hand on rail** |
| T-CLIP | **clipping carabiner to belt loop** — hands on **hardware + loop** |
| T-CLIPBD | **clipboard tick mark** — hand on **board**, other on **chock/rail** |
| T-WHEEL | **wheel chock verify** — hand on **chock**, hangar floor |
| T-MACRO | **finger tracing ripstop grid** on **worn knee zone** (PT04 only) |

No **standing looking down at arranged gear on table**. No **EDC knolling flat lay**.

---

## S-code — composition preset (by slot)

| Code | Slot | Lock |
|------|------|------|
| S-PT01-A | PT01 | 35mm, subject 35%, 3/4 angle, mid-stride, not toward camera |
| S-PT02-A | PT02 | 85mm, 3.5m, subject 55%, profile 35°, gaze at task |
| S-PT02-B | PT02 | 85mm, kneel low angle, hands on task object |
| S-PT04-A | PT04 | 100mm macro, worn fabric zone, knee or pocket |
| S-AHERO-A | A+ HERO | 28mm, subject 35%, task in env, no skyline epic |

**Hood:** default **down** in S-code unless hero is hooded product → note thin fabric, normal head size.

---

## Staging cliché HARD BAN (add to every Negative)

Never generate unless user explicitly requests styled flat lay:

- EDC gear flat lay, knolling, gun cleaning mat, rubber tool mat layout
- stainless steel table with arranged flashlights and multi-tools
- standing at table looking down at gear lineup
- tactical product hero table, golden hour stock commercial perfection
- shade sail courtyard stock background (unless reference)
- perfect knolling symmetry, arranged gloves and flashlights

---

## Step 3 — Pre-flight checklist (output before EN)

```
 Pre-flight PT0_
- [ ] L-code whitelist only
- [ ] T-code motion + contact (not T-BAN-*)
- [ ] S-code composition (not walk-to-camera)
- [ ] Hood down unless flagged
- [ ] No staging cliché words in any field
- [ ] Hero model/color/fabric named
- [ ] **CQR actor ID + height/weight locked (anti-frail)**
- [ ] ≥3 grit nouns in environment
- [ ] Weapon-free + no epic infra
```

Any → rewrite Lock Card steps 2–5 before Imagen Primary.

---

## Step 5 — Imagen Primary (THE paste target)

**150–220 words. Priority order — first sentences matter most.**

Structure (single paragraph or 6 short lines, no bracket tags):

1. **Real photograph, not AI, not CGI** — documentary Amazon listing scale
2. **Anatomy + actor first:** CQR actor [ID] — [height] [weight], broad shoulders, thick muscular neck, athletic V-taper, age [band], [hair/beard/eyes from registry]; **not frail, not elderly, not narrow-shouldered**; normal head-to-body 1:7.5, hood down, visible knuckle creases
3. **Composition:** [S-code one line — lens, distance, angle, subject %]
4. **Location + grit:** [L-code place + 3 imperfection nouns]
5. **Task motion:** [T-code action — present continuous verb, contact point]
6. **Hero garment:** exact model color fabric zones readable
7. **Lighting:** overcast or soft side light 5500–5800K — **default NOT golden hour** unless Hunter/Rider lane
8. **Skin:** pores, matte, tendon tension — not airbrushed
9. **Weapon-free:** no firearms, no weapon racks, no armory
10. **Aspect ratio** last line

**Do not** start with mood poetry or brand slogans. **Do not** use words: armory, port, gantry, knolling, flat lay, gear table.

---

## Step 6 — Imagen Negative (separate block)

Always output standalone negative (user pastes to Negative field or appends):

```
plastic skin, airbrushed face, wax figure, bobblehead, oversized head, merged fingers,
frail, emaciated, gaunt, skinny, underweight, bird chest, pencil neck, narrow shoulders,
stooped posture, hunched elderly man, geriatric, senior citizen, old fragile man,
sunken cheeks, hollow temples, weak frame, generic uncanny white man,
AI generated, CGI, illustration, uncanny valley, golden hour stock photo perfection,
EDC flat lay, knolling, gear arranged on table, gun cleaning mat, rubber tool mat,
stainless steel gear table, standing looking at arranged tools, tactical armory,
weapon rack, firearms, rifles, guns, gantry crane, container terminal, port panorama,
walking toward camera, tablet only pose, hood up oversized head, blown out window,
sterile cleanroom, empty epic industrial void, mushy multi-tool, perfect symmetry
```

Add slot-specific bans from card.

---

## Step 7 — EN Full Assembly (archive — not default Imagen paste)

10 bracket tags for audit / Midjourney / Flux — same as v1, copied from Korean fields.
Label: ` EN Full Assembly (기록용 — Imagen은 Primary 사용)`.

---

## Lighting default change (v2)

| Lane | Default | Golden hour |
|------|---------|-------------|
| Covert, Liberator, Sapper, Alpinist | **overcast / soft side 5500–5800K** | default ban |
| Hunter, Rider | warm low sun OK | optional |
| All | documentary muted saturation | Instagram HDR |

Golden hour only when lane = Hunter/Rider **and** noted in Lock Card.

---

## `.art` turn discipline (token / drift control)

| Mode | Behavior |
|------|----------|
| Default `.art` | 4 slots — each slot: Lock → Pre-flight → Imagen Primary → Negative → Full Assembly |
| `.art 1slot` / `PT02만` | **one slot only** — complete Primary before next request |
| `프롬프트만` | Lock + Pre-flight + Primary + Negative — skip brief |
| After user uploads bad result | QC → rewrite **T-code or L-code** → new Primary only |

If output may truncate: drop Full Assembly first, **never** drop Imagen Primary or Negative.

---

## Brief sync rule

COMPACT brief and sections must cite **same L-code, T-code, S-code** as Lock Card.
Forbidden in brief: epic adjectives (epic, massive, cinematic port, armory, gear room) that contradict Lock.

---

## Reference override

Copy: grade, garment read, palette, subject %.
Replace: location → whitelist downgrade, task → T-code motion, lighting → documentary if reference is golden stock.

---

## Self-check before delivery

- [ ] Every slot has Imagen Primary under 220 words
- [ ] Every slot has separate Imagen Negative
- [ ] No T-BAN codes used
- [ ] No staging cliché words in Primary
- [ ] Full Assembly labeled as archive
