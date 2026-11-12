# Foxtells KOL reports

One repository contains the shared Python generator and separate static sites for ZUS Coffee and Molly Tea.

## Generate reports

Run these commands from the repository root. Python needs no third-party packages.

```bash
python3 generate_zus_kol_report.py --data-dir ./data --brand "ZUS Coffee" --brand-short "ZUS" --output ./sites/zus/index.html
python3 generate_zus_kol_report.py --data-dir ./data/molly-tea --brand "Molly Tea" --brand-short "MollyTea" --color "#eec8cb" --output ./sites/molly-tea/index.html
```

Each site's assets directory contains copies of the platform icons in the root assets directory. If those icons change, copy them to both sites.

Do not edit generated HTML by hand. The root index.html is the previous ZUS deployment entry point and remains until the existing deployment settings have migrated. The root molly-tea.html is the initial local Molly Tea export. Deploy the brand folders below.

## Vercel settings

Keep the existing Vercel projects and their domains. Connect both projects to possathorndev/zus-kol-report after these folders are committed and pushed.

| Setting | ZUS project | Molly Tea project |
|---|---|---|
| Production branch | main | main |
| Root Directory | sites/zus | sites/molly-tea |
| Framework Preset | Other | Other |
| Build Command | Empty override | Empty override |
| Output Directory | . | . |

Use each project's Git settings to select the repository. Configure its Root Directory and build settings before triggering a deployment from the updated main commit. Verify the report, campaign tabs, and images before treating the migration as complete.

Each project publishes only its brand folder. Source snapshots, CSV inputs, and calculation notes stay outside those folders. Source issues for the current reports are recorded in zus-stats-2026-11-12.md and molly-tea-stats-2026-11-12.md.
