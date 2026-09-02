# Automaton / OpenClaw (organization module)

회사 업무 slash·Bulbasaur 연동. **실행은 중앙 허브**(지금=운영자 PC, 이후=사내 서버)에서만 돈다.  
전체 구조: [docs/OPERATOR-HUB.md](../docs/OPERATOR-HUB.md)

## Files (all required for publish)

| File | Purpose |
|------|---------|
| `automaton-tools.manifest.json` | Slash → tool id (e.g. `/childasin` → `child_asin_lookup`) |
| `openclaw-workflow-map.json` | Tool id → Bulbasaur Adapter payload |
| `deploy-overrides.json` | Actor / fallback. **Hub URL은 publish 시 operator.json에서 주입** |

## Hub (publish 시 주입)

`_local/operator.json` → `npm run publish:update` → 배포 ZIP의 `deploy-overrides.json` + `module.json`

| hub 필드 | MY Agent 동작 |
|----------|----------------|
| `openclaw_adapter_base_url` | slash → `POST {url}/cqr/adapter/request` |
| `brand_manual_url` | 채팅에 ORGANIZATION BRAND MANUAL 주입 |
| `product_data_base_url` | 채팅에 PRODUCT DATA API 주입 (예정/연결 시) |

**토큰은 publish에 넣지 않음.** 각 클라이언트 `data/vault/openclaw-adapter.json`:

```json
{
  "base_url": "허브와 동일한 Adapter URL",
  "token": "Bulbasaur MAIN_API_TOKEN",
  "source": "manual"
}
```

## Runtime path

```
MY Agent slash → automaton-tools.manifest.json
  → openclaw-workflow-map.json
  → POST {hub}/cqr/adapter/request  (Bearer token from vault)
  → Bulbasaur on hub PC/server
```

## 사내 서버 이전

`operator.json` hub URL만 변경 → `update_sequence` bump → `publish:update` → 클라이언트 모듈 업데이트.

## Slash commands

`/반품율분석` `/반품율검토` `/카이제곱` `/미국샘플재고` `/CTR` `/발주검토자료` `/라이브계절지수` `/발주서등록` `/발주정보용판매` `/박스바코드생성` `/모델가계도` `/childasin`

Bulbasaur `command_id`와 일치해야 함 (예: `child_asin_lookup`).
