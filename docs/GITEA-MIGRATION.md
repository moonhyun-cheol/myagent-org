# Gitea 중심 Git·Release 운영 룰북

기본 저장소: `https://git.minyoungcorp.com/ins78516/myagent-org`  
이전 상태: `release-targets.json`의 `migration_phase: "primary"`

GitHub `moonhyun-cheol/myagent-org`는 과거 이력과 기존 클라이언트를 위한 읽기 전용 fallback이다. 새 코드·태그·Release의 기준은 Gitea다.

## 안전 원칙

- 일반 `git pull`·`git push`는 Gitea `origin/main`만 사용한다.
- force push, 태그 이동, 같은 sequence의 재서명을 금지한다.
- 토큰을 remote URL, JSON, source, 로그에 넣지 않는다.
- `_local/`과 서명 개인키는 커밋하지 않는다.
- Release 전에 반드시 코드 커밋·push와 태그 push를 끝낸다.
- 서명된 feed와 Release 자산의 repository/tag/name/size/SHA-256을 한 단위로 관리한다.

## Remote 기준

```powershell
git remote -v
git status -sb
git pull --ff-only
```

정상 기준:

- `origin` → Gitea
- `github` → 기존 GitHub fallback
- `main` upstream → `origin/main`

평소에는 `git pull`, `git push`만 사용한다. GitHub fallback을 갱신해야 할 특별한 경우에만 `git push github main`처럼 명시한다.

## 릴리즈 트랙

| 트랙 | 버전/sequence 원본 | 빌드 | 태그 |
|---|---|---|---|
| 조직 모듈 | `manifest.json` | `npm run publish:update` | `update-{sequence}` |
| Work Kit/Feature Pack | `work-kits/catalog-meta.json` | `npm run publish:work-kits` | `work-kits-{sequence}` |
| 관리자 | `manager/launcher-manifest.json` | manager 게시 도구 | `launcher-update-{sequence}` |

조직 모듈 sequence와 Work Kit catalog sequence, 관리자 sequence는 서로 독립적으로 증가시킨다.

## 표준 릴리즈 순서

### 1. 버전과 sequence 결정

변경된 트랙만 sequence를 올린다. 이미 게시된 `update-19`, `work-kits-5`, `launcher-update-6`은 수정하거나 다시 서명하지 않는다.

### 2. 산출물 생성

```powershell
npm run publish:update
npm run publish:work-kits
# 관리자 변경 시 manager 도구로 install/update 산출물과 channel feed 생성
```

허브 연결을 의도적으로 제외할 때만 `--skip-hub`를 사용한다.

### 3. 전체 검증

```powershell
npm run verify:all
npm run publish:releases          # API 쓰기 없는 dry-run
```

Dry-run에서 대상 repository, 태그 commit, 자산 이름·크기·SHA-256을 확인한다.

### 4. 코드와 태그 게시

```powershell
git add -u
git commit -m "release: publish organization update <sequence>"
git push

git tag update-<sequence>         # 해당 트랙만 생성
git tag work-kits-<sequence>
git tag launcher-update-<sequence>
git push origin <tag>
```

실제 변경 트랙의 태그만 만든다. 게시기는 로컬 태그와 Gitea 태그 commit이 다르면 중단한다.

### 5. Gitea Release 생성·검증

PowerShell User 환경변수 또는 현재 세션에 PAT를 준비한다. 토큰은 채팅이나 명령 기록에 남기지 않는다.

```powershell
$env:MY_AGENT_GITEA_TOKEN = [Environment]::GetEnvironmentVariable("MY_AGENT_GITEA_TOKEN", "User")
npm run publish:releases -- --confirm
Remove-Item Env:MY_AGENT_GITEA_TOKEN
```

트랙별 게시:

```powershell
npm run publish:releases -- --track organization --confirm
npm run publish:releases -- --track work-kits --confirm
npm run publish:releases -- --track launcher --confirm
```

중간에 끊긴 동일 Release를 이어서 채울 때만 `--resume`을 추가한다. 게시기는 기존 동명 자산을 덮어쓰지 않고, 모든 자산을 원격에서 다시 읽어 size와 SHA-256을 확인한다.

### 6. 게시 후 확인

```powershell
git status -sb
npm run publish:releases
```

확인 항목:

- working tree clean
- `main`이 `origin/main`과 동기화
- 세 feed URL이 Gitea raw URL
- Release 자산 수, size, SHA-256 일치

## 기존 signed feed 처리

`channels/beta.json`, `channels/work-kits.json`, `manager/channels/launcher-stable.json`의 seq 19/5/6 문서는 이전 당시 서명된 불변 산출물이다. 내부 `repository`가 GitHub를 가리켜도 Gitea에 동일 태그와 자산이 미러되어 있으므로 손으로 수정하지 않는다. 다음 sequence의 정상 빌드에서 Gitea repository로 새로 서명한다.

## 장애 복구

- Release만 없고 태그가 정상: `npm run publish:releases -- --confirm`
- Release 일부 자산만 있음: `npm run publish:releases -- --confirm --resume`
- 태그 불일치: 게시하지 말고 commit/태그의 올바른 기준을 먼저 확인
- 원격 hash 불일치: 기존 자산을 자동 덮어쓰지 말고 해당 Release를 조사
- 토큰 오류: Gitea PAT의 repository Release 쓰기 권한과 만료 여부 확인
