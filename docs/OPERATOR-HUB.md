# CQR 운영 허브 — 뭐가 뭔지 (사내 서버 이전 전제)

한 줄 요약: **MY Agent는 얇은 클라이언트**, **명령·데이터·매크로는 중앙 허브**에서 실행된다.  
지금은 운영자 PC가 허브, 나중에 **사내 서버로 URL만 옮기고 다시 publish**하면 된다.

## 배포 순서 (필수)

1. **Core 먼저** — Organization Feature 설치/합성을 지원하는 MY Agent Core 업데이트
2. **그다음 조직 모듈** — Automaton 실행 파일이 빠진 기본 모듈 (브랜드·스킬·시장조사)
3. **그다음 Work Kit** — 「CQR 명령어 모음」에 서명된 Feature Pack 포함

Core 없이 새 Work Kit만 올리면 Feature 적용이 실패하거나 slash가 동작하지 않는다.

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
| **기본 조직 모듈 ZIP** | 브랜드·스킬·시장조사 (Automaton 실행 파일 없음) | `publish:update` |
| **Organization Feature Pack** | Automaton slash/workflow/Adapter (`org.cqr.automaton-routing`) | `feature-packs/` → Work Kit asset |
| **허브 URL** | Adapter·API 주소 | `_local/operator.json` → publish 시 주입 |
| **작업 키트** | 브랜드/제품개발/명령어 | `publish:work-kits` |

## Automaton은 Work Kit 적용 사용자만

| 단계 | Automaton slash | Adapter connection | Feature 디렉터리 |
|------|-----------------|--------------------|------------------|
| 기본 조직 모듈만 설치 | 없음 (optional index만) | 없음 | 생성 안 됨 |
| 「CQR 명령어 모음」받기만 | 없음 | 없음 | locker에 zip만 가능 |
| 「CQR 명령어 모음」적용 | 활성 | 활성 | `data/organization-features/org.cqr.automaton-routing/` |
| Feature 비활성화 | slash 제거 | 연결 안 씀 | 파일은 남을 수 있음 |
| Feature 제거 | slash 제거 | 없음 | 디렉터리 삭제 (다른 키트 ref 없을 때) |

기본 조직 스킬(브랜드/시장조사 등)은 Feature 비활성·제거와 무관하게 유지된다.

허브 **entitlement**(누가 Adapter 작업을 실행할 수 있는지)는 클라이언트 Feature 설치와 **별도 보안 계층**이다. 클라이언트에 Feature가 없어도 허브가 거부할 수 있고, Feature가 있어도 허브 정책이 우선한다.

## slash가 도는 경로

```
사용자 /childasin KR…_PR
  → MY Agent (활성 Feature manifest)
  → 허브 Adapter POST /cqr/adapter/request
  → Bulbasaur …
```

미적용 사용자가 같은 slash를 입력하면 LLM으로 가지 않고 **feature_required** 안내만 본다.

## 완료 알림과 진행 표시

조직 명령은 `adapter-job-v1` 계약으로 `명령어 접수 → 진행 중 → 완료`를 표시한다. 상세는 Feature Pack의 `adapter-connection.template.json` progress 필드를 따른다.

## git vs 로컬 (중요)

| 위치 | git | 내용 |
|------|-----|------|
| `operator-config.example.json` | ✅ 커밋 | 빈 템플릿만 |
| `_local/operator.json` | ❌ **절대 커밋 금지** | 실제 허브 URL·NAS·bootstrap 키 |
| `feature-packs/automaton-routing/` | ✅ | Automaton authoring (허브 URL 없음) |
| 배포 Feature ZIP | Work Kit asset | publish 시 hub 주입·서명 |
| 클라이언트 `data/organization-features/` | ❌ | 적용 사용자 PC에만 생성 |
| 클라이언트 로컬 vault | ❌ | bootstrap 장치 토큰 |

검증: `npm run verify:no-secrets`

## 운영자가 할 일 (지금 — operator_pc)

1. Core Feature 지원 빌드가 배포된 뒤 `min_core_sequence`를 그 Core sequence로 설정 (추측 금지)
2. `_local/operator.json` 준비
3. `npm run publish:update` — 기본 조직 모듈 (Automaton 없음)
4. `npm run publish:work-kits` — ops shelf에 서명 Feature Pack 포함
5. 직원: 조직 모듈 업데이트 → MY Agent 관리자에서 「CQR 명령어 모음」받기 → **적용**

## 사내 서버 이전 (company_server)

1. 허브 서비스를 사내 서버로 이전
2. `_local/operator.json` hub URL만 변경
3. `publish:update` + `publish:work-kits` 다시 실행
4. 클라이언트 모듈·Work Kit 갱신

## 자주 헷갈리는 것

| 질문 | 답 |
|------|-----|
| 조직 모듈만 설치 | 브랜드/스킬 OK, Automaton slash 없음 |
| Work Kit 받기만 | Feature 실행 안 됨 (적용 필요) |
| `/심층리서치` | 호스트 로컬 시장조사 (Feature 아님) |
| 허브 entitlement | 클라이언트 설치와 별개 |
