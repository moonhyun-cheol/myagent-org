# Gitea 이전 실행 절차

대상 저장소: `https://git.minyoungcorp.com/ins78516/myagent-org`

현재 단계는 `release-targets.json`의 `migration_phase: "mirror"`이다. 이 단계에서는 GitHub 피드와 기존 클라이언트 설정을 유지하면서 Gitea에 Git 이력과 최신 Release 자산을 복제한다.

## 안전 원칙

- 전환이 끝날 때까지 GitHub `origin`과 기존 feed URL을 유지한다.
- `git push --mirror`, force push, 기존 태그 덮어쓰기를 사용하지 않는다.
- 토큰을 remote URL, JSON, source, 로그에 넣지 않는다.
- Gitea `main`이 현재 로컬 이력의 조상일 때만 fast-forward push한다.
- Release보다 `main`과 태그를 먼저 동기화한다.
- 설치 클라이언트의 feed URL은 Core·조직 모듈·관리자 브리지 업데이트가 준비되기 전에는 변경하지 않는다.

## 1. Gitea remote와 이력 동기화

기존 GitHub는 `origin`으로 유지하고 Gitea를 `minyoung`으로 추가한다.

```powershell
git remote add minyoung https://git.minyoungcorp.com/ins78516/myagent-org.git
git fetch minyoung --prune --tags
git merge-base --is-ancestor minyoung/main HEAD
```

마지막 명령이 성공한 경우에만 일반 push한다.

```powershell
git push minyoung main
git push minyoung --tags
```

현재 최신 태그 기준:

- 조직 모듈: `update-19` → `b7735ac`
- Work Kit: `work-kits-5` → `b7735ac`
- 관리자: `launcher-update-6` → `6661daa`

현재 로컬에 앞의 두 태그가 없다면 같은 배포 커밋에 생성한 뒤 다시 확인한다.

```powershell
git tag update-19 b7735ac
git tag work-kits-5 b7735ac
```

이미 존재하는 태그를 이동하거나 덮어쓰지 않는다.

## 2. Release 미러 사전 검사

로컬 산출물은 다음 위치에 있어야 한다.

- `deploy/output/` — 조직 모듈, Work Kit, Feature Pack
- `manager/deploy/output/` — 관리자 설치본·업데이트본

사전 검사는 쓰기 없이 Gitea 저장소와 태그를 확인하고, 업로드할 모든 파일의 size·SHA-256을 출력한다.

```powershell
npm run publish:gitea
```

트랙별 검사:

```powershell
npm run publish:gitea -- --track organization
npm run publish:gitea -- --track work-kits
npm run publish:gitea -- --track launcher
```

태그가 없거나 로컬 태그와 commit이 다르면 게시기는 중단한다.

## 3. 토큰 준비와 Release 게시

Gitea Personal Access Token은 저장소 Release 쓰기 권한이 필요하다. 현재 PowerShell 세션의 환경변수로만 전달한다.

```powershell
$env:MY_AGENT_GITEA_TOKEN = "..."
npm run publish:gitea -- --confirm
Remove-Item Env:MY_AGENT_GITEA_TOKEN
```

부분 게시를 재개할 때만 `--resume`을 사용한다.

```powershell
npm run publish:gitea -- --confirm --resume
```

게시기는 세 Release를 생성한다.

| 태그 | 자산 |
|---|---|
| `update-19` | 조직 모듈 ZIP, 서명 feed |
| `work-kits-5` | Work Kit 3종, Automaton Feature ZIP, catalog/index |
| `launcher-update-6` | 관리자 설치 ZIP, 업데이트 ZIP, 서명 feed |

업로드 뒤 각 원격 자산을 다시 읽어 size와 SHA-256을 검증한다. 기존 Release나 이름이 같은 자산을 자동 덮어쓰지 않는다.

## 4. 브리지 업데이트 전 금지 사항

`mirror` 단계에서는 아래 파일의 활성 URL을 Gitea로 바꾸지 않는다.

- `manifest.json`
- `manager/launcher-manifest.json`
- `work-kits/catalog-meta.json`
- 서명된 `channels/*.json`

기존 설치본은 GitHub feed와 GitHub Release URL 계약을 사용한다. 먼저 모든 소비 클라이언트가 Gitea asset URL을 이해하도록 브리지 버전을 배포해야 한다.

관리자 코드에는 다음 호환 경로가 준비되어 있다.

1. `MY_AGENT_UPDATE_ASSET_URL_TEMPLATE` 환경변수
2. 향후 `launcher-manifest.json`의 `update_asset_url_template`
3. feed가 비-GitHub HTTPS 호스트이면 같은 호스트의 Gitea Release URL 자동 구성

조직 모듈과 Work Kit 소비 로직의 브리지 지원은 MY Agent Core 저장소에서 별도로 배포해야 한다.

## 5. 최종 전환 순서

1. Gitea `main`·태그·Release 미러 완료
2. Core에서 명시적 asset URL 또는 Gitea URL template 지원 배포
3. GitHub에 브리지 업데이트 게시
4. 브리지 payload의 다음 feed URL을 Gitea로 설정
5. 설치 확산 확인
6. `release-targets.json`을 `migration_phase: "bridge"`, 이후 `"primary"`로 전환
7. 마지막에만 Gitea를 `origin`으로 승격

```powershell
git remote rename origin github
git remote rename minyoung origin
git branch --set-upstream-to=origin/main main
```

GitHub는 충분한 전환 기간 동안 읽기 전용 fallback으로 유지한다.
