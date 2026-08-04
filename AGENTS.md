# ZUS KOL Report

For agent workflows, invoke `/foxtells-generate-report` or see [.cursor/skills/foxtells-generate-report/SKILL.md](.cursor/skills/foxtells-generate-report/SKILL.md).

Generates a static HTML performance report for ZUS Coffee KOL campaigns from Foxtells CSV exports or a legacy canonical CSV.

## Commands

```bash
# Multi-campaign (default): load all data/*.csv, combined + per-campaign views
python3 generate_zus_kol_report.py --data-dir ./data --brand "ZUS Coffee" --brand-short "ZUS" --output ./index.html

# Legacy single file (canonical raw.csv schema)
python3 generate_zus_kol_report.py --input ./raw.csv --brand "ZUS Coffee" --brand-short "ZUS" --output ./index.html
```

`--brand` sets the full name in title, header, and footer (default: `ZUS Coffee`). `--brand-short` sets the header watermark and the filename prefix stripped for campaign names (default: `ZUS`, so `ZUS - Foo.csv` → campaign name `Foo`). `--color` sets an optional brand hex (e.g. `#eec8cb`); omit for the default blue theme. A custom color derives the full palette (backgrounds, ink, tags, platform tints); mid/dark brands keep the hex as primary; pale brands darken header/footer for white text.

## Known brands

| Brand | `--brand` | `--brand-short` | `--color` |
|-------|-----------|-----------------|-----------|
| ZUS Coffee | `ZUS Coffee` | `ZUS` | _(omit — default blue)_ |
| Molly Tea | `Molly Tea` | `MollyTea` | `#eec8cb` |
| Yonny | `Yonny` | `Yonny` | `#D75E28` |

`index.html` is generated output — do not hand-edit; regenerate with the script.

## Canonical schema (`raw.csv`)

| Field | Column |
|-------|--------|
| KOL username | `List` (@ stripped, empty rows skipped) |
| IG Post | `IG - View/Like/Comment/Share/Repost/Save (Post)` — optional |
| IG Reels | `IG - View/Like/Comment/Share/Repost/Save (Reels)` |
| TikTok | `TT - View/Like/Comment/Share/Save` (repost always 0) |

- **parse_num**: strip commas; non-digit → missing
- **ER**: `(likes + comments + shares + saves) / views × 100`

## Foxtells format (`data/*.csv`)

- Rows 1–5 are metadata — skipped
- **Header row**: first row where column A is `NO.`, or any row containing `Tiktok - View` / `Reels - View` / `TikTok Views` / `Reels Views` (Sheets exports may use `Column 1` in A)
- **Campaign name**: `Project` on the `In Process` row; else filename stem with `<brand-short> - ` removed (default prefix: `ZUS - `). If the filename contains `Phase N`, that is appended (e.g. `ZUS x Foo — Phase 1`) so multi-phase exports stay distinct.
- **Campaign id**: slugified filename stem (e.g. `ZUS - 5.5.csv` → `zus-5-5`)

### Column aliases (Foxtells → canonical)

| Foxtells | Canonical |
|----------|-----------|
| `List` (or `Column 3` when names are lost) | `List` |
| `Reels - View` … `Reels - Save` | `IG - View` … `IG - Save (Reels)` |
| `Reels Views` … `Reels Saves` (no dash) | same as above |
| `Tiktok - View` … `Tiktok - Share` | `TT - View` … `TT - Share` |
| `TikTok Views` … `TikTok Saves` (no dash) | same as above |

No Post columns in Foxtells exports — Post tab/sections are hidden when a view has no post data.

`Status` is used only for cross-campaign dedupe: if the same username appears in more than one CSV, blank/`cancel` rows are dropped; if any copy is `Done`, non-Done copies (e.g. re-schedule, In Process) are dropped too. Link, Follower, drafts, Caption, etc. are ignored.

## Combined view (`All Campaigns`)

- Overview, compare, highlights, and benchmarks: pooled across **all** KOL rows from every campaign
- KOL tables: rows concatenated from all campaigns; **Campaign** is the first column
- Same username in multiple campaigns = **separate rows** (not merged), except blank/`cancel` (and non-Done when a Done copy exists) duplicates are dropped as above

## HTML output

- Sticky campaign switcher: **All Campaigns** + one pill per CSV
- Each campaign in a `.campaign-panel[data-campaign]`; only one `.active` at a time
- Table sort and Post/Reels/TikTok tabs are scoped to the active panel
