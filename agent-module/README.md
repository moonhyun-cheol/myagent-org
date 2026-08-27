# Organization pack source

This folder is the MY Agent organization module. `npm run publish:update` packs it into `modules/organization`.

| Path | Role |
|------|------|
| `skills/` | Chat overlay: 시장조사, 컨셉 RA |
| `brand/` | Landing overlay + live brand-manual fetch marker |
| `prompt_concept/` | Concept RA (`MY_prompt.md`, AGENTS.md) |
| `data/` | Curated SKU/spec snapshot (not Excel/chroma) |
| `market_research/` | Market RA pipeline |
| `pipelines/market_research.py` | Pack contract entry |

Live brand philosophy: `http://hub.example.internal:8080/api/brand-manual/current.md` (set on `module.json`).

Do not put `.chroma`, `options.db`, Excel, `output/`, or `.env` here.
