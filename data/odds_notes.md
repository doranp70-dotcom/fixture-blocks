# 2026/27 pre-season outright odds — sources and notes

Collected 3 September 2026. All four files come from the same bookmaker (**Sky Bet**) via Fan Banter's
pre-season "outright odds" round-ups, which reproduce the full Sky Bet market for every club with an explicit
market date in each heading (e.g. "League One Winner 26/27 odds (via Sky Bet) – 12th August '26").
Fan Banter re-lists earlier snapshots further down each article (e.g. a 4 June '26 League One list); the CSVs
use only the August snapshot nearest the opening weekend (PL kicked off 15 Aug 2026; EFL on 8 Aug).

Odds were published as **fractional** and converted to decimal as `1 + a/b`, rounded to 4 dp
(e.g. 6/4 -> 2.5, 8/13 -> 1.6154, 1/14 -> 1.0714, 1000/1 -> 1001).

## odds_E0.csv — Premier League (20 teams)
- Source: https://fanbanter.co.uk/premier-league-outright-title-winner-top-four-and-relegation-odds/
- Bookmaker: Sky Bet. Odds date: **10 August 2026** (article published 9 Aug 22:20 UTC, market headings "Sky Bet – 10th August").
- Markets: title winner (20/20), relegation (20/20), **top four** (20/20).
- Column note: the `top6_odds` column holds Sky Bet's **Top 4 finish** market for the PL (no top-6 market was listed).
  `promotion_odds` is blank (not applicable).
- Flag: **Man City 8/1 to be relegated** is exactly as published by Sky Bet (three teams tied at 8/1: Brentford, Man City,
  Nottingham Forest). Verified verbatim on two page loads. Presumably prices in a possible points deduction; not a typo on our side.
- Names: Man Utd, Nott'm Forest, Tottenham, Newcastle, Hull, Ipswich, Coventry.

## odds_E1.csv — Championship (24 teams)
- Source: https://fanbanter.co.uk/efl-championship-outright-title-winner-promotion-and-relegation-odds/
- Bookmaker: Sky Bet. Odds date: **11 August 2026** (headings "(via Sky Bet) – 11th August '26"; published 11 Aug 10:20 UTC).
- Markets: winner (24/24), to be promoted (24/24), relegation (24/24).
- Gaps: no playoff / top-6 market listed despite the article title mentioning playoffs -> `top6_odds` blank.

## odds_E2.csv — League One (24 teams)
- Source: https://fanbanter.co.uk/efl-league-one-outright-title-winner-promotion-and-relegation-odds/
- Bookmaker: Sky Bet. Odds date: **12 August 2026** (headings "(via Sky Bet) – 12th August '26"; published 12 Aug 10:55 UTC).
- Markets: winner (24/24), promotion (24/24), relegation (24/24).
- Gaps: no top-6 market -> `top6_odds` blank.
- Names: Sheffield Wed, MK Dons, Wycombe, Oxford, Peterborough, Cambridge, Burton, Bradford, AFC Wimbledon, Bromley.

## odds_E3.csv — League Two (24 teams)
- Source: https://fanbanter.co.uk/efl-league-two-outright-title-winner-promotion-and-relegation-odds/
- Bookmaker: Sky Bet. Odds date: **14 August 2026** (headings "(via Sky Bet) – 14th August '26"; published 14 Aug 09:20 UTC).
  Note this is ~6 days after League Two's opening weekend (8 Aug), so it is a "first-week" rather than strictly pre-kick-off snapshot.
- Markets: winner (24/24), promotion (24/24), relegation (24/24).
- Gaps: article intro mentions "top seven" but no such list is present -> `top6_odds` blank.
- Cross-check: Oddschecker's 5 Aug 2026 League Two preview also has Salford as favourite (11/2 best price there vs 7/2 Sky Bet on 14 Aug)
  and Barnet as joint-favourite, consistent with this snapshot. Northampton Chronicle (26 May 2026) had Barnet/Port Vale/Rotherham 10/1,
  Chesterfield 11/1 — earlier, not used.
- Names: Salford, Bristol Rovers, Newport, Fleetwood, Crawley, York, Port Vale.

## Sources tried but not used
- Racing Post "Big Kick-Off" League Two preview (9 Aug 2026): odds behind paywall.
- Northampton Chronicle League Two odds (26 May 2026): only 4 teams visible, too early.
- Oddschecker/bettingodds/squawka/bettinglounge outright pages: live (September) prices, not pre-season, so not used.
