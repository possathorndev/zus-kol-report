---
name: foxtells-generate-report
description: >-
  Generate and update a brand's KOL campaign HTML report from Foxtells
  CSVs in data/ or legacy raw.csv. Use when adding campaigns, regenerating
  index.html, fixing report stats, setting brand colors (--color), or working
  with generate_zus_kol_report.py, Foxtells exports, KOL metrics, or campaign
  switcher UI. Invoke as /foxtells-generate-report.
disable-model-invocation: true
---

# Foxtells generate report

Project skill for the KOL static report in this repository. Read [AGENTS.md](../../../AGENTS.md) for full schema, column aliases, and combined-view rules.

**If the user has not specified the brand name, ask for the full brand name and the short watermark word before running. Default to ZUS Coffee / ZUS only for this repo.**

**If the user has not specified a brand color, ask whether they want the default blue theme or a custom hex (e.g. `#eec8cb`). Pass it with `--color` when regenerating.**

## Quick start

```bash
python3 generate_zus_kol_report.py --data-dir ./data --brand "ZUS Coffee" --brand-short "ZUS" --output ./index.html
```

Custom brand color (full theme derived from the hex; header/footer auto-darkened for contrast):

```bash
python3 generate_zus_kol_report.py --data-dir ./data --brand "Molly Tea" --brand-short "MollyTea" --color "#eec8cb" --output ./index.html
```

Open `index.html` in a browser. Use the campaign switcher for **All Campaigns** or a single campaign.

## Add a campaign

1. Export from Foxtells and save as `data/<brand-short> - <name>.csv` (keep the Foxtells layout: metadata rows 1–5, header row with `NO.` in column A).
2. Regenerate with the command above — new CSVs are picked up automatically.
3. Do **not** hand-edit `index.html`; always regenerate.

Campaign display name comes from the `Project` cell on the `In Process` row, else the filename stem (without `<brand-short> - `).

## Constraints

- Only metric columns matter; ignore Status, Link, Follower, drafts, Caption, etc.
- Foxtells `Reels - *` / `Tiktok - *` columns map to canonical IG Reels / TT names (see AGENTS.md).
- **Combined view**: same KOL in multiple campaigns = **separate table rows** with a Campaign column — never merge by username.
- Post tab/sections hide automatically when a view has no post view data.
- **Brand color**: optional `--color "#RRGGBB"`. Omit for default blue. Custom hex derives the full palette; header/footer use a darkened variant for white text.

## Legacy single file

Canonical `raw.csv` format (header on row 1, `List` + `IG - *` / `TT - *` columns):

```bash
python3 generate_zus_kol_report.py --input ./raw.csv --brand "ZUS Coffee" --brand-short "ZUS" --output ./index.html
```

## Verification

After `--data-dir`:

```bash
python3 generate_zus_kol_report.py --data-dir ./data --brand "ZUS Coffee" --brand-short "ZUS" --output ./index.html
```

Expect exit 0, per-campaign row counts printed, and in `index.html`:

- Campaign pills: **All Campaigns** + one per `data/*.csv`
- Combined KOL table includes **Campaign** as first column when viewing All Campaigns

## Changing report logic

Edit `generate_zus_kol_report.py`, then regenerate `index.html`. Keep `AGENTS.md` in sync if column mapping or CLI flags change.
