"""Data-only match-market probabilities for upcoming fixtures (no odds involved).

Goals markets come straight from the Dixon-Coles scoreline grid built with the current
(xG re-rated) strengths. Half-time markets split each side's expected goals into halves using
the first-half share observed this season (blended with the long-run ~44%). Corner markets use
a team corner-rate model (for / against, shrunk toward the league average) with a negative
binomial total. Team tendencies are plain season-to-date frequencies from the same data.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

from model import DIVS, DATA, dc_matrix, lambdas, match_probs, MAXG
from names import canon

HT_SHARE_PRIOR, HT_PRIOR_W = 0.44, 250.0       # long-run first-half share of goals, prior weight in goals
CORNER_PRIOR = {"E0": (5.6, 4.6), "E1": (5.7, 4.7), "E2": (5.6, 4.7), "E3": (5.6, 4.6)}   # home, away avg corners
CORNER_PRIOR_W = 60.0                           # prior weight in corners (≈ 6 games)
NB_K = 25.0                                     # negative-binomial dispersion for corner totals
HG = 8                                          # goals grid for the half model


def load_stats(div):
    df = pd.read_csv(DATA / f"matchodds_{div}.csv")
    df["home"] = df["HomeTeam"].map(canon)
    df["away"] = df["AwayTeam"].map(canon)
    for c in ["FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HR", "AR", "HF", "AF"]:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[df["FTHG"].notna()]


def half_share(st):
    ht = (st["HTHG"] + st["HTAG"]).sum()
    ft = (st["FTHG"] + st["FTAG"]).sum()
    return (ht + HT_SHARE_PRIOR * HT_PRIOR_W) / (ft + HT_PRIOR_W) if ft > 0 else HT_SHARE_PRIOR


def corner_factors(st, div, teams):
    """Per-team corner 'for' and 'against' multipliers vs the league average, shrunk."""
    ph, pa = CORNER_PRIOR[div]
    lh = (st["HC"].sum() + ph * CORNER_PRIOR_W / 6) / (len(st) + CORNER_PRIOR_W / 6) if len(st) else ph
    la = (st["AC"].sum() + pa * CORNER_PRIOR_W / 6) / (len(st) + CORNER_PRIOR_W / 6) if len(st) else pa
    out = {}
    for t in teams:
        h = st[st["home"] == t]
        a = st[st["away"] == t]
        # for: own corners relative to venue average; against: opponents' corners relative to venue average
        for_obs = h["HC"].sum() + a["AC"].sum()
        for_exp = len(h) * lh + len(a) * la
        ag_obs = h["AC"].sum() + a["HC"].sum()
        ag_exp = len(h) * la + len(a) * lh
        cf = (for_obs + CORNER_PRIOR_W) / (for_exp + CORNER_PRIOR_W) if for_exp > 0 else 1.0
        ca = (ag_obs + CORNER_PRIOR_W) / (ag_exp + CORNER_PRIOR_W) if ag_exp > 0 else 1.0
        out[t] = (cf, ca)
    return lh, la, out


def nb_sf(k_thresh, mu, k=NB_K):
    """P(X > k_thresh) for a negative binomial with mean mu and dispersion k."""
    p = k / (k + mu)
    return float(nbinom.sf(k_thresh, k, p))


def goals_markets(lh, la, rho):
    g = dc_matrix([lh], [la], rho)[0]           # (G, G): [home goals, away goals]
    i, j = np.meshgrid(np.arange(MAXG + 1), np.arange(MAXG + 1), indexing="ij")   # i = home goals, j = away goals
    tot = i + j
    diff = i - j
    m = {}
    for n in (0.5, 1.5, 2.5, 3.5, 4.5):
        m[f"over_{n}"] = g[tot > n].sum()
    m["btts"] = g[(i >= 1) & (j >= 1)].sum()
    m["home_2plus"] = g[i >= 2].sum()
    m["away_2plus"] = g[j >= 2].sum()
    m["home_3plus"] = g[i >= 3].sum()
    m["away_3plus"] = g[j >= 3].sum()
    m["home_cs"] = g[j == 0].sum()
    m["away_cs"] = g[i == 0].sum()
    m["home_wtn"] = g[(i > j) & (j == 0)].sum()
    m["away_wtn"] = g[(j > i) & (i == 0)].sum()
    m["home_win"] = g[diff > 0].sum(); m["draw"] = g[diff == 0].sum(); m["away_win"] = g[diff < 0].sum()
    m["home_m1_win"] = g[diff >= 2].sum(); m["home_m1_push"] = g[diff == 1].sum()      # Asian -1
    m["home_m15"] = g[diff >= 2].sum()                                               # -1.5
    m["away_m1_win"] = g[diff <= -2].sum(); m["away_m1_push"] = g[diff == -1].sum()
    m["away_m15"] = g[diff <= -2].sum()
    m["home_p1"] = g[diff >= 0].sum() + 0 * 1                                        # home +1 covers if diff >= 0 (push at -1)
    m["away_p1"] = g[diff <= 0].sum()
    m["home_p15"] = g[diff >= -1].sum(); m["away_p15"] = g[diff <= 1].sum()
    m["draw_no_bet_home"] = m["home_win"] / (1 - m["draw"]) if m["draw"] < 1 else np.nan
    m["draw_no_bet_away"] = m["away_win"] / (1 - m["draw"]) if m["draw"] < 1 else np.nan
    flat = [(float(g[a, b]), f"{a}-{b}") for a in range(MAXG + 1) for b in range(MAXG + 1)]
    flat.sort(reverse=True)
    m["cs_1"], m["cs_1_p"] = flat[0][1], flat[0][0]
    m["cs_2"], m["cs_2_p"] = flat[1][1], flat[1][0]
    m["cs_3"], m["cs_3_p"] = flat[2][1], flat[2][0]
    m["exp_goals"] = lh + la
    return m


def half_markets(lh, la, share):
    l1h, l1a = lh * share, la * share
    l2h, l2a = lh * (1 - share), la * (1 - share)
    k = np.arange(HG + 1)
    p1h, p1a = poisson.pmf(k, l1h), poisson.pmf(k, l1a)
    p2h, p2a = poisson.pmf(k, l2h), poisson.pmf(k, l2a)
    g1 = p1h[:, None] * p1a[None, :]
    g2 = p2h[:, None] * p2a[None, :]
    i, j = np.meshgrid(np.arange(HG + 1), np.arange(HG + 1), indexing="ij")
    m = {}
    m["ht_home"] = g1[i > j].sum(); m["ht_draw"] = g1[i == j].sum(); m["ht_away"] = g1[i < j].sum()
    m["fh_over_0.5"] = 1 - g1[0, 0]
    m["fh_over_1.5"] = g1[(i + j) > 1.5].sum()
    m["sh_over_0.5"] = 1 - g2[0, 0]
    m["sh_over_1.5"] = g2[(i + j) > 1.5].sum()
    m["goal_both_halves"] = (1 - g1[0, 0]) * (1 - g2[0, 0])
    m["home_scores_both_halves"] = (1 - p1h[0]) * (1 - p2h[0])
    m["away_scores_both_halves"] = (1 - p1a[0]) * (1 - p2a[0])
    m["second_half_more_goals"] = float(np.sum([g1[a, b] * g2[c, d] for a in range(HG + 1) for b in range(HG + 1) for c in range(HG + 1) for d in range(HG + 1) if (c + d) > (a + b)]))
    # HT/FT: convolve halves
    htft = {}
    for a in range(HG + 1):
        for b in range(HG + 1):
            pa_ = g1[a, b]
            if pa_ < 1e-9:
                continue
            ht = "H" if a > b else "D" if a == b else "A"
            for c in range(HG + 1):
                for d in range(HG + 1):
                    p = pa_ * g2[c, d]
                    if p < 1e-10:
                        continue
                    fh, fa = a + c, b + d
                    ft = "H" if fh > fa else "D" if fh == fa else "A"
                    htft[ht + ft] = htft.get(ht + ft, 0.0) + p
    for kk in ("HH", "HD", "HA", "DH", "DD", "DA", "AH", "AD", "AA"):
        m[f"htft_{kk}"] = htft.get(kk, 0.0)
    m["ht_share"] = share
    return m


def corner_markets(mu_h, mu_a):
    mu = mu_h + mu_a
    m = {"exp_corners_home": mu_h, "exp_corners_away": mu_a, "exp_corners": mu}
    for n in (7.5, 8.5, 9.5, 10.5, 11.5, 12.5):
        m[f"corners_over_{n}"] = nb_sf(int(n), mu)
    for n in (3.5, 4.5, 5.5, 6.5):
        m[f"home_corners_over_{n}"] = nb_sf(int(n), mu_h, k=NB_K / 2)
        m[f"away_corners_over_{n}"] = nb_sf(int(n), mu_a, k=NB_K / 2)
    m["home_most_corners"] = float(sum(nbinom.pmf(x, NB_K / 2, (NB_K / 2) / (NB_K / 2 + mu_h)) * nbinom.cdf(x - 1, NB_K / 2, (NB_K / 2) / (NB_K / 2 + mu_a)) for x in range(1, 25)))
    m["away_most_corners"] = float(sum(nbinom.pmf(x, NB_K / 2, (NB_K / 2) / (NB_K / 2 + mu_a)) * nbinom.cdf(x - 1, NB_K / 2, (NB_K / 2) / (NB_K / 2 + mu_h)) for x in range(1, 25)))
    return m


def tendencies(st, teams):
    """Season-to-date frequencies per team, from the raw match data."""
    rows = []
    for t in teams:
        h = st[st["home"] == t]; a = st[st["away"] == t]
        gf = pd.concat([h["FTHG"], a["FTAG"]]); ga = pd.concat([h["FTAG"], a["FTHG"]])
        htf = pd.concat([h["HTHG"], a["HTAG"]]); hta = pd.concat([h["HTAG"], a["HTHG"]])
        cf = pd.concat([h["HC"], a["AC"]]); ca = pd.concat([h["AC"], a["HC"]])
        sf = pd.concat([h["HS"], a["AS"]]); sa = pd.concat([h["AS"], a["HS"]])
        stf = pd.concat([h["HST"], a["AST"]]); sta = pd.concat([h["AST"], a["HST"]])
        n = len(gf)
        if n == 0:
            rows.append(dict(team=t, played=0)); continue
        tot = gf + ga
        first = htf + hta; second = tot - first
        rows.append(dict(
            team=t, played=n, gf_pg=gf.mean(), ga_pg=ga.mean(),
            over15=(tot > 1.5).mean(), over25=(tot > 2.5).mean(), over35=(tot > 3.5).mean(), btts=((gf > 0) & (ga > 0)).mean(),
            scored2plus=(gf >= 2).mean(), conceded2plus=(ga >= 2).mean(), clean_sheet=(ga == 0).mean(), failed_to_score=(gf == 0).mean(),
            ht_lead=(htf > hta).mean(), ht_level=(htf == hta).mean(), ht_behind=(htf < hta).mean(),
            goal_both_halves=((first > 0) & (second > 0)).mean(), fh_over05=(first > 0).mean(), sh_over05=(second > 0).mean(),
            fh_share=(first.sum() / tot.sum()) if tot.sum() > 0 else np.nan,
            corners_for=cf.mean(), corners_against=ca.mean(), corners_total=(cf + ca).mean(), corners_over85=((cf + ca) > 8.5).mean(), corners_over105=((cf + ca) > 10.5).mean(),
            shots_for=sf.mean(), shots_against=sa.mean(), sot_for=stf.mean(), sot_against=sta.mean(),
            cards=pd.concat([h["HY"] + 2 * h["HR"].fillna(0), a["AY"] + 2 * a["AR"].fillna(0)]).mean(),
        ))
    return pd.DataFrame(rows)


def build_markets(results, horizon_days=10, today=None):
    today = today or pd.Timestamp(datetime.now().date())
    out_rows, tend_frames = [], []
    for div, r in results.items():
        if div.startswith("_"):
            continue
        cfg = r["cfg"]
        fx = r["fixtures"]
        ts = r["teams"].set_index("team")
        teams = list(ts.index)
        st = load_stats(div)
        share = half_share(st)
        lh_avg, la_avg, cfac = corner_factors(st, div, teams)
        tend = tendencies(st, teams); tend["div"] = div
        tend_frames.append(tend)
        up = fx[(fx["hg"].isna()) & (fx["kickoff"] >= today) & (fx["kickoff"] < today + pd.Timedelta(days=horizon_days))]
        for _, m in up.iterrows():
            h, a = m.home, m.away
            lh, la = lambdas(ts.loc[h, "att_now"], ts.loc[h, "def_now"], ts.loc[a, "att_now"], ts.loc[a, "def_now"], cfg)
            row = dict(div=div, league=cfg["name"], match_id=m.match_id, kickoff=m.kickoff, home=h, away=a, round=int(m["round"]),
                       exp_home_goals=float(lh), exp_away_goals=float(la))
            row.update(goals_markets(float(lh), float(la), cfg["rho"]))
            row.update(half_markets(float(lh), float(la), share))
            mu_h = lh_avg * cfac[h][0] * cfac[a][1]
            mu_a = la_avg * cfac[a][0] * cfac[h][1]
            row.update(corner_markets(mu_h, mu_a))
            th, ta = tend.set_index("team").loc[h], tend.set_index("team").loc[a]
            row.update(dict(home_over25_pct=th.get("over25"), away_over25_pct=ta.get("over25"), home_btts_pct=th.get("btts"), away_btts_pct=ta.get("btts"),
                            home_gbh_pct=th.get("goal_both_halves"), away_gbh_pct=ta.get("goal_both_halves"), home_corners_avg=th.get("corners_total"), away_corners_avg=ta.get("corners_total"),
                            home_played=int(th.get("played", 0)), away_played=int(ta.get("played", 0))))
            out_rows.append(row)
    mk = pd.DataFrame(out_rows).sort_values(["kickoff", "home"]).reset_index(drop=True) if out_rows else pd.DataFrame()
    tend = pd.concat(tend_frames, ignore_index=True) if tend_frames else pd.DataFrame()
    return mk, tend


if __name__ == "__main__":
    from model import build_all
    res = build_all(do_snapshot=False)
    mk, tend = build_markets(res)
    cols = ["kickoff", "home", "away", "exp_home_goals", "exp_away_goals", "over_2.5", "btts", "home_2plus", "ht_draw", "goal_both_halves", "htft_HH", "exp_corners", "corners_over_8.5", "home_m1_win"]
    print(mk[cols].round(3).head(20).to_string())
    print(tend[["div", "team", "played", "over25", "btts", "goal_both_halves", "corners_total", "fh_share"]].round(2).head(10).to_string())
