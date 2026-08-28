# Automaton / OpenClaw (organization module)

회사 업무 slash·Bulbasaur 연동 설정은 **이 저장소** `agent-module/` 에만 둔다. 중립 코어(`myagent`)에는 넣지 않는다.

## Files (all required for publish)

| File | Purpose |
|------|---------|
| `automaton-tools.manifest.json` | Slash → tool id (e.g. `/반품율분석` → `amazon_return_manager_direct`) |
| `openclaw-workflow-map.json` | Tool id → Bulbasaur Adapter payload (`safe_code_execution`, `command_id`, …) |
| `deploy-overrides.json` | Non-secret OpenClaw defaults (`openclaw_adapter_base_url`, actor, fallback) |

## Secrets (never commit)

MY Agent install: `data/vault/openclaw-adapter.json` — `token` (+ optional signing key). Or env `OPENCLAW_ADAPTER_TOKEN` / `MAIN_API_TOKEN`.

## Runtime path

```
MY Agent slash → core peekAutomatonIntent(cqrRoot)
  → org automaton-tools.manifest.json
  → core resolveOpenClawWorkflow(toolId, cqrRoot)
  → org openclaw-workflow-map.json
  → POST http://127.0.0.1:8790/cqr/adapter/request  (Bulbasaur start_local1.ps1)
```

## Verify

```bash
npm run verify:org-automaton
npm run verify:module-pack
```

## Adding a command

1. Add tool entry to `automaton-tools.manifest.json` (`slash_prefixes`, `default_command`, …).
2. Add matching workflow in `openclaw-workflow-map.json` (mirror `my_openclaw_Bulbasaur/configs/discord_workflow_modes.json`).
3. Bump `manifest.json` `update_sequence` and publish module update.
