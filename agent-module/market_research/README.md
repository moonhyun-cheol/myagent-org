# CQR Market Research — 심층리서치 → (요청 시) 타당성 → (승인 후) 기획서

## Open Codex (recommended)

Chat in **MY_Open_Codex** → **CQR_MARKET_RA**

```
/심층리서치 Liberator summer cargo — Amazon US 1-3★ review pain, 5.11 TRUEWERK $35-65
→ research_report.md (pain · gaps · 컨셉 후보)

(리서치 확인 후, 원할 때만)
/타당성 CONCEPT_B로 RAG 검토해줘
→ feasibility_review.md → HITL

둘 다 승인해줘
→ final_product_plan.md

@final_product_plan.md → CQR_CONCEPT_RA (촬영·.dev)
```

**기본은 심층리서치만.** 타당성·기획서는 사용자가 **명시 요청**할 때만 진행.

**Sync inject + agent after edits:**

```powershell
powershell -File ..\..\MY_Open_Codex\scripts\sync-market-ra.ps1
```

See [CQR_MARKET_INJECT.md](CQR_MARKET_INJECT.md) for agent rules.

## Local wrapper (Codex agent calls this)

```powershell
cd market_research
.\scripts\run.ps1 심층리서치 "Liberator summer cargo — Amazon review pain"
.\scripts\run.ps1 pipeline start "..."    # 타당성 — 명시 요청 시
.\scripts\run.ps1 pipeline approve "둘 다 승인해줘"
.\scripts\run.ps1 status
```

Set `CQR_PIPELINE_VENV` if Python venv is not `C:\Users\Temp\cqr-pipeline-venv`.

## Setup

```powershell
cd market_research/cqr_product_pipeline
pip install ".[dev]"    # non-editable — safer on Korean-path workspaces (Windows cp949)
```

Set `CQR_MANAGER_ROOT` to the `cqr_brand_manager` repo root if imports fail.

### NAS Ollama (real LLM — drop `-DryRun`)

**PowerShell에서는 `KEY=value` 한 줄 입력이 안 됩니다.** 아래 중 하나를 쓰세요.

**방법 A — `.env` 파일 (권장, 한 번만 설정)**

`market_research/cqr_product_pipeline/.env` 에 저장 (이미 예시 있음):

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.6:35b
OLLAMA_BASE_URL=http://192.168.1.32:11434
```

**방법 B — 현재 세션만 환경변수**

```powershell
$env:LLM_MODEL = "qwen3.6:35b"
$env:OLLAMA_BASE_URL = "http://192.168.1.32:11434"
```

**실행 경로** — `run.ps1`은 `MY_Open_Codex`가 아니라 `cqr_brand_manager\market_research` 에 있습니다:

```powershell
cd C:\Users\Temp\Desktop\업무\cqr_brand_manager\market_research
.\scripts\run.ps1 pipeline start "Liberator summer cargo gap"
```

`-DryRun` 없으면 feasibility · deep research · product planning 모두 LLM 사용. 실패 시 feasibility는 heuristic fallback (`LLM_FALLBACK_HEURISTIC=true`).

```powershell
.\scripts\run.ps1 pipeline start "Liberator summer cargo gap" -DryRun   # 테스트용
python -m cqr_product_pipeline.cli.run_feasibility --input output\...\research_report.json --use-llm
```


```powershell
python -m cqr_product_pipeline.rag.ingest --rebuild
```

## CLI (direct)

```powershell
# Deep research only (Gemini-style)
python -m cqr_product_pipeline.cli.run_research --brief "..." --dry-run

# Full pipeline
python -m cqr_product_pipeline.cli.run_pipeline --brief "..." --dry-run --thread-id mysession
python -m cqr_product_pipeline.cli.run_pipeline --resume --approve-text "A 승인" --thread-id mysession
```

## Tests

```powershell
pytest
```

## Handoff

| Agent | Role |
|-------|------|
| **CQR_MARKET_RA** | 시장조사 · 타당성 · 기획서 |
| **CQR_CONCEPT_RA** | 촬영 컨셉 · 무드 · `.dev` · `.art` |

See [docs/plans/cqr_product_pipeline.md](../docs/plans/cqr_product_pipeline.md).
