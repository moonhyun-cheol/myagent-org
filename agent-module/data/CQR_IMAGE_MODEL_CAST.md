# CQR Image Model Cast Registry (260702)

Purpose: lock **CQR brand actor IDs** (Mads, Ryan, Sam, Sven, Tyler, Viggo, Carter, David, Erik, Jaxon, Logan) so briefs and `.art` prompts stop drifting to **frail, stooped, elderly, narrow-shouldered generic white men**.

Source: NAS `Al_Image_Prompt_Builder/Model` reference sheets (height/weight banners where present; Tyler spec card; head/body reference reads). **Not** celebrity likeness — generic mission persona only in EN output.

---

## Mandatory workflow

Run **after** product MODEL ROW match + Garment-TPO Gate, **before** brief body or any EN prompt.

1. **Pick one CQR actor ID**
 - **User names actor** (Mads, Ryan, …) → lock that ID — no rotation.
 - **No user pick** → **ACTOR ROTATION** (below): lane **candidate pool** + session ledger — **never** auto-default Ryan every turn.
2. Copy **height · weight · build · age band · hair · beard · eyes** from registry row — never improvise "average man" or "tactical model".
3. ** 주체 프로필** (FULL) and ** 피사체·포즈** / **Imagen Primary anatomy line** must cite: `CQR actor: [ID] · [height] · [weight] · [build keyword]`.
4. ** Constraint Lock** add row: `Actor: [ID] | H/W locked | anti-frail ON | rotation: user-fixed / auto-rotated`.
5. **Imagen Primary** — anatomy in **sentence 2** (after "real photograph"): height, weight, broad shoulders, thick neck, V-taper, age band.
6. **Imagen Negative** — always append **Anti-frail block** (below).
7. **Same `.art` set / same turn** — one actor ID locked across **all slots** (PT01→PT04). Rotation applies **across turns**, not within one prompt set.

**Forbidden defaults (hard ban):**
- generic white man, ordinary guy, passerby build, catalog mannequin
- **same actor every turn when user did not specify** — Ryan / Erik / Sven on repeat without user ask
- elderly, geriatric, senior citizen, old man, retirement age
- frail, emaciated, gaunt, skinny, underweight, bird chest, pencil neck, sunken cheeks
- stooped posture, hunched, slumped shoulders, narrow shoulders, small head on thin neck
- defaulting to 60+ or "weathered grandfather" when actor row says fit 35–50

---

## ACTOR ROTATION (when user does NOT name an actor)

**Goal:** spread the 11 NAS actors — **no duplicate fatigue** across chat turns.

### Session actor ledger

- Maintain mental ledger of **CQR actor IDs already used as male hero** in **this chat**.
- **Before each new brief or `.art` turn**, exclude ledger IDs from the lane pool.
- After picking, **append** chosen ID to ledger.
- **Re-ask** same SKU / same concept / same model code → **must** pick a **different** pool member than last hero for that SKU when any remain.
- If pool fully blocked by ledger → drop **oldest** ledger entry for that lane only, then pick again (full 11-cycle before repeat).

### Pick order (no user actor name)

1. Resolve **lane** from matched MODEL ROW (`line` / background type).
2. Open **lane candidate pool** (table below) — not a single default face.
3. Remove ledger-blocked IDs from pool.
4. Among survivors, pick **deterministic spread**: sort pool alphabetically → index = `(hash(model_code) + turn_ordinal) mod pool_size` — or simply **next pool member after last used for this lane** if hash unavailable.
5. Never pick **global Ryan fallback** unless Liberator pool exhausted and user insists no rotation (should not happen).

### Lane candidate pools (rotate — do not freeze on first name)

| World lane / loadout FIELD male | Candidate pool (rotate) |
|--------------------------------|---------------------------|
| Liberator · TACTICAL URBAN | Ryan · Viggo · Jaxon · David · Tyler |
| Liberator MODERN · LO-CMD FIELD | Jaxon · Viggo · Ryan · David |
| Covert | Carter · Tyler · David |
| Sapper | Erik · Carter · David · Jaxon |
| Expedition-Alpinist | Sven · Mads · Ryan |
| Expedition-Hunter | Sam · Erik · Logan |
| Expedition-Rider | Logan · Tyler · Ryan |
| Lane unknown / mixed | Mads · Ryan · Sam · Sven · Tyler · Viggo · Carter · David · Erik · Jaxon · Logan — full roster minus ledger |

**Hair/build spread within pool:** prefer alternating **blond family** (Sven, Viggo, Mads) vs **dark brown** (Ryan, Carter, David, Erik) vs **salt-pepper mature** (Sam, Jaxon, Erik) when two turns would otherwise look identical.

User says `Tyler` / `Mads` etc. → **skip rotation**; lock user ID immediately.

---

```
frail, emaciated, gaunt, skinny, underweight, bird chest, pencil neck, narrow shoulders,
stooped posture, hunched elderly man, geriatric, senior citizen, old fragile man,
sunken cheeks, hollow temples, weak frame, petite male, small stature man,
generic uncanny catalog model, fashion mannequin, wax figure elderly
```

---

## Anti-frail EN block (append to every Negative)

## Actor registry (11)

### Ryan — Liberator pool / athletic baseline
| Field | Spec |
|-------|------|
| Height / weight | **185 cm · 88 kg** |
| Age band | 35–42 |
| Build | athletic muscular, broad shoulders, V-taper, thick neck, long-leg proportion |
| Hair | short textured brown, styled up/back |
| Beard | short full beard, salt-and-pepper on chin |
| Eyes | light blue or green |
| Skin | fair, light crow's feet, fit not elderly |
| EN anatomy seed | fit Caucasian man, late 30s, 185cm 88kg, broad-shouldered athletic build, thick muscular neck, short textured brown hair, groomed salt-pepper beard, light blue eyes |

### Mads — peak athletic / Nordic rugged
| Field | Spec |
|-------|------|
| Height / weight | **188 cm · 87 kg** |
| Age band | 42–50 (mature fit, not old) |
| Build | powerfully athletic, visible muscle definition, broad shoulders, six-pack tier when shirtless ref |
| Hair | medium-length light brown/blonde, swept back |
| Beard | full short beard, brown with grey |
| Eyes | light blue |
| Skin | sun-weathered, freckles, **fit outdoorsman not frail elder** |
| EN anatomy seed | rugged Nordic-leaning man, mid 40s, 188cm 87kg, powerfully built athletic frame, broad shoulders thick neck, light brown hair swept back, groomed short beard with grey, piercing blue eyes, weathered but strong skin |

### Sven — Alpinist Nordic
| Field | Spec |
|-------|------|
| Height / weight | **187 cm · 84 kg** |
| Age band | 38–45 |
| Build | lean-athletic, broad shoulders, straight posture |
| Hair | short wavy strawberry-blond / light blond |
| Beard | light stubble |
| Eyes | light blue |
| Skin | fair, sun lines, **sturdy not thin** |
| EN anatomy seed | fit Caucasian man, early 40s, 187cm 84kg, lean athletic build broad shoulders, short wavy blond hair, light stubble, blue eyes, upright posture |

### Tyler — NA tactical (mid height, still muscular)
| Field | Spec |
|-------|------|
| Region | North America (US/Canada) |
| Height / weight | **178–183 cm · 75–82 kg** |
| Chest / waist | 40–42 in chest · 32–34 in waist |
| Age band | 35–42 |
| Build | athletic V-taper, muscular not bulky, **mid height ≠ small/frail** |
| Hair | short-medium brown, volume back |
| Beard | light stubble |
| Eyes | blue / green-blue |
| Shirt | M–L |
| EN anatomy seed | fit North American man, late 30s, 180cm 78kg, athletic V-taper 40in chest 33in waist, broad shoulders thick neck, short brown hair styled back, blue-green eyes, groomed stubble, rugged capable build |

### Viggo — tallest tactical presence
| Field | Spec |
|-------|------|
| Height / weight | **189 cm · 88 kg** |
| Age band | 36–44 |
| Build | muscular athletic, military-attention posture, broad shoulders |
| Hair | short sandy blonde, textured top |
| Beard | heavy short stubble |
| Eyes | blue |
| Skin | outdoor weathered, **battle-hardened fit** |
| EN anatomy seed | fit Caucasian man, late 30s, 189cm 88kg, tall muscular athletic build, broad shoulders thick neck, short sandy blonde hair, blue eyes, heavy stubble, rugged outdoor skin |

### David — polished operator
| Field | Spec |
|-------|------|
| Height / weight | **187 cm · 85 kg** |
| Age band | 38–44 |
| Build | athletic V-taper, tactical polo fit, square jaw |
| Hair | short dark brown, textured forward |
| Beard | salt-pepper stubble |
| Eyes | blue-grey |
| Skin | natural texture, early 40s **prime not elderly** |
| EN anatomy seed | fit Caucasian man, early 40s, 187cm 85kg, athletic V-taper broad shoulders, short dark brown hair, salt-pepper stubble, chiseled jaw thick neck, blue-grey eyes |

### Erik — Sapper / field-jacket rugged
| Field | Spec |
|-------|------|
| Height / weight | **186 cm · 85 kg** |
| Age band | 42–50 |
| Build | sturdy athletic, broad shoulders, work-ready |
| Hair | short brown, grey at temples |
| Beard | salt-pepper short beard |
| Eyes | light blue |
| Skin | weathered, stoic — **strong frame not wasted** |
| EN anatomy seed | rugged Caucasian man, late 40s, 186cm 85kg, sturdy athletic build broad shoulders thick neck, short brown hair grey temples, salt-pepper beard, light blue eyes, weathered strong face |

### Jaxon — CMD FIELD / tactical minimal
| Field | Spec |
|-------|------|
| Height / weight | **186 cm · 84 kg** |
| Age band | 42–50 |
| Build | muscular lean, visible arm definition, command posture |
| Hair | short salt-pepper, slicked back |
| Beard | short salt-pepper stubble |
| Eyes | light blue/grey |
| Skin | mature firm — **commanding not frail** |
| EN anatomy seed | fit Caucasian man, late 40s, 186cm 84kg, muscular athletic build broad shoulders, salt-pepper hair slicked back, short stubble, strong jaw thick neck, intense gaze |

### Sam — Hunter / work outdoor
| Field | Spec |
|-------|------|
| Height / weight | **186 cm · 84 kg** (head ref + CQR tier align — no body banner) |
| Age band | 42–50 |
| Build | **sturdy athletic**, thick neck, broad shoulders from reference |
| Hair | short dark brown, neat |
| Beard | short brown-grey beard |
| Eyes | pale blue/grey |
| Skin | sun spots, outdoor weathered — **stocky capable not thin elder** |
| EN anatomy seed | rugged Caucasian man, late 40s, 186cm 84kg, sturdy athletic build thick neck broad shoulders, short dark hair, groomed short beard, grey-blue eyes, sun-weathered strong skin |

### Carter — Covert urban sharp
| Field | Spec |
|-------|------|
| Height / weight | **185 cm · 86 kg** (head ref + tier align) |
| Age band | 38–45 |
| Build | athletic solid, square jaw, thick neck |
| Hair | dark brown wavy, short sides volume top |
| Beard | dark heavy stubble |
| Eyes | dark brown/hazel |
| Skin | natural pores, **mature-athletic not elderly** |
| EN anatomy seed | fit Caucasian man, early 40s, 185cm 86kg, athletic solid build square jaw thick neck, dark brown hair styled up, heavy stubble, hazel eyes, sharp focused expression |

### Logan — Rider wiry-strong (anti-frail critical)
| Field | Spec |
|-------|------|
| Height / weight | **183 cm · 78 kg** — **lean-athletic, NOT frail** |
| Age band | 40–48 |
| Build | wiry-strong, defined jaw, **road-capable lean muscle — forbid skeleton/thin elder read** |
| Hair | short light brown/auburn, brushed up |
| Beard | full auburn-brown beard with grey |
| Eyes | blue-grey |
| Skin | sun-weathered lines — **working man fit, not gaunt** |
| EN anatomy seed | road-worn Caucasian man, mid 40s, 183cm 78kg, wiry-strong athletic build (lean but muscular neck and shoulders), auburn-brown beard, blue-grey eyes, sun-weathered skin, upright capable posture — not frail not elderly |

---

## Imagen Primary — anatomy template (sentence 2)

Replace `[ID]` and fields from row:

```
Normal adult male proportions head-to-body 1:7.5; CQR actor [ID]: [height] [weight], broad shoulders, thick muscular neck, athletic V-taper, upright posture, age [band], [hair], [beard], [eyes]; physically capable fit man not elderly not frail.
```

## Brief template (Korean)

```
- CQR 이미지 모델: [ID] (lane 기본 또는 사용자 지정)
- 체격: [height] / [weight], [build keyword — 왜소·노쇠 금지]
- 연령대: [band] — 노인·허약 연출 금지
- 헤어 / 수염 / 눈: [from row]
- 실루엣: 어깨 넓고 목 두꺼운 athletic fit; 구부정·좁은 어깨 금지
```

---

## QC — frail drift fail

Hard fail if output image or prompt would read as:
- shoulders narrower than head, visible ribcage, collapsed posture
- face reads 60+ when actor band tops at 50
- "skinny old white man" / generic elder passerby

Fix: re-lock actor row H/W, move anatomy to Primary sentence 2, append Anti-frail block, raise weight + shoulder language.

**Same actor twice in chat without user request:** hard fail — re-run ACTOR ROTATION, pick next pool member, note under 확인 필요 if pool was size 1.
