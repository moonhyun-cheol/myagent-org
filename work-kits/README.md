# Work kits (profile bundles)

Authoring lives in this repo. Runtime consumption is via MY Agent Core `/profiles` API and **WorkKitLauncher.exe**.

## Layout

```
work-kits/profiles/{bundleId}/
  group.json          # bundle metadata (id, label, order)
  {modeId}/
    shelf.json        # work mode: pins, plugins, pull slots
```

- **Bundle** (`group.json`) — sidebar brand/category in launcher (e.g. `cqr`).
- **Mode** (`shelf.json`) — apply unit `{ group, id }` (e.g. `cqr/product-dev`).
- Do not rename skill ids to match shelf ids (R-613). Use `ui.pinned_skill_ids` only.

## Publish

```bash
npm run verify:work-kits
npm run publish:work-kits
```

Feed: `channels/work-kits.json`. Per-shelf tarballs on GitHub release `work-kits-{sequence}`.

## Adding a new bundle

1. Create `work-kits/profiles/{bundleId}/group.json`
2. Add `work-kits/profiles/{bundleId}/{modeId}/shelf.json`
3. Run verify + publish — no launcher/core code changes required
