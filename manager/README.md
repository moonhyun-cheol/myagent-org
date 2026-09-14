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

## 남은 단계 (이 저장소 루트에서 실행)

이 이전은 파일 배치까지 완료된 상태입니다. 커밋/푸시와 빌드 배선은 이 저장소를 작업 폴더로 연 세션에서 진행하세요.

```bash
# myagent-org 저장소 루트에서
git add manager
git commit -m "manager: MY Agent 관리자(WorkKitLauncher) 복원 및 이전 (자동업데이트 유지)"
git push origin main

# 관리자 SPA 의존성 (lockfile 재생성 포함)
cd manager/ui/work-kit-launcher && npm install

# 자동업데이트 피드 재서명·재게시 (서명 키 준비 후)
node manager/tools/publish-launcher-update.mjs   # 인자는 스크립트 상단 참조
```

## 참고 (빌드 배선 확인 필요)

원본 런처는 앱 본체 코어(`/profiles`, `/organization-module`, `/launcher` 서빙, `WorkEnvironmentUpdatePollingService`)에
결합돼 있었습니다. 이 저장소에서 독립 실행형으로 빌드·구동하려면 API 베이스 URL/포트, csproj 경로, publish 스크립트의
저장소·릴리스 태그 인자를 이 저장소 기준으로 점검해야 합니다. 파일은 원본 그대로이므로 경로 프리픽스(`manager/`)만
반영하면 됩니다.
