# Automaton / OpenClaw (Organization Feature Pack)

회사 업무 slash·Bulbasaur 연동. **실행은 중앙 허브**(지금=운영자 PC, 이후=사내 서버)에서만 돈다.  
전체 구조: [docs/OPERATOR-HUB.md](../../docs/OPERATOR-HUB.md)

**Feature id:** `org.cqr.automaton-routing`  
**설치 조건:** 「CQR 명령어 모음」 Work Kit **적용** 시 Core가 서명된 Feature Pack을 `data/organization-features/`에 설치·활성화합니다.  
기본 조직 모듈만 설치해도 slash 실행 라우트는 생기지 않습니다.

## Files (authoring → signed Feature Pack)

| File | Purpose |
|------|---------|
| `feature.json` | Core Organization Feature 계약 |
| `automaton-tools.manifest.json` | Slash → tool id |
| `openclaw-workflow-map.json` | Tool id → Bulbasaur Adapter payload |
| `adapter-connection.template.json` | Adapter URL·인증 bootstrap·상태 polling 기본값. **호스트 하드코딩 금지** |
| `deploy-overrides.json` | Actor / fallback. **Hub URL은 Work Kit publish 시 주입** |

## Hub (Work Kit publish 시 주입)

`_local/operator.json` → `npm run publish:work-kits` → ops shelf asset 안의 `features/org.cqr.automaton-routing.zip`

| hub 필드 | MY Agent 동작 |
|----------|----------------|
| `openclaw_adapter_base_url` | slash → `POST {url}/cqr/adapter/request` |

브랜드 매뉴얼·제품 데이터 URL은 **기본 조직 모듈** publish(`publish:update`)에서 주입합니다.

장기 MAIN API 토큰을 Git 또는 ZIP에 넣지 않습니다. bootstrap 키는 교체 가능한 설치 수단이며, Adapter는 사내망 제한·키 교체·장치 토큰 폐기를 적용합니다.

## Runtime path

```
Work Kit 적용 → Feature 설치/활성
MY Agent slash → (활성) automaton-tools.manifest.json
  → openclaw-workflow-map.json
  → adapter-connection.json
  → POST {hub}/cqr/adapter/request
```

미설치 slash는 기본 모듈의 `optional-feature-slash-index.json`으로 `feature_required` 안내만 하고 LLM으로 보내지 않습니다.
