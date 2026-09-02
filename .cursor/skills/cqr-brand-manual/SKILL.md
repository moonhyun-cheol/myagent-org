---
name: cqr-brand-manual
description: >-
  CQR 브랜드 허브 스킬. 사용자 메시지에 CQR·민영·Purpose Above All·라인(LIBERATOR/COVERT/SAPPER/EXPEDITION)·로드아웃·브랜드 매뉴얼이
  보이면 즉시 사용한다. CQR 키워드 인식 후 관련 스킬을 찾고, MCP·brand-manual·product-data endpoint를 확인한 뒤 접속·조사한
  근거로만 답한다. 브랜드 철학·제품 라인·기획·카피·비주얼·적합성 검토에 사용한다.
---

# CQR Brand Manual (Hub)

CQR 관련 요청이 오면 **이 스킬을 먼저** 따른다. 추측으로 브랜드 정책을 만들지 않는다.

## 0. CQR 키워드 → 관련 스킬 탐색 (필수)

메시지에 `CQR` / `cqr` / `민영` / `Purpose Above All` / `PAA` / CQR 라인·로드아웃이 있으면:

1. **이 스킬**을 연다.
2. 의도별로 **관련 스킬·파일을 찾아 읽은 뒤** 작업한다 (이름만 알고 건너뛰지 말 것).

| 의도 | 찾을 스킬 / 파일 |
|------|------------------|
| 브랜드 철학·라인·카피·적합성 | 이 스킬 + live brand manual |
| SKU·ASIN·모델·스펙 | `agent-module/skills/product-data-access.md` |
| 신제품·컨셉·무드·`.art` | `agent-module/skills/brand-concept.md`, `prompt_concept/AGENTS.md`, `prompt_concept/MY_prompt.md` |
| 시장·경쟁·타당성 | `agent-module/skills/market-research.md`, `market_research/CQR_MARKET_INJECT.md` |
| 샘플 사이즈·차트 | `agent-module/skills/size-guide.md` (+ inject) |
| 조직 모듈 스킬 목록 | `agent-module/skills/manifest.json` |

관련 스킬이 workspace에 없으면 `확인 필요`로 표시하고, 있는 근거만으로 답한다.

## 1. 정보조회 endpoint / MCP 확인 후 조사 (필수)

브랜드·카탈로그 사실을 말하기 **전에** 아래를 순서대로 한다.

### 1-A. Endpoint 확인

1. `_local/operator.json` 또는 env에서 조회 URL을 읽는다.
   - `brand_manual_url` / `MY_AGENT_BRAND_MANUAL_URL`
   - `product_data_base_url` / `MY_AGENT_PRODUCT_DATA_BASE_URL`
2. 예시 키만 보고 주소를 지어내지 않는다. git·스킬에 사내 IP를 하드코딩하지 않는다.
3. URL이 비어 있거나 `off`/`none`/`false`면 live fetch를 건너뛰고 `확인 필요`로 진행한다.

### 1-B. MCP 확인

1. 사용 가능한 MCP 네임스페이스를 확인한다 (예: `user-nopspro`).
2. 정보조회·상태 확인에 쓸 도구를 고른다. NOPSPro면 먼저 `nopspro_status`로 연결을 본다.
3. 브랜드 매뉴얼 본문 전용 MCP가 없으면 **HTTP brand_manual_url**을 정본 조회로 쓴다.
4. 인증이 필요하면 해당 MCP의 auth 흐름을 따른다. 실패 시 추측하지 말고 실패 사실을 적는다.

### 1-C. 접속 후 조사

1. live URL이 있으면 접속해 매뉴얼/데이터를 가져온다.
2. 충돌하면 **live brand manual**을 철학·카피에, **product data API**를 SKU·ASIN에 우선한다.
3. 조사한 섹션·출처를 짧은 근거로 남긴 뒤 산출물을 작성한다.

## 2. 기준 문서

- Live: operator `brand_manual_url` (주입 시 `ORGANIZATION BRAND MANUAL`)
- Catalog: operator `product_data_base_url` (주입 시 `PRODUCT DATA`)
- Slash (MY Agent): `/childasin`, `/모델가계도`
- 문서에 없는 정책·스펙·인증·재고·가격은 만들지 않는다.

## 3. 핵심 원칙

1. 판단은 **PURPOSE ABOVE ALL (PAA)** 에서 출발한다.
2. 목적: **Freedom · Justice · Prosperity · Frontier**. **TACTICAL**은 구현 방식이다.
3. 공식 스테이트먼트·고객 노출 문구는 정본 고정 문구를 임의 변형하지 않는다.
4. 제품·콘텐츠는 라인의 목적·인물상·기능·로드아웃·장면이 일치해야 한다.
5. 미확인 기능·소재·인증·성능·직업 적합성을 사실처럼 주장하지 않는다.

## 4. 작업 절차 (산출물)

요청 분류 → 관련 스킬/정본 섹션 확인 → 정합성 점검 → 결과 작성.

검토 요청 형식:

1. **판정**: 적합 / 부분 적합 / 부적합
2. **근거**: 정본 섹션 또는 조사 출처
3. **수정안**: 바로 쓸 문구·방향
4. **확인 필요**: 정본·endpoint만으로 확정 불가한 항목

## 5. 금지

- CQR 키워드인데 관련 스킬·endpoint 확인을 건너뛰기
- `agent-module/data/`·NAS·임베드 번들에서 SKU/ASIN 읽기
- MCP/URL 실패를 무시하고 기억만으로 공식 정책처럼 단정
- 사내 IP·토큰을 사용자 응답이나 커밋 대상 파일에 적기
- 정본에 없는 규칙을 CQR 공식 정책이라고 말하기
