# 2026/27 match odds — football-data.co.uk

Collected 4 September 2026 from https://www.football-data.co.uk/mmz4281/2627/{E0,E1,E2,E3}.csv
(played matches) and https://www.football-data.co.uk/fixtures.csv (upcoming, filtered to Div in E0–E3).

## Files and row counts

| File | Rows | Dates covered | Note |
|---|---|---|---|
| matchodds_E0.csv | 20 | 21/08–31/08/2026 | complete: all 20 PL matches played to date |
| matchodds_E1.csv | 36 | 14/08–29/08/2026 | source file stops at 29/08; the 1–2 Sep round (12 matches) is not yet in it |
| matchodds_E2.csv | 35 | 15/08–30/08/2026 | source file stops at 30/08; the 1–2 Sep round (12 matches) is not yet in it |
| matchodds_E3.csv | 36 | 15/08–29/08/2026 | source file stops at 29/08; the 1 Sep round (12 matches) is not yet in it |
| matchodds_upcoming.csv | 36 | 01/09–02/09/2026 | E1 12, E2 12, E3 12, E0 0 — these are the 1–2 Sep EFL matches, listed by football-data as fixtures (pre-match odds only) |

The task brief expected 48/47/48 rows for E1/E2/E3 (matches played per our fixtures_E*.csv as of 3 Sep). The football-data
season files had not yet been updated with the 1–2 Sep midweek round at collection time: the raw file's last dates are
29/08 (E1), 30/08 (E2), 29/08 (E3), and the same 36 fixtures still sit in fixtures.csv as upcoming. Row counts of 36/35/36
therefore equal the total number of matches on or before 30/08 in fixtures_E1/E2/E3.csv (36/35/36). Re-fetch after the site's
next update to pick up the 1–2 Sep results with closing odds. E0 (no midweek round) is complete.

The EC row (National League: Halifax v Hartlepool) present in fixtures.csv was excluded as instructed.

## Columns present

Played-match files (E0–E3), header:
`Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,AvgH,AvgD,AvgA,B365CH,B365CD,B365CA,AvgCH,AvgCD,AvgCA`

Upcoming file, header: `Div,Date,HomeTeam,AwayTeam,B365H,B365D,B365A,AvgH,AvgD,AvgA`

**Missing in every file: PSH, PSD, PSA, PSCH, PSCD, PSCA (Pinnacle).** The 2026/27 files do not carry Pinnacle at all.
Bookmakers actually present in the source are Bet365 (B365), Betfair Sportsbook (BFD), BetVictor (BV), Bet&Win (BW),
Paddy Power (PP), Sky Bet (SKB), plus Betfair Exchange (BFE), and the Max/Avg aggregates. If a Pinnacle-like "sharp" price is
needed, the market average (Avg*) is the best proxy available here.

## Column meanings

| Column | Meaning |
|---|---|
| Div | Division: E0 Premier League, E1 Championship, E2 League One, E3 League Two |
| Date | Match date, dd/mm/yyyy |
| HomeTeam / AwayTeam | football-data team names, kept verbatim (see below) |
| FTHG / FTAG | Full-time home / away goals |
| B365H / B365D / B365A | Bet365 home / draw / away odds, **pre-match** (collected on the Friday afternoon for weekend games, Tuesday for midweek), decimal |
| AvgH / AvgD / AvgA | **Market average** home / draw / away odds across all bookmakers football-data tracks, pre-match |
| B365CH / B365CD / B365CA | Bet365 home / draw / away **closing** odds (last price before kick-off) |
| AvgCH / AvgCD / AvgCA | Market average **closing** odds |
| PS*, PSC* | Pinnacle pre-match / closing — not present in these files (see above) |

All odds are decimal (European) and include the bookmaker margin; for the Avg columns the implied probabilities
(1/odds) sum to roughly 1.04–1.06, for B365 to about 1.05–1.07.

## Data quality notes

- Every cell in every odds column is populated and > 1 (verified). No row has blanks in the exported columns, although the
  raw source has occasional blanks in other bookmakers' columns (e.g. Betfair Sportsbook closing prices missing for a few games).
- Scores in matchodds_E0–E3 were compared against fixtures_E0–E3.csv (team-pair match after name normalisation):
  127/127 matched, **0 score mismatches**.
- Extraction method: because the season files are ~113 columns wide, the summariser initially misaligned the Avg block by
  one field on nine League One rows (and the closing-Avg on two other rows). The final CSVs were rebuilt by fetching every raw
  line verbatim and parsing it locally against the header; every row parsed to the full 113 fields and every Avg value was
  checked to lie within the range of the six listed bookmakers and not exceed the Max column. The first-pass extraction
  was retained only where it matched the raw parse.
- Genuine quirk in the source, not an error: for Everton v Crystal Palace, Brentford v Tottenham, Newcastle v Liverpool,
  Liverpool v Nott'm Forest and Bournemouth v Everton (E0) the pre-match MaxH is much larger than every listed bookmaker
  (e.g. 3.2 vs ~2.15) — this is in football-data's file itself and does not affect the exported columns.

## Team names per file (verbatim from football-data)

**E0 (20):** Arsenal, Aston Villa, Bournemouth, Brentford, Brighton, Chelsea, Coventry, Crystal Palace, Everton, Fulham, Hull,
Ipswich, Leeds, Liverpool, Man City, Man United, Newcastle, Nott'm Forest, Sunderland, Tottenham

**E1 (24):** Birmingham, Blackburn, Bolton, Bristol City, Burnley, Cardiff, Charlton, Derby, Lincoln, Middlesbrough, Millwall,
Norwich, Portsmouth, Preston, QPR, Sheffield United, Southampton, Stoke, Swansea, Watford, West Brom, West Ham, Wolves, Wrexham

**E2 (24):** AFC Wimbledon, Barnsley, Blackpool, Bradford, Bromley, Burton, Cambridge, Doncaster, Huddersfield, Leicester,
Leyton Orient, Luton, Mansfield, Milton Keynes Dons, Notts County, Oxford, Peterboro, Plymouth, Reading, Sheffield Weds,
Stevenage, Stockport, Wigan, Wycombe

**E3 (24):** Accrington, Barnet, Bristol Rvs, Cheltenham, Chesterfield, Colchester, Crawley Town, Crewe, Exeter, Fleetwood Town,
Gillingham, Grimsby, Newport County, Northampton, Oldham, Port Vale, Rochdale, Rotherham, Salford, Shrewsbury, Swindon,
Tranmere, Walsall, York

**Upcoming file** uses the same names (subset of E1/E2/E3 above).

Mapping to fixtures_E*.csv names that differ: Man United = Man Utd; Tottenham = Spurs; Nott'm Forest = Nott'm Forest;
Sheffield Weds = Sheffield Wednesday; Milton Keynes Dons = MK Dons; Peterboro = Peterborough United; Bristol Rvs = Bristol Rovers;
West Brom = West Bromwich Albion; QPR = Queens Park Rangers; Wolves = Wolverhampton Wanderers; Crewe = Crewe Alexandra;
all other differences are a dropped suffix (City/Town/United/Athletic/Rovers/County/Argyle/Stanley/North End/Orient).
