# myagent-org

**1.0.0-beta.1** · org seq **13** · work-kit catalog seq **1** · [`moonhyun-cheol/myagent-org`](https://github.com/moonhyun-cheol/myagent-org)

CQR용 **조직 모듈**(스킬·slash)과 **작업 키트**(프로필)를 한 레포에서 게시합니다. 앱 본체는 [`myagent`](https://github.com/moonhyun-cheol/myagent).

## 두 갈래 (섞지 않음)

| 갈래 | 소스 | 피드 | 앱 동작 |
|------|------|------|---------|
| **조직 모듈** | `agent-module/` | `channels/beta.json` + 서명 ZIP | 기동·적용 시 백그라운드 설치 |
| **작업 키트** | `work-kits/profiles/` | `channels/work-kits.json` + 키트 tarball | 설정 → 작업 환경에서 받기·적용 |

사용자 UX는 **작업 환경**(CQR 브랜드 정보 / 제품개발 / 명령어 모음)이 전면입니다.

## 작업 키트 (CQR)

- 정의: `work-kits/profiles/cqr/*/shelf.json`
- 카탈로그: `channels/work-kits.json`
- 검증·게시:

```bash
npm run verify:work-kits
npm run publish:work-kits
```

## 조직 모듈

```bash
npm run verify:module-pack
npm run verify:org-automaton
npm run publish:update
```

사내 URL·NAS는 git에 넣지 않습니다. `operator-config.example.json` → `_local/operator.json`.

서명 개인키: `tools/keys/` (커밋 금지).
