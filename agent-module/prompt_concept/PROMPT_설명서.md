# CQR 브랜드 이미지 컨시어지 — 프롬프트 설명서

민영상사 Amazon US **CQR** 브랜드 **이미지 담당 AI 컨시어지(Miny)** 사용 가이드입니다.  
제품·ASIN·이미지를 주면 **촬영 브리프**, **listing AI 프롬프트**, **업로드 QC**, **신제품 visual spec**까지 한 흐름으로 연결합니다.

---

## 목차

| § | 제목 | 언제 읽으면 되는지 |
|---|------|-------------------|
| **§1** | 개요 | 처음 한 번 — 역할·범위 파악 |
| **§2** | 빠른 시작 | Gem에 프롬프트 붙여넣기 직전 |
| **§3** | 파일 구조 | 어떤 md를 열어야 하는지 헷갈릴 때 |
| **§4** | 표준 워크플로 | AI가 매 턴 무엇을 하는지 이해할 때 |
| **§5** | `.art` 생성 방식 | **조립(Assembly) 방법** — 반드시 읽기 |
| **§6** | 출력 모드 | Brief / `.art` / QC / `.dev` 차이 |
| **§7** | 단축 명령 | `.ff` `.art` 등 입력 키워드 빠른 참조 |
| **§8** | 질문 예시 | 채팅에 그대로 복사해 테스트 |
| **§9** | `.art` 슬롯 | listing AI 이미지 4장 구성 |
| **§10** | 브랜드 규칙 | TPO · Mission · Lane · 모델 매칭 |
| **§11** | 페르소나 | Miny 말투·Guard 동작 |
| **§12** | 주의사항 | 환각·실수 줄이기 |
| **부록** | 품질 평가 | 내부 점검용 — 일상 사용 불필요 |

> **번호 규칙:** 본문 **§1~§12**는 설명서 **대목차**입니다.

---

## §1. 개요 — 이 프롬프트가 하는 일

| 하는 일 | 하지 않는 일 |
|--------|-------------|
| 모델코드·ASIN → CQR 세계관 매칭 + TPO 잠금 | 가격·재고·리뷰 수 등 허구 listing 정보 |
| 촬영용 FULL / COMPACT 씬 브리프 | NAS·내부 폴더 경로 노출 |
| listing·A+ **컨셉** 슬롯 AI EN prompt | MAIN·뒷모습 카탈로그 AI 기본 생성 (어색함) |
| 업로드 이미지 **QC** (TPO·Mission·Anti-AI) | 총기·부대·유명인 얼굴 |
| `.dev` 주머니·허리·컬러way 스펙 | Tesla Inc. 공식 CS 톤 |

**역할:** 브랜드 이미지 컨시어지 — Purpose Above All 중심, **임무 있는 캐스팅**만.

---

## §2. 빠른 시작 — Gem·번들 설정

### Gemini (추천 — vision + Imagen)

| 순서 | 작업 |
|------|------|
| ① | [Google AI Studio](https://aistudio.google.com) → Build → Create Gem |
| ② | Name: `CQR Brand Image Concierge` |
| ③ | **`MY_prompt_gemini.md` 전체** → System Instructions에 붙여넣기 |
| ④ | Knowledge 파일 **첨부하지 않음** (중복 충돌 방지) |
| ⑤ | listing·A+·초안 이미지는 **채팅에 업로드** |

### Claude / ChatGPT

| 플랫폼 | 붙여넣을 파일 |
|--------|---------------|
| Claude Project | `MY_prompt_claude.md` |
| ChatGPT 등 | `MY_prompt_bundle_slim.md` |

### Open WebUI (Workspace)

| 순서 | 작업 |
|------|------|
| ① | Workspace → **Models** → Create model |
| ② | Name: `CQR Brand Image Concierge` — Base: vision 지원 LLM |
| ③ | **`MY_prompt_gemini.md` 전체** → System Prompt |
| ④ | Knowledge/RAG **첨부하지 않음** |
| ⑤ | **Access → Public** (또는 팀 Group Read) — **admin 또는 Public 공유 권한 필요** |
| ⑥ | Admin Panel 없으면 **zip 파일 공유** — `SETUP_OPENWEBUI.md` §2-A |

> **컨셉만 줄 때:** `촬영 컨셉` / `.ff` → **브리프만** 출력. AI 이미지 프롬프트는 **`.art`** 또는 `프롬프트도 줘` 등 **명시 요청 시에만**.

### 프롬프트 갱신 (xlsx·규칙 수정 후)

```powershell
cd prompt
python scripts/build_local_bundle.py
python scripts/build_platform_prompts.py
```

→ Gem Instructions에 `MY_prompt_gemini.md` **다시 붙여넣기**

---

## §3. 파일 구조 — 어떤 파일을 쓸지

```
prompt/
├── MY_prompt.md                 ← 원본 규칙 (수정 시 여기부터)
├── MY_prompt_gemini.md          ← ★ Gemini Gem Instructions
├── MY_prompt_claude.md          ← Claude Project
├── MY_prompt_bundle_slim.md     ← ChatGPT 등 generic
├── PROMPT_설명서.md             ← 이 문서
├── SETUP_GEMINI.md              ← §2 요약 1분판
├── data/
│   ├── CQR_PROMPT_GENERATION_PROTOCOL.md  ← ★ `.art` 7-step 조립·whitelist
│   ├── CQR_BRAND_IMAGE_PLAYBOOK.md  ← 역할·라우터·QC·컴퍼스
│   ├── CQR_VISUAL_DNA.md            ← 슬롯·Anti-AI·캐스팅
│   ├── SCENE_BRIEF_ENGINE.md
│   └── codex/CQR_BRAND_CONCEPT.md
└── scripts/
    ├── build_local_bundle.py
    └── build_platform_prompts.py
```

| 파일 | 용도 |
|------|------|
| `MY_prompt_gemini.md` | **매일 사용** — Gem에 이것만 |
| `MY_prompt.md` | 규칙 편집 후 build 스크립트로 번들 재생성 |
| `data/*` | build 시 번들에 embed — Gem에 따로 첨부하지 않음 |

---

## §4. 표준 워크플로 — AI가 매 턴 하는 일

```
의도 분류 → 모델 매칭 → TPO 잠금 → (참조 분석) → 브리프 → 산출물
```

| 산출물 | 요청 예 | 용도 |
|--------|---------|------|
| 촬영 브리프 | `TLP125 촬영 컨셉` | 실사 촬영·기획 회의 |
| `.art` EN prompt | `TLP125 .art` | Imagen / MJ / Flux |
| QC 리포트 | `(업로드) QC` | AI·실사 초안 검수 |
| `.dev` matrix | `TLP130 .dev` | 신규 SKU pocket/fit/color |

매 제품 답변 앞두 줄 (자동):

- **🔍 매칭:** 모델 · 컬러 · 라인 · 확신도  
- **🧶 TPO 잠금:** Tier · 온도대 · 허용/금지 환경  

---

## §5. `.art` 생성 방식 v2 — Dual Output (중요)

**v1 문제:** 10-block EN 조립본 → Imagen이 **앞 200단어만** 읽음 → armory·flat lay drift  
**v2 해결:** 슬롯마다 **두 종류** EN

| 출력 | 용도 | 붙여넣기 |
|------|------|----------|
| **🎯 Imagen Primary** | 150–220 words, anatomy·L-code 먼저 | **Imagen에 이것** |
| **🚫 Imagen Negative** | 별도 블록 | Imagen Negative 필드 |
| 📝 EN Full Assembly | 10 bracket tags | 기록·MJ·감사용 |

**8-step:** Lock(L+T+S code) → Pre-flight ✅ → 한국어 필드 → Primary → Negative → Full Assembly

**코드 3종 (자유 서술 금지)**
- **L-code** — 장소 whitelist (例: L-LIB-04 tailgate)
- **T-code** — 동작 임무 (例: T-POCKET pocket flap pull) — **T-BAN-* 금지**
- **S-code** — 구도 preset (例: S-PT02-A 85mm 3/4)

**금지 staging:** EDC flat lay, gear table knolling, golden hour stock (Hunter/Rider 외)

**품질 팁:** `TLP125 .art PT02만` — 슬롯 1개씩 Primary 생성

상세: `CQR_PROMPT_GENERATION_PROTOCOL.md` v2

---

## §6. 출력 모드表

| 모드 | 활성화 방법 | 출력 내용 |
|------|-------------|-----------|
| **Brief Body** (기본) | 제품명 + 촬영·컨셉·listing/A+ **방향** | 🔍매칭 + 🧶TPO + **FULL** 11섹션 브리프 — **Imagen 프롬프트 없음** |
| **`.art` / `.img`** | `.art` / 컨셉아트 / 이미지프롬프트 / `프롬프트만` | COMPACT 5섹션 + **컨셉 4슬롯** EN prompt |
| **`.ff`** | `.ff` 또는 풀브리프 | FULL 11섹션 (`.art` 없으면 prompt 없음) |
| **`.dev`** | `.dev` 또는 신제품·스펙 | 주머니·허리·컬러 full matrix |
| **QC / 검수** | 이미지 업로드 + QC·검수 | M-ASSET-QC 판정표 |
| **`.ops`** | `.ops` 또는 운영모드 | 답변 + Brand Image Compass + 타임스탬프 |
| **`프롬프트만`** | `프롬프트만` / prompts-only | EN prompt만 (브리프 생략) |

---

## §7. 단축 명령 — 입력 키워드

| 입력 | 동작 |
|------|------|
| `.ff` | FULL 씬 브리프 (11섹션) |
| `.art` / `.img` | COMPACT 브리프 + 컨셉 4슬롯 EN prompt |
| `.dev` | 신제품 spec matrix |
| `.ops` / `운영모드` | Brand Image Compass 메뉴 |
| `프롬프트만` | EN prompt만 |
| `QC` / `검수` / `브랜드 맞나` | 업로드 QC |
| `리스팅 전체` / `MAIN` / `PT03` | 유틸리티 슬롯 추가 (AI rewrite 규칙 적용) |

---

## §8. 질문 예시 — 채팅에 복사

**촬영 브리프 (프롬프트 없음 — 기본)**
```
CQ-TLP125-SGN 촬영 컨셉 풀버전
TFP620 sage-green .ff
```

**컨셉아트 (`.art` 명시 시에만 Imagen 프롬프트)**
```
(이미지 3장 첨부) B0CFQ571ND .art — 이 페이지 톤 유지
TLP710-ONV .art PT01 PT02만
```

**이미지 QC**
```
(AI 결과 업로드) 이 이미지 CQR 브랜드에 맞나? QC 해줘
```

**신제품**
```
Liberator TLP130 .dev — TLP125 베이스 mac pocket 추가
```

**운영**
```
위 브리프 기준 .ops
```

---

## §9. `.art` 슬롯 — listing AI 4장 (컨셉 우선)

| 슬롯 | 역할 | `.art` 기본 포함 |
|------|------|------------------|
| **PT01** | 환경 wide + 임무 | ✅ |
| **PT02** | 3/4 동작 + garment read | ✅ |
| **A+ HERO** | 배너형 task-in-environment | ✅ |
| **PT04** | 착용 중 매크로 (원단·포켓) | ✅ |
| MAIN | 흰 배경 정면 썸네일 | ❌ — `MAIN` 또는 `리스팅 전체` 요청 시 |
| PT03 | 뒷모습 카탈로그 | ❌ — `PT03` 또는 `리스팅 전체` 요청 시 |

MAIN·PT03은 AI보다 **실촬영 권장**. 요청 시 pose rewrite 규칙 적용.

### §9-1. `.art` 슬롯별 실사 출력 (필수)

각 슬롯마다 **한국어 필드** + **bracket EN prompt** (축약 금지).

| 필드 | 내용 |
|------|------|
| **🧭 해부·비율** | head 1:7~1:8, 어깨·목, 후드 규칙, bobblehead 금지 |
| **🎯 임무 구체성** | task verb+명사, 접촉점, blur prop 금지 |
| **📷 카메라 정보** | body, mm, f, ISO, 셔터, 거리 3m+ 권장 |
| **💡 자연스러운 조명** | 광원=환경 일치, 얼굴 shadow 방향 |
| **🧴 피부·질감** | 모공, catchlight, 원단 texture |
| **🎨 색감** | WB, contrast, muted documentary |
| **🌄 배경** | 장소 + **마모·오일·케이블 등 grit 3개 이상** |

**EN tag 순서:**  
`[Real photograph]` → `[Camera]` → `[Natural lighting]` → `[Anatomy and proportions]` → `[Skin and texture]` → `[Color grade]` → `[Mission credibility]` → `[Environment grit]` → `[Scene and subject]` → `[Aspect ratio]`

**QC에서 자주 걸리는 패턴:** 머리 과대 · sterile hangar · **armory+총기** · 태블릿-only · athletic base layer · blown window · airbrushed hands

**금지 장면 (`.art` default):** tactical armory, gear room, weapon rack, gun wall → **warehouse scan / hangar floor / outdoor bench** 등으로 rewrite

---

## §10. 브랜드 규칙 — TPO · Mission · Lane · 매칭

### §10-1. Garment-TPO Gate (의상·배경 조화)

| Tier | 대표 원단 | 허용 TPO | 금지 |
|------|-----------|----------|------|
| **L** | mesh, knit | 도심·transit 18–32°C | 정상·폭설 |
| **M** | ripstop, cargo | 사막·range·숲길 | 알프스 정상 |
| **W** | flannel, fleece | 캠프·가을 숲 | 빙벽 |
| **C** | softshell, winter | 눈·cold ridge | 한여름 사막 |

**원칙:** Covert/Liberator/Alpinist **드라마 < 원단 tier 상한**.

### §10-2. Mission Persona (항상 ON)

- CQR 착용자 = **항상 임무 중**
- **금지:** 학생·직장인·통근자 등 미션 없는 일상 캐스팅
- **허용:** 시민 외형 + 명시 task (site walk, trail scout, hangar prep 등)

### §10-3. CQR 6 World Lane

| Lane | 키워드 |
|------|--------|
| **Covert** | urban, transit, low-signature |
| **Liberator** | range, cargo, ripstop, desert |
| **Expedition-Alpinist** | hiking, trail, ridge |
| **Expedition-Hunter** | flannel, camp, autumn |
| **Expedition-Rider** | motorcycle, road, garage |
| **Sapper** | hangar, aircraft, industrial |

부브랜드: **TSLA** (athletic), **ATIKA** (women's) — CQR 다음 순위.

### §10-4. 모델 매칭 순서

AI가 제품을 찾는 **우선순위** (위에서 성공 시 중단):

| 순위 | 방법 | 예 |
|------|------|-----|
| 1 | 정확 코드 | `TLP125`, `TFP620` |
| 2 | 정규화 코드 | `CQ-TLP125-SGN` → TLP125 + SGN |
| 3 | ASIN | `B0CFQ571ND` |
| 4 | 상품명 fuzzy | tactical, ripstop, flannel … |
| 5 | 컬러 tie-break | SGN, BLK, KHK, ONV, CHC |
| 6 | 패밀리 fallback | 같은 라인 근사치 → ⚠️ 확인 필요 |

매칭 실패 시 AI가 **모델코드 / 컬러 / ASIN / 정확한 상품명** 중 하나를 요청합니다.

---

## §11. 페르소나

| 이름 | 역할 |
|------|------|
| **Miny** (기본) | CQR 브랜드 이미지 컨시어지 · **존댓말** · 촬영·비주얼 기획자 톤 · 인사 생략 |
| **Guard** | 가짜 군·경 identity, 과장 claim, 환불 압박 시 1회 제지 |

사용자가 반말을 **명시 요청**할 때만 반말.

---

## §12. 주의사항 — 환각·실수 줄이기

- Gem Instructions = **`MY_prompt_gemini.md` 단일 파일** (Knowledge 중복 첨부 금지)
- listing·A+ 참조는 채팅 **업로드** — `data/source/listing_refs/`는 보관용
- **⚠️ 확인 필요** 섹션 무시 금지
- MAIN·뒷모습(PT03)은 AI보다 **실촬영** 우선
- xlsx 갱신 후 `build_local_bundle.py` → `build_platform_prompts.py` → Gem 재붙여넣기

---

## 부록. 자체 품질 평가 (내부 점검용)

| 영역 | 점수 | 비고 |
|------|------|------|
| 브랜드 이미지 역할 | 9.6 | Playbook + QC + router |
| Mission·TPO | 9.5 | tier gate + concept-first |
| 컨셉아트 | 9.5 | Anti-AI + 4슬롯 default |
| 모델 매칭 | 9.3 | 94행 index |
| 지식 완성도 | 8.5 | PO·FAQ 미연동 |
| **종합** | **9.5** | 브랜드 이미지 실사용 기준 |

*민영상사 · CQR · Purpose Above All*
