# Product data access (API + slash only)

ORGANIZATION_BRAND_CONTEXT

SKU·PR코드·모델코드·ASIN·자식 ASIN·컬러·스펙·라인업 수치는 **로컬 `data/`·NAS·레포 파일에서 읽지 않는다.**

## 정본 우선순위 (허브 = 지금 운영자 PC → 이후 사내 서버)

1. **PRODUCT DATA** — `module.json`의 `product_data_base_url` (publish 시 허브 주소 주입)
2. **Slash** — `/childasin`, `/모델가계도` → 허브 Adapter (`openclaw_adapter_base_url`) → Bulbasaur
3. **이번 턴 사용자 제공** 자료
4. **ORGANIZATION BRAND MANUAL** — `brand_manual_url` (허브)

충돌 시: live brand manual > product data API > 사용자 자료.  
허브 이전 시 URL만 바뀌고 우선순위는 동일. 구조: `docs/OPERATOR-HUB.md`

## API·slash 둘 다 없을 때

`product_data_base_url` 이 비어 있거나 off면 API fetch를 건너뛴다.  
slash도 실패하면 `확인 필요`로 표시한다. **행을 지어내지 않는다.**

## 금지

- `agent-module/data/`·`model_row_index`·임베드 번들·NAS 경로를 근거로 SKU/ASIN 단정
- API·slash 없이 카탈로그 행·ASIN·재고·가격 추측
