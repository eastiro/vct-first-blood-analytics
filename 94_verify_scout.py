"""Verify the scouting report page (site/scout.html).

Checks that every number on the page matches an offline recomputation from
data/site_v5.json, and that empty-data states degrade honestly.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
URL = "http://127.0.0.1:8777/scout.html"
DATA = json.loads((BASE / "data" / "site_v5.json").read_text(encoding="utf-8"))
R, D = DATA["rounds"], DATA["dict"]
WINDOW = 5

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


def offline(team: str, map_name: str | None, event: str | None = None) -> dict:
    t = D["teams"].index(team)
    mi = D["maps"].index(map_name) if map_name else -1
    ei = D["events"].index(event) if event else -1
    rows = [r for r in R
            if (r[2] == t or r[3] == t)
            and (mi < 0 or r[1] == mi)
            and (ei < 0 or r[0] == ei)]
    won = sum(1 for r in rows if r[4] == t)
    fb = [r for r in rows if r[5] == t]
    fbw = sum(1 for r in fb if r[4] == t)
    # trade stats are conditioned on THIS team getting the first blood
    tr = [r for r in fb if r[11] == 1]
    ut = [r for r in fb if r[11] == 0]
    return {
        "n": len(rows),
        "win": 100 * won / len(rows) if rows else None,
        "fbFor": len(fb),
        "fbConv": 100 * fbw / len(fb) if fb else None,
        "traded": len(tr),
        "tradedWin": 100 * sum(1 for r in tr if r[4] == t) / len(tr) if tr else None,
        "untraded": len(ut),
        "untradedWin": 100 * sum(1 for r in ut if r[4] == t) / len(ut) if ut else None,
    }


def offline_tl(team: str) -> dict:
    """Per-map (n, won, compN) straight from the raw rows.

    阵容时间轴现在固定按地图分组：阵容是按地图选的，把不同地图的阵容
    混在一起算份额没有意义（PRX 最常用的 5 套里 4 套只出现在单一地图上）。
    """
    t = D["teams"].index(team)
    out = defaultdict(lambda: [0, 0, 0])
    for r in R:
        if r[2] != t and r[3] != t:
            continue
        g = out[r[1]]
        g[0] += 1
        if r[4] == t:
            g[1] += 1
        if (r[12] if r[5] == t else r[13]) >= 0:
            g[2] += 1
    return out


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1200})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1200)

        check("page loads with data", pg.evaluate("() => S.raw.rounds.length") == 32786)

        # 下拉选项现在带样本量（"日落之城 · 225 回合"），按前缀选
        def pick(sel, prefix):
            i = pg.evaluate("""([s,p]) => [...document.querySelectorAll(s + ' option')]
                .findIndex(o => o.textContent.startsWith(p))""", [sel, prefix])
            assert i >= 0, f"{sel} 里没有 {prefix}"
            pg.select_option(sel, index=i)

        # ---------- headers ----------
        # 「全部赛事 + 全部地图」现在不截断，会把所有倾向都列出来；
        # 缩小范围时才收回到 top 3。
        nm = pg.evaluate("() => document.querySelectorAll('#verdictBody .vitem').length")
        check("wide scope lists all tendencies", nm >= 3, f"({nm})")

        # ---------- numeric agreement: PRX / Sunset ----------
        pg.select_option("#teamSel", label="Paper Rex")
        pick("#mapSel", "日落之城")
        pg.wait_for_timeout(700)

        off = offline("Paper Rex", "Sunset")
        got = pg.evaluate("""() => {
          const k = [...document.querySelectorAll('#kpis .kpi')];
          const txt = i => k[i].querySelector('b').textContent;
          return {win: txt(0), fbConv: txt(2),
                  traded: document.querySelectorAll('#tradeBlock .kpi b')[0].textContent,
                  untraded: document.querySelectorAll('#tradeBlock .kpi b')[1].textContent,
                  gap: document.querySelectorAll('#tradeBlock .kpi b')[2].textContent,
                  scope: document.getElementById('teamMeta').textContent};
        }""")
        print(f"  offline PRX/Sunset: n={off['n']} win={off['win']:.1f} "
              f"fbConv={off['fbConv']:.1f} traded={off['tradedWin']:.1f} "
              f"untraded={off['untradedWin']:.1f}")
        check("round count matches", str(off["n"]) in got["scope"].replace(",", ""),
              got["scope"])
        check("win rate matches", got["win"] == f"{off['win']:.1f}%", got["win"])
        check("fb conversion matches", got["fbConv"] == f"{off['fbConv']:.1f}%",
              got["fbConv"])

        # the trade block must be conditioned on this team owning the first blood
        check("trade panel uses fb-owner trades only",
              got["traded"] == f"{off['tradedWin']:.1f}%", got["traded"])
        check("untraded conversion matches",
              got["untraded"] == f"{off['untradedWin']:.1f}%", got["untraded"])
        gap = off["untradedWin"] - off["tradedWin"]
        check("gap is positive (untraded > traded)", gap > 0 and float(got["gap"]) > 0,
              f"offline {gap:+.1f}, page {got['gap']}")

        # ---------- economy ----------
        # 「经济结构」面板已按用户要求删除，这里改为验证它确实不在 DOM 里，
        # 并且底层 econ 统计仍然可用（insights 还在用，不能顺手删坏）。
        econ_bars = pg.evaluate("""() => document.querySelectorAll('#econList .bar').length""")
        check("economy panel removed from DOM", econ_bars == 0, str(econ_bars))
        econ_ok = pg.evaluate("""() => {
          const i = S.D.teams.indexOf('Paper Rex');
          const a = aggregate(view, i);
          const tot = a.econ[0][0]+a.econ[1][0]+a.econ[2][0];
          return tot > 0;
        }""")
        check("econ stats still computed under the hood", econ_ok is True)

        # ---------- player level ----------
        players = pg.evaluate("""() => [...document.querySelectorAll('#playerRows tr')]
            .map(tr => [...tr.children].map(td => td.textContent.trim()))""")
        check("player table has rows", len(players) >= 3, f"({len(players)} rows)")
        top_share = float(players[0][2].rstrip("%"))
        check("top player share is a plausible %", 0 < top_share <= 100,
              f"{players[0][0]} {top_share}%")
        psum = sum(float(r[2].rstrip("%")) for r in players)
        check("player shares sum to ~100%", abs(psum - 100) < 1.5, f"{psum:.1f}%")

        # ---------- china: no economy, no geometry ----------
        # 要先选队伍：赛事候选是按队伍生成的，反过来会选不到
        pg.select_option("#teamSel", label="EDward Gaming")
        pg.wait_for_timeout(400)
        pick("#evSel", "VCT 中国 第二赛段")
        pg.wait_for_timeout(200)
        pg.wait_for_timeout(700)
        badges = pg.evaluate("""() => [...document.querySelectorAll('#teamBadges .badge')]
            .map(b => b.textContent)""")
        check("china gets a no-economy badge",
              any("无经济" in b or "经济覆盖" in b for b in badges), str(badges))
        # 「输掉手枪局后第 2 局的买法」已整体删除（分档口径不成立），
        # 这里改为确认相关 DOM 不再存在，且手枪局面板本身还在。
        r2_gone = pg.evaluate("""() => document.querySelector('#r2Hist') === null
            && document.querySelector('#r2Note') === null""")
        check("round-2 buy histogram removed", r2_gone is True)
        pistol = pg.inner_text("#pistolKpis")
        check("pistol panel still present", len(pistol.strip()) > 0, pistol[:30])

        # partial coverage must be flagged, not silently averaged
        pg.select_option("#evSel", value="-1")
        pg.wait_for_timeout(700)
        badges = pg.evaluate("""() => [...document.querySelectorAll('#teamBadges .badge')]
            .map(b => b.textContent)""")
        check("partial coverage is surfaced", any("覆盖" in b for b in badges), str(badges))

        # ---------- small samples are flagged ----------
        pg.select_option("#teamSel", label="Paper Rex")
        pg.wait_for_timeout(500)
        cmp_full = " ".join(pg.evaluate("""() => [...document.querySelectorAll('#kpis .cmp')]
            .map(c => c.textContent)"""))
        check("sample sizes are always disclosed", "n=" in cmp_full, cmp_full[:50])

        tiny = pg.evaluate("""() => {
          const counts = {};
          for(const r of S.raw.rounds){
            const k = r[2] + ':' + r[1];
            counts[k] = (counts[k] || 0) + 1;
          }
          let best = null, bn = 1e9;
          for(const k in counts) if(counts[k] < bn && counts[k] >= 8){ bn = counts[k]; best = k; }
          if(!best) return null;
          const [t, m] = best.split(':').map(Number);
          F.team = t; F.map = m; F.ev = -1; recompute();
          return {n: bn, team: S.D.teams[t], map: S.D.maps[m]};
        }""")
        pg.wait_for_timeout(400)
        cmp_tiny = " ".join(pg.evaluate("""() => [...document.querySelectorAll('#kpis .cmp')]
            .map(c => c.textContent)"""))
        check("small samples are marked", "小样本" in cmp_tiny,
              f"{tiny} -> {cmp_tiny[:40]}")

        # ---------- 倾向面板：只留事实，不留建议 ----------
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1200)
        pick("#teamSel", "")
        pg.evaluate("""() => {
          const i = [...document.querySelectorAll('#teamSel option')]
            .findIndex(o => o.textContent.includes('Paper Rex'));
          F.team = +document.querySelectorAll('#teamSel option')[i].value;
          F.ev = -1; F.map = -1; fillScopeSelects(); recompute();
        }""")
        pg.wait_for_timeout(600)

        check("verdict has no advice paragraphs",
              pg.evaluate("() => document.querySelectorAll('#verdictBody .vtext').length") == 0)
        items = pg.evaluate("""() => [...document.querySelectorAll('#verdictBody .vitem')]
            .map(x => ({ tag: x.querySelector('.vtag').textContent,
                         main: x.querySelector('.vmain').textContent,
                         cmp: x.querySelector('.vcmp').textContent }))""")
        check("every finding carries a baseline", len(items) > 0 and all(
            ("赛事" in o["cmp"] or "基准" in o["cmp"] or "占队内" in o["cmp"]
             or "占 " in o["cmp"]) for o in items), str(items[:2]))
        check("findings do not contain coaching verbs",
              not any(w in (o["main"] + o["cmp"]) for o in items
                      for w in ("建议", "应该", "别指望", "惩罚", "准备")), str(items[:2]))

        # ---------- 联动的回合数 ----------
        cascade = pg.evaluate("""() => {
          const evCount = () => Object.fromEntries(
            [...document.querySelectorAll('#evSel option')]
              .filter(o => o.value !== '-1')
              .map(o => [o.textContent.split(' · ')[0], parseInt(o.textContent.match(/(\\d+) 回合/)[1])]));
          const before = evCount();
          // 选一张跨多个赛事出现的图
          const pickMap = [...document.querySelectorAll('#mapSel option')]
            .find(o => o.value !== '-1' && o.textContent.includes('日落之城'));
          F.map = +pickMap.value; fillScopeSelects(); recompute();
          const after = evCount();
          return { before, after, mapCount: document.querySelectorAll('#mapSel option').length };
        }""")
        changed = [k for k in cascade["after"]
                   if k in cascade["before"] and cascade["after"][k] != cascade["before"][k]]
        check("picking a map changes event round counts", len(changed) > 0,
              f"{list(cascade['before'].items())[:2]} -> {list(cascade['after'].items())[:2]}")
        check("picking a map narrows the event list",
              len(cascade["after"]) < len(cascade["before"]),
              f"{len(cascade['before'])} -> {len(cascade['after'])} events")

        back = pg.evaluate("""() => {
          F.map = -1; fillScopeSelects();
          const allMaps = document.querySelectorAll('#mapSel option').length;
          const ev = [...document.querySelectorAll('#evSel option')]
            .find(o => o.textContent.includes('伦敦'));
          F.ev = +ev.value; fillScopeSelects(); recompute();
          return { allMaps, evMaps: document.querySelectorAll('#mapSel option').length };
        }""")
        check("picking an event narrows the map list",
              back["evMaps"] < back["allMaps"], str(back))

        # ---------- 阵容时间轴 ----------
        NTOP = pg.evaluate("COMP_COLORS.length")
        for team in ("Paper Rex", "EDward Gaming", "FNATIC"):
            pg.evaluate("""(name) => {
              const i = [...document.querySelectorAll('#teamSel option')]
                .findIndex(o => o.textContent.includes(name));
              F.team = +document.querySelectorAll('#teamSel option')[i].value;
              F.ev = -1; F.map = -1; fillScopeSelects(); recompute();
            }""", team)
            pg.wait_for_timeout(450)

            rows = pg.eval_on_selector_all("#compList .tlrow", """els => els.map(e => ({
                k: e.querySelector('.k').textContent.trim(),
                v: e.querySelector('.v').textContent.trim(),
                segs: [...e.querySelectorAll('.tlbar i')].map(i => i.style.width),
                nodata: e.querySelector('.tlbar').classList.contains('nodata')
            }))""")
            exp = offline_tl(team)
            check(f"[{team}] timeline has one row per map",
                  len(rows) == len(exp), f"page={len(rows)} offline={len(exp)}")

            bad = []
            # 行按回合数降序排，offline 也按同样顺序对齐后再逐行核对
            ordered = sorted(exp.items(), key=lambda kv: -kv[1][0])
            for row, (mp, (n, won, cn)) in zip(rows, ordered):
                if f"{100*won/n:.1f}%" not in row["v"] or f"{n:,}" not in row["v"]:
                    bad.append(f"map{mp} page='{row['v']}' want {100*won/n:.1f}%/{n:,}")
                if cn == 0 and not row["nodata"]:
                    bad.append(f"map{mp} should be marked no-data")
            check(f"[{team}] timeline n / win rate match offline", not bad, str(bad[:2]))

            sums = [abs(sum(float(w.rstrip('%')) for w in r["segs"]) - 100)
                    for r in rows if not r["nodata"]]
            check(f"[{team}] every timeline row sums to 100%",
                  all(s < 0.6 for s in sums), f"max diff {max(sums) if sums else 0:.2f}")

            leg = pg.eval_on_selector_all("#compLegend .ci", """els => els.map(e => ({
                name: e.querySelector('.cname').textContent.trim(),
                num: e.querySelector('.cnum').textContent.trim(),
                color: e.querySelector('.csw').style.background }))""")
            comps = [l for l in leg if len(l["name"].split(" · ")) == 5]
            others = [l for l in leg if l not in comps]
            shares = [float(l["num"].split("%")[0]) for l in comps]
            check(f"[{team}] legend lists {NTOP} comps (+ optional 'other'), unique colours",
                  len(comps) == NTOP and len({l["color"] for l in leg}) == len(leg),
                  f"{len(leg)} rows")
            check(f"[{team}] legend shares are sorted",
                  all(shares[i] >= shares[i+1] for i in range(len(shares)-1)), str(shares))
            check(f"[{team}] legend shares add up to ~100%",
                  abs(sum(float(l["num"].split("%")[0]) for l in leg) - 100) < 0.6)

        # 锁定单个赛事 → 行维度切到地图
        pg.evaluate("""() => {
          const i = [...document.querySelectorAll('#teamSel option')]
            .findIndex(o => o.textContent.includes('Paper Rex'));
          F.team = +document.querySelectorAll('#teamSel option')[i].value;
          F.ev = -1; F.map = -1; fillScopeSelects();
          const ev = [...document.querySelectorAll('#evSel option')]
            .find(o => o.textContent.includes('伦敦'));
          F.ev = +ev.value; fillScopeSelects(); recompute();
        }""")
        pg.wait_for_timeout(450)
        check("timeline is always grouped by map",
              pg.text_content("#compTitle").strip() == "阵容 · 按地图",
              pg.text_content("#compTitle"))
        nmap = pg.eval_on_selector_all("#compList .tlrow", "e => e.length")
        check("locking one event narrows the map rows",
              1 <= nmap <= len(D["maps"]), f"rows={nmap}")

        check("no js errors", not errs, str(errs[:2]))

        b.close()

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
