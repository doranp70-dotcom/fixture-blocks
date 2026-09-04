"""Fixture-block expected points model, v2.

Pipeline
1. Load fixtures (2,036 matches), start-of-season outright odds, PL points lines, per-match xG,
   match odds (pre-match + closing), live outright odds, context (deductions, Europe, notes).
2. PRE-SEASON RATINGS: one strength per team (attack = defence = r/2 at the start; the attack/
   defence split is only identifiable from in-season xG). Fitted so that a simulated season of
   the real fixture list reproduces the market's title / relegation / top-N / promotion
   probabilities and, for the PL, the Spreadex points lines. Dixon-Coles Poisson goals model.
3. Every fixture gets frozen "market" win/draw/loss probabilities and expected points (Mkt xP).
4. IN-SEASON RE-RATING: attack and defence ratings updated by maximum a-posteriori fit of the
   match xG data (Poisson likelihood on xG for/against) around the pre-season prior.
5. REST-OF-SEASON SIMULATION with current ratings from the live table -> model probabilities for
   each outright market -> compared with live bookmaker prices -> edge.
6. Blocks of 4 in each team's own date order (original assignment kept), rolling windows,
   run-in difficulty, significance (z) of each block's divergence, luck / performance split,
   closing-line re-rating per game, context flags.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm, poisson

from names import canon

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "out"
HIST = ROOT / "history"

DIVS = {
    "E0": dict(name="Premier League", short="PL", n=20, relegated=3, top=4, top_label="Top 4",
               home_goals=1.60, away_goals=1.35, promo=0, auto=0, playoff=(), rho=-0.10),
    "E1": dict(name="Championship", short="CH", n=24, relegated=3, top=6, top_label="Top 6",
               home_goals=1.45, away_goals=1.20, promo=3, auto=2, playoff=(3, 6), rho=-0.10),
    "E2": dict(name="League One", short="L1", n=24, relegated=4, top=6, top_label="Top 6",
               home_goals=1.45, away_goals=1.22, promo=3, auto=2, playoff=(3, 6), rho=-0.10),
    "E3": dict(name="League Two", short="L2", n=24, relegated=2, top=7, top_label="Top 7",
               home_goals=1.42, away_goals=1.20, promo=4, auto=3, playoff=(4, 7), rho=-0.10),
}
XG_FILES = {"E0": "xg_E0_oddalerts.csv", "E1": "xg_E1.csv", "E2": "xg_E2.csv", "E3": "xg_E3.csv"}
BLOCK = 4
MAXG = 10
PRIOR_SD = 0.10   # sd of the in-season prior on each of attack / defence around the pre-season value
N_SIMS = 10000


# ----------------------------------------------------------------------------- loading
def _read(name, **kw):
    p = DATA / name
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, **kw)
    return df


def load_fixtures(div):
    df = pd.read_csv(DATA / f"fixtures_{div}.csv")
    df["home"] = df["home"].map(canon)
    df["away"] = df["away"].map(canon)
    df["kickoff"] = pd.to_datetime(df["date"], format="%d/%m/%Y %H:%M")
    res = df["result"].astype(str).str.strip()
    played = res.str.contains(r"^\d+\s*-\s*\d+$")
    df["hg"] = np.where(played, res.str.split("-").str[0].str.strip(), np.nan).astype(float)
    df["ag"] = np.where(played, res.str.split("-").str[1].str.strip(), np.nan).astype(float)
    df["div"] = div
    return df[["div", "round", "kickoff", "home", "away", "hg", "ag"]]


def load_xg(div):
    df = _read(XG_FILES[div])
    if df.empty:
        return pd.DataFrame(columns=["home", "away", "home_xg", "away_xg", "xg_source"])
    df["home"] = df["home"].map(canon)
    df["away"] = df["away"].map(canon)
    df = df.rename(columns={"source": "xg_source"})
    return df[["home", "away", "home_xg", "away_xg", "xg_source"]]


def load_xg_opta():
    df = _read("xg_E0.csv")
    if df.empty:
        return df
    df["home"] = df["home"].map(canon)
    df["away"] = df["away"].map(canon)
    return df.rename(columns={"home_xg": "home_xg_opta", "away_xg": "away_xg_opta"})[["home", "away", "home_xg_opta", "away_xg_opta"]]


def load_odds(div):
    df = pd.read_csv(DATA / f"odds_{div}.csv")
    df["team"] = df["team"].map(canon)
    return df


def load_odds_live(div):
    df = _read(f"odds_live_{div}.csv")
    if df.empty:
        return df
    df["team"] = df["team"].map(canon)
    return df


def load_matchodds(div):
    df = _read(f"matchodds_{div}.csv")
    up = _read("matchodds_upcoming.csv")
    if not up.empty:
        up = up[up["Div"] == div]
    frames = [x for x in (df, up) if not x.empty]
    if not frames:
        return pd.DataFrame(columns=["home", "away"])
    m = pd.concat(frames, ignore_index=True)
    m["home"] = m["HomeTeam"].map(canon)
    m["away"] = m["AwayTeam"].map(canon)
    keep = ["home", "away", "B365H", "B365D", "B365A", "AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA", "B365CH", "B365CD", "B365CA"]
    for k in keep:
        if k not in m.columns:
            m[k] = np.nan
    return m[keep].drop_duplicates(["home", "away"], keep="first")


def load_team_stats(div):
    df = _read(f"team_stats_{div}.csv")
    if df.empty:
        return df
    df["team"] = df["team"].map(canon)
    return df


def load_points_lines(div):
    df = _read(f"points_lines_{div}.csv")
    if df.empty or "team" not in df.columns:
        return {}
    df["team"] = df["team"].map(canon)
    return dict(zip(df["team"], df["line"].astype(float)))


def load_deductions(div):
    df = _read("deductions.csv")
    if df.empty:
        return {}
    df = df[df["div"] == div]
    return {canon(t): int(p) for t, p in zip(df["team"], df["points"])}


def load_context():
    ctx = _read("context.csv")
    if not ctx.empty:
        ctx["team"] = ctx["team"].map(canon)
    eu = _read("europe.csv")
    if not eu.empty:
        eu["team"] = eu["team"].map(canon)
    return ctx, eu


# ----------------------------------------------------------------------------- match model
def dc_matrix(lh, la, rho):
    """Dixon-Coles adjusted score-probability grids for vectors of means. Returns (m, G, G)."""
    lh = np.atleast_1d(np.asarray(lh, float))
    la = np.atleast_1d(np.asarray(la, float))
    g = np.arange(MAXG + 1)
    ph = poisson.pmf(g[None, :], lh[:, None])
    pa = poisson.pmf(g[None, :], la[:, None])
    joint = ph[:, :, None] * pa[:, None, :]
    # tau adjustments for 0-0, 1-0, 0-1, 1-1
    joint[:, 0, 0] *= 1 - lh * la * rho
    joint[:, 1, 0] *= 1 + la * rho
    joint[:, 0, 1] *= 1 + lh * rho
    joint[:, 1, 1] *= 1 - rho
    joint = np.clip(joint, 0, None)
    joint /= joint.sum((1, 2), keepdims=True)
    return joint


_HW = np.tril(np.ones((MAXG + 1, MAXG + 1)), -1)  # home goals index i > away j
_DR = np.eye(MAXG + 1)


def match_probs(lh, la, rho=-0.10):
    joint = dc_matrix(lh, la, rho)
    p_h = (joint * _HW[None]).sum((1, 2))
    p_d = (joint * _DR[None]).sum((1, 2))
    return p_h, p_d, 1 - p_h - p_d


def xp_from_probs(p_h, p_d, p_a):
    return 3 * p_h + p_d, 3 * p_a + p_d


def lambdas(att_h, def_h, att_a, def_a, cfg):
    return cfg["home_goals"] * np.exp(att_h - def_a), cfg["away_goals"] * np.exp(att_a - def_h)


def devig(odds):
    p = 1.0 / np.asarray(odds, float)
    return p / p.sum()


# ----------------------------------------------------------------------------- pre-season fit
@dataclass
class Market:
    teams: list
    title: np.ndarray
    releg: np.ndarray
    top: np.ndarray | None
    promo: np.ndarray | None
    lines: np.ndarray | None


def implied(odds, total):
    p = 1.0 / odds.astype(float).to_numpy()
    return p / p.sum() * total


def build_market(odds, cfg, lines):
    teams = list(odds["team"])
    title = implied(odds["title_odds"], 1.0)
    rel_odds = odds["relegation_odds"].astype(float).copy()
    # a meaningful relegation price on a genuine title contender (Man City 8/1, Aug 2026) is a
    # points-deduction price, not a strength signal: drop it from the de-vig as well as from the fit
    t_imp = (1 / odds["title_odds"].astype(float))
    t_imp = t_imp / t_imp.sum()
    r_imp = (1 / rel_odds) / (1 / rel_odds).sum() * cfg["relegated"]
    rel_odds[(r_imp > 0.05) & (t_imp > 0.10)] = 1e6
    releg = implied(rel_odds, cfg["relegated"])
    top = implied(odds["top6_odds"], cfg["top"]) if odds["top6_odds"].notna().all() else None
    promo = implied(odds["promotion_odds"], cfg["promo"]) if odds["promotion_odds"].notna().all() else None
    ln = np.array([lines.get(t, np.nan) for t in teams]) if lines else None
    if ln is not None and np.isnan(ln).all():
        ln = None
    return Market(teams, title, releg, top, promo, ln)


def season_moments(r, hi, ai, cfg, n):
    """Expected points and variance per team over a fixture list, single rating r (att=def=r/2)."""
    lh, la = lambdas(r[hi] / 2, r[hi] / 2, r[ai] / 2, r[ai] / 2, cfg)
    p_h, p_d, p_a = match_probs(lh, la, cfg["rho"])
    xph, xpa = xp_from_probs(p_h, p_d, p_a)
    vh = 9 * p_h + p_d - xph ** 2
    va = 9 * p_a + p_d - xpa ** 2
    E = np.bincount(hi, xph, n) + np.bincount(ai, xpa, n)
    V = np.bincount(hi, vh, n) + np.bincount(ai, va, n)
    return E, V


def rank_probs(pts, cfg, start_pts=None):
    """pts: (sims, n) simulated final points -> dict of probabilities per team."""
    order = np.argsort(-pts, axis=1, kind="stable")
    ranks = np.empty_like(order)
    rows = np.arange(pts.shape[0])[:, None]
    ranks[rows, order] = np.arange(pts.shape[1])[None, :]
    n = pts.shape[1]
    out = {
        "title": (ranks == 0).mean(0),
        "releg": (ranks >= n - cfg["relegated"]).mean(0),
        "top": (ranks < cfg["top"]).mean(0),
        "top2": (ranks < 2).mean(0),
        "top4": (ranks < 4).mean(0),
        "top6": (ranks < 6).mean(0),
        "top7": (ranks < 7).mean(0),
        "bottom": (ranks == n - 1).mean(0),
        "exp_rank": ranks.mean(0) + 1,
    }
    if cfg["promo"]:
        lo, hi_ = cfg["playoff"]
        auto = (ranks < cfg["auto"]).mean(0)
        po = ((ranks >= lo - 1) & (ranks < hi_)).mean(0)
        out["auto"] = auto
        out["playoff"] = po
        out["promo"] = auto + po / 4.0
    else:
        out["promo"] = np.full(n, np.nan)
        out["auto"] = out["promo"]
        out["playoff"] = out["promo"]
    return out


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def fit_ratings(div, fx, odds, lines, n_sims=20000, seed=7, sigma_fixed=None):
    """Fit one strength per team (+ a season-level 'strength uncertainty' sd in points, sigma)
    so the simulated season reproduces the outright market; for the PL also the points lines,
    which pin the scale of expected points. sigma is fitted where lines exist, else fixed."""
    cfg = DIVS[div]
    mk = build_market(odds, cfg, lines)
    teams = mk.teams
    idx = {t: i for i, t in enumerate(teams)}
    hi = fx["home"].map(idx).to_numpy()
    ai = fx["away"].map(idx).to_numpy()
    n = len(teams)
    Z = np.random.default_rng(seed).standard_normal((n_sims, n))
    w_title = (mk.title >= 0.01).astype(float)
    w_rel = ((mk.releg >= 0.01) & (mk.releg > mk.title)).astype(float)
    w_top = (mk.top >= 0.01).astype(float) if mk.top is not None else None
    w_promo = (mk.promo >= 0.01).astype(float) if mk.promo is not None else None
    has_lines = mk.lines is not None
    if has_lines:
        w_line = (~np.isnan(mk.lines)).astype(float)
        lines_arr = np.nan_to_num(mk.lines)
    fit_sigma = has_lines and sigma_fixed is None

    def unpack(p):
        r = p[:n] - p[:n].mean()
        sig = np.log1p(np.exp(p[n])) if fit_sigma else (sigma_fixed if sigma_fixed is not None else 0.0)
        return r, sig

    def probs(r, sig):
        E, V = season_moments(r, hi, ai, cfg, n)
        return E, V, rank_probs(E[None, :] + np.sqrt(V + sig ** 2)[None, :] * Z, cfg)

    def loss(p):
        r, sig = unpack(p)
        E, V, pr = probs(r, sig)
        L = (w_title * (logit(pr["title"]) - logit(mk.title)) ** 2).sum()
        L += (w_rel * (logit(pr["releg"]) - logit(mk.releg)) ** 2).sum()
        if w_top is not None:
            L += (w_top * (logit(pr["top"]) - logit(mk.top)) ** 2).sum()
        if w_promo is not None:
            L += (w_promo * (logit(pr["promo"]) - logit(mk.promo)) ** 2).sum()
        if has_lines:
            L += 0.5 * (w_line * (E - lines_arr) ** 2).sum()
        return L + 0.01 * (r ** 2).sum()

    r0 = 0.25 * (logit(mk.title) - logit(mk.releg))
    r0 = (r0 - r0.mean()) / 6
    p0 = np.concatenate([r0, [np.log(np.expm1(6.0))]]) if fit_sigma else np.concatenate([r0, [0.0]])
    best = None
    for _ in range(3):
        res = minimize(loss, p0 if best is None else best.x, method="Powell",
                       options=dict(maxiter=6000, xtol=1e-4, ftol=1e-6))
        if best is None or res.fun < best.fun:
            best = res
    r, sig = unpack(best.x)
    E, V, pr = probs(r, sig)
    table = pd.DataFrame({
        "team": teams, "rating": r, "att": r / 2, "def": r / 2, "mkt_xpts_season": E, "sd_pts": np.sqrt(V + sig ** 2),
        "sigma_strength": sig,
        "title_mkt": mk.title, "title_model": pr["title"], "releg_mkt": mk.releg, "releg_model": pr["releg"],
        "top_mkt": mk.top if mk.top is not None else np.nan, "top_model": pr["top"],
        "promo_mkt": mk.promo if mk.promo is not None else np.nan, "promo_model": pr["promo"],
        "points_line": mk.lines if has_lines else np.nan,
        "title_odds": odds["title_odds"].to_numpy(), "releg_odds": odds["relegation_odds"].to_numpy(),
        "top_odds": odds["top6_odds"].to_numpy(), "promo_odds": odds["promotion_odds"].to_numpy(),
    }).sort_values("mkt_xpts_season", ascending=False).reset_index(drop=True)
    table["mkt_rank"] = np.arange(1, n + 1)
    return table, best.fun


def get_ratings(div, fx, odds, lines, refit=False):
    cache = DATA / f"ratings_{div}.csv"
    if cache.exists() and not refit:
        r = pd.read_csv(cache)
        if set(r["team"]) == set(odds["team"]) and "sigma_strength" in r.columns:
            return r, float("nan")
    sigma_fixed = None
    if not lines:  # no points lines: borrow the strength-uncertainty sd calibrated on the PL, scaled by games
        pl = DATA / "ratings_E0.csv"
        if pl.exists():
            r0 = pd.read_csv(pl)
            if "sigma_strength" in r0.columns:
                sigma_fixed = float(r0["sigma_strength"].iloc[0]) * (2 * (DIVS[div]["n"] - 1)) / 38.0
    ratings, loss = fit_ratings(div, fx, odds, lines, sigma_fixed=sigma_fixed)
    ratings.to_csv(cache, index=False)
    return ratings, loss


# ----------------------------------------------------------------------------- in-season re-rating
def rerate(div, fx, ratings):
    """MAP fit of attack/defence to played-match xG around the pre-season prior."""
    cfg = DIVS[div]
    teams = list(ratings["team"])
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    a0 = ratings["att"].to_numpy()
    d0 = ratings["def"].to_numpy()
    pl = fx[fx["home_xg"].notna()]
    if pl.empty:
        return a0.copy(), d0.copy(), 0
    hi = pl["home"].map(idx).to_numpy()
    ai = pl["away"].map(idx).to_numpy()
    xh = pl["home_xg"].to_numpy()
    xa = pl["away_xg"].to_numpy()

    def nll(p):
        a, d = p[:n], p[n:]
        lh = cfg["home_goals"] * np.exp(a[hi] - d[ai])
        la = cfg["away_goals"] * np.exp(a[ai] - d[hi])
        ll = (xh * np.log(lh) - lh).sum() + (xa * np.log(la) - la).sum()
        prior = ((a - a0) ** 2).sum() / (2 * PRIOR_SD ** 2) + ((d - d0) ** 2).sum() / (2 * PRIOR_SD ** 2)
        return -ll + prior

    def grad(p):
        a, d = p[:n], p[n:]
        lh = cfg["home_goals"] * np.exp(a[hi] - d[ai])
        la = cfg["away_goals"] * np.exp(a[ai] - d[hi])
        rh = xh - lh
        ra = xa - la
        ga = np.bincount(hi, rh, n) + np.bincount(ai, ra, n)
        gd = -np.bincount(ai, rh, n) - np.bincount(hi, ra, n)
        ga = -ga + (a - a0) / PRIOR_SD ** 2
        gd = -gd + (d - d0) / PRIOR_SD ** 2
        return np.concatenate([ga, gd])

    res = minimize(nll, np.concatenate([a0, d0]), jac=grad, method="L-BFGS-B")
    a, d = res.x[:n], res.x[n:]
    # remove the unidentifiable common mode (att up = def down) with one shared shift; keeps a-d
    c = ((a.mean() - a0.mean()) + (d.mean() - d0.mean())) / 2
    return a - c, d - c, len(pl)


def simulate_rest(div, fx, teams, att, deff, pts_now, n_played, n_sims=N_SIMS, seed=11):
    """Match-level Monte Carlo of the remaining fixtures from the current table, with a
    per-simulation strength shock (posterior uncertainty shrinking with games played)."""
    cfg = DIVS[div]
    idx = {t: i for i, t in enumerate(teams)}
    rem = fx[fx["hg"].isna()]
    n = len(teams)
    rng = np.random.default_rng(seed)
    total = np.tile(pts_now.astype(float), (n_sims, 1))
    if not rem.empty:
        hi = rem["home"].map(idx).to_numpy()
        ai = rem["away"].map(idx).to_numpy()
        sd_post = PRIOR_SD / np.sqrt(1 + np.asarray(n_played, float) / 8.0)      # per team
        ea = rng.standard_normal((n_sims, n)) * sd_post[None, :]
        ed = rng.standard_normal((n_sims, n)) * sd_post[None, :]
        A = att[None, :] + ea
        D = deff[None, :] + ed
        lh = cfg["home_goals"] * np.exp(A[:, hi] - D[:, ai])
        la = cfg["away_goals"] * np.exp(A[:, ai] - D[:, hi])
        gh = rng.poisson(lh)
        ga = rng.poisson(la)
        hw = gh > ga
        dr = gh == ga
        aw = gh < ga
        for m in range(len(rem)):
            total[:, hi[m]] += 3 * hw[:, m] + dr[:, m]
            total[:, ai[m]] += 3 * aw[:, m] + dr[:, m]
    pr = rank_probs(total, cfg)
    pr["exp_pts"] = total.mean(0)
    pr["sd_pts"] = total.std(0)
    return pr


# ----------------------------------------------------------------------------- assembly
def block_assignments(div, tg):
    """Keep the first-ever block assignment so rearranged games don't silently move blocks."""
    p = DATA / "block_assignments.csv"
    cur = tg[["div", "team", "match_id", "block"]].rename(columns={"block": "block_orig"})
    if p.exists():
        old = pd.read_csv(p)
        old = old[old["div"] == div]
        if not old.empty:
            return old
    allf = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=cur.columns)
    allf = pd.concat([allf[allf["div"] != div], cur], ignore_index=True)
    allf.to_csv(p, index=False)
    return cur


def build_division(div, refit=False):
    cfg = DIVS[div]
    fx = load_fixtures(div)
    odds = load_odds(div)
    lines = load_points_lines(div)
    ratings, fit_loss = get_ratings(div, fx, odds, lines, refit)
    teams = list(ratings["team"])
    rmap = dict(zip(ratings["team"], ratings["rating"]))
    rank_map = dict(zip(ratings["team"], ratings["mkt_rank"]))
    deductions = load_deductions(div)

    # --- per-match data
    fx = fx.merge(load_xg(div), on=["home", "away"], how="left")
    if div == "E0":
        fx = fx.merge(load_xg_opta(), on=["home", "away"], how="left")
    else:
        fx["home_xg_opta"] = np.nan
        fx["away_xg_opta"] = np.nan
    fx = fx.merge(load_matchodds(div), on=["home", "away"], how="left")
    att0 = dict(zip(ratings["team"], ratings["att"]))
    def0 = dict(zip(ratings["team"], ratings["def"]))
    lh, la = lambdas(fx["home"].map(att0).to_numpy(), fx["home"].map(def0).to_numpy(),
                     fx["away"].map(att0).to_numpy(), fx["away"].map(def0).to_numpy(), cfg)
    p_h, p_d, p_a = match_probs(lh, la, cfg["rho"])
    fx["mkt_pH"], fx["mkt_pD"], fx["mkt_pA"] = p_h, p_d, p_a
    fx["mkt_xP_home"], fx["mkt_xP_away"] = xp_from_probs(p_h, p_d, p_a)
    fx["mkt_var_home"] = 9 * p_h + p_d - fx["mkt_xP_home"] ** 2
    fx["mkt_var_away"] = 9 * p_a + p_d - fx["mkt_xP_away"] ** 2
    fx["mkt_exp_goals_home"], fx["mkt_exp_goals_away"] = lh, la
    # xG-implied
    has = fx["home_xg"].notna().to_numpy()
    for col in ("xg_pH", "xg_pD", "xg_pA", "xg_xP_home", "xg_xP_away"):
        fx[col] = np.nan
    if has.any():
        qh, qd, qa = match_probs(fx.loc[has, "home_xg"].to_numpy(), fx.loc[has, "away_xg"].to_numpy(), cfg["rho"])
        fx.loc[has, "xg_pH"], fx.loc[has, "xg_pD"], fx.loc[has, "xg_pA"] = qh, qd, qa
        fx.loc[has, "xg_xP_home"], fx.loc[has, "xg_xP_away"] = xp_from_probs(qh, qd, qa)
    # closing-line implied (market-now) probabilities: prefer closing avg, else pre-match avg, else B365
    def pick(cols):
        v = fx[cols[0]].copy()
        for c in cols[1:]:
            v = v.fillna(fx[c])
        return v
    cH = pick(["AvgCH", "AvgH", "B365CH", "B365H"]); cD = pick(["AvgCD", "AvgD", "B365CD", "B365D"]); cA = pick(["AvgCA", "AvgA", "B365CA", "B365A"])
    hasc = cH.notna() & cD.notna() & cA.notna()
    inv = np.vstack([1 / cH, 1 / cD, 1 / cA]).T
    tot = inv.sum(1)
    fx["cl_pH"] = np.where(hasc, inv[:, 0] / tot, np.nan)
    fx["cl_pD"] = np.where(hasc, inv[:, 1] / tot, np.nan)
    fx["cl_pA"] = np.where(hasc, inv[:, 2] / tot, np.nan)
    fx["cl_xP_home"] = 3 * fx["cl_pH"] + fx["cl_pD"]
    fx["cl_xP_away"] = 3 * fx["cl_pA"] + fx["cl_pD"]
    fx["cl_source"] = np.where(fx["AvgCH"].notna(), "closing avg", np.where(fx["AvgH"].notna(), "pre-match avg", np.where(fx["B365H"].notna(), "bet365", "")))
    played = fx["hg"].notna()
    fx["pts_home"] = np.where(played, np.where(fx.hg > fx.ag, 3, np.where(fx.hg == fx.ag, 1, 0)), np.nan)
    fx["pts_away"] = np.where(played, np.where(fx.ag > fx.hg, 3, np.where(fx.hg == fx.ag, 1, 0)), np.nan)
    fx = fx.sort_values(["kickoff", "home"]).reset_index(drop=True)
    slug = lambda t: "".join(ch for ch in t if ch.isalnum())[:8]
    fx["match_id"] = [f"{div}-{slug(h)}-{slug(a)}" for h, a in zip(fx["home"], fx["away"])]
    assert fx["match_id"].is_unique, "match ids must be unique"

    # --- current ratings and rest-of-season simulation
    att_now, def_now, n_fit = rerate(div, fx, ratings)
    att_map = dict(zip(teams, att_now)); def_map = dict(zip(teams, def_now))
    # current-model probabilities per remaining fixture
    rem = fx["hg"].isna().to_numpy()
    fx["now_pW_home"] = np.nan; fx["now_pD"] = np.nan; fx["now_pW_away"] = np.nan
    if rem.any():
        r_ = fx[rem]
        lh2, la2 = lambdas(r_["home"].map(att_map).to_numpy(), r_["home"].map(def_map).to_numpy(),
                           r_["away"].map(att_map).to_numpy(), r_["away"].map(def_map).to_numpy(), cfg)
        q = match_probs(lh2, la2, cfg["rho"])
        fx.loc[rem, "now_pW_home"], fx.loc[rem, "now_pD"], fx.loc[rem, "now_pW_away"] = q
    fx["now_xP_home"] = 3 * fx["now_pW_home"] + fx["now_pD"]
    fx["now_xP_away"] = 3 * fx["now_pW_away"] + fx["now_pD"]

    # --- team-game long table
    rows = []
    for side, opp in (("home", "away"), ("away", "home")):
        H = side == "home"
        rows.append(pd.DataFrame({
            "div": div, "team": fx[side], "opponent": fx[opp], "venue": "H" if H else "A",
            "kickoff": fx["kickoff"], "round": fx["round"], "match_id": fx["match_id"],
            "gf": fx["hg"] if H else fx["ag"], "ga": fx["ag"] if H else fx["hg"], "pts": fx[f"pts_{side}"],
            "mkt_pW": fx["mkt_pH"] if H else fx["mkt_pA"], "mkt_pD": fx["mkt_pD"], "mkt_pL": fx["mkt_pA"] if H else fx["mkt_pH"],
            "mkt_xP": fx[f"mkt_xP_{side}"], "mkt_var": fx[f"mkt_var_{side}"],
            "xg": fx["home_xg"] if H else fx["away_xg"], "xga": fx["away_xg"] if H else fx["home_xg"],
            "xg_xP": fx[f"xg_xP_{side}"],
            "xg_opta": fx["home_xg_opta"] if H else fx["away_xg_opta"], "xga_opta": fx["away_xg_opta"] if H else fx["home_xg_opta"],
            "cl_pW": fx["cl_pH"] if H else fx["cl_pA"], "cl_xP": fx[f"cl_xP_{side}"], "cl_source": fx["cl_source"],
            "now_pW": fx["now_pW_home"] if H else fx["now_pW_away"], "now_xP": fx[f"now_xP_{side}"],
        }))
    tg = pd.concat(rows).sort_values(["team", "kickoff"]).reset_index(drop=True)
    tg["game_no"] = tg.groupby("team").cumcount() + 1
    tg["block"] = (tg["game_no"] - 1) // BLOCK + 1
    ba = block_assignments(div, tg)
    tg = tg.merge(ba[["match_id", "team", "block_orig"]], on=["match_id", "team"], how="left")
    tg["block_orig"] = tg["block_orig"].fillna(tg["block"]).astype(int)
    tg["block_moved"] = tg["block_orig"] != tg["block"]
    tg["played"] = tg["pts"].notna()
    tg["opp_rating"] = tg["opponent"].map(rmap)
    tg["opp_mkt_rank"] = tg["opponent"].map(rank_map)
    tg["result"] = np.where(tg.played, np.where(tg.pts == 3, "W", np.where(tg.pts == 1, "D", "L")), "")
    tg["xgd"] = tg["xg"] - tg["xga"]
    tg["pts_minus_mkt"] = tg["pts"] - tg["mkt_xP"]
    tg["xgxp_minus_mkt"] = tg["xg_xP"] - tg["mkt_xP"]
    tg["luck"] = tg["pts"] - tg["xg_xP"]
    tg["cl_minus_mkt"] = tg["cl_xP"] - tg["mkt_xP"]      # how far the match market re-rated the team for that game
    tg["now_minus_mkt"] = tg["now_xP"] - tg["mkt_xP"]    # current model vs start-of-season model, upcoming games
    # Europe / congestion flags
    ctx, eu = load_context()
    tg["europe"] = ""
    tg["congested"] = False
    if not eu.empty:
        for _, e in eu.iterrows():
            dates = [pd.to_datetime(x, format="%d/%m/%Y") for x in str(e["matchdates"]).split(";") if x]
            m = tg["team"] == e["team"]
            tg.loc[m, "europe"] = e["competition"]
            ko = tg.loc[m, "kickoff"]
            flag = np.zeros(m.sum(), bool)
            for dte in dates:
                flag |= ((ko - dte).dt.days.abs() <= 3).to_numpy()
            tg.loc[m, "congested"] = flag

    # --- rolling windows
    tg["roll4_pts"] = tg.groupby("team")["pts"].transform(lambda s: s.rolling(4, min_periods=1).sum())
    tg["roll4_mkt"] = tg.groupby("team").apply(lambda g: g["mkt_xP"].where(g["played"]).rolling(4, min_periods=1).sum(), include_groups=False).reset_index(level=0, drop=True)
    tg["roll4_xgxp"] = tg.groupby("team")["xg_xP"].transform(lambda s: s.rolling(4, min_periods=1).sum())

    # --- blocks
    g = tg.groupby(["div", "team", "block"])
    blocks = g.agg(
        first_game=("game_no", "min"), last_game=("game_no", "max"), games=("game_no", "size"),
        start=("kickoff", "min"), end=("kickoff", "max"), played=("played", "sum"),
        home_games=("venue", lambda s: (s == "H").sum()),
        mkt_xP=("mkt_xP", "sum"),
        mkt_xP_played=("mkt_xP", lambda s: s[tg.loc[s.index, "played"]].sum()),
        mkt_var_played=("mkt_var", lambda s: s[tg.loc[s.index, "played"]].sum()),
        now_xP=("now_xP", "sum"),
        pts=("pts", "sum"), xg=("xg", "sum"), xga=("xga", "sum"), xg_xP=("xg_xP", "sum"),
        cl_xP=("cl_xP", "sum"), cl_n=("cl_xP", "count"),
        gf=("gf", "sum"), ga=("ga", "sum"),
        avg_opp_rating=("opp_rating", "mean"), avg_opp_rank=("opp_mkt_rank", "mean"),
        congested=("congested", "sum"), moved=("block_moved", "sum"),
        fixtures=("opponent", lambda s: " · ".join(f"{o} ({v})" for o, v in zip(s, tg.loc[s.index, "venue"]))),
    ).reset_index()
    blocks["pts_vs_mkt"] = np.where(blocks.played > 0, blocks.pts - blocks.mkt_xP_played, np.nan)
    blocks["xgxp_vs_mkt"] = np.where(blocks.played > 0, blocks.xg_xP - blocks.mkt_xP_played, np.nan)
    blocks["luck"] = np.where(blocks.played > 0, blocks.pts - blocks.xg_xP, np.nan)
    blocks["z"] = np.where(blocks.played > 0, blocks.pts_vs_mkt / np.sqrt(blocks.mkt_var_played.clip(lower=1e-6)), np.nan)
    blocks["z_xg"] = np.where(blocks.played > 0, blocks.xgxp_vs_mkt / np.sqrt(blocks.mkt_var_played.clip(lower=1e-6) * 0.6), np.nan)
    blocks["p_chance"] = np.where(blocks.played > 0, 2 * (1 - norm.cdf(np.abs(blocks.z.fillna(0)))), np.nan)
    blocks["status"] = np.where(blocks.played == 0, "upcoming", np.where(blocks.played == blocks.games, "complete", "in progress"))
    blocks["mkt_ppg"] = blocks.mkt_xP / blocks.games
    blocks["now_ppg"] = np.where(blocks.played == blocks.games, np.nan, blocks.now_xP / (blocks.games - blocks.played).clip(lower=1))

    # --- team season summary
    ts = tg.groupby("team").agg(
        played=("played", "sum"), pts_won=("pts", "sum"), gf=("gf", "sum"), ga=("ga", "sum"),
        xg=("xg", "sum"), xga=("xga", "sum"), xg_xP=("xg_xP", "sum"),
        mkt_xP_played=("mkt_xP", lambda s: s[tg.loc[s.index, "played"]].sum()),
        mkt_var_played=("mkt_var", lambda s: s[tg.loc[s.index, "played"]].sum()),
        mkt_xP_season=("mkt_xP", "sum"),
        cl_xP=("cl_xP", "sum"), cl_n=("cl_xP", "count"),
        cl_mkt=("mkt_xP", lambda s: s[tg.loc[s.index, "cl_xP"].notna()].sum()),
        europe=("europe", "first"),
    ).reset_index()
    ts["deduction"] = ts["team"].map(deductions).fillna(0).astype(int)
    ts["pts"] = ts["pts_won"] + ts["deduction"]
    ts = ts.merge(ratings[["team", "rating", "att", "def", "mkt_rank", "title_odds", "releg_odds", "top_odds", "promo_odds", "title_mkt", "releg_mkt", "top_mkt", "promo_mkt", "title_model", "releg_model", "top_model", "promo_model", "points_line", "sd_pts"]], on="team")
    ts["att_now"] = ts["team"].map(att_map)
    ts["def_now"] = ts["team"].map(def_map)
    ts["rating_now"] = ts["att_now"] + ts["def_now"]
    ts["pts_vs_mkt"] = ts.pts_won - ts.mkt_xP_played
    ts["xgxp_vs_mkt"] = ts.xg_xP - ts.mkt_xP_played
    ts["luck"] = ts.pts_won - ts.xg_xP
    ts["z"] = np.where(ts.played > 0, ts.pts_vs_mkt / np.sqrt(ts.mkt_var_played.clip(lower=1e-6)), np.nan)
    ts["cl_rerate"] = np.where(ts.cl_n > 0, ts.cl_xP - ts.cl_mkt, np.nan)   # sum over games with match odds
    ts["div"] = div
    # league table position (with deductions), tie-break GD then GF
    ts["gd"] = ts.gf - ts.ga
    ts = ts.sort_values(["pts", "gd", "gf"], ascending=False)
    ts["pos"] = np.arange(1, len(ts) + 1)
    # remaining schedule
    remaining = tg[~tg.played].groupby("team").agg(rem_games=("mkt_xP", "size"), rem_mkt_ppg=("mkt_xP", "mean"),
                                                    rem_now_ppg=("now_xP", "mean"),
                                                    next4_mkt=("mkt_xP", lambda s: s.head(4).sum()),
                                                    next4_now=("now_xP", lambda s: s.head(4).sum()),
                                                    next8_mkt=("mkt_xP", lambda s: s.head(8).sum()),
                                                    next4_fix=("opponent", lambda s: " · ".join(f"{o} ({v})" for o, v in zip(s.head(4), tg.loc[s.head(4).index, "venue"])))).reset_index()
    ts = ts.merge(remaining, on="team", how="left")
    last4 = tg[tg.played].groupby("team").agg(last4_pts=("pts", lambda s: s.tail(4).sum()), last4_mkt=("mkt_xP", lambda s: s.tail(4).sum()),
                                               last4_xgxp=("xg_xP", lambda s: s.tail(4).sum()), last4_n=("pts", lambda s: min(4, len(s)))).reset_index()
    ts = ts.merge(last4, on="team", how="left")
    # extra season stats (npxG, xGoT) from OddAlerts season tables
    st = load_team_stats(div)
    if not st.empty:
        ts = ts.merge(st[["team", "npxg", "xgot", "xpts"]].rename(columns={"xpts": "xpts_oddalerts"}), on="team", how="left")
        ts["finishing"] = ts["gf"] - ts["xgot"]        # goals above expected-goals-on-target: finishing/keeping luck
        ts["shot_quality"] = ts["xgot"] - ts["xg"]     # placement: xGoT above xG
    else:
        ts["npxg"] = ts["xgot"] = ts["xpts_oddalerts"] = ts["finishing"] = ts["shot_quality"] = np.nan
    # context notes
    if not ctx.empty:
        c = ctx[ctx["division"] == div].groupby("team").apply(lambda g: " | ".join(f"[{t}] {n}" for t, n in zip(g["type"], g["note"])), include_groups=False)
        ts["context"] = ts["team"].map(c).fillna("")
    else:
        ts["context"] = ""

    # --- rest-of-season simulation + live odds -> edge
    ts_by_team = ts.set_index("team")
    pts_now = np.array([ts_by_team.loc[t, "pts"] for t in teams], float)
    n_played_arr = np.array([ts_by_team.loc[t, "played"] for t in teams], float)
    sim = simulate_rest(div, fx, teams, att_now, def_now, pts_now, n_played_arr)
    simdf = pd.DataFrame({"team": teams, "sim_exp_pts": sim["exp_pts"], "sim_sd": sim["sd_pts"], "sim_title": sim["title"],
                          "sim_releg": sim["releg"], "sim_top": sim["top"], "sim_top2": sim["top2"], "sim_top4": sim["top4"],
                          "sim_top6": sim["top6"], "sim_top7": sim["top7"], "sim_promo": sim["promo"], "sim_auto": sim["auto"],
                          "sim_playoff": sim["playoff"], "sim_bottom": sim["bottom"], "sim_exp_rank": sim["exp_rank"]})
    ts = ts.merge(simdf, on="team")
    tsi = ts.set_index("team")
    live = load_odds_live(div)
    scanner = []
    live_map = {}
    if not live.empty:
        market_to_sim = {"title": "sim_title", "relegation": "sim_releg", "promotion": "sim_promo",
                         "top4": "sim_top4", "top6": "sim_top7" if div == "E3" else "sim_top6"}
        market_total = {"title": 1, "relegation": cfg["relegated"], "promotion": cfg["promo"], "top4": 4, "top6": 7 if div == "E3" else 6}
        for mkt, grp in live.groupby("market"):
            if mkt not in market_to_sim:
                continue
            inv = 1 / grp["odds_decimal"].astype(float).to_numpy()
            fair = inv / inv.sum() * market_total[mkt]
            overround = inv.sum() / market_total[mkt]
            for (i, row), pf in zip(grp.iterrows(), fair):
                t = row["team"]
                pm = float(tsi.loc[t, market_to_sim[mkt]])
                live_map[(t, mkt)] = float(row["odds_decimal"])
                then = {"title": "title_mkt", "relegation": "releg_mkt", "promotion": "promo_mkt", "top4": "top_mkt", "top6": "top_mkt"}[mkt]
                p_then = float(tsi.loc[t, then]) if then in ts.columns else np.nan
                if mkt == "top6" and div != "E3" and cfg["top"] != 6:
                    p_then = np.nan
                if mkt == "top4" and cfg["top"] != 4:
                    p_then = np.nan
                scanner.append({
                    "div": div, "team": t, "market": mkt, "odds": float(row["odds_decimal"]), "odds_frac": row["odds_frac"],
                    "bookmaker": row["bookmaker"], "as_of": row["as_of_date"],
                    "p_market": pf, "p_market_raw": 1 / float(row["odds_decimal"]), "overround": overround,
                    "p_model": pm, "p_then": p_then,
                    "edge": pm - pf, "ev": pm * float(row["odds_decimal"]) - 1,
                    "fair_odds": (1 / pm) if pm > 0 else np.inf,
                    "kelly": max(0.0, (pm * float(row["odds_decimal"]) - 1) / (float(row["odds_decimal"]) - 1)) if pm > 0 else 0.0,
                    "price_move": (pf - p_then) if not np.isnan(p_then) else np.nan,
                    "p_blend": 0.5 * pm + 0.5 * pf,
                    "ev_blend": (0.5 * pm + 0.5 * pf) * float(row["odds_decimal"]) - 1,
                    "flag": bool((pm - pf) >= 0.03 and pm >= 0.03 and float(row["odds_decimal"]) <= 51),
                })
    scanner = pd.DataFrame(scanner)
    for mkt, col in (("title", "live_title"), ("relegation", "live_releg"), ("promotion", "live_promo"), ("top4", "live_top4"), ("top6", "live_top6")):
        ts[col] = ts["team"].map(lambda t: live_map.get((t, mkt), np.nan))
    ts = ts.sort_values("mkt_rank").reset_index(drop=True)

    # --- this week's fixtures rated on luck / underlying performance
    week = fixtures_this_week(div, fx, ts)
    return dict(div=div, cfg=cfg, fixtures=fx, team_games=tg, blocks=blocks, teams=ts, ratings=ratings,
                scanner=scanner, week=week, fit_loss=fit_loss, n_rerate=n_fit)


def fixtures_this_week(div, fx, ts, today=None, horizon_days=8):
    """Upcoming fixtures in the next `horizon_days`, each rated on how the two teams' underlying
    numbers (xG performance vs market, and luck = points vs xG) tilt the game relative to the
    market. Positive tilt favours the home side."""
    today = today or pd.Timestamp(datetime.now().date())
    up = fx[(fx["hg"].isna()) & (fx["kickoff"] >= today) & (fx["kickoff"] < today + pd.Timedelta(days=horizon_days))].copy()
    if up.empty:
        return pd.DataFrame()
    t = ts.set_index("team")
    def pg(team, col):
        n = max(int(t.loc[team, "played"]), 1)
        return float(t.loc[team, col]) / n
    rows = []
    for _, m in up.iterrows():
        h, a = m.home, m.away
        luck_h, luck_a = pg(h, "luck"), pg(a, "luck")
        perf_h, perf_a = pg(h, "xgxp_vs_mkt"), pg(a, "xgxp_vs_mkt")
        # market-now win probability for the home side: pre-match odds if published, else August model
        mkt_pH = m.cl_pH if not pd.isna(m.cl_pH) else m.mkt_pH
        mkt_pA = m.cl_pA if not pd.isna(m.cl_pA) else m.mkt_pA
        model_edge_h = (m.now_pW_home - mkt_pH) if not pd.isna(m.now_pW_home) else np.nan
        model_edge_a = (m.now_pW_away - mkt_pA) if not pd.isna(m.now_pW_away) else np.nan
        # shrink each side's per-game numbers toward zero while the sample is small (n/(n+4))
        sh_h = int(t.loc[h, "played"]) / (int(t.loc[h, "played"]) + 4.0)
        sh_a = int(t.loc[a, "played"]) / (int(t.loc[a, "played"]) + 4.0)
        luck_gap = luck_a * sh_a - luck_h * sh_h    # >0: home unlucky / away lucky -> favours home regression-wise
        perf_gap = perf_h * sh_h - perf_a * sh_a    # >0: home playing better vs its market expectation than away
        tilt = 4.0 * luck_gap + 4.0 * perf_gap + (8.0 * model_edge_h if not pd.isna(model_edge_h) else 0.0)
        tilt = float(np.clip(tilt, -5, 5))
        rows.append(dict(
            div=div, match_id=m.match_id, kickoff=m.kickoff, home=h, away=a, round=int(m["round"]),
            home_pos=int(t.loc[h, "pos"]), away_pos=int(t.loc[a, "pos"]), home_played=int(t.loc[h, "played"]), away_played=int(t.loc[a, "played"]),
            home_luck=float(t.loc[h, "luck"]), away_luck=float(t.loc[a, "luck"]), home_luck_pg=luck_h, away_luck_pg=luck_a,
            home_perf=float(t.loc[h, "xgxp_vs_mkt"]), away_perf=float(t.loc[a, "xgxp_vs_mkt"]), home_perf_pg=perf_h, away_perf_pg=perf_a,
            home_vs_mkt=float(t.loc[h, "pts_vs_mkt"]), away_vs_mkt=float(t.loc[a, "pts_vs_mkt"]),
            home_xgd_pg=(float(t.loc[h, "xg"]) - float(t.loc[h, "xga"])) / max(int(t.loc[h, "played"]), 1),
            away_xgd_pg=(float(t.loc[a, "xg"]) - float(t.loc[a, "xga"])) / max(int(t.loc[a, "played"]), 1),
            aug_pH=m.mkt_pH, aug_pD=m.mkt_pD, aug_pA=m.mkt_pA,
            mkt_pH=mkt_pH, mkt_pD=(m.cl_pD if not pd.isna(m.cl_pD) else m.mkt_pD), mkt_pA=mkt_pA, mkt_source=(m.cl_source if isinstance(m.cl_source, str) and m.cl_source else "Aug model"),
            now_pH=m.now_pW_home, now_pD=m.now_pD, now_pA=m.now_pW_away,
            model_edge_home=model_edge_h, model_edge_away=model_edge_a, luck_gap=luck_gap, perf_gap=perf_gap, tilt=tilt,
            lean=("Home" if tilt >= 1.0 else "Away" if tilt <= -1.0 else "Neutral"),
            home_eu=bool(tg_eu(t, h)), away_eu=bool(tg_eu(t, a)),
        ))
    return pd.DataFrame(rows).sort_values(["kickoff", "home"]).reset_index(drop=True)


def tg_eu(t, team):
    return isinstance(t.loc[team, "europe"], str) and t.loc[team, "europe"] != ""


def snapshot(results, when=None):
    """Save dated snapshots; return movers vs the previous snapshot."""
    when = when or datetime.now().strftime("%Y-%m-%d")
    d = HIST / when
    d.mkdir(parents=True, exist_ok=True)
    teams = pd.concat([r["teams"] for r in results.values()])
    blocks = pd.concat([r["blocks"] for r in results.values()])
    scanner = pd.concat([r["scanner"] for r in results.values() if not r["scanner"].empty]) if any(not r["scanner"].empty for r in results.values()) else pd.DataFrame()
    teams.to_csv(d / "teams.csv", index=False)
    blocks.to_csv(d / "blocks.csv", index=False)
    if not scanner.empty:
        scanner.to_csv(d / "scanner.csv", index=False)
    prev_dirs = sorted([p for p in HIST.iterdir() if p.is_dir() and p.name < when])
    movers = pd.DataFrame()
    if prev_dirs:
        prev = pd.read_csv(prev_dirs[-1] / "teams.csv")
        cols = ["team", "div", "played", "pts", "pts_vs_mkt", "xgxp_vs_mkt", "luck", "rating_now", "sim_title", "sim_promo", "sim_releg", "live_title", "live_promo", "live_releg", "pos"]
        cols = [c for c in cols if c in prev.columns and c in teams.columns]
        m = teams[cols].merge(prev[cols], on=["team", "div"], suffixes=("", "_prev"))
        for c in cols[2:]:
            m[f"d_{c}"] = m[c] - m[f"{c}_prev"]
        m["since"] = prev_dirs[-1].name
        movers = m
        movers.to_csv(d / "movers.csv", index=False)
    return when, movers, [p.name for p in prev_dirs] + [when]


def build_all(refit=False, do_snapshot=True):
    OUT.mkdir(exist_ok=True)
    results = {d: build_division(d, refit) for d in DIVS}
    pd.concat([r["fixtures"] for r in results.values()]).to_csv(OUT / "matches.csv", index=False)
    pd.concat([r["team_games"] for r in results.values()]).to_csv(OUT / "team_games.csv", index=False)
    pd.concat([r["blocks"] for r in results.values()]).to_csv(OUT / "blocks.csv", index=False)
    pd.concat([r["teams"] for r in results.values()]).to_csv(OUT / "teams.csv", index=False)
    sc = [r["scanner"] for r in results.values() if not r["scanner"].empty]
    if sc:
        pd.concat(sc).to_csv(OUT / "scanner.csv", index=False)
    wk = [r["week"] for r in results.values() if not r["week"].empty]
    if wk:
        pd.concat(wk).to_csv(OUT / "this_week.csv", index=False)
    if do_snapshot:
        when, movers, dates = snapshot(results)
        results["_snapshot"] = dict(when=when, movers=movers, dates=dates)
    return results


if __name__ == "__main__":
    import sys
    res = build_all(refit="--refit" in sys.argv)
    for d, r in res.items():
        if d.startswith("_"):
            continue
        t = r["teams"]
        print(f"\n== {DIVS[d]['name']}  fit loss {r['fit_loss']:.3f}  rerated on {r['n_rerate']} matches")
        cols = ["mkt_rank", "team", "rating", "rating_now", "mkt_xP_season", "points_line", "title_mkt", "title_model", "releg_mkt", "releg_model", "promo_mkt", "promo_model", "sim_title", "sim_releg", "sim_promo", "live_title", "sim_exp_pts"]
        print(t[[c for c in cols if c in t.columns]].round(3).to_string(index=False))
