# Product data access (API + slash only)

ORGANIZATION_BRAND_CONTEXT

SKU·PR코드·모델코드·ASIN·자식 ASIN·컬러·스펙·라인업 수치는 **로컬 `data/`·NAS·레포 파일에서 읽지 않는다.**

## 정본 우선순위

1. **PRODUCT DATA** — 코어가 `product_data_base_url` / `MY_AGENT_PRODUCT_DATA_BASE_URL` 로 주입한 API 응답 (카탈로그·매칭·스펙).
2. **Slash 조회** (OpenClaw → Bulbasaur):
   - `/childasin {PR코드}` — PR/SKU → child ASIN (예: `KR#####_CQXXXXXX_PR`)
   - `/모델가계도 {모델코드}` — 모델 가계도
3. **이번 턴 사용자 제공** 자료.
4. **Live brand manual** — 철학·라인·카피·비주얼 가드레일만 (SKU 테이블 아님).

충돌 시: live brand manual > product data API > 사용자 자료.

## API 미연결 시

`product_data_base_url` 이 비어 있거나 off면 API fetch를 건너뛴다.  
운영 조회는 slash를 쓰거나 `확인 필요`로 표시한다. **행을 지어내지 않는다.**

## 데이터 서버 (예정)

operator `_local/operator.json` 의 `product_data_base_url` 에 연결된다.  
배포 ZIP·git에는 URL을 넣지 않는다. 연결 후 코어가 PRODUCT DATA 블록으로 주입한다.

## 금지

- `agent-module/data/`·`model_row_index`·임베드 번들·NAS 경로를 근거로 SKU/ASIN 단정
- API·slash 없이 카탈로그 행·ASIN·재고·가격 추측
