# Minyoung CQR Brand Image Concierge

**한글 설명서:** [PROMPT_설명서.md](PROMPT_설명서.md)

AI concierge for **CQR brand image** on Amazon US — scene briefs, listing-matched AI prompts, upload QC, and product dev visual spec.

## Quick start

```powershell
cd cqr_brand_manager\prompt_concept
python scripts/build_local_bundle.py
python scripts/build_platform_prompts.py
# Open Codex CQR_CONCEPT_RA 연동 (관리자만)
powershell -File ..\..\MY_Open_Codex\scripts\sync-prompt-ra.ps1
```

Paste platform file as **sole** system instructions — no Knowledge attachments.

| File | Use |
|------|-----|
| **MY_prompt_gemini.md** | Gemini Gem — vision + Imagen |
| **MY_prompt_claude.md** | Claude Project |
| MY_prompt_bundle_slim.md | ChatGPT / generic |

## What it does

| Intent | Output |
|--------|--------|
| Product + shoot / concept / mood (default) | **CONCEPT_CORE** (10 sections) |
| `.ff` / 풀브리프 / 캐스팅 / 컷시트 | FULL + CONCEPT-CONCRETIZATION-PACK |
| `.art` / listing refs | COMPACT + **main one (PT02)**; more only on request; no upsell |
| Upload + QC | Brand fit / TPO / Anti-AI report |
| `.dev` | Pocket / waist / colorway matrix |

Default `.art`: **one main (PT02)**. Extra slots only if user asks. Do not offer `.art` after concept.

## Test prompts

```
CQ-TLP125-SGN 촬영 컨셉
TLP710-ONV .art
(upload) QC — 브랜드 맞나?
Liberator TLP130 .dev
```

## Key docs

- `../data/CQR_BRAND_IMAGE_PLAYBOOK.md` — role, router, QC, compass
- `../data/CQR_VISUAL_DNA.md` — slots, Anti-AI, casting map
- `MY_prompt.md` — source rules
