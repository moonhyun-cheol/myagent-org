# CQR Film Mood Reference — 기획·컨셉 브리프 전용

Purpose: every **FULL scene brief** includes ** 무드 참고** as **one unified film anchor** — same work, same character, same actor — with **on-screen wardrobe similar to the hero CQR garment** so mood-board search is practical.

## Hard rules

1. **Mandatory** on every FULL scene brief — never omit.
2. **One work only** — 등장인물 and 배우 must belong to **that same 작품**.
3. **Garment-first pick** — prefer a pool row where the character **actually wears a similar garment category** to the hero CQR SKU (see selection order below). Lane/mood alone is not enough.
4. **Planning / discussion only** — never copy names into `.art` / Imagen EN.
5. **Never** celebrity likeness in any image prompt.
6. User-supplied film in chat → pick a character **from that work** who wears the **closest garment type** to hero SKU.
7. Mark debatable fits under 확인 필요.

## Selection order (before writing )

1. Read hero **category** from matched model row or user input: `pant` / `short` / `shirt` / `jacket` / `fleece` / `flannel shirt` etc.
2. Read hero **garment family**: cargo pant, ripstop pant, tactical shirt, mesh shirt, flannel, softshell, fleece jacket, etc.
3. Filter lane pool to rows whose **착장 유형** matches or is closest to hero family.
4. Among matches, pick best **lane + TPO + mission** fit.
5. If no strong wardrobe match: pick closest row, state **착장 gap** in **이 컨셉과의 연결** and add garment term to **무드보드 검색**.

Tie-break: **garment similarity > lane mood > epic scale (lower wins)**.

## Garment family → pool filter (quick map)

| Hero CQR family | Prefer pool **착장 유형** |
|-----------------|---------------------------|
| Cargo / ripstop pant, tactical pant | cargo pant, tactical pant, utility pant |
| Lightweight pant, LT pant | tactical pant, chino-adjacent field pant |
| Tactical / combat shirt, long sleeve operator shirt | tactical shirt, field shirt, rolled-sleeve utility shirt |
| Mesh / interlock / performance shirt | lightweight field shirt, base-layer under open shirt (note layer gap) |
| Flannel shirt | flannel, plaid work shirt, heavy shirt |
| Softshell / jacket / fleece outer | field jacket, work jacket, fleece midlayer on screen |
| Short | cargo short, field short (rare — note gap if pool weak) |

## Output block format (mandatory structure)

### 무드 참고 (기획·실촬 논의 전용 — AI 이미지·EN 사용 금지)

**작품:** [title, year] — grade, scale, texture to borrow

**등장인물:** [character **in this work**] — task energy vs CQR mission

**배우:** [performer of this character] — casting note — **likeness·AI 생성 금지**

**착장 매칭:** [what this character wears on screen — cut, pocket read, fabric weight] ↔ [hero CQR garment family] — match / partial / gap

**이 컨셉과의 연결:** borrow vs TPO downgrade; if wardrobe not 1:1, say what to **ignore** on screen

**무드보드 검색:** 2–3 phrases — **`[work] [character] [garment word] still`** e.g. `Hurt Locker William James cargo pants still`

Forbidden: character whose on-screen outfit is suit-only when hero is cargo pant; three unrelated picks.

## Lane pool — unified anchors (pick ONE row)

| Lane | 착장 유형 (on screen) | 작품 | 등장인물 | 배우 | Borrow |
|------|------------------------|------|----------|------|--------|
| **Liberator** | cargo / tactical pant | *The Hurt Locker* (2008) | William James | Jeremy Renner | desert utility pant read, sun-worn cargo, procedural motion |
| **Liberator** | tactical shirt + pant | *Zero Dark Thirty* (2012) | Maya | Jessica Chastain | field ops kit, docu grit, task focus — **not** raid epic |
| **Liberator** | operator tactical kit | *Sicario* (2015) | Matt Graver | Josh Brolin | muted tac pant + shirt, border logistics walk |
| **Covert** | plainclothes + low-sig outer | *Michael Clayton* (2007) | Michael Clayton | George Clooney | urban transit coat layer, overcast restraint — **pant gap if hero is cargo** |
| **Covert** | tactical covert kit | *Sicario* (2015) | Alejandro Gillick | Benicio del Toro | low-signature dark kit, corridor scale — note **not cargo-heavy** |
| **Expedition-Alpinist** | trail pant + worn outer | *The Revenant* (2015) | Hugh Glass | Leonardo DiCaprio | trail pant texture, cold margin — **downgrade epic** |
| **Expedition-Alpinist** | climbing / field pant | *Everest* (2015) | Beck Weathers | Josh Brolin | ridge docu pant silhouette — tier check |
| **Expedition-Hunter** | flannel / work shirt | *Wind River* (2017) | Cory Lambert | Jeremy Renner | flannel-ready, forest margin, camp gravity |
| **Expedition-Hunter** | field shirt + work pant | *Leave No Trace* (2018) | Will | Ben Foster | camp chore, soft overcast, worn work pant |
| **Expedition-Rider** | denim / road jacket | *Logan* (2017) | Logan | Hugh Jackman | roadside stop, practical jacket, muted neo-western |
| **Expedition-Rider** | road-worn shirt | *The Motorcycle Diaries* (2004) | Ernesto (young) | Gael García Bernal | road kit adjust — **no political iconography** |
| **Sapper** | field jacket / work layer | *Arrival* (2016) | Ian Donnelly | Jeremy Renner | hangar-adjacent scale, overcast industrial — **jacket hero** |
| **Sapper** | NASA work coverall / field layer | *The Martian* (2015) | Mark Watney | Matt Damon | work-site tone, utilitarian read — **not** sci-fi hero |

Add rows over time when a **verified on-screen garment match** exists for a CQR family. Do not add rows without wardrobe plausibility.

## TPO downgrade rule

If the chosen row's environment exceeds fabric tier:
- keep **grade + character energy + on-screen garment silhouette** where tier allows
- swap in brief body to tier-allowed location
- explain in **이 컨셉과의 연결** and 확인 필요

## .art firewall

When user later requests `.art`:
- Re-express casting as **generic mission persona** only
- Primary / Negative: **zero** movie titles, character names, actor names
