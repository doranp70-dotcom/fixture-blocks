# Weekly refresh runbook

Run every Monday morning (after the weekend round) — by the scheduled Claude task, or by hand.
The dashboard's artifact URL is `https://claude.ai/code/artifact/5398eee2-48dc-44fa-ace3-7b354a290c1a`.

## 0. Get the project
```
git clone <repo-url> fixture-blocks && cd fixture-blocks
pip install pandas numpy scipy openpyxl   # if missing
mkdir -p inbox
```

## 1. Fetch each source and drop the text in `inbox/` (formats in `ingest.py`)
Only WebFetch reaches the web from a cloud session (no shell internet). For every fetch, ask for the
raw text verbatim — never a reformatted table (the summariser drops rows when it reformats).

| File to write | URL | Prompt to use |
|---|---|---|
| `inbox/fixtures_E0.txt` | https://fixturedownload.com/results/epl-2026 | "Output every fixture row verbatim as: round, date, home team, away team, result. Include all rows on the page, no truncation." |
| `inbox/fixtures_E1.txt` | https://fixturedownload.com/results/championship-2026 | same |
| `inbox/fixtures_E2.txt` | https://fixturedownload.com/results/efl-league-one-2026 | same |
| `inbox/fixtures_E3.txt` | https://fixturedownload.com/results/efl-league-two-2026 | same |
| `inbox/xg_E0.txt` … `E3.txt` | https://www.oddalerts.com/xg/premier-league · /xg/championship · /xg/league-one · /xg/league-two | "Output the entire 'Recent Results with xG' section as plain text: each date heading on its own line exactly as shown (e.g. 'Sat, Sep 5'), then one line per match formatted as homeXG\|Home Team\|H - A\|Away Team\|awayXG. Every match, no omissions, no commentary." |
| `inbox/matchodds_E0.txt` … `E3.txt` | https://www.football-data.co.uk/mmz4281/2627/E0.csv (E1, E2, E3) | "Output the raw CSV verbatim, header line first, every row, every column, no reformatting." If it truncates, fetch again by date range ("only rows dated after 20/09/2026") and concatenate under one header. |
| `inbox/matchodds_upcoming.txt` | https://www.football-data.co.uk/fixtures.csv | same |
| `inbox/odds_live_E0.txt` … `E3.txt` | https://www.bet365.com/hub/en-gb/football/football-competitions/premier-league · /championship · /league-one · /league-two | "List every outright (season-long) market on this page. For EACH team-based market, output the market name as a heading line, then every team and its fractional odds in page order as 'Team odds, Team odds, ...'. Include all rows (20 teams for the PL, 24 for the EFL). Do not summarise or omit teams." |
| `inbox/manual.json` | the artifact database, collection `manual` (Artifact tool, `read_db` / `list`) | save the documents as a JSON list of `{id, hg, ag, hxg, axg}` (id = the document id) |

Fallbacks if a source is down: Squawka (`/en/features/premier-league-xg-table/`, Opta, PL only — keep it in
`xg_E0.csv`, never mixed into the OddAlerts file); statz.ai `/competitions/<league>/xg` for aggregate cross-checks;
Oddspedia Insights / justbookies for outright prices (see `data/odds_live_notes.md`).

## 2. Ingest, build, check
```
python ingest.py        # merges inbox/ into data/, prints what changed (also inbox/last_ingest.log)
python build.py         # model -> out/fixture_blocks_2026-27.xlsx + out/fixture_blocks.html, history/<date>/
```
Sanity checks before publishing: every division's "games played" in the build output went up by the
number of games that weekend; no "unknown team" lines in the ingest log (add aliases to `names.py` if so);
`out/this_week.csv` lists next weekend's games; the Movers line names plausible teams.

## 3. Publish
- Republish the dashboard: Artifact tool, `file_path: out/fixture_blocks.html`, `url:` the artifact URL above
  (omit `capabilities` so the stored `db` grant carries forward). Label it with the date.
- Send `out/fixture_blocks_2026-27.xlsx` to the user (SendUserFile).
- `git add -A && git commit -m "Weekly refresh <date>" && git push`.

## 4. Summary message
One short paragraph: rounds ingested per division, the top movers (from build.py's output), any new scanner
flags, and anything that failed or looked wrong. Never paper over a source that didn't load — say which one and
that its columns are stale this week.
