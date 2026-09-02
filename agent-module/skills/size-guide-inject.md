# Size Guide — Verify-First Inject

## Workflow

```
- [ ] Open product URL (browser)
- [ ] Dismiss cookie/consent if blocking
- [ ] Open size chart (Find your size / Size Chart)
- [ ] Select category tab (Over Pants vs Pants, etc.)
- [ ] Toggle inch/cm to match user input
- [ ] Extract table → JSON
- [ ] Match measurements → recommendation
```

## Chart extraction (browser)

1. Click **Find your size** / **Size guide** / **Size Chart**
2. Click **Or check size chart** if a wizard opens first
3. Select product-category tab
4. Toggle unit
5. Read `table` or `.size-chart` / `.size-suggester` modal text

Normalize columns:

| Page label | JSON field |
|------------|------------|
| Belly circumference, Waist, (C) | `waist_min` / `waist_max` |
| Inseam, (D) | `inseam_min` / `inseam_max` |
| Chest, Bust | `chest_min` / `chest_max` |

```json
{
  "scheme": "alpha | waist_inseam | numeric_eu",
  "unit": "inch | cm",
  "category": "over_pants",
  "source_url": "https://...",
  "rows": [
    { "size": "L", "waist_min": 34.5, "waist_max": 36.5, "inseam_min": 32.5, "inseam_max": 33.0 }
  ]
}
```

Save extracted charts under `tools/size_guide/presets/` (git-tracked samples) or ephemeral cache — never commit user PII.

## Match inputs

- `waist_in` / `waist_cm` — belt line
- `inseam_in` / `inseam_cm` — optional
- `layering` — over-pants / shell over gear
- `reference_size` — e.g. US L (fallback only)

Run matcher:

```bash
python tools/size_guide/match_size.py CHART.json --waist 35 --inseam 32 --unit inch --layering
```

Or pipeline:

```bash
python pipelines/size_guide.py match --preset ufpro_over_pants --waist 35 --unit inch
```

## Brand presets (hints — always re-verify)

### UF PRO (ufpro.com)

| Product | Scheme | PDP sizes | Chart opener |
|---------|--------|-----------|--------------|
| Combat/Tactical pants | waist_inseam | 34/32, 36/32 | Size Charts footer |
| Over pants (Monsoon XT) | alpha | S–3XL | Find your size → Or check size chart |
| Jackets, tops | alpha | letter | same modal |

Modal: `.size-suggester`, `.size-chart`. Tabs: Pants | Over pants | Shorts | …  
Unit toggle: `.input__checkable` (inch/cm).

**Monsoon XT Over Pants — L (inch, verified sample):** waist 34.50–36.50, inseam 32.50–33.00. US men's L → **L**, not 36/32.

Preset file: `tools/size_guide/presets/ufpro_over_pants.json`

## Pitfalls

| Issue | Fix |
|-------|-----|
| Chart in JS modal | Click Find your size; no static fetch |
| Wrong tab | Over pants ≠ Pants |
| Scheme confusion | Read PDP size buttons first |
| LLM brand memory | Ignore; use extracted table only |

## Example (UF PRO Monsoon XT)

User: 미국 L 사이즈면? + URL

Verified answer: **L**, confidence medium (reference size), over-pants layering caveat if waist with layers > 36.5" → XL.

Wrong: 36/32 (combat scheme on over-pants product).
