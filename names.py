"""Canonical team names and aliases used across fixtures, odds and xG sources."""

# canonical name -> aliases seen in sources
ALIASES = {
    # Premier League
    "Arsenal": [], "Aston Villa": [], "Bournemouth": ["AFC Bournemouth"], "Brentford": [],
    "Brighton": ["Brighton & Hove Albion", "Brighton and Hove Albion"], "Chelsea": [],
    "Coventry": ["Coventry City"], "Crystal Palace": [], "Everton": [], "Fulham": [],
    "Hull": ["Hull City"], "Ipswich": ["Ipswich Town"], "Leeds": ["Leeds United"],
    "Liverpool": [], "Man City": ["Manchester City"], "Man Utd": ["Manchester United", "Man United"],
    "Newcastle": ["Newcastle United"], "Nott'm Forest": ["Nottingham Forest", "Nottm Forest", "Nott'm Forest"],
    "Tottenham": ["Spurs", "Tottenham Hotspur"], "Sunderland": [],
    # Championship
    "Birmingham": ["Birmingham City"], "Blackburn": ["Blackburn Rovers"], "Bolton": ["Bolton Wanderers"],
    "Bristol City": [], "Burnley": [], "Cardiff": ["Cardiff City"], "Charlton": ["Charlton Athletic"],
    "Derby": ["Derby County"], "Lincoln": ["Lincoln City"], "Middlesbrough": [], "Millwall": [],
    "Norwich": ["Norwich City"], "Portsmouth": [], "Preston": ["Preston North End"],
    "QPR": ["Queens Park Rangers"], "Sheffield United": ["Sheffield Utd", "Sheff Utd"], "Southampton": [],
    "Stoke": ["Stoke City"], "Swansea": ["Swansea City"], "Watford": [],
    "West Brom": ["West Bromwich Albion"], "West Ham": ["West Ham United"],
    "Wolves": ["Wolverhampton Wanderers", "Wolverhampton"], "Wrexham": [],
    # League One
    "AFC Wimbledon": [], "Barnsley": [], "Blackpool": [], "Bradford": ["Bradford City"], "Bromley": [],
    "Burton": ["Burton Albion"], "Cambridge": ["Cambridge United", "Cambridge Utd"], "Doncaster": ["Doncaster Rovers"],
    "Huddersfield": ["Huddersfield Town"], "Leicester": ["Leicester City"], "Leyton Orient": [],
    "Luton": ["Luton Town"], "MK Dons": ["Milton Keynes Dons"], "Mansfield": ["Mansfield Town"],
    "Notts County": [], "Oxford": ["Oxford United", "Oxford Utd"], "Peterborough": ["Peterborough United", "Peterborough Utd", "Peterboro"],
    "Plymouth": ["Plymouth Argyle"], "Reading": [], "Sheffield Wed": ["Sheffield Wednesday", "Sheff Wed", "Sheffield Weds"],
    "Stevenage": [], "Stockport": ["Stockport County"], "Wigan": ["Wigan Athletic"],
    "Wycombe": ["Wycombe Wanderers"],
    # League Two
    "Accrington": ["Accrington Stanley"], "Barnet": [], "Bristol Rovers": ["Bristol Rvs"], "Cheltenham": ["Cheltenham Town"],
    "Chesterfield": [], "Colchester": ["Colchester United"], "Crawley": ["Crawley Town"],
    "Crewe": ["Crewe Alexandra"], "Exeter": ["Exeter City"], "Fleetwood": ["Fleetwood Town"],
    "Gillingham": [], "Grimsby": ["Grimsby Town"], "Newport": ["Newport County"],
    "Northampton": ["Northampton Town"], "Oldham": ["Oldham Athletic"], "Port Vale": [],
    "Rochdale": [], "Rotherham": ["Rotherham United"], "Salford": ["Salford City"],
    "Shrewsbury": ["Shrewsbury Town"], "Swindon": ["Swindon Town"], "Tranmere": ["Tranmere Rovers"],
    "Walsall": [], "York": ["York City"],
}

_LOOKUP = {}
for canon, al in ALIASES.items():
    _LOOKUP[canon.lower()] = canon
    for a in al:
        _LOOKUP[a.lower()] = canon


def canon(name: str) -> str:
    n = name.strip()
    key = n.lower()
    if key in _LOOKUP:
        return _LOOKUP[key]
    raise KeyError(f"Unknown team name: {name!r} — add it to names.ALIASES")
