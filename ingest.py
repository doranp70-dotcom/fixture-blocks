"""Weekly ingest: parse raw source text dropped in inbox/ and merge it into data/.

The weekly refresh (a person or a scheduled Claude session) fetches each source page and saves
the page text in inbox/ using the formats below, then runs:  python ingest.py && python build.py

inbox/fixtures_E0.txt .. E3.txt   fixturedownload.com results page, one match per line:
                                   "1, 21/08/2026 20:00, Arsenal, Coventry, 3 - 0"  (or the same fields in a |-table)
inbox/xg_E0.txt .. E3.txt          oddalerts.com/xg/<league> "Recent Results with xG":
                                   a date heading line "Wed, Sep 2" then one line per match
                                   "homeXG|Home Team|H - A|Away Team|awayXG"
inbox/matchodds_E0.txt .. E3.txt   football-data.co.uk/mmz4281/2627/E0.csv verbatim (header line + rows)
inbox/matchodds_upcoming.txt       football-data.co.uk/fixtures.csv verbatim
inbox/odds_live_E0.txt .. E3.txt   bet365 hub page: a market heading line ("To Win Outright", "To Be Relegated",
                                   "To Be Promoted", "Top 4 Finish", "To Finish Top 6", "Top 7 Finish") followed by
                                   "Team 5/6, Team 3/1, ..." on the next line(s)
inbox/manual.json                  entries typed into the dashboard (list of {id, hg, ag, hxg, axg})
Files are optional; whatever is present is merged. Times for EFL divisions are converted from UTC to UK time.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from names import canon

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
INBOX = ROOT / "inbox"
DIVS = ["E0", "E1", "E2", "E3"]
XG_FILES = {"E0": "xg_E0_oddalerts.csv", "E1": "xg_E1.csv", "E2": "xg_E2.csv", "E3": "xg_E3.csv"}
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
MON.update({"Sept": 9})
SEASON_START = datetime(2026, 8, 1)
log = []


def say(msg):
    log.append(msg)
    print(msg)


def is_bst(ts: datetime) -> bool:
    return (datetime(2026, 3, 29, 1) <= ts < datetime(2026, 10, 25, 1)) or (datetime(2027, 3, 28, 1) <= ts < datetime(2027, 10, 31, 1))


# ------------------------------------------------------------------ fixtures
def ingest_fixtures(div):
    p = INBOX / f"fixtures_{div}.txt"
    if not p.exists():
        return
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip().strip("|")
        if not line or line.lower().startswith("round"):
            continue
        parts = [x.strip() for x in re.split(r"\s*[|,]\s*", line)]
        if len(parts) < 5:
            continue
        rnd, date, home, away, result = parts[0], parts[1], parts[2], parts[3], parts[4]
        if not rnd.isdigit():
            continue
        try:
            ts = datetime.strptime(date, "%d/%m/%Y %H:%M")
        except ValueError:
            continue
        rows.append((int(rnd), ts, canon(home), canon(away), result))
    if not rows:
        say(f"{div}: fixtures inbox file had no parseable rows")
        return
    cur = pd.read_csv(DATA / f"fixtures_{div}.csv")
    cur["_h"] = cur["home"].map(canon)
    cur["_a"] = cur["away"].map(canon)
    idx = {(h, a): i for i, (h, a) in enumerate(zip(cur["_h"], cur["_a"]))}
    # detect timezone: EFL pages are UTC (Saturday 3pm shows 14:00 in BST) - shift if most Sat games are at 14:00
    sat = [ts for _, ts, *_ in rows if ts.weekday() == 5 and is_bst(ts)]
    utc = sat and sum(1 for ts in sat if ts.hour == 14) > sum(1 for ts in sat if ts.hour == 15)
    n_res, n_date = 0, 0
    for rnd, ts, h, a, res in rows:
        if utc and is_bst(ts):
            ts = ts + timedelta(hours=1)
        k = (h, a)
        if k not in idx:
            say(f"{div}: unknown fixture {h} v {a} - skipped")
            continue
        i = idx[k]
        res_norm = res if re.match(r"^\d+\s*-\s*\d+$", res) else "-"
        if res_norm != "-":
            res_norm = re.sub(r"\s*-\s*", " - ", res_norm)
        if str(cur.at[i, "result"]).strip() != res_norm and res_norm != "-":
            cur.at[i, "result"] = res_norm
            n_res += 1
        d = ts.strftime("%d/%m/%Y %H:%M")
        if cur.at[i, "date"] != d:
            cur.at[i, "date"] = d
            n_date += 1
    cur.drop(columns=["_h", "_a"]).to_csv(DATA / f"fixtures_{div}.csv", index=False)
    say(f"{div}: fixtures - {n_res} new results, {n_date} date changes ({'UTC->UK shifted' if utc else 'times as given'})")


# ------------------------------------------------------------------ xG
def ingest_xg(div):
    p = INBOX / f"xg_{div}.txt"
    if not p.exists():
        return
    date = None
    new = []
    for line in p.read_text().splitlines():
        line = line.strip()
        m = re.match(r"^(?:\w{3,9},?\s+)?(\w{3,9})\.?\s+(\d{1,2})(?:,?\s*(\d{4}))?$", line)
        if m and m.group(1)[:3].title() in MON:
            mon, day = MON[m.group(1)[:3].title()], int(m.group(2))
            year = int(m.group(3)) if m.group(3) else (2026 if mon >= 7 else 2027)
            date = datetime(year, mon, day)
            continue
        if "|" not in line:
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 5:
            continue
        hx, h, sc, a, ax = parts
        ms = re.match(r"^(\d+)\s*-\s*(\d+)$", sc)
        if not ms or date is None or date < SEASON_START:
            continue
        try:
            new.append(dict(date=date.strftime("%d/%m/%Y"), home=canon(h), away=canon(a), home_goals=int(ms.group(1)), away_goals=int(ms.group(2)), home_xg=float(hx), away_xg=float(ax), source="oddalerts.com"))
        except (KeyError, ValueError) as e:
            say(f"{div}: xG row skipped ({e}): {line}")
    if not new:
        say(f"{div}: xG inbox file had no parseable rows")
        return
    f = DATA / XG_FILES[div]
    cur = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["date", "home", "away", "home_goals", "away_goals", "home_xg", "away_xg", "source"])
    cur["home"] = cur["home"].map(canon)
    cur["away"] = cur["away"].map(canon)
    have = {(h, a) for h, a in zip(cur["home"], cur["away"])}
    add = [r for r in new if (r["home"], r["away"]) not in have]
    # sanity: scores must agree with the fixtures file where present
    fx = pd.read_csv(DATA / f"fixtures_{div}.csv")
    fx["home"] = fx["home"].map(canon)
    fx["away"] = fx["away"].map(canon)
    res = {(h, a): r for h, a, r in zip(fx["home"], fx["away"], fx["result"])}
    fdate = {(h, a): pd.to_datetime(d, dayfirst=True, errors="coerce") for h, a, d in zip(fx["home"], fx["away"], fx["date"])}
    today = pd.Timestamp(datetime.now().date())
    ok = []
    for r in add:
        if (r["home"], r["away"]) not in res:
            say(f"{div}: xG row {r['home']} v {r['away']} is not a 2026/27 fixture in this division - skipped (old season / other competition)")
            continue
        rd = pd.to_datetime(r["date"], dayfirst=True)
        fd = fdate.get((r["home"], r["away"]))
        if rd > today or (pd.notna(fd) and abs((rd - fd).days) > 3):
            say(f"{div}: xG row {r['home']} v {r['away']} dated {r['date']} does not match the fixture date ({fd.date() if pd.notna(fd) else '?'}) - skipped (old season)")
            continue
        want = res.get((r["home"], r["away"]))
        if want == "-":
            say(f"{div}: xG row {r['home']} v {r['away']} but the fixture is not marked played yet - skipped")
            continue
        if want and want != "-" and want != f"{r['home_goals']} - {r['away_goals']}":
            say(f"{div}: xG row score {r['home']} {r['home_goals']}-{r['away_goals']} {r['away']} disagrees with fixtures ({want}) - skipped")
            continue
        ok.append(r)
    out = pd.concat([cur, pd.DataFrame(ok)], ignore_index=True)
    out.to_csv(f, index=False)
    say(f"{div}: xG - {len(ok)} new matches added ({len(out)} total)")


# ------------------------------------------------------------------ match odds (football-data)
def _parse_fd(text):
    lines = [l for l in text.splitlines() if l.strip()]
    hdr = None
    rows = []
    for l in lines:
        l = l.lstrip("\ufeff")
        if l.startswith("Div,"):
            hdr = l.split(",")
            continue
        if hdr is None:
            continue
        parts = l.split(",")
        if len(parts) < len(hdr):
            parts += [""] * (len(hdr) - len(parts))
        rows.append(dict(zip(hdr, parts[: len(hdr)])))
    return rows


def ingest_matchodds():
    keep = ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
            "B365H", "B365D", "B365A", "PSH", "PSD", "PSA", "AvgH", "AvgD", "AvgA", "B365CH", "B365CD", "B365CA", "PSCH", "PSCD", "PSCA", "AvgCH", "AvgCD", "AvgCA", "B365>2.5", "B365<2.5", "AHh", "B365AHH", "B365AHA"]
    for div in DIVS:
        p = INBOX / f"matchodds_{div}.txt"
        if not p.exists():
            continue
        rows = _parse_fd(p.read_text())
        rows = [r for r in rows if r.get("Div") == div and r.get("HomeTeam")]
        if not rows:
            say(f"{div}: match odds inbox had no rows")
            continue
        cols = [c for c in keep if c in rows[0]]
        pd.DataFrame(rows)[cols].to_csv(DATA / f"matchodds_{div}.csv", index=False)
        say(f"{div}: match odds - {len(rows)} rows ({', '.join(c for c in ('PSCH', 'AvgCH') if c in cols) or 'no closing cols'})")
    p = INBOX / "matchodds_upcoming.txt"
    if p.exists():
        rows = [r for r in _parse_fd(p.read_text()) if r.get("Div") in DIVS]
        cols = [c for c in ["Div", "Date", "HomeTeam", "AwayTeam", "B365H", "B365D", "B365A", "PSH", "PSD", "PSA", "AvgH", "AvgD", "AvgA"] if rows and c in rows[0]]
        pd.DataFrame(rows)[cols].to_csv(DATA / "matchodds_upcoming.csv", index=False)
        say(f"upcoming match odds - {len(rows)} rows")


# ------------------------------------------------------------------ live outright odds (bet365 hub)
MARKET_MAP = [
    (re.compile(r"win outright|winner", re.I), "title"),
    (re.compile(r"relegat", re.I), "relegation"),
    (re.compile(r"promot", re.I), "promotion"),
    (re.compile(r"top ?4", re.I), "top4"),
    (re.compile(r"top ?6|top ?7|play.?off", re.I), "top6"),
]


def frac_to_dec(s):
    s = s.strip().lower()
    if s in ("evs", "evens", "1/1"):
        return 2.0
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", s)
    if m:
        return round(1 + int(m.group(1)) / int(m.group(2)), 4)
    try:
        return float(s)
    except ValueError:
        return None


def ingest_odds_live(div, as_of):
    p = INBOX / f"odds_live_{div}.txt"
    if not p.exists():
        return
    market = None
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip().strip("#*- ")
        if not line:
            continue
        is_heading = len(line) < 60 and "," not in line and not re.search(r"\d+\s*/\s*\d+|evs|evens", line, re.I)
        if is_heading:
            market = next((m for rx, m in MARKET_MAP if rx.search(line)), None)   # None = a market we don't track
            continue
        if market is None:
            continue
        for item in line.split(","):
            item = item.strip()
            m = re.match(r"^(.*?)\s+(\d+/\d+|evs|evens)$", item, re.I)
            if not m:
                continue
            try:
                team = canon(m.group(1))
            except KeyError:
                say(f"{div}: live odds unknown team '{m.group(1)}' - skipped")
                continue
            dec = frac_to_dec(m.group(2))
            rows.append(dict(team=team, market=market, odds_decimal=dec, odds_frac=m.group(2), bookmaker="bet365",
                             source=f"https://www.bet365.com/hub/en-gb/football/football-competitions/{ {'E0':'premier-league','E1':'championship','E2':'league-one','E3':'league-two'}[div] }", as_of_date=as_of))
    if not rows:
        say(f"{div}: live odds inbox had no parseable rows")
        return
    df = pd.DataFrame(rows).drop_duplicates(["team", "market"])
    counts = df.groupby("market").size().to_dict()
    df.to_csv(DATA / f"odds_live_{div}.csv", index=False)
    say(f"{div}: live odds - {counts}")


# ------------------------------------------------------------------ manual entries from the dashboard
def ingest_manual():
    p = INBOX / "manual.json"
    if not p.exists():
        return
    entries = json.loads(p.read_text())
    if isinstance(entries, dict):
        entries = [dict(id=k, **v) for k, v in entries.items()]
    by_div = {}
    for e in entries:
        div = e["id"].split("-")[0]
        by_div.setdefault(div, []).append(e)
    for div, es in by_div.items():
        fx = pd.read_csv(DATA / f"fixtures_{div}.csv")
        slug = lambda t: "".join(ch for ch in canon(t) if ch.isalnum())[:8]
        ids = {f"{div}-{slug(h)}-{slug(a)}": i for i, (h, a) in enumerate(zip(fx["home"], fx["away"]))}
        xgf = DATA / XG_FILES[div]
        xg = pd.read_csv(xgf)
        n = 0
        for e in es:
            i = ids.get(e["id"])
            if i is None:
                say(f"manual entry {e['id']} not found")
                continue
            if str(fx.at[i, "result"]).strip() == "-":
                fx.at[i, "result"] = f"{int(e['hg'])} - {int(e['ag'])}"
                n += 1
            if e.get("hxg") is not None and e.get("axg") is not None:
                h, a = canon(fx.at[i, "home"]), canon(fx.at[i, "away"])
                if not ((xg["home"].map(canon) == h) & (xg["away"].map(canon) == a)).any():
                    ts = datetime.strptime(fx.at[i, "date"], "%d/%m/%Y %H:%M")
                    xg.loc[len(xg)] = [ts.strftime("%d/%m/%Y"), h, a, int(e["hg"]), int(e["ag"]), float(e["hxg"]), float(e["axg"]), "dashboard entry"]
        fx.to_csv(DATA / f"fixtures_{div}.csv", index=False)
        xg.to_csv(xgf, index=False)
        say(f"{div}: {n} results applied from dashboard entries")


def main():
    INBOX.mkdir(exist_ok=True)
    as_of = datetime.now().strftime("%Y-%m-%d")
    for div in DIVS:
        ingest_fixtures(div)
    ingest_manual()
    for div in DIVS:
        ingest_xg(div)
    ingest_matchodds()
    for div in DIVS:
        ingest_odds_live(div, as_of)
    (ROOT / "inbox" / "last_ingest.log").write_text("\n".join(log))
    return log


if __name__ == "__main__":
    main()
