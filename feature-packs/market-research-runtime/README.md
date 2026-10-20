# org.cqr.market-research-runtime

선택형 Feature Pack. 조직 모듈의 `pipelines/market_research.py`가 쓸 Python 실행 환경만 담당합니다.
파이프라인 코드는 조직 모듈에, 무거운 의존성은 여기(사용자 PC에서 설치)에 둡니다.

## 흐름
1. `CQR 상품개발` Work Kit 적용 → Core가 이 팩을 `data/organization-features/org.cqr.market-research-runtime/`에 풉니다(서명 검증).
2. 관리자가 `setup-venv.ps1`을 실행합니다.
   - Python 3.11~3.13을 찾고, 없으면 python.org 3.12 설치 파일을 받아 서명(Python Software Foundation)을 확인한 뒤 사용자 범위로 조용히 설치합니다.
   - `<MY Agent 루트>/runtime/pipeline-venv`에 venv를 만들고 `requirements.txt`를 PyPI에서 설치합니다.
3. Core `market-pipeline-capability.ts`는 `runtime/pipeline-venv/Scripts/python.exe`를 PATH Python보다 먼저 씁니다.
4. 키트 적용 해제 시 `setup-venv.ps1 -Remove`가 이 스크립트가 만든 venv만 지웁니다(`.cqr-runtime.json` 표식 확인).

로그: `<MY Agent 루트>/logs/market-research-runtime-setup.log`
