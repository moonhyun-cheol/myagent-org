# MY_CUSTOM_CODEX-COMPANY

Independent **organization module** update stream for [MY Agent](https://github.com/moonhyun-cheol/MY_CUSTOM_CODEX).

This repository is not the core app. Core updates and module updates are signed, versioned, and published separately. Additional module repositories can be attached later without changing the core.

## Layout

- `manifest.json` — module version and `update_sequence`
- `channels/` — signed feed published on release
- `tools/publish-module-update.mjs` — builds the module zip from a private source tree

## Source vs public git

Plaintext organization content is **not** stored in this public git history. The publish tool packs the private source checkout into `deploy/output/` as a signed zip.

Set `MY_AGENT_ORGANIZATION_MODULE_SOURCE` to the private organization source checkout. The publish tool packs that tree into `modules/organization` inside the signed zip.

## Commands

```bash
npm run admin:update-keygen
npm run admin:update-key-status
npm run publish:update
```

The module private signing key stays in `tools/keys/` and must not be committed. Ownership of this GitHub repository can be transferred later without renaming the update contract.
