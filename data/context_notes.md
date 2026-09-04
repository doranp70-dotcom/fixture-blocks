# Context data notes - built 3 Sep 2026 (WebFetch/WebSearch only; shell has no internet)

## 1. team_stats_E0..E3.csv (OddAlerts season-to-date tables)

Source: https://www.oddalerts.com/xg/{premier-league|championship|league-one|league-two}
Page timestamps: PL and Championship "Data last updated: 2026-09-04 03:35:53"; League One and
League Two "2026-09-03 16:25:36". PL covers rounds 1-2 (20 matches), EFL rounds 1-4
(Championship 48, League One 47 - Oxford v Reading postponed to 08/09, League Two 48).

Each division page has five separate tables; each was requested verbatim with its own WebFetch
prompt ("Reproduce the full '<name>' table exactly, every row ...") and the five were joined on
team name. Column meaning on the page:

| CSV column | Page table | Page column | Page definition |
|---|---|---|---|
| played | all | P | matches played |
| goals | xG / npxG / xGoT | G | goals scored |
| xg | xG (also repeated in npxG and xGoT tables) | xG | "total expected goals a team should have scored based on the quality of their chances" |
| xga | xGA | xGA | expected goals conceded (page's xGA table also has GA, /90, +/-) |
| npxg | npxG | npxG | "xG excluding penalties, giving a truer picture of open-play chance creation" |
| xgot | xGoT | xGoT | "Expected goals from shots that were on target only" |
| xpts | xPTS | xPTS | "How many league points a team deserves based on xG performance" |
| points | xPTS | PTS | points earned from results; deductions NOT applied (Southampton shows 7, official 3) |

Columns dropped from the page (not in the requested header): GA (goals against), /90 rates,
+/- (actual minus expected). Nothing is blank - the page supplies every requested column.

Internal consistency checks passed for every division: P/G/xG values identical across the
xG, npxG and xGoT tables; sum(goals) == sum(GA); sum(xG) == sum(xGA) to 0.01; points totals
consistent with match counts (E0 56 pts/20 games, E1 129/48, E2 127/47, E3 126/48).

Caveat (from earlier work, xg_notes.md): OddAlerts' season totals do not exactly equal the sum
of their own per-match xG list (differences ~0.1). These files use the table values as printed.

Cross-check vs https://statz.ai/competitions/<div>/xg (Sportmonks data, 1 dp):
- Played and Points agree for all 92 teams.
- xG and xGA agree to within rounding (<=0.05) for 91 of 92 teams; Blackburn xG 3.04 (OddAlerts)
  vs 3.1 (statz) - a 0.06 gap, i.e. underlying value ~3.05-3.09.
- xPts differs by 0.1-0.15 for a handful (Man Utd 4.94 vs 4.8, Brentford 4.7 vs 4.6, Swansea
  7.16 vs 7.1, Portsmouth 5.66 vs 5.6, Sheffield Wed 9.79 vs 9.7, Blackpool 7.32 vs 7.2, Luton
  6.66 vs 6.6, Bristol Rovers 8.86 vs 8.8). Same shot data, slightly different xPts simulation
  or truncation; not material.
- Both sites appear to run the same underlying provider, so this is a transcription check more
  than an independent-model check. Opta (Squawka) values differ more - see xg_notes.md.

Team names are as printed on OddAlerts (long forms: "Manchester United", "Milton Keynes Dons",
"Queens Park Rangers", "Wolverhampton Wanderers", "AFC Bournemouth", "Brighton & Hove Albion",
"Tottenham Hotspur", "West Bromwich Albion", "Sheffield Wednesday"). All resolve via names.canon().

## 2. europe.csv (9 rows)

Clubs: Champions League - Arsenal (champions), Man City (2nd), Man Utd (3rd), Aston Villa (4th,
also Europa League holders), Liverpool (5th, European Performance Spot). Europa League -
Bournemouth (6th), Sunderland (7th), Crystal Palace (Conference League holders). Conference
League - Brighton (8th; via play-off round). Confirmed by uefa.com key-dates pages, Sky Sports
(premier-league-sides-in-europe-26-27) and the Wikipedia 2026-27 competition pages (whose
36-team league-phase lists are populated).

Matchday windows (first day used in the CSV):
- CL: 8-10 Sep, 13-14 Oct, 20-21 Oct, 3-4 Nov, 24-25 Nov, 8-9 Dec 2026; 19-20 Jan, 27 Jan 2027.
  NOTE: MD1 is 8-10 September, NOT 15-17 September - uefa.com, Sky and Wikipedia all agree.
  (The single autumn FIFA window is 21 Sep-6 Oct 2026, hence no European football then.)
- EL: 16-17 Sep, 15 Oct, 22 Oct, 5 Nov, 26 Nov, 10 Dec 2026; 21 Jan, 28 Jan 2027.
- UECL: 15 Oct, 22 Oct, 5 Nov, 26 Nov, 10 Dec, 17 Dec 2026 (6 matchdays).
Knockout play-offs Feb 2027 onward are not included. uefa.com notes "dates are subject to change".
Sources: https://www.uefa.com/uefachampionsleague/news/02a6-20d57cfcd03e-407c22a7f465-1000--2026-27-champions-league-teams-dates-draws-format-final/
https://www.uefa.com/uefaeuropaleague/news/02a6-20d57d095740-e1e0b3de85df-1000--2026-27-europa-league-teams-dates-draws-format-final/
https://en.wikipedia.org/wiki/2026%E2%80%9327_UEFA_Conference_League
https://www.skysports.com/football/news/11095/13548546/premier-league-sides-in-europe-26-27-who-has-qualified-plus-dates-and-schedule-for-champions-league-europa-league-and-conference-league

## 3. context.csv (37 rows: 21 manager, 3 deduction, 2 finance, 11 other)

### Source reliability
- Wikipedia 2026-27 Premier League and 2026-27 EFL Championship pages: STALE pre-season
  snapshots (0 matches played) and the PL page contains VANDALISM - it claims "Manchester United
  deducted 60 points for 100 charges of filming training". No news source supports this; it is a
  mangled copy of the (real) Southampton -4 story. Ignored. Their managerial-change tables were
  used only where corroborated by news.
- Wikipedia 2026-27 EFL League One (updated to 30 Aug) and League Two (29 Aug) pages: current;
  their managerial-change tables were spot-checked against club/news sources and agree.
- Wikipedia "List of current Premier League and EFL managers": snapshot as of ~29 Jun 2026; used
  as the 92-club baseline (appointment dates), then overlaid with July/August news.
- premierleague.com "Manager line-up complete" (5 Aug), Sky Sports PL managers (20 Aug) and
  Paddy Power sack-race piece (2 Sep) give the current PL picture: 9 new permanent managers,
  NO in-season sacking as of 2 Sep 2026.
- Searches for "sacked August/September 2026" in EFL returned nothing for 2026/27; the current
  L1/L2 Wikipedia pages list no in-season changes. Championship post-July changes: none found.

### Cut-off handling
type=manager rows are changes completed on/after 1 Jun 2026. Late-May appointments (Bristol
City, Lincoln, Huddersfield, Barnsley, Tranmere, Northampton, Walsall) and pre-season
permanent appointments (Carrick 22 May, De Zerbi 31 Mar) are included as type=other so the
"new manager, first full season" context is not lost. Newcastle's change (6 Aug) is the latest.

### Deductions / charges / finance found
- Southampton: -4 for 2026/27 (EFL espionage case, May 2026). IMPORTANT: the `points` column in
  team_stats_E1.csv (OddAlerts, and statz.ai) shows 7 = points EARNED on the pitch (W2 D1 L1 per
  fixtures_E1.csv); the deduction is NOT applied there - official table position is 3 pts.
  Apply it downstream. Eckert FA hearing pending.
- Man City: 115-charge verdict still pending (23 Aug 2026 confirmation).
- Chelsea: FA (31 Jul 2026) GBP 10m fine + suspended 2-window registration ban to 30 Jun 2027;
  PL (Mar 2026) GBP 10.75m fine + suspended 1-year first-team transfer ban. No live deduction.
- Oxford: EFL SCMP transfer embargo from 10 Jul 2026 (summer window); expected to clear by Jan.
- Sheffield Wed: takeover completed 2 May 2026, no 2026/27 deduction.
- Leicester: -6 was 2025/26; nothing carried over found.
- No club among the 92 found in administration. (Morecambe, in crisis, is outside the 92.)
- Hull City embargo hits in search relate to 2021/22 (COVID loan) - not current.

### Gaps
- Could not fetch the fandom Championship managers page (402) or ESPN Championship guide (empty).
- Chelsea's interim manager name (Calum McFarlane, 22 Apr-30 Jun) comes only from the Wikipedia
  managers list.
- The Heckingbottom "resigned" tweet (1 Apr 2026) is not corroborated (Preston season page still
  lists him); treated as an April-fools item and excluded.
- No search was done per club for minor items (ownership changes, stadium issues); only the
  headline categories requested.
