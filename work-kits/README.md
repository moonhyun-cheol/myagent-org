# Work kits (CQR profiles)

Authoring tree for **work-kit catalog feed** (R-612). Not the organization-module ZIP.

## Layout

```
work-kits/
  catalog-meta.json          # channel, sequence, GitHub repo for release assets
  profiles/
    {group}/
      group.json
      {kit-id}/
        shelf.json           # pins, pull, label — per-shelf tarball root
        agent-plugins/…      # optional pull payload
        skills/…             # optional pull payload
channels/
  work-kits.json             # generated catalog (plain JSON, unsigned)
```

## CQR kits

| `group/id` | Label |
|------------|-------|
| `cqr/brand-info` | CQR 브랜드 정보 |
| `cqr/product-dev` | CQR 제품개발 |
| `cqr/ops` | CQR 명령어 모음 |

Pins align with `agent-module/skills/manifest.json` (R-613). Organization skills ship in the **signed org ZIP**, not in kit tarballs.

## Commands

```bash
npm run verify:work-kits
npm run publish:work-kits        # writes channels/work-kits.json + deploy/output/*.tar.gz
npm run publish:work-kits -- --bump   # increment catalog sequence
```

MY Agent resolves `work_kit_catalog_feed_url` → `channels/work-kits.json` on this repo.
