# Open WebUI — CQR Brand Image Concierge 설정·공유 가이드

민영상사 CQR 프롬프트를 Open WebUI **Workspace**에 올려 두었는데, 다른 사람에게 **안 보이거나 링크 공유가 안 되는** 경우가 많습니다.  
Open WebUI는 Gem과 달리 **워크스페이스 항목이 기본 비공개(Private)** 이며, URL만으로 Instructions·모델 프리셋이 전달되지 않습니다.

---

## 1. 왜 안 보이나요?

| 원인 | 설명 |
|------|------|
| **기본 Private** | Workspace → Models / Prompts에 만든 항목은 **본인만** 보임 |
| **RBAC 권한** | 일반 사용자에게 `workspace.models` / `prompts` 접근·공유 권한이 꺼져 있을 수 있음 |
| **베이스 모델 ACL** | 커스텀 모델이 Ollama/OpenAI 등 **베이스 모델** 위에 올라가면, 베이스 모델 권한 없으면 커스텀도 숨김 |
| **링크 공유 한계** | 채팅 링크는 대화만 공유 — **System Prompt·Workspace 모델 정의는 포함되지 않음** |

---

## 2-A. Admin Panel이 **안 보일** 때 (먼저 확인)

**Admin Panel은 `admin` 역할 계정에만** 나타납니다. 일반 `user` / `pending` 계정에는 **메뉴 자체가 없습니다.**

### Admin Panel 위치 (admin일 때만)

1. 화면 **왼쪽 하단** 프로필(아바타) 클릭  
2. 메뉴에서 **Admin Panel** 선택  
   - 일부 버전: 사이드바 ⚙️ Settings 근처

### 안 보이는 대표 원인

| 상황 | 의미 | 할 일 |
|------|------|--------|
| **회사·팀이 운영하는 Open WebUI**에 초대로 가입 | 본인은 **일반 user** — 서버 설정 변경 불가 | **인스턴스 관리자(첫 가입자·IT)**에게 Public 모델 또는 권한 요청 |
| 첫 설치가 아닌 **두 번째 계정**으로 가입 | admin은 **최초 1계정**만 자동 부여 | 관리자에게 role `admin` 또는 모델 공유 요청 |
| 「관리자 승인 대기」 | `pending` 상태 | 관리자가 Users에서 **user**로 승인해야 함 |
| Docker/회사 배포 | UI만 쓰고 **서버 env는 IT만** | §2-B zip 공유가 현실적 |

> **본인이 서버 주인인데도 Admin Panel이 없다면** → 로그인한 계정이 **최초 admin 계정이 아닐** 가능성이 큽니다. 첫 설치 때 만든 계정으로 다시 로그인하거나, [Reset Admin Password](https://docs.openwebui.com/troubleshooting/password-reset) 절차로 admin 복구.

### Admin 없이 할 수 있는 것 (지금 바로)

| 방법 | 설명 |
|------|------|
| **zip 파일 공유** | `MY_prompt_gemini.md` + `PROMPT_설명서.md` → 팀원 각자 Workspace → Models → System Prompt 붙여넣기 |
| **Workspace Access Control** | (권한이 있으면) 본인 모델 편집 → **Access** → 특정 **User / Group**에 Read — Public 없이도 1:1 공유 가능 |
| **Export / Import** | Models Export 권한 있으면 JSON 내보내기 → 팀원 Import |

Admin Panel 없이 **Public 전체 공개**만은 보통 **관리자 또는 Share Models + Public Models 권한**이 필요합니다.

### Admin이 **누구인지** 어떻게 알아?

Open WebUI에는 일반 user가 **관리자 목록을 조회하는 메뉴가 없습니다.** 아래 순서로 찾으세요.

| 순서 | 방법 |
|------|------|
| 1 | **URL·계정을 준 사람** — IT, 팀장, Open WebUI 도입 담당자 (가장 빠름) |
| 2 | **회사 IT 헬프데스크** — “Open WebUI Workspace 모델 Public 공유” 티켓 |
| 3 | **로그아웃 후 로그인 화면** — `SHOW_ADMIN_DETAILS`가 켜져 있으면 **관리자 연락처**가 표시될 수 있음 (설정에 따라 없을 수도 있음) |
| 4 | **승인 대기(pending)였던 적** — 대기 화면에 관리자 이름·이메일이 나왔을 수 있음 |
| 5 | **본인이 서버 주인** — 최초 가입 계정 = admin. DB에서 확인: `SELECT email, role FROM user WHERE role='admin';` |

**규칙:** 같은 인스턴스에서 **맨 처음 만든 계정 1개**가 기본 admin입니다. 이후 admin은 기존 admin만 지정할 수 있습니다.

관리자에게 보낼 문구 예시:

> Open WebUI Workspace에 등록한 `CQR Brand Image Concierge` 모델을 팀과 공유하려 합니다.  
> 접근 제어가 **비공개**만 가능해서 Public/그룹 Read 설정을 부탁드립니다.  
> (또는 Share Models · Public Models 권한 부여)

---

## 2-B. 관리자 — 다른 사람에게 보이게 (인스턴스 내 공유)

### A. 커스텀 모델 공개 (가장 흔한 해결)

1. **Admin Panel** → **Settings** → **Models** (또는 Workspace → Models)
2. CQR용 커스텀 모델 열기
3. **Access / Visibility** 를 **Private → Public** 으로 변경  
   - 또는 특정 **Group**에 Read 권한 부여
4. 같은 화면에서 **System Prompt** 필드에 `MY_prompt_gemini.md` 전체가 들어갔는지 확인

> GitHub Discussion #9058: non-admin이 모델이 안 보일 때 **Private로 남아 있는지**가 1순위 원인입니다.

### B. 그룹·권한 (팀 단위)

**Admin Panel → Users → Groups → [그룹] → Permissions**

| 권한 | 권장 |
|------|------|
| Workspace → Models access | ✅ |
| Workspace → Prompts access | ✅ (프롬프트 템플릿 별도 저장 시) |
| Allow sharing | ✅ |
| Allow **public** sharing | 팀 전체 공개 시 ✅ |

서버 `.env` 예시 (관리자만 변경):

```env
USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS=true
USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS=true
USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_SHARING=true
USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING=true
```

소규모 내부망에서 ACL 관리가 번거로우면 (보안 trade-off):

```env
BYPASS_MODEL_ACCESS_CONTROL=true
```

### C. 베이스 모델 권한

커스텀 모델의 **Base model** (예: `gemini-2.0-flash`, `gpt-4o`)도 해당 사용자/그룹에 **Read**가 있어야 합니다.  
베이스만 Private이면 커스텀 CQR 모델도 목록에 안 뜹니다.

---

## 3. 권장 설치 방법 (한 사람이 세팅 → 팀이 복제)

### Step 1 — 커스텀 모델 생성

| 항목 | 값 |
|------|-----|
| Name | `CQR Brand Image Concierge` |
| Base model | Vision 지원 모델 (Gemini / GPT-4o 등) |
| System Prompt | **`MY_prompt_gemini.md` 전체 붙여넣기** |
| Knowledge / RAG | **첨부하지 않음** (번들에 이미 embed) |

### Step 2 — 프롬프트 갱신 시

```powershell
cd prompt
python scripts/build_local_bundle.py
python scripts/build_platform_prompts.py
```

→ Open WebUI 모델 설정의 System Prompt를 **`MY_prompt_gemini.md`로 다시 교체**

### Step 3 — 팀원에게 전달 (링크 대신 파일)

Open WebUI **워크스페이스 링크만으로는 Instructions가 전달되지 않습니다.** 아래 중 하나를 사용하세요.

| 방법 | 적합한 경우 |
|------|-------------|
| **Public 모델** (§2-A) | 같은 Open WebUI 인스턴스 사용자 |
| **zip 공유** | `MY_prompt_gemini.md` + `PROMPT_설명서.md` → 각자 System Prompt에 붙여넣기 |
| **Export JSON** | Admin이 모델 정의 export → 팀원 import (버전·메뉴에 따라 Export 위치 상이) |

zip 예시:

```
CQR_concierge_share.zip
├── MY_prompt_gemini.md
├── PROMPT_설명서.md
└── SETUP_OPENWEBUI.md   ← 본 파일
```

---

## 4. 동작 규칙 (컨셉 vs `.art`)

| 사용자 입력 | AI 출력 |
|-------------|---------|
| `TLP125 촬영 컨셉` / `.ff` | **FULL 씬 브리프만** — Imagen 프롬프트 없음 |
| listing·A+ **방향**만 언급 | 브리프만 — 이미지 프롬프트 없음 |
| `TLP125 .art` / `컨셉아트` / `프롬프트만` | COMPACT 브리프 + **Imagen Primary / Negative** |
| 이미지 업로드 + QC | QC 리포트만 — `.art` 요청 시에만 재프롬프트 |

이미지 생성 프롬프트가 필요하면 채팅에 **`.art`** 또는 **「프롬프트도 줘」**를 명시하세요.

---

## 5. 문제 해결 체크리스트

- [ ] 커스텀 모델 Visibility = **Public** (또는 그룹 Read)
- [ ] 팀원 계정에 Workspace Models **access** 권한
- [ ] 베이스 LLM도 해당 사용자에게 visible
- [ ] System Prompt = 최신 `MY_prompt_gemini.md`
- [ ] Knowledge/RAG에 중복 md 업로드 **안 함**
- [ ] 공유는 **파일 zip** 또는 Public 모델 — 채팅 URL만 기대하지 않기

---

## 6. 참고

- [Open WebUI Model Management](https://docs.openwebui.com/features/model-management)
- [RBAC / Sharing permissions](https://docs.openwebui.com/enterprise/rbac)
- [Env: USER_PERMISSIONS_WORKSPACE_*](https://docs.openwebui.com/reference/env-configuration/)
