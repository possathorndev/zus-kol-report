# Foxtells KOL reports

One repository contains the shared Python generator and separate static sites for ZUS Coffee, Molly Tea, SB Design Square, and Yonny.

## Generate reports

Run these commands from the repository root. Python needs no third-party packages.

```bash
python3 generate_zus_kol_report.py --data-dir ./data --brand "ZUS Coffee" --brand-short "ZUS" --output ./sites/zus/index.html
python3 generate_zus_kol_report.py --data-dir ./data/molly-tea --brand "Molly Tea" --brand-short "MollyTea" --color "#eec8cb" --output ./sites/molly-tea/index.html
python3 generate_zus_kol_report.py --data-dir ./data/sb --brand "SB Design Square" --brand-short "SB" --output ./sites/sb/index.html
python3 generate_zus_kol_report.py --data-dir ./data/yonny --brand "Yonny" --brand-short "Yonny" --color "#D75E28" --output ./sites/yonny/index.html
```

Each site's assets directory contains copies of the platform icons in the root assets directory. If those icons change, copy them to all sites.

Do not edit generated HTML by hand. The root index.html is the previous ZUS deployment entry point and remains until the existing deployment settings have migrated. The root molly-tea.html is the initial local Molly Tea export. Deploy the brand folders below.

## Vercel settings

Keep the existing Vercel projects and their domains. Connect each project to possathorndev/zus-kol-report after its folder is committed and pushed. Use main as the production branch, Other as the framework preset, an empty Build Command override, and . as the Output Directory override.

| Vercel project | Root Directory |
|---|---|
| zus-kol-report | sites/zus |
| mollytea-kol-report | sites/molly-tea |
| sb-kol-report | sites/sb |
| yonny-kol-report | sites/yonny |

Use each project's Git settings to select the repository. Configure its Root Directory and build settings before triggering a deployment from the updated main commit. Verify the report, campaign tabs, and images before treating the migration as complete.

Each project publishes only its brand folder. Source snapshots, CSV inputs, and calculation notes stay outside those folders. Source issues for the current reports are recorded in zus-stats-2026-11-12.md and molly-tea-stats-2026-11-12.md.

## Archived SB and Yonny reports

The SB and Yonny inputs in data/sb and data/yonny contain only archived rows with numeric platform views. Their NO. column preserves the original archive row number. The full source exports remain in archieve/sb and archieve/yonny (superwadee).

SB contains 31 KOLs with metrics. Yonny contains 10 KOLs for Platinum Pop 0726 and 3 for Seacon Square 0726. The Seacon Square rows retain their source status of In Process despite having metrics. Yonny has no reach columns, so the report hides reach. These figures have not been refreshed from social platforms. See sb-yonny-stats-2026-11-12.md for checked totals and source limitations.
