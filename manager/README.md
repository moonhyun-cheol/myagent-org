# MY Agent 관리자 (WorkKitLauncher)

MY Agent **관리자 프로그램**(코드명 `WorkKitLauncher`)을 이 조직 저장소(`ins78516/myagent-org`)에서 관리합니다.
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
  루트 `tools/publish-gitea-releases.mjs` · `tools/update/update-signing.mjs` · `tools/verify-launcher-update.mjs`.

업데이트 대상은 사내 Gitea primary로 설정되어 있습니다
(`launcher-manifest.json` → `ins78516/myagent-org`,
피드 URL `https://git.minyoungcorp.com/ins78516/myagent-org/raw/branch/main/manager/channels/launcher-stable.json`).

> ⚠️ `channels/launcher-stable.json`은 **서명된 문서**입니다. 현재 seq 6 문서는 손으로 수정하지 않습니다.
> 다음 sequence에서 운영자 서명 개인키(`tools/keys/`, 커밋 금지)로 새 Gitea 대상 피드를 생성·게시하세요.

## 게시

사전: .NET 8 SDK, Node, 서명 개인키, Gitea Release 쓰기 PAT.

클라이언트는 설치된 MY Agent의 `core/config/defaults/update-public.pem`으로 피드를 검증합니다.
따라서 서명은 **앱 본체(MY Agent) 업데이트와 같은 RSA 키**여야 합니다. 조직 모듈 키와 섞지 마세요.

```powershell
cd manager
$env:MY_AGENT_UPDATE_SIGNING_KEY = "C:\\path\\to\\update-private.pem"
node tools/publish-launcher-update.mjs --write-channel
node tools/publish-launcher-install.mjs
cd ..
npm run verify:all
npm run publish:releases -- --track launcher       # dry-run
# commit/push와 launcher-update-{sequence} 태그 push 후:
npm run publish:releases -- --track launcher --confirm
```

전체 순서와 재개 방법은 루트 `docs/GITEA-MIGRATION.md`를 따릅니다. `publish-github-launcher-update.mjs`는 GitHub fallback 유지가 필요한 예외 상황에만 사용합니다.

### Gitea 자산 URL

관리자 updater는 `launcher-manifest.json`의 `update_asset_url_template`을 우선 사용하고, Gitea raw feed 호스트에서도 같은 저장소의 Release URL을 구성할 수 있습니다. 현재 manifest는 Gitea template을 명시합니다. 기존 seq 6 signed feed는 이전 당시의 불변 산출물이므로 손으로 바꾸지 않고, 다음 sequence부터 Gitea repository로 새로 서명합니다.

## 독립 구동 배선

- API: 관리자가 로컬 MY Agent Core(`127.0.0.1`, 기본 포트 10200, `/profiles`·`/organization-module`)를 기동·재사용합니다. 이 저장소에 별도 API 서버는 없습니다.
- UI: 현재 MY Agent는 `/launcher/`를 404로 제거했으므로, WebView가 같은 origin의 `/launcher/*`를 로컬 `web/` 파일로 가로채 제공합니다.
- 업데이트 저장소/태그: `ins78516/myagent-org`, `launcher-update-{sequence}`.
