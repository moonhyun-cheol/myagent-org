# MY Agent 관리자 (WorkKitLauncher)

MY Agent **관리자 프로그램**(코드명 `WorkKitLauncher`)을 이 조직 저장소(`moonhyun-cheol/myagent-org`)로 이전한 것입니다.
update-51에서 앱 본체(`moonhyun-cheol/myagent`)의 설정 화면으로 통합되며 제품 트리에서 제거됐던 프로그램을,
운영자용 별도 실행 프로그램으로 다시 복원했습니다. 원본은 앱 본체 커밋 `27f8fb5^`(제거 직전 상태)에서 그대로 가져왔습니다.

> 이 폴더는 **관리자(운영자) 프로그램**입니다. MY Agent 클라이언트 본체가 아니며, 조직 모듈/작업 키트 게시 파이프라인(`agent-module/`, `work-kits/`, 루트 `tools/`)과도 별개입니다.

## 구조

| 경로 | 내용 |
|------|------|
| `shell/WorkKitLauncher/` | WPF 셸 (`.csproj`, `App`, `MainWindow`, 자동업데이트 서비스 일체) |
| `ui/work-kit-launcher/` | 관리자 SPA (`ProfileLibrary` 등 작업 키트 받기/적용/해제 UI) |
| `core/src/updates/launcher-update-feed.ts` | 런처 업데이트 피드 파서(코어측 참조 모듈) |
| `channels/launcher-stable.json` | 서명된 런처 업데이트 피드(샘플/직전 상태) |
| `launcher-manifest.json` | 런처 매니페스트(버전/업데이트 대상 저장소·피드 URL) |
| `tools/` | 런처 publish·verify·서명·설치 스크립트 |

## 자동 업데이트 (유지됨)

관리자 프로그램의 자동 업데이트 기능은 그대로 보존했습니다.

- 클라이언트측: `shell/WorkKitLauncher/LauncherUpdateService.cs` · `LauncherUpdatePollingService.cs` ·
  `LauncherUpdateApplier.cs` · `LauncherUpdateFeedVerifier.cs` (RSA-PSS 서명 검증 → 다운로드 → 적용).
- 게시측: `tools/publish-launcher-update.mjs` · `tools/publish-github-launcher-update.mjs` ·
  `tools/update/update-signing.mjs` · `tools/verify-launcher-update.mjs`.

이전에 따라 업데이트 대상 저장소를 앱 본체에서 이 조직 저장소로 재지정했습니다
(`launcher-manifest.json` → `moonhyun-cheol/myagent-org`,
피드 URL `…/myagent-org/main/manager/channels/launcher-stable.json`).

> ⚠️ `channels/launcher-stable.json`은 **서명된 문서**입니다. 저장소 이전 후 실제 업데이트를 서비스하려면
> 운영자 서명 개인키(`tools/keys/`, 커밋 금지)로 **다시 서명·게시**해야 합니다. 손으로 JSON을 고치면 서명이 깨집니다.
> 재게시는 위 publish 스크립트로 수행하세요.

## 게시 (이 저장소 `manager/`에서)

사전: .NET 8 SDK, Node, `gh` 로그인, 서명 개인키.

클라이언트는 설치된 MY Agent의 `core/config/defaults/update-public.pem`으로 피드를 검증합니다.
따라서 서명은 **앱 본체(MY Agent) 업데이트와 같은 RSA 키**여야 합니다. 조직 모듈 키와 섞지 마세요.

```bash
cd manager
# 예: MY Agent 제품 repo의 tools/keys/update-private.pem
$env:MY_AGENT_UPDATE_SIGNING_KEY = "C:\\path\\to\\update-private.pem"

npm --prefix ui/work-kit-launcher install
node tools/publish-github-launcher-update.mjs            # dry-run
node tools/publish-github-launcher-update.mjs --confirm  # install-zip + update-zip + 서명 피드
```

피드 게시 위치는 `manager/channels/launcher-stable.json`입니다 (`launcher-manifest.json`의 `update_feed_url`과 동일).

## 독립 구동 배선

- API: 관리자가 로컬 MY Agent Core(`127.0.0.1`, 기본 포트 10200, `/profiles`·`/organization-module`)를 기동·재사용합니다. 이 저장소에 별도 API 서버는 없습니다.
- UI: 현재 MY Agent는 `/launcher/`를 404로 제거했으므로, WebView가 같은 origin의 `/launcher/*`를 로컬 `web/` 파일로 가로채 제공합니다.
- 업데이트 저장소/태그: `moonhyun-cheol/myagent-org`, `launcher-update-{sequence}`.
