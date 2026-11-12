# Molly Tea campaign statistics

Source snapshot retrieved at 2026-11-12 12:42:28 UTC.

[Google Sheets source](https://docs.google.com/spreadsheets/d/1FqC7gEqUY-ZO7i9hngeIl0OkPz41QRDJmLsUywBqrxE/edit)

| Campaign | Completed KOL rows | TikTok views | Instagram Reels views | Total views | Engagements |
|---|---:|---:|---:|---:|---:|
| Molly Tea Special Event | 27 | 172,982 | 44,253 | 217,235 | 4,425 |
| Molly Tea Halloween | 27 | 121,220 | 30,609 | 151,829 | 2,863 |
| Total | 54 | 294,202 | 74,862 | 369,064 | 7,288 |

## Source issues

- The report uses detailed metrics from rows marked Done. Each campaign has 27 completed KOL rows. Special Event has 26 Instagram Reels metric rows. Halloween has 27. The combined KOL count is 54 campaign participations, not 54 unique people.
- The source summary boxes differ from the detailed rows. Special Event shows 180,722 views and 4,017 engagements. Its detailed rows total 217,235 views and 4,425 engagements across TikTok and Instagram. Halloween shows 123,410 views and 2,661 engagements. Its detailed rows total 151,829 views and 2,863 engagements. The report uses the detailed rows. The cause of the differences has not been verified.
- Special Event row 55 and Halloween row 71 both link usedbywpr to Instagram post De_uEBVpH5A. Their recorded metrics differ. Both remain under their source campaigns. Combined totals include both entries and may count the same Instagram post twice. Confirm campaign attribution before treating combined totals as unique content performance.
- Special Event row 37, gungging__g, records Instagram reach of 1,495 against 387 views. Halloween row 52, tu_story, records TikTok reach of 2,400 against 2,397 views. Values are preserved as recorded and need confirmation.
- The Google Sheet was read only. Candidate and cancelled rows remain in the snapshot and are excluded from the performance report.

## Calculations

- Engagements equal likes plus comments plus shares plus reposts plus saves. TikTok has no repost field in this sheet.
- Aggregate ER is total engagements divided by total views, multiplied by 100. The HTML report displays mean KOL ER, the average of individual post rates. The CSV includes both.
- Reach totals sum recorded post reach. They do not measure unique people across posts or campaigns.
- Metrics are a snapshot of the Google Sheet. Live social-platform counts were not checked.

## Files and rebuild

- molly-tea.html is the generated report. index.html remains the ZUS report.
- data/molly-tea contains the two completed-campaign CSV inputs.
- source/molly-tea-2026-11-12.json preserves relevant source fields and original sheet row numbers.

```bash
python3 generate_zus_kol_report.py --data-dir ./data/molly-tea --brand "Molly Tea" --brand-short "MollyTea" --color "#eec8cb" --output ./molly-tea.html
```

## Verification

Checked all platform totals against the source snapshot independently of the CSV parser. Checked KOL identities, mean KOL ER, combined totals, three campaign panels, the pink theme, and local image paths. Browser visual and interaction checks were unavailable.
