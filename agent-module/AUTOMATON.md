# Automaton / OpenClaw (organization module)

회사 업무 slash·Bulbasaur 연동 설정은 **이 저장소** `agent-module/` 에만 둔다. 중립 코어(`myagent`)에는 넣지 않는다.

## Files (all required for publish)

| File | Purpose |
|------|---------|
| `automaton-tools.manifest.json` | Slash → tool id (e.g. `/반품율분석` → `amazon_return_manager_direct`) |
| `openclaw-workflow-map.json` | Tool id → Bulbasaur Adapter payload (`safe_code_execution`, `command_id`, …) |
| `deploy-overrides.json` | Actor / fallback only. **Adapter host is not in GitHub.** |

## Secrets and host (never commit)

GitHub 배포에는 토큰도 서버 주소도 넣지 않는다. 활성화 서버도 쓰지 않는다.

각 MY Agent 설치의 `data/vault/openclaw-adapter.json`:

```json
{
  "base_url": "http://ADAPTER-PC:8790",
  "token": "...",
  "source": "manual"
}
```

또는 env `OPENCLAW_ADAPTER_BASE_URL` + `OPENCLAW_ADAPTER_TOKEN`. Adapter PC를 옮기면 `base_url`만 바꾼다.

## Runtime path

```
MY Agent slash → core peekAutomatonIntent(cqrRoot)
  → org automaton-tools.manifest.json
  → core resolveOpenClawWorkflow(toolId, cqrRoot)
  → org openclaw-workflow-map.json
  → POST {vault-or-env base_url}/cqr/adapter/request
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

## Slash commands (org overlay)

Manifest `slash_prefixes` and `openclaw-workflow-map.json` keys must match. Discord Gate 와 동일:

`/반품율분석` `/반품율검토` `/카이제곱` `/미국샘플재고` `/CTR` `/발주검토자료` `/라이브계절지수` `/발주서등록` `/발주정보용판매` `/박스바코드생성` `/모델가계도`

