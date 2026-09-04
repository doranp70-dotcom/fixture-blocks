"""Build the hosted dashboard: embeds the model output as JSON into dashboard_template.html."""
from __future__ import annotations

import json
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import pandas as pd

from model import DIVS, HIST

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

STD_FRACS = [Fraction(a, b) for a, b in [
    (1, 33), (1, 25), (1, 20), (1, 16), (1, 14), (1, 12), (1, 10), (1, 9), (1, 8), (1, 7), (1, 6), (1, 5), (2, 9), (1, 4), (2, 7), (3, 10), (1, 3), (4, 11), (2, 5), (4, 9),
    (1, 2), (8, 15), (4, 7), (8, 13), (4, 6), (8, 11), (4, 5), (5, 6), (10, 11), (1, 1), (11, 10), (6, 5), (5, 4), (11, 8), (6, 4), (13, 8),
    (7, 4), (15, 8), (2, 1), (9, 4), (5, 2), (11, 4), (3, 1), (10, 3), (7, 2), (4, 1), (9, 2), (5, 1), (11, 2), (6, 1), (13, 2), (7, 1),
    (15, 2), (8, 1), (17, 2), (9, 1), (10, 1), (11, 1), (12, 1), (14, 1), (16, 1), (18, 1), (20, 1), (22, 1), (25, 1), (28, 1), (33, 1),
    (40, 1), (50, 1), (66, 1), (80, 1), (100, 1), (125, 1), (150, 1), (200, 1), (250, 1), (300, 1), (350, 1), (500, 1), (1000, 1), (1500, 1), (2000, 1)]]


def frac(dec) -> str:
    if dec is None or pd.isna(dec):
        return ""
    x = float(dec) - 1
    best = min(STD_FRACS, key=lambda f: abs(float(f) - x) / max(x, 0.05))
    return f"{best.numerator}/{best.denominator}"


def clean(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%dT%H:%M")
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, bool):
        return v
    return v


def load_history():
    """Compact per-snapshot series for price / model trajectories."""
    out = []
    if not HIST.exists():
        return out
    for d in sorted(p for p in HIST.iterdir() if p.is_dir()):
        f = d / "teams.csv"
        if not f.exists():
            continue
        t = pd.read_csv(f)
        keep = ["team", "played", "pts", "pts_vs_mkt", "xgxp_vs_mkt", "luck", "rating_now", "sim_title", "sim_promo", "sim_releg", "sim_top4", "sim_top6", "sim_top7", "live_title", "live_promo", "live_releg", "live_top4", "live_top6", "pos"]
        keep = [k for k in keep if k in t.columns]
        rec = {row["team"]: {k: clean(row[k]) for k in keep if k != "team"} for _, row in t[keep].iterrows()}
        sf = d / "scanner.csv"
        if sf.exists():
            sc = pd.read_csv(sf)
            for _, r in sc.iterrows():
                if r["team"] in rec:
                    rec[r["team"]]["pm_" + r["market"]] = clean(r["p_market"])
        out.append({"date": d.name, "teams": rec})
    return out


def build(results: dict, path: Path):
    snap = results.get("_snapshot", {})
    results = {k: v for k, v in results.items() if not k.startswith("_")}
    data = {"updated": datetime.now().strftime("%-d %b %Y"), "snapshot": snap.get("when"), "divs": {}, "history": load_history()}
    mv = snap.get("movers") if snap else None
    for d, r in results.items():
        cfg = r["cfg"]
        top_sim = {"E0": "sim_top4", "E1": "sim_top6", "E2": "sim_top6", "E3": "sim_top7"}[d]
        teams = []
        for _, t in r["teams"].sort_values("mkt_rank").iterrows():
            teams.append({
                "team": t.team, "rank": int(t.mkt_rank), "rating": clean(t.rating), "ratingNow": clean(t.rating_now), "att": clean(t.att_now), "def": clean(t.def_now),
                "mktXp": clean(t.mkt_xP_season), "line": clean(t.points_line),
                "title": frac(t.title_odds), "releg": frac(t.releg_odds), "titleP": clean(t.title_mkt), "relegP": clean(t.releg_mkt), "topP": clean(t.top_mkt), "promoP": clean(t.promo_mkt),
                "played": int(t.played), "pts": clean(t.pts), "ptsWon": clean(t.pts_won), "deduction": int(t.deduction), "pos": int(t.pos), "gf": clean(t.gf), "ga": clean(t.ga),
                "mktXpPlayed": clean(t.mkt_xP_played), "xg": clean(t.xg), "xga": clean(t.xga), "xgXp": clean(t.xg_xP),
                "luck": clean(t.luck), "z": clean(t.z), "clRerate": clean(t.cl_rerate), "clN": int(t.cl_n),
                "npxg": clean(t.get("npxg")), "xgot": clean(t.get("xgot")), "finishing": clean(t.get("finishing")), "shotQuality": clean(t.get("shot_quality")),
                "simPts": clean(t.sim_exp_pts), "simSd": clean(t.sim_sd), "simTitle": clean(t.sim_title), "simTop": clean(t[top_sim]), "simPromo": clean(t.sim_promo), "simReleg": clean(t.sim_releg), "simRank": clean(t.sim_exp_rank),
                "liveTitle": clean(t.live_title), "liveReleg": clean(t.live_releg), "livePromo": clean(t.live_promo), "liveTop4": clean(t.live_top4), "liveTop6": clean(t.live_top6),
                "liveTitleF": frac(t.live_title), "liveRelegF": frac(t.live_releg), "livePromoF": frac(t.live_promo), "liveTop4F": frac(t.live_top4), "liveTop6F": frac(t.live_top6),
                "remGames": clean(t.rem_games), "remPpg": clean(t.rem_mkt_ppg), "remNowPpg": clean(t.rem_now_ppg), "next4Mkt": clean(t.next4_mkt), "next4Now": clean(t.next4_now), "next8Mkt": clean(t.next8_mkt), "next4Fix": t.next4_fix if isinstance(t.next4_fix, str) else "",
                "last4Pts": clean(t.last4_pts), "last4Mkt": clean(t.last4_mkt), "last4Xgxp": clean(t.last4_xgxp), "last4N": clean(t.last4_n),
                "europe": t.europe if isinstance(t.europe, str) else "", "context": t.context if isinstance(t.context, str) else "",
            })
        games = {}
        for team, g in r["team_games"].groupby("team"):
            games[team] = [{
                "g": int(x.game_no), "b": int(x.block), "bo": int(x.block_orig), "date": clean(x.kickoff), "opp": x.opponent, "v": x.venue, "id": x.match_id,
                "oppRank": int(x.opp_mkt_rank), "gf": clean(x.gf), "ga": clean(x.ga), "pts": clean(x.pts),
                "pW": clean(x.mkt_pW), "pD": clean(x.mkt_pD), "pL": clean(x.mkt_pL), "mxp": clean(x.mkt_xP), "mvar": clean(x.mkt_var),
                "xg": clean(x.xg), "xga": clean(x.xga), "xgxp": clean(x.xg_xP), "xgo": clean(x.xg_opta), "xgao": clean(x.xga_opta),
                "clW": clean(x.cl_pW), "clxp": clean(x.cl_xP), "clsrc": x.cl_source if isinstance(x.cl_source, str) else "",
                "nowW": clean(x.now_pW), "nowxp": clean(x.now_xP), "eu": bool(x.congested),
            } for _, x in g.sort_values("game_no").iterrows()]
        blocks = {}
        for team, b in r["blocks"].groupby("team"):
            blocks[team] = [{
                "b": int(x.block), "games": int(x.games), "mktXp": clean(x.mkt_xP), "played": int(x.played),
                "pts": clean(x.pts), "mktXpPlayed": clean(x.mkt_xP_played), "xg": clean(x.xg), "xga": clean(x.xga),
                "xgXp": clean(x.xg_xP), "home": int(x.home_games), "start": clean(x.start), "end": clean(x.end),
                "status": x.status, "ppg": clean(x.mkt_ppg), "nowXp": clean(x.now_xP), "nowPpg": clean(x.now_ppg),
                "z": clean(x.z), "pChance": clean(x.p_chance), "luck": clean(x.luck), "eu": int(x.congested), "moved": int(x.moved), "oppRank": clean(x.avg_opp_rank),
            } for _, x in b.sort_values("block").iterrows()]
        scanner = []
        if not r["scanner"].empty:
            for _, x in r["scanner"].iterrows():
                scanner.append({"team": x.team, "market": x.market, "odds": clean(x.odds), "frac": x.odds_frac, "book": x.bookmaker, "asOf": x.as_of,
                                "pMkt": clean(x.p_market), "pThen": clean(x.p_then), "move": clean(x.price_move), "pModel": clean(x.p_model), "pBlend": clean(x.p_blend),
                                "edge": clean(x.edge), "ev": clean(x.ev), "evBlend": clean(x.ev_blend), "fair": clean(x.fair_odds) if x.fair_odds != float("inf") else None,
                                "kelly": clean(x.kelly), "flag": bool(x.flag)})
        fixtures = [{"id": x.match_id, "date": clean(x.kickoff), "home": x.home, "away": x.away, "hg": clean(x.hg), "ag": clean(x.ag), "hxg": clean(x.home_xg), "axg": clean(x.away_xg), "round": int(x["round"])}
                    for _, x in r["fixtures"].sort_values("kickoff").iterrows()]
        movers = []
        if mv is not None and not mv.empty:
            for _, x in mv[mv["div"] == d].iterrows():
                movers.append({k: clean(x[k]) for k in mv.columns if k not in ("div",)})
        week = []
        if not r["week"].empty:
            for _, x in r["week"].iterrows():
                week.append({k: clean(x[k]) for k in r["week"].columns if k != "div"})
        data["divs"][d] = {"week": week, "name": cfg["name"], "short": cfg["short"], "n": cfg["n"], "relegated": cfg["relegated"],
                           "top": cfg["top"], "topLabel": cfg["top_label"], "games": 2 * (cfg["n"] - 1), "promo": cfg["promo"],
                           "teams": teams, "blocks": blocks, "gamesByTeam": games, "scanner": scanner, "fixtures": fixtures, "movers": movers}
    tpl = (ROOT / "dashboard_template.html").read_text()
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    path.write_text(html)
    return path


if __name__ == "__main__":
    from model import build_all
    res = build_all()
    p = build(res, OUT / "fixture_blocks.html")
    print("wrote", p, p.stat().st_size // 1024, "KB")
