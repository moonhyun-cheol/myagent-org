# CQR 시장조사

ORGANIZATION_BRAND_CONTEXT

내부 전략·라인 언어는 **live brand manual**이 정본이다. CQR 키워드·endpoint/MCP 조사 절차는 `skills/cqr-brand-manual.md`를 먼저 따른다. 카탈로그·스펙 사실은 `skills/product-data-access.md`와 product data API만 쓴다. 웹에서 온 수치와 내부 자료를 섞지 말고, 가정은 `가정:`으로 표시한다.

실행·산출물 형식은 `market_research/CQR_MARKET_INJECT.md`가 우선한다.

## 배포 클라이언트 (MY Agent)

- `/심층리서치 <브리프>` — 호스트가 `pipelines/market_research.py research` 실행
- `/타당성 <브리프>` — feasibility (HITL)
- `/기획서 <승인문>` — product plan
- 파이프라인(Python) 없으면 inject 규칙으로 채팅 근거 조사 (dead-end 금지)

## 금지

- 로컬 `data/`·NAS·레포 파일에서 SKU/스펙 단정
- API·slash 없이 라인업·ASIN 추측
- 배포 사용자에게 Cursor/`run.ps1` 수동 실행을 기본 경로로 요구
