# CQR Visual DNA — Listing-Matched Concept Art

Purpose: turn scene briefs into AI concept art that matches CQR Amazon listing and A+ image grammar. Purpose Above All must read in posture and environment, not only in copy.

**Core rule:** garment fabric tier and verified use temperature beat world-lane drama. Listing photography scale, not blockbuster poster scale.

**Mission Persona Rule:** every CQR wearer has an active task in frame. No generic student, office worker, commuter, or mission-empty "ordinary person". Civilian look is OK only with explicit mission (transit check, site walk, trail scout, camp prep, tool run, etc.).

## Garment-TPO Gate (mandatory before image prompts)

Run after model match, before any EN prompt.

0. **IMAGE MODEL CAST lock** — user-named actor OR **rotate** from lane candidate pool + session ledger (CQR_IMAGE_MODEL_CAST.md ACTOR ROTATION). Copy height/weight/build/hair/beard into Lock Card. Anti-frail ON. **Do not default Ryan every turn.**
1. Identify hero garment category and fabric family from matched row or title.
2. Assign fabric tier: L Light summer / M Mid duty outdoor / W Warm midlayer / C Cold shell.
3. Lock temperature band, allowed locations, forbidden locations, and pose intensity from tier rules in MY_prompt Garment-TPO Gate.
4. If development 배경 or lane default exceeds tier ceiling, **downgrade the scene** to a believable TPO and note under 확인 필요.
5. Write every slot inside the same locked TPO band.

### Tier quick reference

| Tier | Typical fabrics | Allowed TPO | Forbidden |
|------|-----------------|-------------|-----------|
| L | mesh, interlock, knit, vent shirt | urban, transit, warm city, flat trail, desert walk 18–32C | summit, snow, blizzard, ice climb, cliff hero |
| M | ripstop pant, cargo, light flex, combat shirt | urban tactical, desert bench, range, trail below treeline, hangar | alpine summit, blizzard, technical crux |
| W | flannel, brushed twill, grid fleece top | autumn camp, forest stroll, tailgate, cabin porch 0–18C | ice climb, exposed alpine ridge |
| C | softshell 3L, sherpa, winter hiking pant | snow edge, cold ridge, winter outdoor | summer desert noon, beach |

### Believable scale rule

- Amazon listing photo = real person doing a **credible everyday task** in a **credible place** for that fabric.
- Bad: thin covert mesh shirt on exposed mountain summit at dawn.
- Good: same shirt in transit hall exit, rooftop walk at dusk, or parking structure patrol at 26C.
- Bad: ripstop cargo pant on Everest ridge.
- Good: same pant on Sonora desert bench stride or urban kneel at vehicle check.

## When to activate

- User uploads listing images, A+ panels, or storefront screenshots
- User asks for 컨셉아트, 이미지 프롬프트, AI image, same format as listing, 같은 양식
- User says `.art` or `.img` after a scene brief
- User names ASIN and wants visual set

## Reference-first rule

1. If user supplied listing images in the session, analyze them before writing prompts.
2. Mirror observed slot structure, aspect ratio feel, palette, model casting, distance, background density, **and TPO scale**.
3. Do not invent a new art direction when references exist. Extend the same grammar to the new model/scene.
4. If reference image shows an environment incompatible with current hero garment tier, **do not copy that environment** — copy composition and grade only, swap to tier-appropriate location.
5. If no reference image, use lane defaults **only inside fabric tier limits** and mark style choices under 확인 필요.

## Image analysis checklist (per reference)

Record for each uploaded image:

- slot type: MAIN / LIFESTYLE / DETAIL / A+ HERO / A+ FEATURE / INFOGRAPHIC
- aspect feel: square 1:1, portrait 4:5, banner 16:9 or 970×600 feel
- subject count and gender presentation
- camera distance: full / 3-4 / waist-up / macro
- lens feel: environmental wide 24–35mm / standard 50mm / portrait 70–85mm
- pose and motion: static catalog / walk / crouch / climb / scan / transit
- **TPO scale:** listing-believable / slightly dramatic / overly epic — if overly epic, do not replicate for mismatched garment
- hero garment visibility: which pieces readable, color accuracy, pocket zones shown
- palette: dominant 3 colors + accent
- grade: warm golden / cool overcast / high-contrast desert / muted urban / flannel amber
- background: studio white / gradient / full environment / shallow depth blur
- props and loadout density: minimal / moderate / heavy
- text overlay: none / feature callout / split panel (A+)
- forbidden elements present: weapons, logos, celebrity likeness — never reproduce

## CQR Amazon storefront grammar (reference)

CQR Brand Store and typical US listing pages mix **two families** of images. AI generation quality differs sharply between them.

| Family | Slots | Real CQR use | AI default |
|--------|-------|--------------|------------|
| **Concept** | PT01, PT02, A+ HERO, A+ FEATURE (lifestyle half) | Task in environment; Purpose Above All readable | **Generate by default** — this is where `.art` shines |
| **Utility** | MAIN, PT03 back, PT04 macro, size chart | White-bg catalog, flat back read, fabric close-up | **Do not default** — AI front/back catalog shots look uncanny; emit only if user asks 리스팅 전체 / MAIN / PT03 / 카탈로그 |

Storefront hero tiles and A+ banners follow **concept family** grammar: environmental wide, mid-action, documentary grade — not dead-center catalog stare.

When user shares storefront URL or listing screenshots without naming slots, classify each image as Concept or Utility before writing prompts. Mirror Concept grammar for AI output. For Utility references, note "실촬영 권장" unless user explicitly wants AI catalog prompts.

## Concept vs Utility — awkward-AI ban (mandatory)

These patterns fail on CQR listings when AI-generated. **Never output for default `.art` set:**

- dead front-facing catalog stare, arms at sides, eyes locked to camera, white void — uncanny MAIN mimic
- pure back view, static shoulders square to camera, no motion or environment — awkward PT03 mimic
- mannequin symmetry, identical left/right crease, floating hem, plastic skin sheen
- beauty-retouch glow, oversharpened pores, hyper-saturated tactical green
- empty pose with no mission noun — "standing in pants" with no task

**If user needs MAIN or PT03 via AI**, rewrite away from catalog mimic:

| Slot | Bad AI pattern | Required rewrite |
|------|----------------|------------------|
| MAIN | straight-on full front, blank stare | slight 3/4 turn, weight on one leg, soft neutral gradient not pure white void, gaze off-camera toward task object, one hand adjusting belt or pocket — garment still 85% readable |
| PT03 | static back catalog, arms pinned | three-quarter rear walk on trail or site, mid-stride away from camera, head turn 15° showing jaw profile, environment anchors scale — back pocket readable in motion not flat poster |
| PT04 | floating fabric swatch | macro on worn garment — knee bend crease, hand pulling pocket flap, ripstop grid on live body zone |

Default `.art` slot order: **PT01 → PT02 → A+ HERO → PT04** (concept-first). Add MAIN or PT03 only when user explicitly requests full listing or those slots.

## Profession → mission casting map (AI-friendly)

Pick **one row** per scene. Civilian look OK only with mission column filled. Match lane + fabric tier.

| Lane | Profession / role | Active mission in frame (examples) | Age · build · look |
|------|-------------------|-------------------------------------|---------------------|
| Covert | transit security contractor | badge check at hall choke point; rooftop equipment survey at blue hour | 28–38 lean, low-signature, no overt tactical cosplay |
| Covert | logistics field auditor | warehouse inbound walk with tablet; parking structure perimeter check | 30–45 average-athletic, plain belt, no patches |
| Covert | urban recon analyst | harbor edge phone map check; glass corridor exit scan | 28–40 sharp but understated |
| Liberator | range safety officer | berm walk resetting lane tape; truck-bed gear sort before convoy | 30–42 athletic, cargo readable, empty belt only |
| Liberator | desert field contractor | Sonora bench stride with tool pouch; concrete yard kneel at vehicle check | 32–45 sun-weathered, not Hollywood operator |
| Liberator | EDC instructor (no weapon visible) | teaching pocket layout at tailgate; cargo pocket demo crouch | 30–40 approachable pro |
| Expedition-Alpinist | trail section scout | forest switchback pace; boulder field pole plant below treeline | 28–42 trail-ready, not summit hero unless Tier C |
| Expedition-Alpinist | SAR volunteer | bridge approach with pack; meadow map check at dawn | 30–50 functional outdoor |
| Expedition-Hunter | camp quartermaster | tailgate stove prep; cabin porch wood stack carry | 35–50 relaxed outdoor, flannel-forward |
| Expedition-Hunter | land management tech | autumn forest fence line walk; truck bed kit unload | 30–48 work-casual outdoor |
| Expedition-Rider | overland mechanic | garage bay torque check; desert road fuel stop bike lean | 28–45 grease-tolerant, motion energy |
| Expedition-Rider | moto tour prep | helmet on tank, jacket zip mid-motion at dawn pull-off | 30–40 road dust acceptable |
| Sapper | hangar turn technician | aircraft wheel chock check; tool cart roll under wing | 28–45 industrial pro, not cosplay |
| Sapper | robotics field engineer | crane yard tablet read; launch pad periphery cable walk | 30–50 clean workwear scale |
| Sapper | facilities maintenance lead | robotics lab bench cable trace; concrete floor marker paint | 32–48 even daylight face |

Forbidden across all rows: generic student, office worker, commuter, shopper, fashion model with no task, "ordinary guy" without mission noun.

Product-title bridge (when lane unknown): tactical pant / combat shirt → Liberator or Covert by color; hiking / ripstop outdoor → Alpinist; flannel / fleece → Hunter; work cargo / coverall → Sapper; rider jacket → Rider.

## Photoreal output mandate (ALWAYS ON for `.art` / `.img`)

Every image slot must read like **real on-location commercial photography**, not AI concept art. Generic one-line EN prompts are **forbidden**.

Per slot, output **both**:
1. Korean structured fields — 카메라 정보 · 자연스러운 조명 · 피부·질감 묘사 · 색감 (each **2–4 concrete sentences**, numbers where plausible)
2. EN prompt — same content in **bracket-tagged blocks** (copy-paste ready)

Opening line of every EN prompt must state real photography medium, e.g. *Real photograph, not illustration, not CGI, not AI art.*

## Anti-AI / photoreal realism block

Layer these cues in the Korean fields **and** EN prompt:

**Skin and face:** visible pores, fine lines, uneven skin tone, subtle stubble or clean natural skin, micro shadows under eyes, slight asymmetry, relaxed jaw, no beauty-filter smoothness, no wax figure sheen, no plastic gloss, no identical twin symmetry.

**Eyes and gaze:** look at task object, horizon, or off-camera action — not laser stare into lens unless MAIN utility slot explicitly requested. Natural catchlight from environment, not studio ring reflection.

**Body and pose:** weight on one leg, mid-motion acceptable on foot or hand, asymmetric arms, tendon tension at wrist, fabric tension at knee/hip/elbow, believable sweat or dust only when TPO allows.

**Garment texture:** ripstop grid readable, cotton weave, flannel nap, seam puckering, natural crease at bend, gravity on cargo pockets, no melted fabric, no airbrushed folds.

**Environment texture:** concrete grain, dust on boot, dry grass, metal scuff, shallow atmospheric haze — not CGI-perfect cleanliness.

**Camera authenticity:** name **body + lens + focal length + aperture + ISO + shutter**; slight handheld micro-imperfection OK; subtle film grain or sensor noise; no computational HDR crunch, no oversharpened edges.

**Lighting authenticity:** **one motivated natural or practical source** — sun angle, open shade, window spill, overcast sky dome, golden hour rim — soft shadow falloff, no ring light, no flat dual-beauty lighting, no neon teal-orange blockbuster grade unless reference proves it.

Standard negative (always append): plastic skin, wax figure, uncanny valley, AI generated, Midjourney look, DALL-E smoothness, CGI, 3D render, illustration, digital art, beauty retouch, airbrushed, symmetrical mannequin, dead eyes, catalog stare, static back view, HDR halos, oversaturated, hyperreal fake, floating garment, melted fabric, perfect symmetry, pure white void (unless MAIN utility requested), oversized head, bobblehead, big head small body, narrow shoulders, chibi proportions, **frail, emaciated, gaunt, skinny, underweight, bird chest, pencil neck, stooped elderly man, geriatric, senior citizen, old fragile man, sunken cheeks, hollow temples, weak frame, generic uncanny white man**, sterile cleanroom, CGI warehouse, blur prop only, generic tablet pose, athletic hoodie in industrial work scene (unless hero is hoodie), hood framing oversized face, detached studio lighting on face, **firearms, rifles, guns, handguns, ammunition, weapon rack, gun wall, tactical armory, gear room with weapons, plate carrier wall with rifles, blown out white window, airbrushed hands, merged fingers, plastic glossy skin, mushy background weapons, generic gear storage room**.

## Anatomy and proportion mandate (mandatory — known AI failure)

Every `.art` slot must specify adult human proportions in Korean ** 해부·비율** field and **[Anatomy and proportions]** EN block.

Required in output:
- **Head-to-body ratio ~1:7 to 1:8** (normal adult male); never bobblehead, never enlarged head on narrow shoulders
- **Normal shoulder width** relative to head; neck length believable
- **Hood rule:** if hood up, hood must not inflate head silhouette — prefer **hood down or hood back** unless reference shows hood up; if hood up, explicitly state *normal head size inside hood, hood fabric thin not padded*
- **Hands:** visible **knuckle creases**, tendon lines at wrist, subtle vein hint; fingers separated; one clear contact point on task object (crate edge, wheel chock, tool handle — tablet only with second contact)
- **Camera distance:** 85mm at 2.5–4m avoids wide-angle head distortion; forbid close wide selfie distortion unless intentional

Forbidden defaults: cute enlarged head, fashion model pin-head opposite error, AI "hero face" scale-up.

## Mission credibility mandate (mandatory — no staged props)

Every slot needs ** 임무 구체성** field (2–3 sentences) and **[Mission credibility]** EN block.

Required:
- **One specific task verb + object noun** — not "looking at tablet" alone
 - Bad: holding tablet, looking at blurry machine edge
 - Good: logging torque values on rugged tablet while free hand rests on landing gear strut; reading cable routing tag on avionics bay panel
- **Task object fully readable** in frame or clearly identifiable — not anonymous blur blob in foreground
- **Physical contact** — hand on real surface (strut, crate, map, tool, rifle case closed, rope) — not floating gesture
- **Decision moment** — what is being verified, adjusted, or scouted **right now**

Forbidden: generic tablet hero pose, tablet-only both hands no second contact, out-of-focus mystery prop, model posing between unrelated stock elements, **tactical armory or gear room setting**, any visible weapon shape.

## Environment grit mandate (mandatory — no sterile CGI sets)

** 배경·환경** must include **minimum 3 lived-in imperfection nouns** matched to location type.

| Location type | Pick ≥3 imperfection cues |
|---------------|---------------------------|
| Hangar / Sapper | floor scuff marks, tire marks, coiled cable, oil spot near mat, chalk mark, used glove on bench |
| Desert / Liberator | dust on boot, sun-bleached sign, rock chip, worn bench edge, wind-blown grit |
| Forest / Alpinist | mud on heel, broken twig, worn trail tread, leaf debris, damp rock patch |
| Urban / Covert | pavement gum stain, scuffed door frame, wet reflection patch, faded paint |

Forbidden default: polished spotless concrete, perfect pegboard, museum-clean workshop, no wear anywhere, Unreal Engine environment.

**[Environment grit]** EN block: one dense sentence listing imperfections + motivated clutter (not chaos).

## Lane–garment coherence gate (run with Garment-TPO)

Hero garment category must match world lane **readability**. If mismatch, downgrade scene or change casting garment — note under 확인 필요.

| Lane | Hero garment should read as | Forbidden mismatch (unless hero product IS the mismatch item) |
|------|---------------------------|---------------------------------------------------------------|
| Sapper | work shirt, coverall, ripstop work pant, utility cargo | athletic hoodie, gym mesh top, fashion fleece |
| Liberator | combat shirt, tactical cargo, ripstop pant | office polo, flannel camp shirt |
| Hunter | flannel, fleece, hunter top | tactical plate carrier look, hangar coverall |
| Covert | low-signature urban tactical, mesh vent shirt | overt range belt with heavy pouches |
| Alpinist | hiking pant, trail shirt, softshell | hangar workwear, desert only props |
| Rider | rider jacket, motion pant | hangar, flannel camp |

If user matched product is hooded mesh / athletic top → route to **Covert or Alpinist**, not Sapper hangar, unless user explicitly requests Sapper-with-this-garment and scene is downgraded to believable TPO.

## Lighting–environment lock (mandatory)

Face and garment highlight direction **must match** stated environment source in ** 자연스러운 조명**.

Required:
- Name primary source position (e.g. skylight camera-left 40° elevation)
- Shadow under chin/nose must fall **away from key light**
- Catchlight in eye from same source — not ring-light twin dots
- No brighter face than environment logic allows

Forbidden: subject lit brighter than background without motivated fill; floating rim on hood; HDR even glow on skin; **blown-out white window with no exterior detail**; flat even fill erasing nose shadow.

## Forbidden AI environment clichés (HARD BAN — default `.art`)

These locations trigger AI stock tropes, policy violations, and sterile renders. **Never use as default scene** unless user explicitly requests and policy-safe rewrite applied.

| BANNED setting / prop | Why |
|------------------------|-----|
| tactical armory, gear room, gun room, weapon rack, gun wall | AI always adds **visible firearms** — CQR **policy forbidden** |
| plate carrier wall + rifles on shelf | stock tactical cliché + weapons |
| pegboard perfect tool wall (no wear) | sterile CGI |
| generic "gear storage room" | resolves to armory 80%+ of generations |
| mystery blur machine/drone prop at frame edge | mission credibility fail |

**Use approved alternatives instead** (pick lane-fit):

| Lane | Approved locations (weapon-free) |
|------|----------------------------------|
| Covert | parking structure walk, transit hall, warehouse **inbound cart scan**, loading dock clipboard check |
| Liberator | **desert bench outdoor**, range **berm exterior** (no guns in frame), pickup tailgate pocket demo, concrete yard vehicle check |
| Sapper | hangar **floor** wheel chock check, crane yard, robotics lab bench, **maintenance cart** — **no weapon racks** |
| Alpinist | trail switchback, bridge, boulder field |
| Hunter | camp tailgate, cabin porch, truck bed |
| Rider | garage bay open door, desert pull-off, fuel stop |

If user brief says "armory" or "gear room": **rewrite location** to nearest approved row and note under 확인 필요.

## Weapon-free scene mandate (Amazon + CQR policy — ALWAYS ON)

Every EN prompt must include **[Weapon-free scene policy]** block (or equivalent sentences in [Environment grit]) stating:

- **No firearms, rifles, handguns, ammunition, or weapon silhouettes visible** anywhere in frame
- **No weapon racks, gun walls, tactical armory shelves**
- Belts/holsters: **empty holster or no holster** only; no gun shapes
- Range scenes: **berm, lane tape, target frame back view only** — no firearms on subject or props

Korean ** 장면·정책** field (1–2 sentences): confirm banned elements excluded + chosen approved location.

QC fail automatic: any visible gun shape → 재생성.

## Exposure and skin micro-detail mandate

** 자연스러운 조명** and **[Natural lighting]** must include exposure logic:

- Windows: **not blown to pure white** — retain soft exterior gradient or blind detail; expose for subject not clipping background to void
- Highlight rolloff on forehead and cheek — no plastic specular blob
- Shadow side of face **measurably darker** than key side (min 1-stop falloff feel)

** 피부·질감** and **[Skin and texture]** must include **hand micro-detail**:

- visible **knuckle creases**, tendon tension at wrist, subtle vein hint, matte skin
- **Forbidden:** airbrushed smooth hands, finger merged, plastic gloss, beauty filter poreless skin

## Tablet scene cap (mission credibility)

- **Tablet-only pose forbidden** — tablet may appear only if **second contact point** exists (hand on crate, wheel, map, tool handle) AND task is named (SKU scan, torque log, inbound label check)
- Default slot set: **max 1 of 4 slots** may include tablet unless user requests tablet-focused set
- Prefer: clipboard, gloved hand on equipment, kneeling tool check **without** tablet when possible

## Camera presets by slot (default — override only when reference analyzed)

| Slot | Body | Lens | Aperture | ISO | Shutter | Notes |
|------|------|------|----------|-----|---------|-------|
| PT01 | Canon EOS R5 / Sony A7IV | 35mm | f/4–f/5.6 | 200–400 | 1/250–1/500 | environmental wide, eye level or slight low, deep focus |
| PT02 | Canon EOS R5 | 50mm or 85mm | f/2.8–f/4 | 100–320 | 1/320–1/800 | 3/4 body, subject sharp, background soft falloff |
| A+ HERO | Nikon Z8 / Canon R5 | 28mm or 35mm | f/5.6–f/8 | 200–500 | 1/200–1/400 | banner wide, subject 30–40% frame height |
| PT04 | Canon R5 | 85mm or 100mm macro | f/4–f/5.6 | 200–640 | 1/200–1/320 | worn fabric macro, shallow DOF on stitch/ripstop |
| MAIN utility | Phase One / Canon R5 | 70–85mm | f/5.6–f/8 | 100–200 | 1/125–1/250 | minimal env gradient, garment 85% readable |

Always specify: camera height, subject distance, depth of field intent, subtle natural grain level (low/medium).

## Natural lighting presets by lane (pick one — match Garment-TPO)

| Lane | Default lighting recipe |
|------|-------------------------|
| Covert | overcast sky softbox, blue-hour ambient + weak street practical, low contrast |
| Liberator | late afternoon sun 15–25° above horizon, hard-but-short shadow, warm fill from sand/concrete bounce |
| Alpinist | early morning side light 20°, soft overcast forest canopy, cool fill |
| Hunter | golden hour back rim + warm front fill from campfire bounce or open shade |
| Rider | low sun rim on dust, garage fluorescent + open door daylight mix |
| Sapper | even industrial skylight + single directional window, neutral 5500K |

Forbidden default: ring light, twin softbox beauty setup, neon cyberpunk grade, unreal volumetric god rays.

## Color grade presets ( 색감 field)

Each slot must specify:
- **White balance** (e.g. 5200K daylight, 6500K overcast, 4800K golden hour)
- **Contrast** (low / medium / medium-high — never crushed blacks + clipped highlights together)
- **Saturation** (natural to slightly muted — CQR default muted documentary)
- **3 dominant colors** + 1 accent tied to hero garment color code
- **Grade reference** (e.g. Kodak Portra 400 scan feel, neutral commercial outdoor, desaturated desert documentary)

Forbidden: Instagram teal-orange, oversaturated tactical green, AI neon clarity boost.

## Structured Korean fields (mandatory per slot)

Replace vague one-liners. Minimum content:

### 카메라 정보
Body, lens mm, aperture, ISO, shutter, camera height, subject distance, DOF, grain/noise level, handheld vs tripod.

### 자연스러운 조명
Primary source + direction + time of day + color temp + shadow quality + fill (bounce from what surface) + what is **not** used (no ring light).

### 피부·질감 묘사
Skin pores, tone variation, stubble/grooming, eye catchlight source, sweat/dust/sun weathering level, fabric micro-texture on hero zones, environment surface texture.

### 색감
White balance, contrast, saturation, 3 colors + accent, grade reference, highlight/shadow rolloff note.

## Amazon listing slot map (CQR default)

Generate concept-first set unless user asks for one slot or full listing including utility slots.

| Slot | Family | Role | Default composition |
|------|--------|------|---------------------|
| MAIN | Utility | Search thumbnail clarity | Hero garment fully readable. White or very light neutral bg. **AI only on explicit request** — use 3/4 turn task pose rewrite, not dead front catalog. |
| PT01 | Concept | World-establishing lifestyle | Environmental wide but **listing scale**. Model 30–50% frame height. Terrain must fit fabric tier — not epic summit by default. |
| PT02 | Concept | Product-readable action | 3/4 body. Motion mid-stride or task pose matched to garment: walk, kneel, crouch, tool check — not crux climb unless Tier C winter hero. |
| PT03 | Utility | Alternate angle or color story | Profile, back pocket view, or layered outfit read. **AI only on explicit request** — prefer motion rear three-quarter, not static back catalog. |
| PT04 | Utility* | Detail / fabric | Macro or close crop: ripstop grid, stitching, waistband, hardware, flannel weave. *Default set uses **worn macro** variant (concept-safe), not flat swatch. |
| A+ HERO | Concept | Brand banner | Cinematic wide but still believable for fabric tier. Purpose Above All through task, not empty epic landscape. |
| A+ FEATURE | Concept | Split or callout panel | Subject on one side, negative space for copy on other OR inset detail circles. |

## Lane visual defaults (no reference image)

Use only when fabric tier allows. Lane sets mood; tier sets ceiling.

### Covert
- Palette: charcoal, stone gray, black, muted navy
- Locations: parking structure, transit hall, rooftop at dusk, harbor edge, glass office corridor
- Lighting: overcast urban or blue-hour; low-key
- Casting: lean operator, 28–38, chest rig or belt without weapon

### Liberator
- Palette: coyote, ranger green, sage, dust tan, black
- Locations: desert bench, range berm, pickup truck bed, concrete yard — not alpine summit unless winter Tier C hero
- Lighting: golden hour or harsh noon with controlled shadow; documentary not Hollywood
- Casting: athletic male 30–42; cargo readable; holster empty or belt only

### Expedition-Alpinist
- Palette: forest green, granite gray, sky blue, trail dust
- Locations: forest trail, boulder field, trekking bridge, meadow — ridge and summit **only for alpine-rated hero garments**, not light shirts
- Lighting: early morning side light or soft overcast
- Casting: trail-ready build; poles and pack only when tier supports

### Expedition-Hunter
- Palette: amber, rust flannel red, pine shadow
- Locations: camp edge, autumn forest, truck tailgate, cabin porch
- Lighting: warm low sun; flannel texture priority
- Casting: relaxed outdoor; camp chore scale

### Expedition-Rider
- Palette: asphalt gray, leather black, sunset orange rim light
- Locations: desert road, garage bay, fuel stop
- Lighting: rim light and dust; motion energy

### Sapper
- Palette: safety yellow accent, concrete gray, navy coverall
- Locations: hangar floor, launch pad periphery, robotics lab, crane yard
- Lighting: even industrial daylight; professional not cosplay

## Global CQR photo grammar

- Commercial outdoor photography, not illustration unless user asks illustrated mode
- Real locations and believable weathering on skin and fabric
- Male hero casting default for CQR tactical/outdoor unless product is clearly unisex/women's — **use CQR IMAGE MODEL CAST registry (11 actors); lock height/weight/build; never generic frail elderly white man**
- Fit: **athletic V-taper, broad shoulders, thick neck** — regular to relaxed tactical; show articulation at knee and hip in action shots
- No visible firearms, no unit patches, no agency logos, no celebrity faces
- No oversaturated Instagram filter; slight grain acceptable in lifestyle slots
- Product color must match named color code when known (SGN sage, BLK, KHK, ONV olive, CHC charcoal)
- Purpose Above All: subject doing a task, not posing empty at camera
- **Garment-environment harmony is mandatory** — if fabric looks summer-light, environment must look summer-light

## Output: listing-matched AI prompt set

**Generation method:** CQR_PROMPT_GENERATION_PROTOCOL.md — ** Constraint Lock Card first**, whitelist location only, EN **assembly not authoring**.

After scene brief (or together if user says `.art` only), output slots in this order.

### Constraint Lock
Scale tier, whitelist **L-code**, task+contact, composition preset, hero garment lane OK, explicit slot bans. **Output this block first** per protocol.

### Garment-TPO
Fabric tier, temp band, one-line reason this slot location fits the hero garment.

### 슬롯명
Amazon slot label and purpose in one line.

### 비율
1:1, 4:5, 16:9, or match uploaded reference ratio.

### 구도·거리
Framing, subject scale in frame, camera height, listing scale not poster scale.

### 피사체·포즈
Demographics, expression, motion, gaze. **Active mission task** with asymmetric weight shift. Forbidden: generic student, office worker, commuter.

### 해부·비율
Structured 2–3 sentences: head-to-body ~1:7–1:8, shoulder width, neck, hood rule, camera distance to avoid distortion, hand contact on task object.

### 임무 구체성
Structured 2–3 sentences: specific task verb + object noun, what decision happens now, physical contact point — not generic tablet stare at blur prop.

### 히어로 garment
Model code, color, fabric weight cue, visible details. **Lane–garment coherence** confirmed or flagged.

### 배경·환경
Location nouns + **minimum 3 grit/imperfection cues** from Environment grit mandate. Must match Garment-TPO. **Not** banned armory/gear-room cliché.

### 장면·정책
1–2 sentences: confirm **no firearms, weapon rack, gun wall, tactical armory**; state approved location from alternative table.

### 카메라 정보
Structured 2–4 sentences: body, lens mm, f-stop, ISO, shutter, distance, height, DOF, grain. Use slot preset table unless reference overrides.

### 자연스러운 조명
Structured 2–4 sentences: source, direction, time, color temp, shadow, fill, **lighting–environment lock**, **window not blown out**. No ring light.

### 피부·질감 묘사
Structured 2–4 sentences: skin pores/tone, **knuckle creases, tendon lines, vein hint on hands**, catchlight from environment source, garment micro-texture, environment surface texture.

### 색감
Structured 2–4 sentences: white balance, contrast, saturation, 3 colors + accent, grade reference (Portra/neutral/documentary).

### Negative
Full photoreal negative list including anatomy, sterile environment, staged mission, lane-garment mismatch terms.

### EN prompt
Copy-paste block with **mandatory bracket tags in this order** (each tag = one dense paragraph):

[Real photograph]
[Camera]
[Natural lighting]
[Anatomy and proportions]
[Skin and texture]
[Color grade]
[Weapon-free scene policy]
[Mission credibility]
[Environment grit]
[Scene and subject — garment lane match, pose, gaze away from camera]
[Aspect ratio]

End with: *real on-location photograph, indistinguishable from professional commercial shoot, not AI, not CGI, not illustration.*

### KR note
One line on reference match, lane default, garment TPO, lane–garment coherence.

## EN prompt skeleton (template)

[Real photograph] Real on-location commercial photograph, not illustration, not CGI, not AI art, not digital painting.

[Camera] Shot on Canon EOS R5, 85mm lens, f/2.8, ISO 200, 1/400 sec, eye-level camera, subject distance 3m (avoid wide-angle head distortion), shallow depth of field with soft background falloff, subtle natural sensor grain.

[Natural lighting] Single skylight from camera-left at 35 degrees elevation, cool 5800K industrial daylight, shadow under nose falling to camera-right, fill from concrete floor bounce only, catchlight in eyes from skylight, **window exposure retained with soft exterior gradient not blown pure white**, no ring light, face shadow side visibly darker than key side.

[Anatomy and proportions] Normal adult male proportions head-to-body ratio 1:7.5, natural shoulder width, proportional neck, hood down or thin hood back not enlarging head silhouette, no bobblehead, one hand on wheel chock second hand on clipboard not tablet-only pose.

[Skin and texture] Visible skin pores and natural tone variation, light stubble, **knuckle creases and tendon tension on hands**, subtle vein hint, matte skin without plastic shine, light oil smudge on knuckle, ripstop fabric grid readable with seam puckering at elbow.

[Color grade] White balance 5600K, medium contrast, slightly muted saturation, dominant concrete grey and navy with safety yellow accent, neutral commercial documentary grade, soft highlight rolloff without HDR halos.

[Weapon-free scene policy] No firearms, rifles, handguns, ammunition, or weapon silhouettes visible; no weapon racks, gun walls, or tactical armory; empty belt only; maintenance hangar floor only without gun shelves.

[Mission credibility] Aircraft turn technician verifying wheel chock placement while marking checklist on clipboard, reading tire chalk mark on concrete, specific maintenance task not generic posing.

[Environment grit] Working aircraft hangar floor with scuff marks, coiled power cable, faint oil spot near rubber mat, worn work glove on bench, chalk tire mark, **not sterile armory and no weapons on shelves**.

[Scene and subject] Wearing navy ripstop work shirt and utility cargo pant matching Sapper lane, asymmetric stance, gaze at checklist task not camera, believable industrial scale listing photography.

[Aspect ratio] — Aspect ratio 1:1

Forbidden in EN block: weapon, firearm, rifle, gun rack, armory, logo, text overlay, oversized head, bobblehead, sterile cleanroom, blur prop mission, tablet-only pose, athletic base layer in work scene (unless hero product), plastic skin, airbrushed hands, blown out window, uncanny valley, detached studio face lighting.

## Workflow tie-in

1. Model match → Garment-TPO Gate → scene brief (Brief Body Mode)
2. Reference analyze if images present — copy grammar and scale, not incompatible environment
3. Emit concept-first slot set (default 4: PT01, PT02, A+ HERO, PT04 worn-macro) unless user narrows or asks full listing / MAIN / PT03
4. Each EN prompt must be self-contained; do not say "as above"
5. Mark unverified color or fabric under 확인 필요 per slot

## Multi-image session rule

When user uploads multiple references from one ASIN page:

- Identify which file maps to which slot
- Preserve cross-slot consistency: same model casting, same colorway, same location family, same grade, same TPO band
- Vary only composition and distance per slot map
