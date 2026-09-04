"""Build odds_live_E0..E3.csv from bet365 hub snapshots (fetched 4 Sep 2026 ~10:15 UTC via WebFetch).
Raw lists pasted verbatim from the WebFetch output (two identical passes per page)."""
import csv, sys
sys.path.insert(0, "/home/claude/work/fixblocks")
import names

AS_OF = "2026-09-04"
BOOK = "bet365"
HUB = "https://www.bet365.com/hub/en-gb/football/football-competitions/"

RAW = {
"E0": (HUB + "premier-league", 20, {
"title": "Arsenal 5/6, Man City 3/1, Chelsea 11/2, Liverpool 16/1, Man Utd 18/1, Tottenham 80/1, Aston Villa 100/1, Brighton 100/1, Brentford 100/1, Newcastle 150/1, Everton 200/1, Bournemouth 250/1, Leeds 350/1, Nottm Forest 500/1, Sunderland 1000/1, Ipswich 1500/1, Fulham 1500/1, Crystal Palace 1500/1, Hull 1500/1, Coventry 2000/1",
"relegation": "Hull 2/5, Coventry 4/9, Ipswich 6/5, Sunderland 5/2, Fulham 5/2, Crystal Palace 11/4, Nottm Forest 7/1, Leeds 10/1, Everton 10/1, Bournemouth 12/1, Tottenham 12/1, Man City 14/1, Newcastle 20/1, Aston Villa 20/1, Brighton 25/1, Brentford 33/1, Chelsea 250/1, Man Utd 250/1, Liverpool 250/1, Arsenal 1500/1",
"top4": "Arsenal 1/33, Man City 1/4, Chelsea 2/5, Liverpool 10/11, Man Utd 5/4, Brentford 5/1, Tottenham 6/1, Brighton 6/1, Aston Villa 7/1, Newcastle 8/1, Everton 16/1, Bournemouth 16/1, Leeds 20/1, Nottm Forest 25/1, Fulham 66/1, Crystal Palace 66/1, Sunderland 66/1, Ipswich 100/1, Coventry 250/1, Hull 250/1",
}),
"E1": (HUB + "championship", 24, {
"title": "West Ham 2/1, Wolverhampton 4/1, Middlesbrough 8/1, Southampton 12/1, Millwall 16/1, Birmingham 16/1, Burnley 20/1, Swansea 20/1, Norwich 25/1, West Brom 25/1, Sheff Utd 33/1, Wrexham 33/1, QPR 40/1, Charlton 50/1, Bristol City 50/1, Derby 66/1, Watford 80/1, Stoke 80/1, Cardiff 100/1, Blackburn 100/1, Portsmouth 200/1, Lincoln City 200/1, Bolton 250/1, Preston 500/1",
"promotion": "West Ham 2/5, Wolverhampton 13/8, Middlesbrough 7/4, Southampton 10/3, Burnley 4/1, Birmingham 4/1, Millwall 9/2, Swansea 7/1, Sheff Utd 8/1, Norwich 8/1, Wrexham 8/1, West Brom 9/1, Bristol City 16/1, QPR 16/1, Charlton 16/1, Derby 16/1, Watford 20/1, Blackburn 25/1, Cardiff 25/1, Stoke 25/1, Portsmouth 33/1, Bolton 50/1, Lincoln City 66/1, Preston 100/1",
"relegation": "Lincoln City 4/7, Preston 10/11, Bolton 6/4, Portsmouth 2/1, Sheff Utd 3/1, Cardiff 7/2, Blackburn 4/1, Charlton 6/1, Watford 6/1, Stoke 8/1, Derby 8/1, QPR 9/1, Bristol City 14/1, West Brom 16/1, Swansea 20/1, Norwich 20/1, Wrexham 25/1, Burnley 40/1, Millwall 50/1, Southampton 150/1, Birmingham 150/1, Middlesbrough 200/1, Wolverhampton 200/1, West Ham 250/1",
}),
"E2": (HUB + "league-one", 24, {
"title": "Leicester 4/1, Luton 6/1, Huddersfield 6/1, Sheff Wed 15/2, Bradford 9/1, Stockport 9/1, Plymouth 14/1, Milton Keynes Dons 16/1, Oxford Utd 20/1, Blackpool 25/1, Mansfield 25/1, Wycombe 28/1, Reading 33/1, Leyton Orient 50/1, Cambridge Utd 50/1, Doncaster 50/1, Stevenage 66/1, Barnsley 66/1, Notts County 80/1, Wigan 100/1, Peterborough 100/1, Bromley 150/1, Burton Albion 150/1, AFC Wimbledon 150/1",
"promotion": "Leicester 6/5, Luton 13/8, Huddersfield 7/4, Sheff Wed 9/4, Bradford 5/2, Stockport 11/4, Plymouth 4/1, Milton Keynes Dons 9/2, Oxford Utd 7/1, Blackpool 8/1, Wycombe 9/1, Reading 10/1, Mansfield 10/1, Doncaster 14/1, Leyton Orient 16/1, Cambridge Utd 16/1, Stevenage 20/1, Notts County 20/1, Barnsley 20/1, Wigan 25/1, Peterborough 28/1, Bromley 33/1, Burton Albion 33/1, AFC Wimbledon 40/1",
"relegation": "AFC Wimbledon 6/5, Burton Albion 5/4, Bromley 13/8, Peterborough 7/4, Wigan 2/1, Notts County 5/2, Stevenage 5/2, Barnsley 11/4, Doncaster 10/3, Cambridge Utd 10/3, Leyton Orient 10/3, Reading 5/1, Mansfield 6/1, Oxford Utd 6/1, Wycombe 13/2, Blackpool 7/1, Plymouth 12/1, Milton Keynes Dons 12/1, Stockport 20/1, Bradford 20/1, Sheff Wed 28/1, Luton 28/1, Huddersfield 33/1, Leicester 33/1",
"top6": "Leicester 4/9, Luton 8/13, Huddersfield 4/6, Sheff Wed 5/6, Bradford 10/11, Stockport 1/1, Plymouth 6/4, Milton Keynes Dons 7/4, Oxford Utd 5/2, Blackpool 10/3, Wycombe 7/2, Mansfield 7/2, Reading 4/1, Leyton Orient 11/2, Doncaster 11/2, Cambridge Utd 6/1, Barnsley 6/1, Stevenage 13/2, Notts County 13/2, Wigan 8/1, Peterborough 10/1, Bromley 11/1, Burton Albion 11/1, AFC Wimbledon 12/1",
}),
"E3": (HUB + "league-two", 24, {
"title": "Bristol Rovers 5/1, Barnet 6/1, Salford City 7/1, York 9/1, Oldham 12/1, Grimsby 12/1, Chesterfield 16/1, Swindon 16/1, Walsall 20/1, Port Vale 20/1, Crewe 25/1, Colchester 25/1, Rotherham 33/1, Northampton 33/1, Fleetwood Town 40/1, Exeter 40/1, Rochdale 40/1, Cheltenham 40/1, Tranmere 50/1, Gillingham 50/1, Shrewsbury 100/1, Crawley Town 100/1, Accrington Stanley 100/1, Newport County 200/1",
"promotion": "Bristol Rovers 1/1, Barnet 6/5, Salford City 6/5, York 6/4, Grimsby 5/2, Oldham 5/2, Chesterfield 10/3, Walsall 4/1, Crewe 4/1, Swindon 4/1, Port Vale 9/2, Colchester 9/2, Rotherham 7/1, Northampton 8/1, Fleetwood Town 10/1, Tranmere 12/1, Rochdale 12/1, Cheltenham 12/1, Gillingham 14/1, Exeter 16/1, Shrewsbury 20/1, Crawley Town 25/1, Accrington Stanley 33/1, Newport County 33/1",
"relegation": "Newport County 9/4, Accrington Stanley 5/2, Crawley Town 3/1, Shrewsbury 7/2, Exeter 5/1, Gillingham 5/1, Cheltenham 8/1, Rochdale 8/1, Fleetwood Town 8/1, Tranmere 8/1, Rotherham 10/1, Port Vale 12/1, Northampton 14/1, Swindon 16/1, Walsall 20/1, Colchester 20/1, Crewe 25/1, Chesterfield 25/1, Oldham 40/1, Grimsby 40/1, York 66/1, Salford City 80/1, Bristol Rovers 80/1, Barnet 80/1",
# NB: League Two play-off zone is places 3-7; bet365 offers "Top 7 Finish" (no Top 6). Stored under market=top6 -- see notes.
"top6": "Bristol Rovers 4/11, Barnet 4/9, Salford City 8/13, York 8/11, Oldham 5/6, Grimsby 10/11, Chesterfield 1/1, Crewe 6/4, Walsall 7/4, Colchester 15/8, Port Vale 2/1, Swindon 9/4, Rotherham 9/4, Fleetwood Town 5/2, Northampton 7/2, Tranmere 9/2, Cheltenham 5/1, Exeter 6/1, Gillingham 7/1, Rochdale 7/1, Shrewsbury 10/1, Crawley Town 12/1, Newport County 14/1, Accrington Stanley 14/1",
}),
}

def parse(s):
    out = []
    for item in s.split(","):
        item = item.strip()
        team, frac = item.rsplit(" ", 1)
        a, b = frac.split("/")
        out.append((names.canon(team), frac, round(1 + int(a) / int(b), 4)))
    return out

for div, (url, n, markets) in RAW.items():
    rows = []
    for mkt, s in markets.items():
        parsed = parse(s)
        teams = [t for t, _, _ in parsed]
        assert len(parsed) == n, (div, mkt, len(parsed))
        assert len(set(teams)) == n, (div, mkt, "dup teams")
        for t, frac, dec in parsed:
            rows.append([t, mkt, dec, frac, BOOK, url, AS_OF])
    # consistency: same team set across markets
    sets = {m: {r[0] for r in rows if r[1] == m} for m in markets}
    base = next(iter(sets.values()))
    assert all(s == base for s in sets.values()), (div, "team sets differ")
    path = f"/home/claude/work/fixblocks/data/odds_live_{div}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["team", "market", "odds_decimal", "odds_frac", "bookmaker", "source", "as_of_date"])
        w.writerows(rows)
    print(div, len(rows), "rows;", sorted(markets), "->", path)
