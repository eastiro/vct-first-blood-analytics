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

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
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
        "tradedPct": 100 * len(tr) / len(fb) if fb else None,
        "tradedWin": 100 * sum(1 for r in tr if r[4] == t) / len(tr) if tr else None,
        "untraded": len(ut),
        "untradedWin": 100 * sum(1 for r in ut if r[4] == t) / len(ut) if ut else None,
    }


def offline_tl(team: str) -> dict:
    """Per-map (n, won, compN) straight from the raw rows.

    阵容面板的行维度跟着地图选择器走：全部地图时按地图分组（阵容是按地图选的，
    把不同地图的阵容混在一起算份额没有意义——PRX 最常用的 5 套里 4 套只出现在
    单一地图上），选定一张图时按赛事排成时间轴。
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


def offline_tl_events(team: str, map_name: str) -> list[tuple[int, int, int, int]]:
    """(eventIdx, n, won, compN) for one map, in event order."""
    t = D["teams"].index(team)
    mi = D["maps"].index(map_name)
    out = defaultdict(lambda: [0, 0, 0])
    for r in R:
        if (r[2] != t and r[3] != t) or r[1] != mi:
            continue
        g = out[r[0]]
        g[0] += 1
        if r[4] == t:
            g[1] += 1
        if (r[12] if r[5] == t else r[13]) >= 0:
            g[2] += 1
    return [(ei, *out[ei]) for ei in sorted(out)]


def offline_comp_cells(team: str, map_name: str) -> dict[tuple[int, int], list[int]]:
    """(eventIdx, compId) -> [rounds, wins] for one team on one map.

    阵容条上的悬停要报「这套阵容在这个赛事里的胜率」，不是整行的胜率。
    """
    t = D["teams"].index(team)
    mi = D["maps"].index(map_name)
    out: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    for r in R:
        if (r[2] != t and r[3] != t) or r[1] != mi:
            continue
        mc = r[12] if r[5] == t else r[13]
        if mc < 0:
            continue
        cell = out[(r[0], mc)]
        cell[0] += 1
        if r[4] == t:
            cell[1] += 1
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
        # 「首杀后能不能赢」面板已删除（那个 18.8pp 是人数差不是补枪技巧）。
        # 同一组数字现在只剩「首杀未被补」一张卡片，按标签定位而不是按下标，
        # 卡片顺序以后再变也不会误报。
        got = pg.evaluate("""() => {
          const cards = [...document.querySelectorAll('#kpis .kpi')];
          const byLabel = {};
          for(const c of cards){
            const lab = (c.querySelector('.klab')?.textContent || '').replace('?','').trim();
            byLabel[lab] = c.querySelector('b').textContent;
          }
          const txt = i => cards[i].querySelector('b').textContent;
          return {win: txt(0),
                  fbConv: byLabel['首杀→胜'] || '',
                  untradedRate: byLabel['首杀未被补'] || '',
                  labels: Object.keys(byLabel),
                  scope: document.getElementById('teamMeta').textContent};
        }""")
        print(f"  offline PRX/Sunset: n={off['n']} win={off['win']:.1f} "
              f"fbConv={off['fbConv']:.1f} untraded={off['untradedWin']:.1f}")
        check("round count matches", str(off["n"]) in got["scope"].replace(",", ""),
              got["scope"])
        check("win rate matches", got["win"] == f"{off['win']:.1f}%", got["win"])
        check("fb conversion matches", got["fbConv"] == f"{off['fbConv']:.1f}%",
              got["fbConv"])

        # 「首杀未被补」= 1 - 被补率，必须等于离线算的 untraded 胜率口径
        check("untraded share matches offline",
              got["untradedRate"] == f"{100 - off['tradedPct']:.1f}%",
              f"page={got['untradedRate']} want={100 - off['tradedPct']:.1f}%")
        check("trade panel is gone", pg.evaluate(
            "() => document.querySelectorAll('#tradeBlock').length") == 0)

        # ---------- economy ----------
        # 「经济结构」面板已按用户要求删除，这里改为验证它确实不在 DOM 里，
        # 并且底层 econ 统计仍然可用（全买局那条判断还在用，不能顺手删坏）。
        econ_bars = pg.evaluate("""() => document.querySelectorAll('#econList .bar').length""")
        check("economy panel removed from DOM", econ_bars == 0, str(econ_bars))
        econ_ok = pg.evaluate("""() => {
          const i = S.D.teams.indexOf('Paper Rex');
          const a = aggregate(view, i);
          const b = buildBaselines(F.ev, F.map);
          return a.econ[2][0] > 0 && b.fullWin != null;
        }""")
        check("full-buy stats still computed under the hood", econ_ok is True)

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
            ("平均" in o["cmp"] or "50%" in o["cmp"] or "占队内" in o["cmp"]
             or "占 " in o["cmp"]) for o in items), str(items[:2]))
        check("findings do not contain coaching verbs",
              not any(w in (o["main"] + o["cmp"]) for o in items
                      for w in ("建议", "应该", "别指望", "惩罚", "准备")), str(items[:2]))

        # eco 局胜率已删除：那一档是「≤1 把长枪」，12% 是冲锋枪强起，
        # 6.9% 花了 8000 以上，胜率说不出「省钱的回合有多难赢」。
        check("eco-round win rate removed from findings",
              not any(o["tag"] == "eco 局" for o in items),
              str([o["tag"] for o in items]))
        check("eco term dropped from glossary",
              pg.evaluate("() => !('eco 局' in TERMS)") is True)
        check("full-buy finding still present",
              any(o["tag"] == "全买局" for o in items),
              str([o["tag"] for o in items]))

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

            rows = pg.eval_on_selector_all("#compList .tlrow:not(.tlhead)", """els => els.map(e => ({
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
            shares = [float(l["num"].split("%")[0]) for l in comps]
            check(f"[{team}] legend lists {NTOP} comps, unique colours",
                  len(comps) == NTOP and len({l["color"] for l in leg}) == len(leg),
                  f"{len(leg)} rows")
            check(f"[{team}] legend shares are sorted",
                  all(shares[i] >= shares[i+1] for i in range(len(shares)-1)), str(shares))
            # 图例现在只列该队全局最常用的 NTOP 套，不含「其他」，
            # 所以合计必然小于 100%（剩下的散在长尾里）。
            check(f"[{team}] legend shares are a proper subset of the total",
                  0 < sum(shares) <= 100.01,
                  f"{sum(shares):.1f}%")

        # 锁定单个赛事 → 行维度仍是地图
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
        check("all-maps scope groups rows by map",
              pg.text_content("#compTitle").strip() == "阵容 · 按地图",
              pg.text_content("#compTitle"))
        nmap = pg.eval_on_selector_all("#compList .tlrow:not(.tlhead)", "e => e.length")
        check("locking one event narrows the map rows",
              1 <= nmap <= len(D["maps"]), f"rows={nmap}")

        # 行尾那个「53.8% · 461」没有列头的话，和图例的「11.2% · 269 回合」
        # 长得一样，一个是胜率一个是阵容占比，读者分不出来。
        head = pg.evaluate("""() => {
          const h = document.querySelector('#compList .tlhead');
          if(!h) return null;
          return { k: h.querySelector('.k').textContent.trim(),
                   v: h.querySelector('.v').textContent.trim() };
        }""")
        check("comp rows carry a column header",
              head is not None and head["v"] == "胜率 · 回合", str(head))
        check("header names the row dimension",
              head is not None and head["k"] == "地图", str(head))

        # ---------- 选定一张地图 → 行维度切到赛事（时间轴） ----------
        # 阵容是按地图选的，所以「版本变化」只有在同一张图上才看得出来。
        # 在全部地图下按赛事排，一套只打某张图的阵容会在没打这张图的赛事里
        # 显示 0%，看上去像换阵容，其实是赛程里没有这张图。
        for team, map_name, map_zh in (("Paper Rex", "Lotus", "莲华古城"),
                                       ("EDward Gaming", "Lotus", "莲华古城")):
            pg.evaluate("""([name, mp]) => {
              const ti = [...document.querySelectorAll('#teamSel option')]
                .findIndex(o => o.textContent.includes(name));
              F.team = +document.querySelectorAll('#teamSel option')[ti].value;
              F.ev = -1; F.map = -1; fillScopeSelects();
              const mi = [...document.querySelectorAll('#mapSel option')]
                .findIndex(o => o.textContent.includes(mp));
              F.map = +document.querySelectorAll('#mapSel option')[mi].value;
              fillScopeSelects(); recompute();
            }""", [team, map_zh])
            pg.wait_for_timeout(500)

            check(f"[{team}/{map_name}] single map switches to the time axis",
                  pg.text_content("#compTitle").strip() == "阵容 · 按时间",
                  pg.text_content("#compTitle"))

            head_k = pg.evaluate(
                "() => document.querySelector('#compList .tlhead .k').textContent.trim()")
            check(f"[{team}/{map_name}] header relabels the row dimension",
                  head_k == "赛事", head_k)

            rows = pg.eval_on_selector_all("#compList .tlrow:not(.tlhead)", """els => els.map(e => ({
                k: e.querySelector('.k').textContent.trim(),
                v: e.querySelector('.v').textContent.trim(),
                segs: [...e.querySelectorAll('.tlbar i')].map(i => ({
                  w: i.style.width, t: i.getAttribute('title') || '' }))
            }))""")
            exp = offline_tl_events(team, map_name)
            check(f"[{team}/{map_name}] one row per event played",
                  len(rows) == len(exp), f"page={len(rows)} offline={len(exp)}")

            # 行必须按赛事先后排，标签也要对得上
            want_labels = [DATA["zh"]["events"][D["events"][ei]] for ei, *_ in exp]
            check(f"[{team}/{map_name}] rows are in event order",
                  [r["k"] for r in rows] == want_labels,
                  f"page={[r['k'] for r in rows]}")

            bad = []
            for row, (ei, n, won, cn) in zip(rows, exp):
                if f"{100*won/n:.1f}%" not in row["v"] or f"{n:,}" not in row["v"]:
                    bad.append(f"ev{ei} page='{row['v']}' want {100*won/n:.1f}%/{n:,}")
            check(f"[{team}/{map_name}] time-axis n / win rate match offline",
                  not bad, str(bad[:2]))

            sums = [abs(sum(float(s["w"].rstrip('%')) for s in r["segs"]) - 100)
                    for r in rows]
            check(f"[{team}/{map_name}] every time row sums to 100%",
                  all(s < 0.6 for s in sums), f"max diff {max(sums) if sums else 0:.2f}")

            # 悬停要报这套阵容自己的胜率，不是整行胜率。一行里几套阵容的胜率
            # 可以差 20pp 以上（PRX 莲华古城 S1 是 68.4% vs 45.7%），
            # 报整行那个数等于没回答「哪套好用」。
            want = offline_comp_cells(team, map_name)
            # 页面上只有该范围前 6 套上色，其余并进灰色的「其他 N 套」。
            # 这里按同样的规则算出哪些套会有独立的悬停文案。
            scope_n: dict[int, int] = defaultdict(int)
            for (ev, cid), (cn, _cw) in want.items():
                scope_n[cid] += cn
            visible = {cid for cid, _ in
                       sorted(scope_n.items(), key=lambda kv: -kv[1])[:6]}
            bad = []
            for row, (ei, *_rest) in zip(rows, exp):
                got = {}
                for s in row["segs"]:
                    parts = s["t"].split(" · ")
                    # 「其他 N 套」是灰色长尾，没有单一胜率可报，跳过
                    if parts[0].startswith("其他"):
                        # 但也不能报一个合并后的胜率，那等于给一堆阵容编一个数
                        if "胜率" in s["t"]:
                            bad.append(f"ev{ei} merged tail must not carry a win rate: "
                                       f"{s['t']!r}")
                        continue
                    # 阵容名占 5 段，后面是 份额 / 回合 / 胜率
                    if len(parts) < 8:
                        bad.append(f"ev{ei} tooltip too short: {s['t']!r}")
                        continue
                    n = int(parts[6].replace("回合", "").strip())
                    wr = float(parts[7].replace("胜率", "").replace("%", "").strip())
                    got[tuple(parts[:5])] = (n, wr)
                for (ev, cid), (cn, cw) in want.items():
                    if ev != ei or cid not in visible:
                        continue
                    name = tuple(DATA["zh"]["agents"][D["agents"][a]]
                                 for a in DATA["comps"][cid])
                    if name not in got:
                        bad.append(f"ev{ei} comp{cid} missing from tooltips")
                        continue
                    gn, gwr = got[name]
                    # 页面按 1 位小数显示，3/16 = 18.75% 会写成 18.8%，
                    # 所以比四舍五入后的字符串，不要比浮点差
                    if gn != cn or f"{gwr:.1f}" != f"{100*cw/cn:.1f}":
                        bad.append(f"ev{ei} comp{cid} page={gn}/{gwr:.1f}% "
                                   f"want={cn}/{100*cw/cn:.1f}%")
            check(f"[{team}/{map_name}] tooltip carries each comp's own win rate",
                  not bad, str(bad[:3]))

            # 同一套阵容在所有行必须同色，否则看不出走势
            colors = pg.evaluate("""() => {
              const m = new Map();
              let clash = 0;
              for(const i of document.querySelectorAll('#compList .tlbar i')){
                const t = i.getAttribute('title') || '';
                const name = t.split(' · ').slice(0, 5).join(' · ');
                const c = i.style.background;
                if(!name || name.startsWith('其他')) continue;
                if(m.has(name) && m.get(name) !== c) clash++;
                m.set(name, c);
              }
              return { comps: m.size, clash };
            }""")
            check(f"[{team}/{map_name}] a comp keeps one colour across events",
                  colors["clash"] == 0, str(colors))

        check("no js errors", not errs, str(errs[:2]))

        b.close()

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
