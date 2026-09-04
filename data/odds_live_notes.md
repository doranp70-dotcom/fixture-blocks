# Live outright odds — weekly source, extraction prompt, fallbacks, gaps

Research done 4 Sep 2026 (system clock 10:15–10:30 UTC; the brief said "3 Sep"). All fetching via WebFetch only
(no shell internet). Files produced: `odds_live_E0.csv` … `odds_live_E3.csv`, `points_lines_E0.csv`.

## TL;DR — recommended weekly source (all four divisions): the bet365 "hub" competition pages

The bet365 hub is server-rendered plain HTML (unlike bet365.com's sportsbook, Oddschecker, Sky Bet, Betfair,
William Hill, thepools, Oddsportal — all JS/blocked). Each page carries the **complete** outright markets for the
division, live at fetch time, and WebFetch reads them cleanly. One bookmaker only (bet365), but every team,
every market, one URL per division:

| Div | URL | Markets on page (all full-field) |
|---|---|---|
| E0 Premier League | https://www.bet365.com/hub/en-gb/football/football-competitions/premier-league | To Win Outright, To be Relegated, Top 4 Finish (+ Top Goalscorer) |
| E1 Championship | https://www.bet365.com/hub/en-gb/football/football-competitions/championship | To Win Outright, To Be Promoted, To Be Relegated |
| E2 League One | https://www.bet365.com/hub/en-gb/football/football-competitions/league-one | To Win Outright, To Be Promoted, To be Relegated, To Finish Top 2, To Finish Top 6, To Finish Bottom |
| E3 League Two | https://www.bet365.com/hub/en-gb/football/football-competitions/league-two | To Win Outright, To Be Promoted, To Be Relegated, Top 3 Finish, Top 7 Finish, To Finish Bottom |

### Exact WebFetch prompt (tested twice per page — identical output both times, 20/24 rows per market)

```
List every outright (season-long) market on this page, e.g. To Win Outright, To Be Promoted, To Be Relegated,
Top 4 Finish, Top 6 Finish, Top 2 Finish, Top 3 Finish, Top 7 Finish, To Finish Bottom, Top Goalscorer.
For EACH team-based market, output the market name as a heading, then every team and its fractional odds in
page order as "Team odds, Team odds, ...". Include all rows (there should be 20 [or 24] teams per market).
Do not summarise or omit teams.
```

Use "20" for the PL, "24" for EFL. The comma-separated "Team odds" format is what makes it robust — the
summariser never truncated it, whereas table-shaped prompts on other sites did.

### Refresh procedure (weekly)
1. WebFetch each of the four hub URLs with the prompt above (WebFetch caches 15 min per URL; a second call
   inside that window just re-summarises the same HTML — good for a prompt-stability check, useless for a
   price re-check).
2. Paste the four outputs into the `RAW` dict of `/home/claude/work/fixblocks/build_odds_live.py` and set
   `AS_OF` to the fetch date, then run it. It asserts 20/24 rows per market, no duplicate teams, and the
   same team set across markets, and maps names via `names.canon` (aliases for bet365's short forms — Sheff Utd,
   Sheff Wed, Wolverhampton, Oxford Utd, Cambridge Utd, Nottm Forest, Milton Keynes Dons, Lincoln City, etc. —
   were added to `names.py` today).
3. Sanity-check a couple of favourites against Oddspedia Insights (fallback #1 below).

### Caveats on the hub
- **No timestamp on the page.** The prices are live bet365 prices at fetch time; `as_of_date` = fetch date.
  Verified current: PL winner Arsenal 5/6 / Man City 3/1 / Chelsea 11/2 matches Oddspedia (2 Sep, bet365:
  Arsenal 5/6, City 7/2 — City has since shortened) and justbookies (bet365 column 5/6, 7/2); Championship
  promotion West Ham 2/5 / Wolves 13/8 / Boro 7/4 is a step on from Oddspedia's 1 Sep 4/7, 6/4, 2/1;
  League Two winner Bristol Rovers 5/1 / Barnet 6/1 / Salford 7/1 matches Oddspedia's live bet365 feed
  (+500/+600/+700) exactly.
- One bookmaker. If you need a market-average or best price you must combine with a fallback source.
- The hub also carries "Top Goalscorer" and "To Finish Bottom" (E2/E3) markets — not captured.

## What is in the CSVs (market column = title | relegation | top4 | top6 | promotion; decimal = 1 + a/b, 4 dp)

| File | Rows | title | relegation | promotion | top4 | top6 | Not available |
|---|---|---|---|---|---|---|---|
| odds_live_E0.csv | 60 | 20 | 20 | – | 20 | – | **top6** (bet365 hub has no PL Top 6 market; checked twice) |
| odds_live_E1.csv | 72 | 24 | 24 | 24 | – | – | **top6 / play-offs** (no Top 6 market on the hub; justbookies' Championship Top 6 page currently shows "No Odds") |
| odds_live_E2.csv | 96 | 24 | 24 | 24 | – | 24 | – (bet365 "To Finish Top 6") |
| odds_live_E3.csv | 96 | 24 | 24 | 24 | – | 24* | – |

\* **E3 `top6` is bet365's "Top 7 Finish"** (League Two's play-off zone is 3rd–7th; bet365 has no Top 6 market
for League Two). It is stored under `top6` so the column set matches the other divisions and the brief's
"top-6/play-offs" intent — treat it as P(play-off zone), not P(top 6). bet365's "Top 3 Finish" (automatic
promotion) is available on the same page if wanted.

All four team sets match `odds_E*.csv` / `fixtures_E*.csv` exactly (checked programmatically).

## Fallbacks (ranked), with what WebFetch actually returns

1. **Oddspedia Insights** (bet365 prices, explicit article date, full-field lists, plain HTML). Prompt that
   works: `Output the article date and bookmaker, then a compact list "Team | odds" for every team in every
   odds list/table on the page, with the market heading before each list. Include all rows. No commentary.`
   - PL winner: https://oddspedia.com/insights/football/premier-league-winner-odds (2 Sep 2026, 20/20)
   - PL relegation: https://oddspedia.com/insights/football/premier-league-relegation-odds (1 Sep 2026, 20/20;
     NB these prices matched bettingodds.com's *Sky Bet* column rather than its bet365 column — bookmaker
     attribution on Oddspedia articles is soft)
   - Championship promotion: https://oddspedia.com/insights/football/championship-promotion-odds (1 Sep, 24/24;
     winner list on the same page is top-11 only)
   - No League One / League Two insights articles found. Oddspedia's league odds pages
     (`oddspedia.com/football/england/league-two/odds` etc.) show the Winner market in American odds but only
     5 rows before a "Show all odds" JS toggle.
2. **justbookies.com** — plain-HTML 4-bookmaker tables (Bet365, Betfred, BetGoodwin, AK Bets), all rows read
   cleanly, `article:modified_time` in page metadata. PL: winner, relegation, top-2, top-4, top-6, stay-up,
   bottom; Championship: winner, promotion, relegation, top-2/3/6. **No League One/Two.** Freshness varies
   page-by-page: PL top-4 and Championship promotion modified 1 Sep 2026 (current), PL top-6 25 Aug,
   Championship winner 17 Aug, **PL relegation 3 Aug and Championship relegation undated and clearly stale**
   (Preston 1/1, Bolton 6/4 vs 10/11 / 6/4 now; Hull 1/4 vs 2/5 now). Always read the modified date.
   Prompt: `Describe the odds table: column headers (bookmaker names, in order). Then output every row as
   "Team | col1 | col2 | col3 | col4" with the fractional odds under each bookmaker column. Include ALL rows.
   Quote the exact modified/last-updated date from page metadata or body.`
   - https://www.justbookies.com/premier-league-winner-odds/ , /epl-relegation-odds/ , /epl-top-4-odds/ ,
     /epl-top-6-odds/ , /championship-winner-odds/ , /championship-promotion-odds/ ,
     /championship-relegation-odds/ , /championship-top-6-odds/ (empty today)
3. **thatsagoal.com/odds/efl-outright-odds** — complete winner / promotion / relegation tables for
   Championship, League One AND League Two (bet365) in one page, reads perfectly — but it is a **static
   13 Aug 2026 snapshot** (published/modified 2026-08-13). Good pre-season reference, not a weekly source.
   No PL page.
4. **fanbanter.co.uk** — the four articles used for `odds_E*.csv` have **not** been updated since 10/11/12/14
   Aug 2026 (re-checked all four today: only the August Sky Bet headings, plus a 4 June list on the League One
   page). They re-list dated snapshots when they do update, so worth re-checking monthly, but they are not a
   weekly source.
5. **bettingodds.com** market pages (e.g. https://www.bettingodds.com/football/league-two/promotion) — 7–10
   bookmaker columns incl. Sky Bet and bet365, "Updated: <time> <date>" stamp (League Two promotion 3 Sep,
   Championship winner 4 Sep). But the page HTML is huge and tracking-link-laden, so WebFetch's summariser only
   sees the first 3–12 rows ("content cuts off"), and it mis-assigned columns at least once (its "Bet365"
   column for League Two did not match bet365's own prices). Some pages' stamps are stale (21–27 July). Not
   usable for full tables; fine for a favourite-only spot check.
6. Partial-list article sources (top 5–10 only, dated): Squawka outright-market hubs
   (squawka.com/en/outright-markets/…, updated 31 Aug, Sky Bet/bet365), Paddy Power News (3 Sep, PL title and
   relegation, top 4–5 only), William Hill News (27–28 Aug, Championship/L1/L2 promotion, 5–6 teams),
   Betfred Insights (12–20 Aug, top 7–10), bet365 News (news.bet365.com, 12–14 Aug, top 8–10),
   OLBG news (page shows "2 Sep" but the odds are identical to the 13 Aug bet365 lists — **displayed date is
   not the odds date**), LiveScore (LiveScoreBet, undated, top 7–8), footyaccumulators (18 Aug top-4 top 10),
   compare.bet (1 Sep, top 5 only), bettinglounge.co.uk (2 rows only).

## Sources tested and rejected
- oddschecker.com outright pages — JS, empty. Their /tips/ articles are plain HTML but pre-season (5 Aug).
- sports.williamhill.com — 403. bet365.com sportsbook — JS (the /hub/ pages are the exception).
- thepools.com — JS ("magic-frontend doesn't work without JavaScript"). sportinglife.com/football/outrights — 404.
- bettingodds.com/football/english-premier-league/outright — 404 (real paths are /football/premier-league/winner etc.).
- sportsgambler.com, vegasinsider.com (PL winner only, BetMGM, 17 Aug), covers.com — US-centric / PL-only.
- racingpost.com — paywalled. footballleagueworld.co.uk — robots.txt disallowed. cannonstats.com — 429 (x3).
- Betfair exchange / Sky Bet / Ladbrokes / Coral / Betway — not tested beyond search; all JS front-ends.

## Points-total lines (Goal 2) — `points_lines_E0.csv`
- Only one bookmaker season-points market found for 2026/27: **Spreadex** season points spreads (spread betting,
  sell–buy), from https://www.spreadex.com/sports/blog/features/premier-league-points-predictions-202627/
  ("All prices quoted correct as of 3pm 28 July [2026]"). All 20 clubs. `line` = midpoint of the quoted
  spread; the sell–buy spread is recorded in the `bookmaker` field (e.g. "Spreadex (spread 77-79)").
  `over_odds`/`under_odds` are blank — a spread bet has no fixed odds.
- Not found: any fixed-odds over/under points lines (Sky Bet, bet365, Paddy Power, Pinnacle, US books) for the
  PL, and nothing at all for the Championship. cannonstats.com's "Premier League 2026-27 Point Totals:
  Over/Under Picks for Every Team" almost certainly quotes a US sportsbook's lines but returned HTTP 429 on
  three attempts — retry later. Sporting Index (the other spread firm) not found for 26/27.
- Nothing invented: every number in the CSV is verbatim from the Spreadex article.
