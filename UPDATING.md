# Weekly update — Fixture Blocks 2026/27

The full runbook (sources, prompts, order of operations) is in WEEKLY.md; `ingest.py` parses raw source text from `inbox/` into `data/`. Three ways, pick whichever suits the week.

## A. No code: type into the workbook
Open `fixture_blocks_2026-27.xlsx` → **Matches** sheet → fill in **HG / AG / Home xG / Away xG** (blue-on-yellow cells) for the games played. Every other sheet recalculates. Kick-off dates that moved can be edited in column E (blocks are fixed at build time, so a moved game stays in its original block until the next rebuild).

## B. Ask Claude
Say "update the fixture blocks" in this session (or a new one, attaching the `fixture-blocks` folder). Claude re-fetches results and xG from the sources below, reruns `build.py`, sends the new workbook and republishes the dashboard at the same link.

## C. Rebuild locally (Claude Code on the Mac)
```
cd fixture-blocks
python3 -m pip install pandas numpy scipy openpyxl   # once
python3 build.py
```
Outputs land in `out/`. Ratings are cached in `data/ratings_*.csv` — the market benchmark never drifts. `--refit` only if you change an odds file (~6 min).

### Sources and fetch recipes
| What | Source | Notes |
|---|---|---|
| Results & fixture dates | `https://fixturedownload.com/results/epl-2026`, `/championship-2026`, `/efl-league-one-2026`, `/efl-league-two-2026` (CSV/XLSX downloads on the same pages: `/download/epl-2026-GMTStandardTime.csv` etc.) | Times on the EFL pages are UTC; Premier League page is UK local. |
| Match xG, all four divisions | `https://www.oddalerts.com/xg/premier-league`, `/xg/championship`, `/xg/league-one`, `/xg/league-two` → "Recent Results with xG" | Sportmonks shot data. Per-match lines are the primary data; the page's own totals differ by up to ~0.2. |
| PL xG (Opta alternative) | `https://www.squawka.com/en/features/premier-league-xg-table/` | Different model — differs by up to ~0.5 xG a match; don't mix into the OddAlerts series. |
| Aggregate cross-check | `https://statz.ai/competitions/<league>/xg` | Team totals incl. xPts. |
| Outright odds (fixed) | fanbanter.co.uk Sky Bet round-ups, 10–14 Aug 2026 | Already in `data/odds_*.csv`; do not change mid-season. |

### File formats
`data/fixtures_E*.csv`: `round,date,home,away,result` — `dd/mm/yyyy HH:MM`, result `2 - 1` or `-`.
`data/xg_E*.csv`: `date,home,away,home_goals,away_goals,home_xg,away_xg,source` — team names can be any form listed in `names.py`.

Team-name aliases live in `names.py` (fixturedownload, Sky Bet and OddAlerts each spell clubs differently). An unknown name stops the build with a clear message — add it to `ALIASES`.
