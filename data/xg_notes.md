# Team-level xG sources for 2026/27 (E0-E3) - tested 3 Sep 2026

All fetching was done with the WebFetch tool (no shell internet). WebFetch renders a page to
markdown and answers a prompt with a small model, so two caveats apply everywhere below:

1. Some sites (FBref, FootyStats, Wikipedia) came back as STALE cached snapshots from 2025/26
   or earlier, even though the URL is the "current season" URL. Always check the season/date the
   page reports before trusting numbers.
2. The summarising model is unreliable when asked to "list every match" from a busy page - it
   drops rows, mis-assigns numbers to adjacent matches, and mis-counts. Asking for the RAW TEXT of
   a named section verbatim (see recipes) was reliable and reproducible across repeated fetches;
   asking for reformatted tables was not.

## What was obtained

| Div | File | Rows | Source | Provider | Verified against |
|-----|------|------|--------|----------|------------------|
| E0 Premier League | xg_E0.csv | 20 (rounds 1-2, complete) | squawka.com PL xG table article | Opta | scores vs worldfootball.net matchday pages and fixtures_E0.csv (all 20 match) |
| E0 (alt) | xg_E0_oddalerts.csv | 20 | oddalerts.com | unnamed (values agree with statz.ai, which credits Sportmonks) | same |
| E1 Championship | xg_E1.csv | 48 (rounds 1-4, complete) | oddalerts.com | as above | scores vs worldfootball.net matchdays 1-4 and fixtures_E1.csv (all 48 match) |
| E2 League One | xg_E2.csv | 47 (rounds 1-4; Oxford v Reading rearranged to 08/09) | oddalerts.com | as above | scores vs fixtures_E2.csv (all 47 match) |
| E3 League Two | xg_E3.csv | 48 (rounds 1-4, complete) | oddalerts.com | as above | scores vs fixtures_E3.csv (all 48 match) |

Note: EFL divisions have played 4 rounds, not 5 (Aug 14-17, Aug 22-23, Aug 28-30, Sep 1-2).

Team names are as written on the source. PL from Squawka uses short forms (Tottenham, Brighton,
Bournemouth, Manchester United); OddAlerts uses long forms (Tottenham Hotspur, Brighton & Hove
Albion, AFC Bournemouth, Milton Keynes Dons, Queens Park Rangers, Wolverhampton Wanderers,
West Bromwich Albion). The fixtures_*.csv files use a third convention (Spurs, Man Utd, MK Dons,
Nott'm Forest) - a name map is needed to join.

Provider differences matter: Opta (Squawka) and the OddAlerts feed disagree per match by up to
~0.5 xG (e.g. Newcastle v Liverpool: Opta 1.25-3.07, OddAlerts 1.21-3.51; Brentford v Spurs:
3.81-0.62 vs 4.16-0.52). Do not mix providers within one division's time series. If you want one
provider across all four divisions, use xg_E0_oddalerts.csv for the PL.

## Sources tested

### 1. Understat - https://understat.com/league/EPL/2026
- WebFetch: BLOCKED (robots.txt disallowed). Not usable via WebFetch at all. PL only anyway.

### 2. FBref
- https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures -> HTTP 403
- https://fbref.com/en/comps/9/2026-2027/schedule/2026-2027-Premier-League-Scores-and-Fixtures -> 403
- https://fbref.com/en/comps/10/2026-2027/schedule/2026-2027-Championship-Scores-and-Fixtures -> 403
- https://fbref.com/en/squads/18bb7c10/2026-2027/matchlogs/c9/passing/Arsenal-Match-Logs-Premier-League -> 403
- https://fbref.com/en/comps/10/schedule/Championship-Scores-and-Fixtures -> loaded, but it was a
  STALE 2025-26 snapshot (the summariser also reported no xG columns on it).
- https://fbref.com/en/comps/9/Premier-League-Stats -> loaded, but was a 2019-20 era snapshot.
- Verdict: FBref is not usable through WebFetch. The explicit-season URLs are bot-blocked (403) and
  the season-less URLs return old cached copies. This also means the only known public source of
  team xAG/xA per match (FBref passing match logs) is NOT reachable.

### 3. FootyStats
- https://footystats.org/england/premier-league -> loaded, but STALE (2025/26 content). Shows
  team-level "xGF" only; no per-match xG on the overview.
- https://footystats.org/england/championship/xg -> loaded, STALE (mid 2025/26, MP=21-22).
  Team aggregates only (xG, xGA per 90, home/away splits); no per-match values. FootyStats also
  uses its own non-standard xG model.
- Verdict: not usable for 2026/27 via WebFetch, and even when current it is aggregates only.

### 4. Squawka (Opta) - PL only  ** RECOMMENDED for E0 **
- https://www.squawka.com/en/features/premier-league-xg-table/
- WebFetch: readable, current ("Last updated September 1, 2026", covers GW1-GW2). Credits Opta.
- Exposes: an xG-based league table (P/W/D/L/GF/GA/GD/Pts computed from rounded xG results), and
  per-match sections "GW1 xG results", "GW2 xG results", ... each with actual score, raw xG for
  both teams, rounded xG result. No dates on the page (get dates from worldfootball or
  fixtures_E0.csv). No xGA column as such (derive from opponent xG), no xA/xAG, no npxG, no xPts.
- Championship equivalent: none found (Squawka has a Championship predicted table only).
- Caveat: an editorial feature, not a data page; it may stop being updated or may be replaced by a
  new URL mid-season (the 2025-26 one lived at /features/xg-table-premier-league-2025-26/).

### 5. OddAlerts  ** RECOMMENDED for E1, E2, E3 (and usable for E0) **
- https://www.oddalerts.com/xg/premier-league
- https://www.oddalerts.com/xg/championship
- https://www.oddalerts.com/xg/league-one
- https://www.oddalerts.com/xg/league-two
- WebFetch: readable and current (page states "Data last updated: 2026-09-03 05:20:34").
- Exposes: team xG table (#, Team, P, G, xG, /90, +/-), plus separate xGA, npxG, xGoT and xPts
  tables (the page defines npxG and xPts), and a "Recent Results with xG" section listing every
  match this season with home xG, score, away xG, grouped under date headings. The section runs
  back to the first round of 2026/27 and then continues into 2025/26 play-off matches (May 2026)
  which must be dropped. No xA. Provider not named on the page; values agree with statz.ai
  (Sportmonks shot data) to within rounding on per-team totals, so it is very likely Sportmonks.
- Caveat: the aggregate table's xG totals do not exactly equal the sum of the listed per-match
  values (e.g. Man Utd table 6.61 vs 2.18+4.33=6.51; L1 MK Dons 7.76 vs 7.58). Treat the
  per-match list as the primary data and compute your own aggregates.
- Caveat: no dates on individual match lines beyond the day heading; dates in the CSVs come from
  those headings and were cross-checked against worldfootball/fixtures files.

### 6. statz.ai (Sportmonks)
- https://statz.ai/competitions/league-one/xg (also /championship/xg, /league-two/xg,
  /premier-league/xg)
- WebFetch: readable, current 2026/27. Credits "Shot-level data supplied by Sportmonks, updates
  after every finished match".
- Exposes: team aggregates only - #, Team, Played, xG, xGA, xGD, Points, xPts, Points-xPts.
  Fixtures page (/competitions/league-one/fixtures) and match pages (/h2h/...) show scores but NO
  per-match xG in the fetched HTML. Team stats page has no xA/xAG/npxG.
- Use as a cross-check for aggregates, or a fallback if OddAlerts disappears.

### 7. FotMob
- https://www.fotmob.com/leagues/48/table/championship?filter=xg (and /matches/...)
- WebFetch: loads only the JS shell; no table or match data in the HTML. API
  (https://www.fotmob.com/api/leagues?id=48) is robots.txt blocked. Not usable.

### 8. Score/date verification sources (no xG)
- worldfootball.net matchday pages are readable and current, e.g.
  https://www.worldfootball.net/competition/co91/england-premier-league/se121880/2026-2027/ro320915/matchday/md1/results-and-standings/
  https://www.worldfootball.net/competition/co20/england-championship/se123100/2026-2027/ro323575/matchday/md1/results-and-standings/
  (increment md1..mdN). Good for dates and scores.
- premierleague.com -> 401. Wikipedia 2026-27 PL page -> stale pre-season snapshot.

## Availability summary

| Metric | E0 | E1 | E2 | E3 |
|--------|----|----|----|----|
| Per-match team xG | Yes (Squawka/Opta; OddAlerts) | Yes (OddAlerts) | Yes (OddAlerts) | Yes (OddAlerts) |
| Per-match xGA | derive from opponent xG | same | same | same |
| npxG | OddAlerts season table only (not per match) | same | same | same |
| xPts | OddAlerts / statz.ai season tables only | same | same | same |
| xA / xAG (team, per match) | NOT available via WebFetch (FBref blocked) | No | No | No |

## Weekly update recipes

Always use the "raw text, verbatim, no reformatting" prompt style; then parse the 5-line blocks
(homeXG / home / "h - a" / away / awayXG) under each "Day, Mon D" heading. Discard any blocks
dated before 14 Aug 2026 (previous season's play-offs). Diff against the existing CSV on
(date, home, away).

E0 (primary, Opta):
  URL: https://www.squawka.com/en/features/premier-league-xg-table/
  Prompt: "Reproduce the raw text of every section titled 'GW<n> xG results' (all gameweeks on
  the page) EXACTLY as it appears, every line, without reformatting or summarising."
  Each match gives: Actual result / xG result (home xG-away xG) / Rounded xG result. Take dates
  from fixtures_E0.csv or worldfootball. Check the page's "Last updated" line first.
  If the article stops updating, switch to the OddAlerts recipe below (different provider - do not
  splice into the Opta series; keep xg_E0_oddalerts.csv as the parallel series).

E0 (alt), E1, E2, E3 (OddAlerts):
  URLs: https://www.oddalerts.com/xg/premier-league | /xg/championship | /xg/league-one | /xg/league-two
  Prompt: "Output the raw page text of the entire 'Recent Results with xG' section, from the
  first date heading through to the last match, EXACTLY as it appears with line breaks preserved.
  No reformatting, no summarising, no commentary, no omissions."
  If the output looks truncated (fewer matches than rounds x 12), re-fetch asking only for a date
  window ("list ONLY matches dated Aug 24 to Aug 31") and stitch. Year is not printed on the day
  headings - infer it. The section has held ~50 matches so far; if it becomes capped later in the
  season, fetch weekly so nothing scrolls off.

Cross-check for aggregates (any division):
  URL: https://statz.ai/competitions/<premier-league|championship|league-one|league-two>/xg
  Prompt: "Reproduce the full xG table exactly: every row with #, Team, Played, xG, xGA, xGD,
  Points, xPts."
