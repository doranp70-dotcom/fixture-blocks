"""One-shot rebuild: CSVs in data/ -> model -> Excel workbook + dashboard HTML in out/.

    python build.py            # rebuild using cached start-of-season ratings
    python build.py --refit    # refit ratings from data/odds_*.csv (only if the odds files change; ~6 min)

Weekly inputs to refresh before running:
    data/fixtures_E0..E3.csv   results column ("H - A" for played games, "-" otherwise) and any rearranged dates
    data/xg_E0_oddalerts.csv, data/xg_E1..E3.csv   one row per played match with home/away xG
See UPDATING.md for the sources and fetch recipes.
"""
import sys
from pathlib import Path

from model import build_all, OUT
import build_xlsx
import build_dashboard
import markets

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    refit = "--refit" in sys.argv
    res = build_all(refit=refit)
    for d, r in res.items():
        if d.startswith("_"):
            continue
        t = r["teams"]
        print(f"{r['cfg']['name']:15s} games played {int(t.played.sum()) // 2:3d}  xG rows {int(r['fixtures'].home_xg.notna().sum()):3d}")
    mk, tend = markets.build_markets(res)
    mk.to_csv(OUT / "match_markets.csv", index=False)
    tend.to_csv(OUT / "tendencies.csv", index=False)
    res["_markets"] = dict(markets=mk, tendencies=tend)
    print(f"match markets for {len(mk)} fixtures in the next 10 days")
    xlsx = build_xlsx.build(res, OUT / "fixture_blocks_2026-27.xlsx")
    html = build_dashboard.build(res, OUT / "fixture_blocks.html")
    print("wrote", xlsx)
    print("wrote", html)
    snap = res.get("_snapshot", {})
    if snap:
        print("snapshot", snap["when"], "· history:", ", ".join(snap["dates"]))
        mv = snap.get("movers")
        if mv is not None and not mv.empty:
            top = mv.reindex(mv["d_pts_vs_mkt"].abs().sort_values(ascending=False).index).head(8)
            print("movers since", top["since"].iloc[0], ":", "; ".join(f"{r.team} {r.d_pts_vs_mkt:+.1f}" for r in top.itertuples()))
    print("Open the workbook in Excel - it recalculates all formulas on load.")
