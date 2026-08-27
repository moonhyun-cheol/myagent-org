# MY_CUSTOM_CODEX-COMPANY

Independent **organization module** update stream for [MY Agent](https://github.com/moonhyun-cheol/MY_CUSTOM_CODEX).

This repository is not the core app. Core updates and module updates are signed, versioned, and published separately.

## Layout

- `agent-module/` — organization pack source (skills, 컨셉 RA, 시장조사 파이프라인)
- `manifest.json` — module version and `update_sequence`
- `channels/` — signed feed published on release (`npm run publish:update` writes `channels/{channel}.json`)
- `schema/` — `module.json` and organization skills-manifest contracts
- `tools/publish-module-update.mjs` — packs `agent-module/` into `modules/organization`

Excel/RAG 코퍼스(`.chroma`, NAS extracts)는 이 git에 넣지 않습니다. 너무 크고 자주 바뀝니다.

## End-user install

MY Agent 설정 → 스킬 → 조직 모듈에서 이 저장소가 만든 서명 ZIP을 고르면 추가됩니다. 피드 JSON은 필요 없습니다.

## Commands

```bash
npm run admin:update-keygen
npm run admin:update-key-status
npm run verify:module-pack
npm run publish:update
```

The module private signing key stays in `tools/keys/` and must not be committed.
