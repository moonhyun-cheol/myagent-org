# CQR 운영 허브 — 뭐가 뭔지 (사내 서버 이전 전제)

한 줄 요약: **MY Agent는 얇은 클라이언트**, **명령·데이터·매크로는 중앙 허브**에서 실행된다.  
지금은 운영자 PC가 허브, 나중에 **사내 서버로 URL만 옮기고 다시 publish**하면 된다.

## 구성도

```
┌─────────────────────────────────────────────────────────────┐
│  중앙 허브 (지금: 운영자 PC → 이후: 사내 서버)                  │
│                                                             │
│  :8790  OpenClaw Adapter + Bulbasaur  ← /childasin 등 slash │
│  :8080  Brand manual API + Product data API  ← 채팅 정본     │
│         NAS / 매크로 / ChildAsin 출력  ← Adapter가 직접 접근   │
└───────────────────────────▲─────────────────────────────────┘
                            │ HTTP (hub URL)
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   [MY Agent A]        [MY Agent B]        [운영자 MY Agent]
   배포받은 직원          배포받은 직원          본인 PC
```

## 역할表

| 이름 | 뭐냐 | 어디 설정 |
|------|------|-----------|
| **myagent-org** (이 레포) | slash 목록·스킬·작업 키트 **정의** | GitHub |
| **조직 모듈 ZIP** | MY Agent에 설치되는 패키지 | `publish:update` |
| **허브 URL** | Adapter·API 주소 (모두 같은 머신) | `_local/operator.json` → publish 시 ZIP에 주입 |
| **Adapter 토큰** | 허브 인증 | 각 MY Agent `data/vault/openclaw-adapter.json` (git 금지) |
| **작업 키트** | 브랜드/제품개발/명령어 UI 모드 | `publish:work-kits` |

## slash가 도는 경로

```
사용자 /childasin KR…_PR
  → MY Agent (설치된 org 모듈 manifest)
  → 허브 Adapter POST /cqr/adapter/request
  → Bulbasaur child_asin_lookup
  → NAS/매크로 (허브 PC 또는 허브가 보는 NAS)
```

배포받은 사람 PC에 Bulbasaur가 없어도 된다. **허브만 살아 있으면** 된다.

## git vs 로컬 (중요)

| 위치 | git | 내용 |
|------|-----|------|
| `operator-config.example.json` | ✅ 커밋 | 빈 템플릿만 |
| `_local/operator.json` | ❌ **절대 커밋 금지** | 실제 IP·NAS·허브 URL |
| `agent-module/data/` | ❌ | 내부 스냅샷 (`.gitkeep`만) |
| `data/vault/openclaw-adapter.json` | ❌ | 각 MY Agent PC 토큰 |

검증: `npm run verify:no-secrets`

## 운영자가 할 일 (지금 — operator_pc)

1. 템플릿 복사 → `_local/operator.json` (gitignore)

```bash
mkdir -p _local
cp operator-config.example.json _local/operator.json
# _local/operator.json 에 hub URL·nas 경로만 채움 (git에 올리지 않음)
```

2. 허브 PC에서 Bulbasaur `start_local1` (Adapter :8790 상시)
3. **허브 URL을 ZIP에 넣을 때만** `npm run publish:update`  
   **아직 미연결이면** `npm run publish:update -- --skip-hub` (IP가 GitHub 릴리스에도 안 들어감)
4. 각 클라이언트 `data/vault/openclaw-adapter.json` — `base_url` + `token` (git/ZIP 금지)

## 사내 서버 이전 (company_server)

1. 허브 서비스(Adapter, API, NAS 마운트)를 **사내 서버**로 이전
2. `_local/operator.json` 의 `hub` URL만 새 호스트로 변경
3. `deployment_phase`: `"company_server"`
4. `manifest.json` `update_sequence` 올리고 `npm run publish:update`
5. 클라이언트 MY Agent 모듈 업데이트
6. 클라이언트 vault `base_url` 갱신 (또는 재배포 안내)

**레포 코드·slash 정의는 그대로**, **URL만 바뀐다.**

## git에 넣으면 안 되는 것

- 허브 IP/hostname이 들어 있는 `_local/operator.json`
- `openclaw-adapter.json` 토큰
- `agent-module/data/` 내부 스냅샷

## 자주 헷갈리는 것

| 질문 | 답 |
|------|-----|
| Cursor / 이 레포 clone | 개발용. slash 실행 안 함 |
| MY Agent | 직원 앱. slash·채팅 클라이언트 |
| Bulbasaur / Adapter | 허브에서만 실행 |
| update-14 | `/childasin` 포함 org 모듈 |
| work-kits-2 | 작업 환경(브랜드/제품개발/명령어) UI |
