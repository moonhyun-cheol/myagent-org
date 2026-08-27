# 이식 지도 — 조직 모듈 `myagent-org`

작업은 **이 저장소만** 한다. 구 저장소 CQR_PA는 보관용이며 여기서 개발하지 않는다.

**이 저장소: organization-module `1.0.0-beta.1` · `update_sequence` 5 · GitHub `moonhyun-cheol/myagent-org`**

구 저장소에 남은 *조직* 수정만 여기 넣는다. 앱 본체 수정은 `myagent`다.

## 어디로

| 구 저장소에서 고친 것 | 넣는 곳 | 이 저장소 경로 |
|---|---|---|
| 컨셉 RA 스킬·프롬프트 | **여기** | `agent-module/skills/brand-concept.md`, `agent-module/prompt_concept/` |
| 시장조사 스킬·파이프라인 | **여기** | `agent-module/skills/market-research.md`, `agent-module/market_research/` |
| 브랜드 데이터·카탈로그 | **여기** | `agent-module/data/` |
| 랜딩 브랜드 오버레이 | **여기** | `agent-module/brand/` |
| 스킬 목록 (조직 모드) | **여기** | `agent-module/skills/manifest.json` |
| 창/API/UI/설치기 | **`myagent`** | `shell/`, `core/`, `ui/workspace/` — 이 저장소에 넣지 말 것 |
| 내장 스킬 (코드/랜딩/프롬프트 마스터) | **`myagent`** | `core/config/defaults/skills/` |
| `.chroma`, Excel, NAS 추출 | 넣지 않음 | gitignore |

CQR_PA에는 `agent-module/`이 없다. 예전에 코어 스킬 폴더에 있던 조직 문서는 **복사해서** 위 경로에 둔다. 코어 `skills/manifest.json`에 `org:*`를 다시 넣지 않는다.

## 지금 뭐가 다른지

코어 쪽 파일 목록은 코어 저장소에서:

```powershell
$env:MY_AGENT_LEGACY_ROOT = "C:\Users\Temp\Desktop\업무\CQR_PA"
npm run port:status
```

`apply_org`로 나온 경로만 이 저장소 `agent-module/`에 옮긴다.

## 형제 저장소

코어 버전·시퀀스는 `MY_CUSTOM_CODEX/repo-target.json`.
