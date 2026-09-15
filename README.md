# myagent-org

**1.0.0-beta.1** · org seq **19** · work-kit catalog seq **5** · [`moonhyun-cheol/myagent-org`](https://github.com/moonhyun-cheol/myagent-org)

CQR **조직 모듈**(스킬·slash), **작업 키트**, 운영자용 **MY Agent 관리자**를 서로 독립된 배포 트랙으로 게시합니다. 앱 본체는 [`myagent`](https://github.com/moonhyun-cheol/myagent).

## 허브 구조 (먼저 읽기)

MY Agent = 클라이언트. **slash·데이터·Bulbasaur = 중앙 허브** (지금 운영자 PC → 이후 사내 서버).

→ **[docs/OPERATOR-HUB.md](docs/OPERATOR-HUB.md)** — 뭐가 뭔지, publish, 토큰, 서버 이전

## 세 갈래 (섞지 않음)

| 갈래 | 소스 | 피드 | 앱 동작 |
|------|------|------|---------|
| **조직 모듈** | `agent-module/` | `channels/beta.json` + 서명 ZIP | 기동·적용 시 백그라운드 설치 |
| **작업 키트** | `work-kits/profiles/` | `channels/work-kits.json` + 키트 tarball | 설정 → 작업 환경에서 받기·적용 |
| **관리자** | `manager/` | `manager/channels/launcher-stable.json` + install/update zip | 운영자용 별도 프로그램 설치·업데이트 |

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

사내 URL·NAS·토큰은 git에 넣지 않습니다. `operator-config.example.json` → `_local/operator.json` (로컬만). 허브 연결 후 `publish:update`, 미연결이면 `publish:update -- --skip-hub`.

서명 개인키: `tools/keys/` (커밋 금지).

## Gitea 이전

사내 Gitea 대상과 이전 단계는 `release-targets.json`에서 관리합니다. 현재는 기존 GitHub 업데이트를 유지하면서 Gitea에 이력·Release를 복제하는 **mirror 단계**입니다.

```bash
npm run verify:gitea
npm run publish:gitea                 # dry-run
npm run publish:gitea -- --confirm    # MY_AGENT_GITEA_TOKEN 필요
```

태그 동기화, 자산 목록, 브리지·최종 전환 순서는 [docs/GITEA-MIGRATION.md](docs/GITEA-MIGRATION.md)를 따릅니다. Core·관리자·조직 모듈 소비자가 Gitea URL을 지원하기 전에는 활성 feed URL을 바꾸지 않습니다.
