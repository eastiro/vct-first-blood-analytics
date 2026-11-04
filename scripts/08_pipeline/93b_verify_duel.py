"""Verify the player-comparison page (site/duel.html).

Checks that the scatter's range labels, the mean reference lines and the
detail table all agree with an offline recomputation from data/site_v3.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
URL = "http://127.0.0.1:8777/duel.html"
DATA = json.loads((BASE / "data" / "site_v3.json").read_text(encoding="utf-8"))
D, R, Z = DATA["dict"], DATA["rounds"], DATA["zh"]
MIN_TRIES, MIN_SHARE = 20, 25

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


def offline(ev_idx: int) -> list[dict]:
    """Recompute the scatter population straight from the payload."""
    per: dict[int, dict] = {}
    rounds: dict[int, int] = {}
    fb: dict[int, int] = {}
    for r in R:
        if r[0] != ev_idx:
            continue
        for t in (r[2], r[3]):
            if t >= 0:
                rounds[t] = rounds.get(t, 0) + 1
        k, v = r[15], r[16]
        if k < 0:
            continue
        a = per.setdefault(k, {"win": 0, "lose": 0, "team": -1})
        a["win"] += 1
        if r[5] >= 0:
            a["team"] = r[5]
            fb[r[5]] = fb.get(r[5], 0) + 1
        if v >= 0 and v != k:
            per.setdefault(v, {"win": 0, "lose": 0, "team": -1})["lose"] += 1

    out = []
    for pid, s in per.items():
        n = s["win"] + s["lose"]
        if n < MIN_TRIES or s["team"] < 0:
            continue
        tf = fb.get(s["team"], 0)
        if not tf:
            continue
        share = 100 * s["win"] / tf
        if share < MIN_SHARE:
            continue
        rd = rounds.get(s["team"], 0)
        out.append({
            "pid": pid,
            "name": (DATA["players"][pid] or {}).get("n", "?"),
            "team": s["team"],
            "n": n, "win": s["win"],
            "rate": 100 * s["win"] / n,
            "per100": 100 * n / rd if rd else 0,
            "share": share,
        })
    return out


def near(a: float, b: float, tol: float = 0.051) -> bool:
    """Exact .x5 ties round differently: 65/208 = 31.25, JS toFixed gives 31.3
    (half-up) while Python's .1f gives 31.2 (banker's). Both are correct, so
    compare the numbers with a tolerance slightly wider than one tie step."""
    return abs(a - b) <= tol


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1200})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1200)

        ev_idx = pg.evaluate("() => state.ev")
        ev_name = Z["events"][D["events"][ev_idx]]
        pts = offline(ev_idx)
        print(f"\n  scope: {ev_name} · {len(pts)} players")

        # ---------- 点不再用大小编码样本量 ----------
        dead = pg.evaluate("""() => ({
            radiusOf: typeof radiusOf !== 'undefined',
            median:   typeof median   !== 'undefined',
            legend:   document.getElementById('dotLegend') !== null,
            css:      !!document.querySelector('style').textContent.match(/\\.dotlegend\\s*\\.lg-dot/)
        })""")
        check("dot size no longer encodes sample size", dead["radiusOf"] is False, str(dead))
        check("dot-size legend removed", dead["legend"] is False, str(dead))
        check("unused dot legend CSS removed", dead["css"] is False, str(dead))
        check("median helper removed", dead["median"] is False, str(dead))

        # ---------- 明细表 ----------
        heads = pg.evaluate("""() => [...document.querySelectorAll('thead th')]
            .map(th => th.textContent.trim())""")
        check("table has 7 columns", len(heads) == 7, str(heads))
        check("table leads with name / team", heads[:2] == ["选手", "队伍"], str(heads[:2]))
        check("attempt count is its own column", "尝试" in heads, str(heads))

        rows = pg.evaluate("""() => [...document.querySelectorAll('#duelRows tr')]
            .map(tr => [...tr.children].map(td => td.textContent.trim()))""")
        check("one row per qualifying player", len(rows) == len(pts),
              f"page={len(rows)} offline={len(pts)}")

        exp = sorted(pts, key=lambda x: -x["n"])
        check("rows are sorted by attempts, descending",
              [r[2] for r in rows] == [str(w["n"]) for w in exp],
              f"page={[r[2] for r in rows][:5]}")

        bad = []
        for got, want in zip(rows, exp):
            if got[0] != want["name"]:
                bad.append(f"name {got[0]!r} != {want['name']!r}")
                continue
            if got[1] != D["teams"][want["team"]]:
                bad.append(f"{want['name']} team {got[1]!r}")
            if int(got[2]) != want["n"]:
                bad.append(f"{want['name']} attempts {got[2]} != {want['n']}")
            if int(got[3]) != want["win"]:
                bad.append(f"{want['name']} fb {got[3]} != {want['win']}")
            if got[4] != f"{want['rate']:.1f}%":
                bad.append(f"{want['name']} rate {got[4]} != {want['rate']:.1f}%")
            if not near(float(got[5]), want["per100"]):
                bad.append(f"{want['name']} per100 {got[5]} != {want['per100']:.1f}")
            if not near(float(got[6].rstrip('%')), want["share"]):
                bad.append(f"{want['name']} share {got[6]} != {want['share']:.1f}%")
        check("every table cell matches offline", not bad, str(bad[:3]))

        wins = sum(w["win"] for w in pts)
        check("fb column sums to the scope total",
              sum(int(r[3]) for r in rows) == wins,
              f"{sum(int(r[3]) for r in rows)} vs {wins}")

        # ---------- 虚线 = 均值，并且写明 ----------
        mx = sum(w["per100"] for w in pts) / len(pts)
        my = sum(w["rate"] for w in pts) / len(pts)
        cap = pg.inner_text("#caption")
        check("caption names the dashed line as a mean", "虚线" in cap and "均值" in cap, cap[-60:])
        check("caption spells out the x mean", f"{mx:.1f}" in cap, f"want {mx:.1f}")
        check("caption spells out the y mean", f"{my:.1f}" in cap, f"want {my:.1f}")
        check("caption states the sample the mean covers",
              f"{len(pts)} 位" in cap or f"{len(pts)}位" in cap, cap)

        # 均值不能等于中位数那种「谁都不在」的位置——这里只是记录两者都算得出来，
        # 页面上必须用均值（用户明确说中位「不知道」，均值更正常）。
        src = (BASE / "site" / "duel.html").read_text(encoding="utf-8")
        check("page uses mean() for the reference lines",
              "const mx = mean(xs), my = mean(ys)" in src)

        # ---------- 换赛事也要对 ----------
        for target in ("Masters London 2026", "VCT Pacific Stage 2"):
            idx = D["events"].index(target)
            pg.select_option("#evSel", value=str(idx))
            pg.wait_for_timeout(700)
            rows2 = pg.evaluate("""() => [...document.querySelectorAll('#duelRows tr')]
                .map(tr => [...tr.children].map(td => td.textContent.trim()))""")
            exp2 = sorted(offline(idx), key=lambda x: -x["n"])
            check(f"[{Z['events'][target]}] row count matches",
                  len(rows2) == len(exp2), f"page={len(rows2)} offline={len(exp2)}")
            cap2 = pg.inner_text("#caption")
            mx2 = sum(w["per100"] for w in exp2) / len(exp2)
            check(f"[{Z['events'][target]}] mean updates with the scope",
                  f"{mx2:.1f}" in cap2, f"want {mx2:.1f}")

        check("no js errors", not errs, str(errs))
        b.close()

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
