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
| `automaton-tools.manifest.json` | Slash → tool id + 선언형 최종 응답 정책 |
| `AUTOMATON.md` | Feature 운영·런타임 계약 |
| `DISCORD_RESPONSE_FORMATS.md` | Discord 최종 문자열·ACK·배치 양식 SoT |
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

## 선언형 최종 응답

Discord의 문자·줄 구조 권위 원본은 `DISCORD_RESPONSE_FORMATS.md`입니다. 서비스가 만든 `payload.message`가 있으면 Core는 이를 재요약하거나 제목·engine/status/stdout 래퍼를 추가하지 않고 그대로 전달합니다.

새 명령은 `automaton-tools.manifest.json`에 다음만 선언합니다.

- `response.profile: "discord"`
- 기존 양식 이름인 `template_id`
- `payload.message`가 없을 때만 쓰는 `fallback_profile`
- ACK의 안정적인 `command_id`와 배치 시간 힌트
- 쉼표 배치 지원 여부·표시명·상한

기존 `text`·`quantity`·`files`·`status` 프로필은 Discord 메시지가 누락된 경우의 안전 폴백으로만 재사용합니다. `files`는 허용된 최종 파일만 남기고 JSON·로그·임시 산출물을 제외합니다. 수량·파일이 없으면 값을 만들거나 거짓 완료하지 않습니다.

예:

```json
{
  "profile": "discord",
  "template_id": "ctr-report",
  "fallback_profile": "files",
  "allowed_extensions": [".xlsx", ".csv"],
  "ack": {
    "enabled": true,
    "command_id": "downloadtable_ctr",
    "batch_time_hint": "수 분 이상 (데이터 범위에 따라 달라질 수 있음)"
  },
  "batch": { "supported": true, "label_ko": "CTR", "cap": null }
}
```
