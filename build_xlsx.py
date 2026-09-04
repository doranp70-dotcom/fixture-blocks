"""Build the Excel workbook from model outputs. Everything downstream of the Matches sheet is formula-driven."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from model import DIVS, BLOCK

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

FONT = "Arial"
F_BASE = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_HDR = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_INPUT = Font(name=FONT, size=10, color="0000FF")
F_TITLE = Font(name=FONT, size=14, bold=True)
F_NOTE = Font(name=FONT, size=9, italic=True, color="555555")
FILL_HDR = PatternFill("solid", fgColor="1F3864")
FILL_SUB = PatternFill("solid", fgColor="D9E1F2")
FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")
FILL_BLOCK = [PatternFill("solid", fgColor=c) for c in ("EEF3FB", "FFFFFF")]
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center")

NUM2 = "0.00"
NUM1 = "0.0"
PM2 = '+0.00;-0.00;0.00'
PCT = "0.0%"
DATE = "dd mmm yy"
DATET = "ddd dd mmm yy hh:mm"


def hdr(ws, row, headers, widths=None):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 30


def style_range(ws, min_row, max_row, min_col, max_col, font=F_BASE, fmt=None, align=None):
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for c in row:
            c.font = font
            if fmt:
                c.number_format = fmt
            if align:
                c.alignment = align


def build(results: dict, path: Path):
    wb = Workbook()
    snap_info = results.get("_snapshot", {})
    results = {k: v for k, v in results.items() if not k.startswith("_")}
    matches = pd.concat([r["fixtures"] for r in results.values()]).reset_index(drop=True)
    tg = pd.concat([r["team_games"] for r in results.values()]).reset_index(drop=True)
    blocks = pd.concat([r["blocks"] for r in results.values()]).reset_index(drop=True)
    teams = pd.concat([r["teams"] for r in results.values()]).reset_index(drop=True)
    league_name = {d: DIVS[d]["name"] for d in DIVS}

    # ------------------------------------------------------------------ Helper (Poisson grid)
    hp = wb.active
    hp.title = "Helper"
    hdr(hp, 1, ["home goals", "away goals", "home win", "draw", "away win"], [11, 11, 10, 8, 10])
    r = 2
    for i in range(11):
        for j in range(11):
            hp.cell(row=r, column=1, value=i)
            hp.cell(row=r, column=2, value=j)
            hp.cell(row=r, column=3, value=1 if i > j else 0)
            hp.cell(row=r, column=4, value=1 if i == j else 0)
            hp.cell(row=r, column=5, value=1 if i < j else 0)
            r += 1
    style_range(hp, 2, r - 1, 1, 5)
    hp["G1"] = "Poisson outcome grid (0-10 goals each side) used by the xG -> expected points formulas on the Matches sheet."
    hp["G1"].font = F_NOTE
    hp.sheet_properties.tabColor = "999999"

    # ------------------------------------------------------------------ Matches
    ws = wb.create_sheet("Matches")
    mh = ["match_id", "div", "League", "Round", "Kick-off", "Home", "Away", "HG", "AG", "Home xG", "Away xG",
          "Mkt P(H)", "Mkt P(D)", "Mkt P(A)", "Mkt xP Home", "Mkt xP Away",
          "xG P(H)", "xG P(D)", "xG P(A)", "xG xP Home", "xG xP Away", "Pts Home", "Pts Away", "Played", "xG source"]
    hdr(ws, 1, mh, [10, 5, 15, 6, 17, 16, 16, 5, 5, 8, 8, 8, 8, 8, 9, 9, 8, 8, 8, 9, 9, 7, 7, 6, 14])
    POIS = "SUMPRODUCT(POISSON(Helper!$A$2:$A$122,{lh},FALSE)*POISSON(Helper!$B$2:$B$122,{la},FALSE)*Helper!${col}$2:${col}$122)"
    for i, m in matches.iterrows():
        r = i + 2
        ws.cell(row=r, column=1, value=m.match_id)
        ws.cell(row=r, column=2, value=m["div"])
        ws.cell(row=r, column=3, value=league_name[m["div"]])
        ws.cell(row=r, column=4, value=int(m["round"]))
        ws.cell(row=r, column=5, value=m.kickoff.to_pydatetime()).number_format = DATET
        ws.cell(row=r, column=6, value=m.home)
        ws.cell(row=r, column=7, value=m.away)
        for col, val in ((8, m.hg), (9, m.ag), (10, m.home_xg), (11, m.away_xg)):
            c = ws.cell(row=r, column=col, value=None if pd.isna(val) else float(val))
            c.font, c.fill = F_INPUT, FILL_INPUT
        ws.cell(row=r, column=12, value=float(m.mkt_pH)).number_format = PCT
        ws.cell(row=r, column=13, value=float(m.mkt_pD)).number_format = PCT
        ws.cell(row=r, column=14, value=float(m.mkt_pA)).number_format = PCT
        ws.cell(row=r, column=15, value=f"=3*L{r}+M{r}").number_format = NUM2
        ws.cell(row=r, column=16, value=f"=3*N{r}+M{r}").number_format = NUM2
        ws.cell(row=r, column=17, value=f'=IF(OR(J{r}="",K{r}=""),"",{POIS.format(lh=f"J{r}", la=f"K{r}", col="C")})').number_format = PCT
        ws.cell(row=r, column=18, value=f'=IF(OR(J{r}="",K{r}=""),"",{POIS.format(lh=f"J{r}", la=f"K{r}", col="D")})').number_format = PCT
        ws.cell(row=r, column=19, value=f'=IF(Q{r}="","",1-Q{r}-R{r})').number_format = PCT
        ws.cell(row=r, column=20, value=f'=IF(Q{r}="","",3*Q{r}+R{r})').number_format = NUM2
        ws.cell(row=r, column=21, value=f'=IF(Q{r}="","",3*S{r}+R{r})').number_format = NUM2
        ws.cell(row=r, column=22, value=f'=IF(OR(H{r}="",I{r}=""),"",IF(H{r}>I{r},3,IF(H{r}=I{r},1,0)))')
        ws.cell(row=r, column=23, value=f'=IF(OR(H{r}="",I{r}=""),"",IF(I{r}>H{r},3,IF(H{r}=I{r},1,0)))')
        ws.cell(row=r, column=24, value=f'=IF(OR(H{r}="",I{r}=""),0,1)')
        ws.cell(row=r, column=25, value=None if pd.isna(m.get("xg_source")) else m.xg_source)
    n_m = len(matches) + 1
    style_range(ws, 2, n_m, 1, 7)
    style_range(ws, 2, n_m, 12, 25)
    for row in ws.iter_rows(min_row=2, max_row=n_m, min_col=8, max_col=11):
        for c in row:
            c.font, c.fill = F_INPUT, FILL_INPUT
    ws.freeze_panes = "H2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(mh))}{n_m}"
    ws["H1"].comment = Comment("Blue/yellow cells are the only inputs: full-time goals and per-match team xG. Everything else recalculates.", "Claude")
    ws["L1"].comment = Comment("Start-of-season market probabilities from the strength model fitted to Sky Bet outright odds (Aug 2026). Fixed for the season - see Ratings sheet.", "Claude")
    ws["Q1"].comment = Comment("Win/draw/loss probabilities implied by the match xG figures (independent Poisson, 0-10 goals). 'xG xP' = 3*P(win)+P(draw).", "Claude")
    ws.sheet_properties.tabColor = "FFC000"

    # ------------------------------------------------------------------ TeamGames
    wt = wb.create_sheet("TeamGames")
    th = ["key", "div", "League", "Team", "Game", "Block", "Kick-off", "Opponent", "Venue", "match_id", "Opp mkt rank",
          "GF", "GA", "Result", "Pts", "Mkt P(W)", "Mkt P(D)", "Mkt P(L)", "Mkt xP", "xG", "xGA", "xGD", "xG xP",
          "Played", "Pts - Mkt xP", "xG xP - Mkt xP", "row", "Close xP", "Now xP", "Euro wk", "Block (orig)", "xG Opta", "xGA Opta"]
    hdr(wt, 1, th, [22, 5, 14, 16, 6, 6, 17, 16, 6, 10, 8, 5, 5, 7, 5, 8, 8, 8, 8, 7, 7, 7, 8, 6, 9, 10, 6, 8, 8, 7, 8, 8, 8])
    tg = tg.sort_values(["div", "team", "game_no"]).reset_index(drop=True)
    for i, g in tg.iterrows():
        r = i + 2
        wt.cell(row=r, column=1, value=f"{g.team}|{g.game_no}")
        wt.cell(row=r, column=2, value=g["div"])
        wt.cell(row=r, column=3, value=league_name[g["div"]])
        wt.cell(row=r, column=4, value=g.team)
        wt.cell(row=r, column=5, value=int(g.game_no))
        wt.cell(row=r, column=6, value=int(g.block))
        wt.cell(row=r, column=7, value=g.kickoff.to_pydatetime()).number_format = DATET
        wt.cell(row=r, column=8, value=g.opponent)
        wt.cell(row=r, column=9, value=g.venue)
        wt.cell(row=r, column=10, value=g.match_id)
        wt.cell(row=r, column=11, value=int(g.opp_mkt_rank))
        wt.cell(row=r, column=27, value=f"=MATCH(J{r},Matches!$A:$A,0)")
        H = f'I{r}="H"'
        M = "AA%d" % r
        wt.cell(row=r, column=12, value=f'=IF(INDEX(Matches!$X:$X,{M})=0,"",IF({H},INDEX(Matches!$H:$H,{M}),INDEX(Matches!$I:$I,{M})))')
        wt.cell(row=r, column=13, value=f'=IF(INDEX(Matches!$X:$X,{M})=0,"",IF({H},INDEX(Matches!$I:$I,{M}),INDEX(Matches!$H:$H,{M})))')
        wt.cell(row=r, column=14, value=f'=IF(L{r}="","",IF(L{r}>M{r},"W",IF(L{r}=M{r},"D","L")))')
        wt.cell(row=r, column=15, value=f'=IF(L{r}="","",IF(L{r}>M{r},3,IF(L{r}=M{r},1,0)))')
        wt.cell(row=r, column=16, value=f'=IF({H},INDEX(Matches!$L:$L,{M}),INDEX(Matches!$N:$N,{M}))').number_format = PCT
        wt.cell(row=r, column=17, value=f'=INDEX(Matches!$M:$M,{M})').number_format = PCT
        wt.cell(row=r, column=18, value=f'=IF({H},INDEX(Matches!$N:$N,{M}),INDEX(Matches!$L:$L,{M}))').number_format = PCT
        wt.cell(row=r, column=19, value=f'=IF({H},INDEX(Matches!$O:$O,{M}),INDEX(Matches!$P:$P,{M}))').number_format = NUM2
        wt.cell(row=r, column=20, value=f'=IF({H},INDEX(Matches!$J:$J,{M}),INDEX(Matches!$K:$K,{M}))&""').number_format = NUM2
        # the &"" trick above would make numbers text; use proper numeric handling instead:
        wt.cell(row=r, column=20, value=f'=IF(INDEX(Matches!$J:$J,{M})="","",IF({H},INDEX(Matches!$J:$J,{M}),INDEX(Matches!$K:$K,{M})))').number_format = NUM2
        wt.cell(row=r, column=21, value=f'=IF(INDEX(Matches!$K:$K,{M})="","",IF({H},INDEX(Matches!$K:$K,{M}),INDEX(Matches!$J:$J,{M})))').number_format = NUM2
        wt.cell(row=r, column=22, value=f'=IF(T{r}="","",T{r}-U{r})').number_format = PM2
        wt.cell(row=r, column=23, value=f'=IF({H},INDEX(Matches!$T:$T,{M}),INDEX(Matches!$U:$U,{M}))').number_format = NUM2
        wt.cell(row=r, column=24, value=f'=INDEX(Matches!$X:$X,{M})')
        wt.cell(row=r, column=25, value=f'=IF(O{r}="","",O{r}-S{r})').number_format = PM2
        wt.cell(row=r, column=26, value=f'=IF(W{r}="","",W{r}-S{r})').number_format = PM2
        wt.cell(row=r, column=28, value=None if pd.isna(g.cl_xP) else float(g.cl_xP)).number_format = NUM2
        wt.cell(row=r, column=29, value=None if pd.isna(g.now_xP) else float(g.now_xP)).number_format = NUM2
        wt.cell(row=r, column=30, value="Y" if g.congested else None)
        wt.cell(row=r, column=31, value=int(g.block_orig))
        wt.cell(row=r, column=32, value=None if pd.isna(g.xg_opta) else float(g.xg_opta)).number_format = NUM2
        wt.cell(row=r, column=33, value=None if pd.isna(g.xga_opta) else float(g.xga_opta)).number_format = NUM2
    n_t = len(tg) + 1
    style_range(wt, 2, n_t, 1, 33)
    for r in range(2, n_t + 1):
        for col in (12, 13, 14, 15, 24):
            wt.cell(row=r, column=col).alignment = Alignment(horizontal="center")
    wt.freeze_panes = "E2"
    wt.auto_filter.ref = f"A1:{get_column_letter(len(th))}{n_t}"
    wt.column_dimensions["AA"].hidden = True
    wt["AB1"].comment = Comment("Expected points implied by the closing (or latest pre-match) average bookmaker odds for that game - the match market's own re-rating of the team. Blank until football-data.co.uk publishes the round.", "Claude")
    wt["AC1"].comment = Comment("Expected points for an unplayed game under the CURRENT re-rated model (vs Mkt xP = start-of-season model).", "Claude")
    wt.sheet_properties.tabColor = "5B9BD5"
    TG_LAST = n_t

    # ------------------------------------------------------------------ Blocks
    wbk = wb.create_sheet("Blocks")
    bh = ["key", "div", "League", "Team", "Block", "Games", "First", "Last", "Fixtures (H/A)", "Home games",
          "Start", "End", "Played", "Mkt xP (block)", "Mkt xP (played)", "Pts", "xG", "xGA", "xG xP",
          "Pts - Mkt xP", "xG xP - Mkt xP", "Status", "Mkt xP / game", "Avg opp mkt rank",
          "Luck (Pts - xGxP)", "z (vs mkt)", "Chance %", "Now xP (unplayed)", "Euro wks", "Games moved"]
    hdr(wbk, 1, bh, [22, 5, 14, 16, 6, 6, 6, 6, 60, 7, 11, 11, 7, 9, 9, 6, 7, 7, 8, 9, 10, 11, 9, 9, 9, 8, 8, 9, 7, 7])
    blocks = blocks.sort_values(["div", "team", "block"]).reset_index(drop=True)
    TGR = f"TeamGames!$D$2:$D${TG_LAST}"
    TGB = f"TeamGames!$F$2:$F${TG_LAST}"
    TGP = f"TeamGames!$X$2:$X${TG_LAST}"

    def sumifs(col, r, played=False):
        rng = f"TeamGames!${col}$2:${col}${TG_LAST}"
        extra = f",{TGP},1" if played else ""
        return f"=SUMIFS({rng},{TGR},$D{r},{TGB},$E{r}{extra})"

    for i, b in blocks.iterrows():
        r = i + 2
        wbk.cell(row=r, column=1, value=f"{b.team}|{b.block}")
        wbk.cell(row=r, column=2, value=b["div"])
        wbk.cell(row=r, column=3, value=league_name[b["div"]])
        wbk.cell(row=r, column=4, value=b.team)
        wbk.cell(row=r, column=5, value=int(b.block))
        wbk.cell(row=r, column=6, value=f"=COUNTIFS({TGR},$D{r},{TGB},$E{r})")
        wbk.cell(row=r, column=7, value=int(b.first_game))
        wbk.cell(row=r, column=8, value=int(b.last_game))
        wbk.cell(row=r, column=9, value=b.fixtures)
        wbk.cell(row=r, column=10, value=int(b.home_games))
        wbk.cell(row=r, column=11, value=b.start.to_pydatetime()).number_format = DATE
        wbk.cell(row=r, column=12, value=b.end.to_pydatetime()).number_format = DATE
        wbk.cell(row=r, column=13, value=f"=SUMIFS({TGP},{TGR},$D{r},{TGB},$E{r})")
        wbk.cell(row=r, column=14, value=sumifs("S", r)).number_format = NUM2
        wbk.cell(row=r, column=15, value=sumifs("S", r, True)).number_format = NUM2
        wbk.cell(row=r, column=16, value=sumifs("O", r))
        wbk.cell(row=r, column=17, value=sumifs("T", r)).number_format = NUM2
        wbk.cell(row=r, column=18, value=sumifs("U", r)).number_format = NUM2
        wbk.cell(row=r, column=19, value=sumifs("W", r)).number_format = NUM2
        wbk.cell(row=r, column=20, value=f'=IF(M{r}=0,"",P{r}-O{r})').number_format = PM2
        wbk.cell(row=r, column=21, value=f'=IF(M{r}=0,"",S{r}-O{r})').number_format = PM2
        wbk.cell(row=r, column=22, value=f'=IF(M{r}=0,"upcoming",IF(M{r}=F{r},"complete","in progress"))')
        wbk.cell(row=r, column=23, value=f"=N{r}/F{r}").number_format = NUM2
        wbk.cell(row=r, column=24, value=f'=AVERAGEIFS(TeamGames!$K$2:$K${TG_LAST},{TGR},$D{r},{TGB},$E{r})').number_format = NUM1
        wbk.cell(row=r, column=25, value=f'=IF(M{r}=0,"",P{r}-S{r})').number_format = PM2
        wbk.cell(row=r, column=26, value=None if pd.isna(b.z) else round(float(b.z), 2)).number_format = PM2
        wbk.cell(row=r, column=27, value=None if pd.isna(b.p_chance) else float(b.p_chance)).number_format = PCT
        wbk.cell(row=r, column=28, value=None if pd.isna(b.now_xP) or b.played == b.games else float(b.now_xP)).number_format = NUM2
        wbk.cell(row=r, column=29, value=int(b.congested))
        wbk.cell(row=r, column=30, value=int(b.moved))
    n_b = len(blocks) + 1
    style_range(wbk, 2, n_b, 1, 30)
    wbk["Z1"].comment = Comment("How many standard deviations the block's points are from the market expectation, given the variance of those fixtures. |z| > 2 is unusual (Chance % = how often a block this extreme happens by luck alone).", "Claude")
    wbk.freeze_panes = "F2"
    wbk.auto_filter.ref = f"A1:{get_column_letter(len(bh))}{n_b}"
    wbk.conditional_formatting.add(f"T2:U{n_b}", ColorScaleRule(start_type="num", start_value=-4, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=4, end_color="63BE7B"))
    wbk.sheet_properties.tabColor = "5B9BD5"
    BK_LAST = n_b

    # ------------------------------------------------------------------ Ratings / Teams
    wr = wb.create_sheet("Ratings")
    rh = ["div", "League", "Team", "Mkt rank", "Rating (Aug)", "Season Mkt xP", "Points line", "Pts sd", "Title odds", "Releg odds",
          "Title % (mkt)", "Title % (model)", "Releg % (mkt)", "Releg % (model)", "Top-N % (mkt)", "Top-N % (model)",
          "Promo % (mkt)", "Promo % (model)",
          "Rating now", "Attack now", "Defence now", "Sim exp pts", "Sim title %", "Sim top-N %", "Sim promo %", "Sim releg %",
          "Live title", "Live releg", "Live promo", "Live top4", "Live top6/7", "Deduction", "Europe", "Context"]
    hdr(wr, 1, rh, [5, 14, 16, 7, 8, 9, 8, 7, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 14, 60])
    teams = teams.sort_values(["div", "mkt_rank"]).reset_index(drop=True)
    top_sim = {"E0": "sim_top4", "E1": "sim_top6", "E2": "sim_top6", "E3": "sim_top7"}
    for i, t in teams.iterrows():
        r = i + 2
        vals = [t["div"], league_name[t["div"]], t.team, int(t.mkt_rank), float(t.rating), float(t.mkt_xP_season), t.points_line, float(t.sd_pts),
                float(t.title_odds), float(t.releg_odds), t.title_mkt, t.title_model, t.releg_mkt, t.releg_model,
                t.top_mkt, t.top_model, t.promo_mkt, t.promo_model,
                t.rating_now, t.att_now, t.def_now, t.sim_exp_pts, t.sim_title, t[top_sim[t["div"]]], t.sim_promo, t.sim_releg,
                t.live_title, t.live_releg, t.live_promo, t.live_top4, t.live_top6, int(t.deduction), t.europe, t.context]
        for c, v in enumerate(vals, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            cell = wr.cell(row=r, column=c, value=v)
            if c in (5, 19, 20, 21):
                cell.number_format = "0.000"
            elif c in (6, 7, 8, 9, 10, 22, 27, 28, 29, 30, 31):
                cell.number_format = NUM2
            elif 11 <= c <= 18 or 23 <= c <= 26:
                cell.number_format = PCT
    n_r = len(teams) + 1
    style_range(wr, 2, n_r, 1, len(rh))
    wr.freeze_panes = "D2"
    wr.auto_filter.ref = f"A1:{get_column_letter(len(rh))}{n_r}"
    wr["S1"].comment = Comment("Attack + defence after re-rating on this season's match xG (MAP fit around the August prior). Drives the Sim columns and the Scanner.", "Claude")
    wr["W1"].comment = Comment("Rest-of-season Monte Carlo (10,000 runs) from the current table with current ratings and strength uncertainty.", "Claude")
    wr["E1"].comment = Comment("Team strength on a log scale: expected goals for = league average x exp(rating - opponent rating). Fitted so a simulated season reproduces the Sky Bet outright market (title, relegation, top-4/promotion) from August 2026.", "Claude")
    wr["F1"].comment = Comment("Sum of market expected points over all 38/46 fixtures - the season benchmark for each team.", "Claude")
    wr.sheet_properties.tabColor = "70AD47"

    # ------------------------------------------------------------------ League grids
    max_blocks = {d: int(blocks[blocks["div"] == d]["block"].max()) for d in DIVS}
    for d, cfg in DIVS.items():
        wl = wb.create_sheet(cfg["name"])
        nb = max_blocks[d]
        wl["A1"] = f"{cfg['name']} 2026/27 — fixture blocks of {BLOCK} vs the start-of-season outright market"
        wl["A1"].font = F_TITLE
        wl["A2"] = "Each block: Mkt = expected points from the pre-season market model · Pts = actual points so far · xGxP = expected points implied by match xG · +/- = Pts minus Mkt xP for the games already played."
        wl["A2"].font = F_NOTE
        base = ["Team", "Mkt rank", "Season Mkt xP", "P", "Pts", "Mkt xP (played)", "Pts +/-", "xG xP", "xGxP +/-", "xG", "xGA"]
        r0 = 4
        for i, h in enumerate(base, 1):
            c = wl.cell(row=r0 + 1, column=i, value=h)
            c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
        wl.merge_cells(start_row=r0, start_column=1, end_row=r0, end_column=len(base))
        wl.cell(row=r0, column=1, value="Season to date").font = F_BOLD
        wl.cell(row=r0, column=1).alignment = CENTER
        col = len(base) + 1
        sub = ["Mkt", "Pts", "xGxP", "+/-"]
        for b in range(1, nb + 1):
            wl.merge_cells(start_row=r0, start_column=col, end_row=r0, end_column=col + len(sub) - 1)
            c = wl.cell(row=r0, column=col, value=f"Block {b}")
            c.font, c.alignment, c.fill = F_BOLD, CENTER, FILL_SUB
            for k, s in enumerate(sub):
                cc = wl.cell(row=r0 + 1, column=col + k, value=s)
                cc.font, cc.fill, cc.alignment = F_HDR, FILL_HDR, CENTER
            col += len(sub)
        last_col = col - 1
        dteams = teams[teams["div"] == d].sort_values("mkt_rank")
        BK = f"Blocks!$A$2:$A${BK_LAST}"

        def bidx(colL, keyexpr):
            return f'IFERROR(INDEX(Blocks!${colL}$2:${colL}${BK_LAST},MATCH({keyexpr},{BK},0)),"")'

        r = r0 + 2
        for _, t in dteams.iterrows():
            key = f'$A{r}'
            wl.cell(row=r, column=1, value=t.team).font = F_BOLD
            wl.cell(row=r, column=2, value=int(t.mkt_rank))
            wl.cell(row=r, column=3, value=f'=IFERROR(INDEX(Ratings!$F:$F,MATCH({key},Ratings!$C:$C,0)),"")').number_format = NUM1
            wl.cell(row=r, column=4, value=f"=SUMIFS({TGP},{TGR},{key})")
            wl.cell(row=r, column=5, value=f"=SUMIFS(TeamGames!$O$2:$O${TG_LAST},{TGR},{key})")
            wl.cell(row=r, column=6, value=f"=SUMIFS(TeamGames!$S$2:$S${TG_LAST},{TGR},{key},{TGP},1)").number_format = NUM2
            wl.cell(row=r, column=7, value=f'=IF(D{r}=0,"",E{r}-F{r})').number_format = PM2
            wl.cell(row=r, column=8, value=f"=SUMIFS(TeamGames!$W$2:$W${TG_LAST},{TGR},{key})").number_format = NUM2
            wl.cell(row=r, column=9, value=f'=IF(D{r}=0,"",H{r}-F{r})').number_format = PM2
            wl.cell(row=r, column=10, value=f"=SUMIFS(TeamGames!$T$2:$T${TG_LAST},{TGR},{key})").number_format = NUM2
            wl.cell(row=r, column=11, value=f"=SUMIFS(TeamGames!$U$2:$U${TG_LAST},{TGR},{key})").number_format = NUM2
            col = len(base) + 1
            for b in range(1, nb + 1):
                k = f'{key}&"|{b}"'
                fill = FILL_BLOCK[b % 2]
                c1 = wl.cell(row=r, column=col, value="=" + bidx("N", k)); c1.number_format = NUM2
                c2 = wl.cell(row=r, column=col + 1, value=f'=IF({bidx("M", k)}=0,"",{bidx("P", k)})')
                c3 = wl.cell(row=r, column=col + 2, value=f'=IF({bidx("M", k)}=0,"",{bidx("S", k)})'); c3.number_format = NUM2
                c4 = wl.cell(row=r, column=col + 3, value="=" + bidx("T", k)); c4.number_format = PM2
                for c in (c1, c2, c3, c4):
                    c.fill = fill
                    c.alignment = Alignment(horizontal="center")
                col += len(sub)
            r += 1
        r_last = r - 1
        style_range(wl, r0 + 2, r_last, 2, last_col, font=F_BASE)
        for rr in range(r0 + 2, r_last + 1):
            wl.cell(row=rr, column=1).font = F_BOLD
            for cc in range(2, len(base) + 1):
                wl.cell(row=rr, column=cc).alignment = Alignment(horizontal="center")
        # colour the +/- columns
        for b in range(nb):
            cL = get_column_letter(len(base) + 4 + b * 4)
            wl.conditional_formatting.add(f"{cL}{r0+2}:{cL}{r_last}", ColorScaleRule(start_type="num", start_value=-4, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=4, end_color="63BE7B"))
        wl.conditional_formatting.add(f"G{r0+2}:G{r_last}", ColorScaleRule(start_type="num", start_value=-8, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=8, end_color="63BE7B"))
        wl.conditional_formatting.add(f"I{r0+2}:I{r_last}", ColorScaleRule(start_type="num", start_value=-8, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=8, end_color="63BE7B"))
        # block fixtures listing underneath
        r = r_last + 3
        wl.cell(row=r, column=1, value="Block fixtures (H = home, A = away), in each team's own date order").font = F_BOLD
        r += 1
        for i, h in enumerate(["Team"] + [f"Block {b}" for b in range(1, nb + 1)], 1):
            c = wl.cell(row=r, column=i, value=h)
            c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
        r += 1
        for _, t in dteams.iterrows():
            wl.cell(row=r, column=1, value=t.team).font = F_BOLD
            for b in range(1, nb + 1):
                c = wl.cell(row=r, column=1 + b, value=f'=IFERROR(INDEX(Blocks!$I$2:$I${BK_LAST},MATCH($A{r}&"|{b}",{BK},0)),"")')
                c.font = Font(name=FONT, size=8)
                c.alignment = Alignment(wrap_text=True, vertical="top")
            wl.row_dimensions[r].height = 48
            r += 1
        wl.column_dimensions["A"].width = 16
        for cc in range(2, len(base) + 1):
            wl.column_dimensions[get_column_letter(cc)].width = 8
        for cc in range(len(base) + 1, last_col + 1):
            wl.column_dimensions[get_column_letter(cc)].width = 6.5
        wl.freeze_panes = wl.cell(row=r0 + 2, column=2)
        wl.sheet_properties.tabColor = "C00000"

    # ------------------------------------------------------------------ Team view
    wv = wb.create_sheet("Team")
    wv["A1"] = "Team fixture breakdown"
    wv["A1"].font = F_TITLE
    wv["A2"] = "Pick a team:"
    wv["A2"].font = F_BOLD
    wv["B2"] = "Arsenal"
    wv["B2"].font = Font(name=FONT, size=12, bold=True, color="0000FF")
    wv["B2"].fill = FILL_INPUT
    dv = DataValidation(type="list", formula1=f"=Ratings!$C$2:$C${n_r}", allow_blank=False)
    wv.add_data_validation(dv)
    dv.add("B2")
    wv["D2"] = "League:"; wv["D2"].font = F_BOLD
    wv["E2"] = '=IFERROR(INDEX(Ratings!$B:$B,MATCH($B$2,Ratings!$C:$C,0)),"")'
    wv["G2"] = "Rank:"; wv["G2"].font = F_BOLD
    wv["H2"] = '=IFERROR(INDEX(Ratings!$D:$D,MATCH($B$2,Ratings!$C:$C,0)),"")'
    wv["J2"] = "Mkt xP:"; wv["J2"].font = F_BOLD
    wv["K2"] = '=IFERROR(INDEX(Ratings!$F:$F,MATCH($B$2,Ratings!$C:$C,0)),"")'; wv["K2"].number_format = NUM1
    wv["M2"] = "Odds T/R:"; wv["M2"].font = F_BOLD
    wv["N2"] = '=IFERROR(INDEX(Ratings!$H:$H,MATCH($B$2,Ratings!$C:$C,0))&" / "&INDEX(Ratings!$I:$I,MATCH($B$2,Ratings!$C:$C,0)),"")'
    # block summary
    r = 4
    wv.cell(row=r, column=1, value="Blocks").font = F_BOLD
    r += 1
    bsh = ["Block", "Games", "Fixtures (H/A)", "Start", "End", "Played", "Mkt xP", "Mkt xP (played)", "Pts", "Pts +/-", "xG", "xGA", "xG xP", "xGxP +/-", "Status", "Mkt xP/game"]
    for i, h in enumerate(bsh, 1):
        c = wv.cell(row=r, column=i, value=h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r += 1
    max_nb = max(max_blocks.values())
    bcols = {"Games": "F", "Fixtures (H/A)": "I", "Start": "K", "End": "L", "Played": "M", "Mkt xP": "N", "Mkt xP (played)": "O", "Pts": "P", "Pts +/-": "T", "xG": "Q", "xGA": "R", "xG xP": "S", "xGxP +/-": "U", "Status": "V", "Mkt xP/game": "W"}
    for b in range(1, max_nb + 1):
        wv.cell(row=r, column=1, value=b)
        for j, h in enumerate(bsh[1:], 2):
            cl = bcols[h]
            core = f'IFERROR(INDEX(Blocks!${cl}$2:${cl}${BK_LAST},MATCH($B$2&"|"&$A{r},Blocks!$A$2:$A${BK_LAST},0)),"")'
            if h in ("Mkt xP (played)", "Pts", "xG", "xGA", "xG xP"):
                core = f'IF($F{r}=0,"",{core})'
            c = wv.cell(row=r, column=j, value="=" + core)
            if h in ("Start", "End"):
                c.number_format = DATE
            elif h in ("Pts +/-", "xGxP +/-"):
                c.number_format = PM2
            elif h in ("Mkt xP", "Mkt xP (played)", "xG", "xGA", "xG xP", "Mkt xP/game"):
                c.number_format = NUM2
            if h == "Fixtures (H/A)":
                c.alignment = Alignment(wrap_text=True, vertical="top")
                c.font = Font(name=FONT, size=8)
            else:
                c.alignment = Alignment(horizontal="center")
        wv.row_dimensions[r].height = 26
        r += 1
    wv.conditional_formatting.add(f"J6:J{r-1}", ColorScaleRule(start_type="num", start_value=-4, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=4, end_color="63BE7B"))
    wv.conditional_formatting.add(f"N6:N{r-1}", ColorScaleRule(start_type="num", start_value=-4, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=4, end_color="63BE7B"))
    r += 1
    wv.cell(row=r, column=1, value="Game by game").font = F_BOLD
    r += 1
    gsh = ["Game", "Block", "Kick-off", "Opponent", "H/A", "Opp mkt rank", "GF", "GA", "Res", "Pts", "Mkt P(W)", "Mkt P(D)", "Mkt P(L)", "Mkt xP", "xG", "xGA", "xGD", "xG xP", "Pts - Mkt", "xGxP - Mkt",
           "Close xP", "Now xP", "Euro wk", "Cum Pts", "Cum Mkt", "Cum xGxP"]
    for i, h in enumerate(gsh, 1):
        c = wv.cell(row=r, column=i, value=h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r += 1
    gcols = {"Block": "F", "Kick-off": "G", "Opponent": "H", "H/A": "I", "Opp mkt rank": "K", "GF": "L", "GA": "M", "Res": "N", "Pts": "O", "Mkt P(W)": "P", "Mkt P(D)": "Q", "Mkt P(L)": "R", "Mkt xP": "S", "xG": "T", "xGA": "U", "xGD": "V", "xG xP": "W", "Pts - Mkt": "Y", "xGxP - Mkt": "Z",
             "Close xP": "AB", "Now xP": "AC", "Euro wk": "AD"}
    g_first = r
    for gno in range(1, 47):
        wv.cell(row=r, column=1, value=gno)
        for j, h in enumerate(gsh[1:], 2):
            if h == "Cum Pts":
                c = wv.cell(row=r, column=j, value=f'=IF(J{r}="","",SUM(J${g_first}:J{r}))')
            elif h == "Cum Mkt":
                c = wv.cell(row=r, column=j, value=f'=IF(N{r}="","",SUM(N${g_first}:N{r}))')
            elif h == "Cum xGxP":
                c = wv.cell(row=r, column=j, value=f'=IF(R{r}="","",SUM(R${g_first}:R{r}))')
            else:
                cl = gcols[h]
                ix = f'INDEX(TeamGames!${cl}$2:${cl}${TG_LAST},MATCH($B$2&"|"&$A{r},TeamGames!$A$2:$A${TG_LAST},0))'
                if h in ("Close xP", "Now xP", "Euro wk"):
                    c = wv.cell(row=r, column=j, value=f'=IFERROR(IF({ix}="","",{ix}),"")')
                else:
                    c = wv.cell(row=r, column=j, value=f'=IFERROR({ix},"")')
            c.alignment = Alignment(horizontal="center")
            if h in ("Close xP", "Now xP", "Cum Pts", "Cum Mkt", "Cum xGxP"):
                c.number_format = NUM2
            if h == "Kick-off":
                c.number_format = DATET
            elif h in ("Mkt P(W)", "Mkt P(D)", "Mkt P(L)"):
                c.number_format = PCT
            elif h in ("Mkt xP", "xG", "xGA", "xG xP"):
                c.number_format = NUM2
            elif h in ("xGD", "Pts - Mkt", "xGxP - Mkt"):
                c.number_format = PM2
        r += 1
    wv.conditional_formatting.add(f"S{g_first}:T{r-1}", ColorScaleRule(start_type="num", start_value=-2, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=2, end_color="63BE7B"))
    style_range(wv, 6, r - 1, 1, 26, font=F_BASE)
    G_FIRST, G_LAST = g_first, r - 1
    for rr in range(6, 6 + max_nb):
        wv.cell(row=rr, column=3).font = Font(name=FONT, size=8)
    for cl, w in zip("ABCDEFGHIJKLMNOPQRST", [7, 7, 34, 16, 11, 9, 8, 9, 7, 8, 9, 9, 9, 9, 12, 9, 8, 9, 10, 11]):
        wv.column_dimensions[cl].width = w
    wv.freeze_panes = "A4"
    wv.sheet_properties.tabColor = "7030A0"

    # ------------------------------------------------------------------ Scanner
    wsc = wb.create_sheet("Scanner")
    sc = pd.concat([r["scanner"] for r in results.values() if not r["scanner"].empty]) if any(not r["scanner"].empty for r in results.values()) else pd.DataFrame()
    wsc["A1"] = "Outright value scanner — model probability vs live bet365 price"
    wsc["A1"].font = F_TITLE
    wsc["A2"] = "p(model) = rest-of-season simulation with current xG-rerated strengths. p(market) = bet365 price de-vigged. Blend = 50/50 of the two (the model is one input, the market knows things it doesn't). Flag = model edge >= 3 pts, p(model) >= 3%, price <= 50/1. Kelly = full-Kelly fraction on the blended probability. Not advice - a shortlist to investigate."
    wsc["A2"].font = F_NOTE
    sh = ["League", "Team", "Market", "Price", "Decimal", "p (market)", "p (Aug market)", "Price move", "p (model)", "Blend", "Edge (model)", "EV (model)", "EV (blend)", "Fair odds", "Kelly (blend)", "Flag", "As of"]
    for i, h in enumerate(sh, 1):
        c = wsc.cell(row=4, column=i, value=h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r = 5
    if not sc.empty:
        sc = sc.sort_values(["flag", "edge"], ascending=[False, False])
        for _, x in sc.iterrows():
            kb = max(0.0, (x.p_blend * x.odds - 1) / (x.odds - 1))
            vals = [league_name[x["div"]], x.team, x.market, x.odds_frac, x.odds, x.p_market, x.p_then, x.price_move, x.p_model, x.p_blend, x.edge, x.ev, x.ev_blend, x.fair_odds, kb, "FLAG" if x.flag else "", x.as_of]
            for c, v in enumerate(vals, 1):
                if isinstance(v, float) and (pd.isna(v) or v == float("inf")):
                    v = None
                cell = wsc.cell(row=r, column=c, value=v)
                cell.font = F_BASE
                if c in (6, 7, 9, 10, 15):
                    cell.number_format = PCT
                elif c in (8, 11):
                    cell.number_format = '+0.0%;-0.0%;0.0%'
                elif c in (12, 13):
                    cell.number_format = '+0%;-0%;0%'
                elif c in (5, 14):
                    cell.number_format = NUM2
            r += 1
    for cl, w in zip("ABCDEFGHIJKLMNOPQ", [14, 16, 11, 8, 8, 9, 10, 9, 9, 9, 10, 9, 9, 9, 9, 7, 11]):
        wsc.column_dimensions[cl].width = w
    wsc.freeze_panes = "A5"
    wsc.auto_filter.ref = f"A4:Q{max(r-1,5)}"
    wsc.conditional_formatting.add(f"K5:K{max(r-1,5)}", ColorScaleRule(start_type="num", start_value=-0.15, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=0.15, end_color="63BE7B"))
    wsc.conditional_formatting.add(f"M5:M{max(r-1,5)}", ColorScaleRule(start_type="num", start_value=-0.3, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=0.3, end_color="63BE7B"))
    wsc.sheet_properties.tabColor = "C00000"

    # ------------------------------------------------------------------ This week
    wwk = wb.create_sheet("This week")
    wk = pd.concat([r["week"] for r in results.values() if not r["week"].empty]) if any(not r["week"].empty for r in results.values()) else pd.DataFrame()
    wwk["A1"] = "This week's fixtures rated on luck and underlying performance"
    wwk["A1"].font = F_TITLE
    wwk["A2"] = "Luck = points minus xG-implied points (negative = playing better than the points say). Perf = xG-implied points minus the August market expectation. Tilt (-5..+5, + = home) = 4 x luck gap + 4 x performance gap (both per game, shrunk toward 0 while samples are small) + 8 x (current-model P(home) - market P(home)). Market P = published pre-match price where football-data has it, else the August model. Rebuilt every week."
    wwk["A2"].font = F_NOTE
    wh2 = ["League", "Kick-off", "Home", "Pos", "Away", "Pos", "Home luck", "Home perf", "Home vs mkt", "Away luck", "Away perf", "Away vs mkt", "Home xGD/gm", "Away xGD/gm", "P(H) Aug", "P(D) Aug", "P(A) Aug", "P(H) mkt", "P(A) mkt", "Mkt source", "P(H) model", "P(A) model", "Luck gap", "Perf gap", "Model edge (H)", "Tilt", "Lean"]
    for i, h in enumerate(wh2, 1):
        c = wwk.cell(row=4, column=i, value=h); c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r = 5
    if not wk.empty:
        for _, x in wk.assign(a=wk["tilt"].abs()).sort_values("a", ascending=False).iterrows():
            vals = [league_name[x["div"]], x.kickoff.to_pydatetime(), x.home, x.home_pos, x.away, x.away_pos, x.home_luck, x.home_perf, x.home_vs_mkt, x.away_luck, x.away_perf, x.away_vs_mkt, x.home_xgd_pg, x.away_xgd_pg, x.aug_pH, x.aug_pD, x.aug_pA, x.mkt_pH, x.mkt_pA, x.mkt_source, x.now_pH, x.now_pA, x.luck_gap, x.perf_gap, x.model_edge_home, x.tilt, x.lean]
            for c, v in enumerate(vals, 1):
                if isinstance(v, float) and pd.isna(v):
                    v = None
                cell = wwk.cell(row=r, column=c, value=v); cell.font = F_BASE
                if c == 2:
                    cell.number_format = DATET
                elif c in (7, 8, 9, 10, 11, 12, 13, 14, 23, 24, 26):
                    cell.number_format = PM2
                elif 15 <= c <= 22 and c != 20:
                    cell.number_format = PCT
                elif c == 25:
                    cell.number_format = '+0.0%;-0.0%;0.0%'
            r += 1
        wwk.conditional_formatting.add(f"Z5:Z{r-1}", ColorScaleRule(start_type="num", start_value=-5, start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="num", end_value=5, end_color="63BE7B"))
    for cl, w in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [13, 17, 15, 5, 15, 5, 8, 8, 8, 8, 8, 8, 8, 8, 7, 7, 7, 7, 7, 13, 8, 8, 8, 8, 9, 6]):
        wwk.column_dimensions[cl].width = w
    wwk.column_dimensions["AA"].width = 8
    wwk.freeze_panes = "C5"
    wwk.sheet_properties.tabColor = "C00000"

    # ------------------------------------------------------------------ Movers
    wm = wb.create_sheet("Movers")
    snap = snap_info
    mv = snap.get("movers", pd.DataFrame()) if snap else pd.DataFrame()
    wm["A1"] = "Week-on-week movers"
    wm["A1"].font = F_TITLE
    if mv is None or mv.empty:
        wm["A2"] = f"First snapshot ({snap.get('when', '')}). Movers appear from the second weekly build onwards (history/ folder keeps every snapshot)."
        wm["A2"].font = F_NOTE
    else:
        wm["A2"] = f"Change since the {mv['since'].iloc[0]} snapshot. Positive = improved."
        wm["A2"].font = F_NOTE
        mh2 = ["League", "Team", "P", "Δ P", "Pts", "Δ Pts", "Pts vs Mkt", "Δ", "xGxP vs Mkt", "Δ", "Luck", "Δ", "Rating now", "Δ", "Sim title", "Δ", "Sim promo", "Δ", "Sim releg", "Δ", "Live title", "Δ", "Live promo", "Δ", "Live releg", "Δ", "Pos", "Δ"]
        for i, h in enumerate(mh2, 1):
            c = wm.cell(row=4, column=i, value=h)
            c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
        r = 5
        mv = mv.assign(absd=mv["d_pts_vs_mkt"].abs()).sort_values("absd", ascending=False)
        for _, x in mv.iterrows():
            vals = [league_name[x["div"]], x.team, x.played, x.d_played, x.pts, x.d_pts, x.pts_vs_mkt, x.d_pts_vs_mkt, x.xgxp_vs_mkt, x.d_xgxp_vs_mkt, x.luck, x.d_luck, x.rating_now, x.d_rating_now,
                    x.sim_title, x.d_sim_title, x.sim_promo, x.d_sim_promo, x.sim_releg, x.d_sim_releg, x.live_title, x.d_live_title, x.live_promo, x.d_live_promo, x.live_releg, x.d_live_releg, x.pos, -x.d_pos]
            for c, v in enumerate(vals, 1):
                if isinstance(v, float) and pd.isna(v):
                    v = None
                cell = wm.cell(row=r, column=c, value=v)
                cell.font = F_BASE
                if c in (15, 16, 17, 18, 19, 20):
                    cell.number_format = PCT
                elif c in (7, 8, 9, 10, 11, 12, 21, 22, 23, 24, 25, 26):
                    cell.number_format = PM2
                elif c in (13, 14):
                    cell.number_format = "0.000"
            r += 1
        wm.freeze_panes = "C5"
    wm.column_dimensions["A"].width = 14
    wm.column_dimensions["B"].width = 16
    wm.sheet_properties.tabColor = "70AD47"

    # ------------------------------------------------------------------ What-if
    ww = wb.create_sheet("What-if")
    ww["A1"] = "What-if: type hypothetical scores for a team's next four games"
    ww["A1"].font = F_TITLE
    ww["A2"] = "Pick a team:"; ww["A2"].font = F_BOLD
    ww["B2"] = "Arsenal"; ww["B2"].font = Font(name=FONT, size=12, bold=True, color="0000FF"); ww["B2"].fill = FILL_INPUT
    dv2 = DataValidation(type="list", formula1=f"=Ratings!$C$2:$C${n_r}", allow_blank=False)
    ww.add_data_validation(dv2); dv2.add("B2")
    ww["D2"] = "Blue cells are yours: enter GF / GA (and optionally xG for / against) for the next four unplayed games. Everything else recalculates."
    ww["D2"].font = F_NOTE
    # hidden helper: next-4 unplayed game keys per team
    wn = wb.create_sheet("NextGames")
    wn.append(["team", "g1", "g2", "g3", "g4"])
    nxt = tg[~tg["played"]].groupby("team").head(4)
    for team, grp in nxt.groupby("team"):
        keys = [f"{team}|{int(g)}" for g in grp.sort_values("game_no")["game_no"]]
        wn.append([team] + keys + [""] * (4 - len(keys)))
    wn.sheet_state = "hidden"
    NG_LAST = wn.max_row
    wh = ["#", "Game", "Kick-off", "Opponent", "H/A", "Mkt P(W)", "Mkt xP", "Now xP", "GF (you)", "GA (you)", "xG for (you)", "xG ag (you)", "Pts", "xG xP", "Pts - Mkt"]
    for i, h in enumerate(wh, 1):
        c = ww.cell(row=4, column=i, value=h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    POISW = "SUMPRODUCT(POISSON(Helper!$A$2:$A$122,{lh},FALSE)*POISSON(Helper!$B$2:$B$122,{la},FALSE)*Helper!${col}$2:${col}$122)"
    for k in range(4):
        r = 5 + k
        ww.cell(row=r, column=1, value=k + 1)
        key = f'INDEX(NextGames!${get_column_letter(2+k)}$2:${get_column_letter(2+k)}${NG_LAST},MATCH($B$2,NextGames!$A$2:$A${NG_LAST},0))'
        rowm = f'MATCH({key},TeamGames!$A$2:$A${TG_LAST},0)'
        ww.cell(row=r, column=2, value=f'=IFERROR(INDEX(TeamGames!$E$2:$E${TG_LAST},{rowm}),"")')
        ww.cell(row=r, column=3, value=f'=IFERROR(INDEX(TeamGames!$G$2:$G${TG_LAST},{rowm}),"")').number_format = DATET
        ww.cell(row=r, column=4, value=f'=IFERROR(INDEX(TeamGames!$H$2:$H${TG_LAST},{rowm}),"")')
        ww.cell(row=r, column=5, value=f'=IFERROR(INDEX(TeamGames!$I$2:$I${TG_LAST},{rowm}),"")')
        ww.cell(row=r, column=6, value=f'=IFERROR(INDEX(TeamGames!$P$2:$P${TG_LAST},{rowm}),"")').number_format = PCT
        ww.cell(row=r, column=7, value=f'=IFERROR(INDEX(TeamGames!$S$2:$S${TG_LAST},{rowm}),"")').number_format = NUM2
        ww.cell(row=r, column=8, value=f'=IFERROR(INDEX(TeamGames!$AC$2:$AC${TG_LAST},{rowm}),"")').number_format = NUM2
        for c in (9, 10, 11, 12):
            cell = ww.cell(row=r, column=c); cell.font, cell.fill = F_INPUT, FILL_INPUT
        ww.cell(row=r, column=13, value=f'=IF(OR(I{r}="",J{r}=""),"",IF(I{r}>J{r},3,IF(I{r}=J{r},1,0)))')
        ww.cell(row=r, column=14, value=f'=IF(OR(K{r}="",L{r}=""),"",3*{POISW.format(lh=f"K{r}", la=f"L{r}", col="C")}+{POISW.format(lh=f"K{r}", la=f"L{r}", col="D")})').number_format = NUM2
        ww.cell(row=r, column=15, value=f'=IF(M{r}="","",M{r}-G{r})').number_format = PM2
    ww["A10"] = "Totals"; ww["A10"].font = F_BOLD
    ww["G10"] = "=SUM(G5:G8)"; ww["G10"].number_format = NUM2
    ww["H10"] = "=SUM(H5:H8)"; ww["H10"].number_format = NUM2
    ww["M10"] = "=SUM(M5:M8)"
    ww["N10"] = "=SUM(N5:N8)"; ww["N10"].number_format = NUM2
    ww["O10"] = '=IF(COUNT(M5:M8)=0,"",SUM(M5:M8)-SUMPRODUCT((M5:M8<>"")*G5:G8))'; ww["O10"].number_format = PM2
    ww["A12"] = "Season so far"; ww["A12"].font = F_BOLD
    ww["B12"] = "Pts"; ww["C12"] = f'=SUMIFS(TeamGames!$O$2:$O${TG_LAST},TeamGames!$D$2:$D${TG_LAST},$B$2)'
    ww["D12"] = "Mkt xP (played)"; ww["E12"] = f'=SUMIFS(TeamGames!$S$2:$S${TG_LAST},TeamGames!$D$2:$D${TG_LAST},$B$2,TeamGames!$X$2:$X${TG_LAST},1)'; ww["E12"].number_format = NUM2
    ww["A13"] = "After these 4"; ww["A13"].font = F_BOLD
    ww["B13"] = "Pts"; ww["C13"] = "=C12+M10"
    ww["D13"] = "Mkt xP"; ww["E13"] = '=E12+SUMPRODUCT((M5:M8<>"")*G5:G8)'; ww["E13"].number_format = NUM2
    ww["F13"] = "Pts vs Mkt"; ww["G13"] = "=C13-E13"; ww["G13"].number_format = PM2
    ww["A15"] = "Pts needed in the remaining games to hit the season market xP:"; ww["A15"].font = F_NOTE
    ww["H15"] = f'=IFERROR(INDEX(Ratings!$F$2:$F${n_r},MATCH($B$2,Ratings!$C$2:$C${n_r},0))-C13,"")'; ww["H15"].number_format = NUM1
    for cl, w in zip("ABCDEFGHIJKLMNO", [7, 6, 18, 16, 5, 8, 8, 8, 8, 8, 10, 10, 6, 8, 9]):
        ww.column_dimensions[cl].width = w
    style_range(ww, 5, 8, 1, 8)
    ww.sheet_properties.tabColor = "7030A0"

    # ------------------------------------------------------------------ Charts
    from openpyxl.chart import LineChart, BarChart, Reference
    wch = wb.create_sheet("Charts")
    wch["A1"] = "Charts follow the team selected on the Team sheet"
    wch["A1"].font = F_TITLE
    lc = LineChart()
    lc.title = "Cumulative points: actual vs market xP vs xG xP"
    lc.y_axis.title = "points"; lc.x_axis.title = "game"
    lc.height, lc.width = 9, 22
    data = Reference(wv, min_col=24, max_col=26, min_row=G_FIRST - 1, max_row=G_LAST)
    cats = Reference(wv, min_col=1, min_row=G_FIRST, max_row=G_LAST)
    lc.add_data(data, titles_from_data=True); lc.set_categories(cats)
    wch.add_chart(lc, "A3")
    bc = BarChart(); bc.type = "col"; bc.title = "Points vs market xP by block"; bc.height, bc.width = 9, 22
    data2 = Reference(wv, min_col=10, min_row=5, max_row=5 + max_nb)
    cats2 = Reference(wv, min_col=1, min_row=6, max_row=5 + max_nb)
    bc.add_data(data2, titles_from_data=True); bc.set_categories(cats2)
    wch.add_chart(bc, "A22")
    wch.sheet_properties.tabColor = "7030A0"

    # ------------------------------------------------------------------ Context
    wc = wb.create_sheet("Context")
    wc["A1"] = "Context flags: managers, deductions, finance, Europe"
    wc["A1"].font = F_TITLE
    ctx = pd.read_csv(ROOT / "data" / "context.csv") if (ROOT / "data" / "context.csv").exists() else pd.DataFrame()
    eu = pd.read_csv(ROOT / "data" / "europe.csv") if (ROOT / "data" / "europe.csv").exists() else pd.DataFrame()
    for i, h in enumerate(["Date", "Team", "Div", "Type", "Note", "Source"], 1):
        c = wc.cell(row=3, column=i, value=h); c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r = 4
    for _, x in ctx.iterrows():
        for c, v in enumerate([x.date, x.team, x.division, x.type, x.note, x.source], 1):
            cell = wc.cell(row=r, column=c, value=v); cell.font = F_BASE; cell.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1
    r += 1
    for i, h in enumerate(["Team", "Competition", "Matchday dates (league-phase)"], 1):
        c = wc.cell(row=r, column=i, value=h); c.font, c.fill, c.alignment = F_HDR, FILL_HDR, CENTER
    r += 1
    for _, x in eu.iterrows():
        for c, v in enumerate([x.team, x.competition, x.matchdates.replace(";", ", ")], 1):
            wc.cell(row=r, column=c, value=v).font = F_BASE
        r += 1
    for cl, w in zip("ABCDEF", [11, 16, 6, 10, 90, 50]):
        wc.column_dimensions[cl].width = w
    wc.sheet_properties.tabColor = "999999"

    # ------------------------------------------------------------------ Glossary
    wg = wb.create_sheet("Glossary")
    wg["A1"] = "The words, in plain English"; wg["A1"].font = F_TITLE
    gl = [
        ("Expected points (Mkt xP)", "How many points the pre-season betting market thought a team would take from a game or a block. From Sky Bet's August outright odds turned into a strength per team, then each fixture priced home and away. Frozen for the season, so it is a fair yardstick. Arsenal at home to Coventry ≈ 2.2; away at Man City ≈ 1.0."),
        ("vs expected (+/-)", "Points won minus expected points over the games played. Positive = ahead of the market, negative = behind."),
        ("Deserved points (xG xP)", "The points a team would have averaged if each game were decided by the chances created (xG) rather than who finished them. Each match is replayed thousands of times from its xG."),
        ("Playing (Perf)", "Deserved points minus expected points: whether a team is genuinely better or worse than the market thought, ignoring luck."),
        ("Luck", "Points won minus deserved points. Positive = getting more than the chances deserved (likely to fall back); negative = unlucky (likely to bounce). This is 'playing better / worse than the points say'."),
        ("z", "How unusual a divergence is, in standard deviations given those fixtures. Beyond ±2 is rare; within ±1 is noise."),
        ("xG / xGA", "Expected goals for / against: the quality of chances created / allowed, added up."),
        ("Finishing", "Goals minus expected goals on target (xGoT): finishing better or worse than the shots deserved. Usually fades."),
        ("Strength / Rating", "The model's number for how good a team is: 0 = league average, +0.7 = title favourite, −0.8 = likely relegation side. 'Aug' from the market; 'now' after re-rating on this season's xG."),
        ("Projected points (Sim)", "Current points plus the rest of the season simulated 10,000 times with current strengths."),
        ("Season target", "Expected points for the whole season from the August market (matches the Spreadex points lines in the PL)."),
        ("Next 4 / Run-in", "Expected points from the next four fixtures (8+ soft, under 5 hard) / average per remaining game."),
        ("Scanner: Bookie says / Model says / Gap / Blend / Value / Stake guide", "The bookmaker's price as a percentage (margin removed); the model's percentage; the difference; halfway between the two; expected return per £1; full-Kelly stake on the blend (most people use a quarter)."),
        ("This week: Tilt", "−5 to +5 (positive = home): luck gap + playing gap + the model's disagreement with the match price, shrunk while samples are small."),
        ("Blocks", "Each team's fixtures in date order cut into fours. Each block: points won / expected, and the difference."),
    ]
    for i, (a, b) in enumerate(gl, 3):
        wg.cell(row=i, column=1, value=a).font = F_BOLD
        c = wg.cell(row=i, column=2, value=b); c.font = F_BASE; c.alignment = Alignment(wrap_text=True, vertical="top")
    wg.column_dimensions["A"].width = 34; wg.column_dimensions["B"].width = 120
    wg.sheet_properties.tabColor = "1F3864"

    # ------------------------------------------------------------------ README
    wd = wb.create_sheet("README", 0)
    lines = [
        ("Fixture blocks vs the outright market — 2026/27 (Premier League, Championship, League One, League Two)", F_TITLE),
        (f"Built {datetime.now():%d %b %Y}. 92 teams · 2,036 fixtures · blocks of {BLOCK} games in each team's own date order (38 games = 9 blocks + a 2-game tail; 46 games = 11 blocks + 2).", F_NOTE),
        ("", F_BASE),
        ("WHAT EACH SHEET IS", F_BOLD),
        ("Premier League / Championship / League One / League Two — the weekly grid: one row per team (in market order), one group of columns per block: Mkt xP, Pts, xG xP, +/-. Underneath, the fixtures in each block.", F_BASE),
        ("Team — pick any of the 92 teams from the dropdown (B2) for its block summary and all 38/46 games with market probabilities, points, xG, xGA and xG-implied points.", F_BASE),
        ("Blocks — every team-block (1,030 rows) with sums, filterable. Status = upcoming / in progress / complete.", F_BASE),
        ("TeamGames — every team-game (4,072 rows): the long table everything is summed from.", F_BASE),
        ("Matches — the 2,036 fixtures. THE ONLY INPUT SHEET: blue cells on yellow (HG, AG, Home xG, Away xG). Type or paste a result and its xG here and every other sheet recalculates.", F_BASE),
        ("Ratings — the start-of-season strength model: Sky Bet outright odds (Aug 2026), implied probabilities, fitted rating, and the season expected-points benchmark for each team.", F_BASE),
        ("This week — the coming week's fixtures rated on luck (points vs xG) and underlying performance (xG vs the August market): who is playing better than the points say, who worse, and which games those collide in. Rebuilt weekly.", F_BASE),
        ("Scanner — every live bet365 outright price vs the model's rest-of-season simulation: de-vigged market %, model %, a 50/50 blend, edge, EV, Kelly. Flagged prices first, then by model edge. A shortlist to investigate, not a tip sheet.", F_BASE),
        ("Movers — week-on-week changes in each team's picture (points vs market, luck, rating, model % and live prices). Fills from the second weekly build.", F_BASE),
        ("What-if — pick a team, type scores for its next four games, see the block and season numbers move.", F_BASE),
        ("Charts — cumulative points vs market vs xG, and block +/- bars, for the team chosen on the Team sheet.", F_BASE),
        ("Context — managerial changes, deductions, embargoes and European fixture dates that the numbers can't see.", F_BASE),
        ("Helper / NextGames — lookup tables for the formulas. Leave them alone.", F_BASE),
        ("", F_BASE),
        ("HOW THE NUMBERS ARE MADE", F_BOLD),
        ("1. Market: Sky Bet pre-season outright odds (title, relegation, top-4 for the PL, promotion for the EFL) via fanbanter.co.uk, 10-14 Aug 2026. Odds -> implied probabilities, normalised so titles sum to 1, relegation to 3 (4 in L1, 2 in L2), etc.", F_BASE),
        ("2. Ratings: a Dixon-Coles Poisson goals model (home xG = league home average x exp(attack - opponent defence); away likewise). Pre-season, attack = defence = half the team's strength, fitted so that a 20,000-run season simulation reproduces the market's title / relegation / top-N / promotion probabilities AND, for the PL, the Spreadex season points lines (28 Jul 2026), which pin the scale of expected points; the fitted strength-uncertainty (sd ~11 pts) is reused for the EFL divisions. Man City's 8/1 relegation price is treated as a points-deduction price, not a strength signal, and is ignored.", F_BASE),
        ("2b. In-season: attack and defence are re-rated by a Bayesian (MAP) fit of this season's match xG around the August prior, then the rest of the season is simulated 10,000 times from the live table (Southampton's -4 applied) to give current probabilities for every outright market. The Scanner compares those with live bet365 prices.", F_BASE),
        ("3. Mkt xP per fixture = 3 x P(win) + P(draw) from those ratings, including home advantage. This is frozen for the season: it is the 'what the market expected' yardstick.", F_BASE),
        ("4. xG xP per fixture = the same 3 x P(win) + P(draw), but with the two teams' actual match xG as the Poisson means. It is what the game 'deserved'. Compare it with Pts (luck) and with Mkt xP (performance vs expectation).", F_BASE),
        ("5. Blocks = each team's fixtures sorted by kick-off date and cut into fours. +/- columns are always 'actual minus market' over the games played so far in that block, so an in-progress block is comparable.", F_BASE),
        ("", F_BASE),
        ("DATA SOURCES", F_BOLD),
        ("Fixtures & results: fixturedownload.com (EPL, Championship, EFL League One, EFL League Two 2026/27).", F_BASE),
        ("Match xG (all four divisions): oddalerts.com/xg/<league> 'Recent results with xG' (Sportmonks shot data). Opta xG for the PL differs by up to ~0.5 per match - do not mix providers within a division.", F_BASE),
        ("Team-level xA per match is not published for free for any of these divisions (FBref is bot-blocked), so it is not included. xG, xGA, xGD and xG-implied points are.", F_BASE),
        ("", F_BASE),
        ("WEEKLY UPDATE", F_BOLD),
        ("Option A (no code): on the Matches sheet, fill in HG / AG / Home xG / Away xG for the week's games. Done.", F_BASE),
        ("Option B (regenerate): update data/fixtures_*.csv (results) and data/xg_*.csv, then run  python build.py  — it rebuilds this workbook and the dashboard from the CSVs. Ratings are cached (data/ratings_*.csv) so the market benchmark never drifts; use --refit only if you change the odds files.", F_BASE),
        ("Option C: ask Claude to 'update the fixture blocks' - it re-fetches results and xG from the sources above and republishes both files.", F_BASE),
    ]
    for i, (txt, f) in enumerate(lines, 1):
        c = wd.cell(row=i, column=1, value=txt)
        c.font = f
        c.alignment = Alignment(wrap_text=True, vertical="top")
    wd.column_dimensions["A"].width = 150
    wd.sheet_properties.tabColor = "1F3864"

    # order sheets
    order = ["README", "Glossary"] + [DIVS[d]["name"] for d in DIVS] + ["Team", "This week", "Scanner", "Movers", "What-if", "Charts", "Blocks", "TeamGames", "Matches", "Ratings", "Context", "Helper", "NextGames"]
    wb._sheets = [wb[n] for n in order]
    wb.active = 1
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)
    return path


if __name__ == "__main__":
    from model import build_all
    res = build_all()
    p = build(res, OUT / "fixture_blocks_2026-27.xlsx")
    print("wrote", p)
