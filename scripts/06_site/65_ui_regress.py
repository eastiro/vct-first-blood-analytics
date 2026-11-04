"""Final UI regression test covering all six requested changes."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"
FIG = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics\figures")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label} {detail}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1700, "height": 1200})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(900)

        # 1. leaderboards collapse to 5 and can be expanded
        check("weapon list starts at 5 rows",
              len(pg.query_selector_all("#weaponRows tr")) == 5)
        more_vis = pg.evaluate("!document.getElementById('weaponMore').hidden")
        check("weapon shows an expand control", more_vis is True)
        pg.click("#weaponMore")
        pg.wait_for_timeout(400)
        check("weapon expands past 5",
              len(pg.query_selector_all("#weaponRows tr")) > 5,
              f"({len(pg.query_selector_all('#weaponRows tr'))} rows)")
        pg.click("#weaponMore")
        pg.wait_for_timeout(300)
        check("weapon collapses back to 5",
              len(pg.query_selector_all("#weaponRows tr")) == 5)

        # 2. map is now large
        box = pg.evaluate("""() => {
          const r = document.querySelector('.mapwrap').getBoundingClientRect();
          return {w: Math.round(r.width), h: Math.round(r.height)};
        }""")
        check("map is large", box["w"] >= 500, f"({box['w']}x{box['h']} px)")

        # 3. team selector is a <select>
        check("team filter is a dropdown",
              pg.evaluate("document.getElementById('teamSelect').tagName") == "SELECT")

        def pick_sel(sel, label):
            """选项现在带样本量（"伦敦大师赛 2026 · 415 回合"），按文本片段选。"""
            i = pg.evaluate("""([s, lab]) => [...document.querySelectorAll(s + ' option')]
                .findIndex(o => o.textContent.includes(lab))""", [sel, label])
            assert i >= 0, f"{sel} 里没有 {label}"
            pg.select_option(sel, index=i)

        # 4. team options shrink with the event
        n_all = pg.evaluate("document.querySelectorAll('#teamSelect option').length")
        pick_sel("#eventSelect", "伦敦")
        pg.wait_for_timeout(700)
        n_lon = pg.evaluate("document.querySelectorAll('#teamSelect option').length")
        check("London scopes the team list", n_lon < n_all, f"({n_all} -> {n_lon})")
        check("London shows ~12 teams", 10 <= n_lon - 1 <= 14, f"({n_lon-1} teams)")

        pick_sel("#eventSelect", "太平洋")
        pg.wait_for_timeout(700)
        n_pac = pg.evaluate("document.querySelectorAll('#teamSelect option').length")
        check("Pacific scopes the team list", 10 <= n_pac - 1 <= 20, f"({n_pac-1} teams)")

        # 5. agent pin shows per-map breakdown, not a single row
        # 5. agent pin shows per-map breakdown, not a single row
        pg.goto(URL, wait_until="networkidle")     # reset all filters
        pg.wait_for_timeout(800)
        # click the top agent ROW (the leaderboard doubles as the picker)
        first = pg.query_selector("#agentRows tr.pickable")
        check("agent rows are clickable", first is not None)
        agent_name = first.inner_text().split("\n")[0].split("\t")[0]
        first.click()
        pg.wait_for_timeout(700)
        pinned = pg.evaluate("F.agent")
        check("clicking an agent row pins it", pinned >= 0, f"(agent={pinned})")
        rows = len(pg.query_selector_all("#agentRows tr"))
        check("agent pin -> per-map rows", rows >= 5, f"({rows} maps for {agent_name})")
        check("agent panel retitled",
              "在哪拿首杀" in pg.inner_text("#agentPanelTitle"))

        # 5b. agent chips shrink with the event
        n_ac_sha = pg.evaluate("document.querySelectorAll('#agentSelect option').length")
        pick_sel("#eventSelect", "太平洋")
        pg.wait_for_timeout(600)
        n_ac_pac = pg.evaluate("document.querySelectorAll('#agentSelect option').length")
        check("agent chips follow the event", n_ac_pac != n_ac_sha,
              f"({n_ac_sha} -> {n_ac_pac})")

        # 5c. a pinned team must not leak its opponents into the team table
        pg.select_option("#teamSelect", index=1)
        pg.wait_for_timeout(600)
        team_rows = len(pg.query_selector_all("#teamRows tr"))
        check("team table shows only the pinned team", team_rows == 1,
              f"({team_rows} rows)")

        # 6. no dead state: switching event never leaves 0 rounds
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(700)
        dead = []
        for label in ("伦敦", "美洲", "EMEA", "太平洋", "中国"):
            pick_sel("#eventSelect", label)
            pg.wait_for_timeout(450)
            n = pg.evaluate("view.length")
            if n == 0:
                dead.append(label)
        check("no event switch yields an empty view", not dead, str(dead))

        # 7. China still reports numbers with no coordinates.
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(700)
        pick_sel("#eventSelect", "中国 第二赛段")
        pg.wait_for_timeout(600)
        # 「全部地图」不再画点，而是走按图拆分的表
        agg_shown = pg.evaluate(
            "document.getElementById('mapTable').classList.contains('show')")
        check("aggregate mode shows the per-map table", agg_shown is True)

        china_ev = pg.evaluate("F.ev")
        china_name = pg.evaluate("S.D.events[F.ev]")
        china_n = pg.evaluate("view.length")
        check("China event is selected", "China" in china_name,
              f"(ev={china_ev}, {china_name})")
        check("China keeps its rounds", china_n > 2900, f"({china_n})")

        # 选单张地图之后才应该出现「没有坐标」的空状态
        pg.select_option("#mapSelect", index=1)
        pg.wait_for_timeout(600)
        overlay = pg.evaluate(
            "document.getElementById('emptyState').classList.contains('show')")
        check("China shows the no-geometry notice", overlay is True)

        # 8. 队伍表默认跟随赛事，不再永远显示整季
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(700)
        pick_sel("#eventSelect", "太平洋 第二赛段")
        pg.wait_for_timeout(600)
        pac_rows = pg.evaluate("document.querySelectorAll('#teamRows tr').length")
        note = pg.inner_text("#teamCompareNote")
        check("team table follows the event", "太平洋" in note,
              note[:60])
        check("team table is scoped to the event, not the season",
              pac_rows <= 20, f"({pac_rows} rows)")

        # 9. 狙击首杀列有数、且在合理区间
        snipes = pg.evaluate("""() => [...document.querySelectorAll('#teamRows tr')]
            .map(tr => parseFloat(tr.children[7].textContent)).filter(v => !isNaN(v))""")
        check("snipe column renders", len(snipes) >= 8, f"({len(snipes)} rows)")
        check("snipe column is a percentage 0-100",
              all(0 <= v <= 100 for v in snipes), str(snipes[:5]))

        # 10. 赛段对比面板已按用户要求整块删除（"玩围棋的人进来会云里雾里"，
        # 而且选国际赛事时 region 回落到 ALL，拿全赛区混合数据去比单个大师赛
        # 的 S1/S2 本来就是错的口径）。这里只确认它确实不再存在。
        stage_left = pg.evaluate("""() => ['stageRows','stageNote','stageCards',
            'stageLead','stageFoot'].filter(id => document.getElementById(id)).length""")
        check("stage comparison panel removed", stage_left == 0, f"({stage_left} left)")

        # 11. 队标 + 官方缩写（每个队都要有，且图片要真能加载）
        meta = pg.evaluate("""() => ({
          n: S.TM.length,
          tags: S.TM.filter(x => x.tag).length,
          logos: S.TM.filter(x => x.logo).length
        })""")
        check("every team has an official tag", meta["tags"] == meta["n"], str(meta))
        check("every team has a logo", meta["logos"] == meta["n"], str(meta))

        broken = pg.evaluate("""() => [...document.querySelectorAll('#teamRows img.tlogo')]
            .filter(i => i.complete && i.naturalWidth === 0).length""")
        check("team logos actually load", broken == 0, f"({broken} broken)")

        n_tag = pg.evaluate("document.querySelectorAll('#teamRows .ttag').length")
        n_row = pg.evaluate("document.querySelectorAll('#teamRows tr').length")
        check("every row shows its tag chip", n_tag == n_row, f"({n_tag}/{n_row})")

        known = pg.evaluate("""() => {
          const i = S.D.teams.indexOf('EDward Gaming');
          return i >= 0 ? S.TM[i].tag : null;
        }""")
        check("EDG tag is EDG", known == "EDG", str(known))

        # 12. 筛选写进地址栏（走下拉框，不依赖任何搜索组件）
        pg.goto(URL + "?ev=VCT+Pacific+Stage+2", wait_until="networkidle")
        pg.wait_for_timeout(900)
        # 选项文案带回合数（"Paper Rex  ·  415 回合"），按索引选
        idx = pg.evaluate("""() => [...document.querySelectorAll('#teamSelect option')]
            .findIndex(o => o.textContent.startsWith('Paper Rex'))""")
        pg.select_option("#teamSelect", index=idx)
        pg.wait_for_timeout(600)
        qs = pg.evaluate("() => location.search")
        check("filters are written to the URL", "team=Paper+Rex" in qs, qs)
        check("selecting a team scopes the view",
              pg.evaluate("() => S.D.teams[F.team]") == "Paper Rex")

        # 13. 从链接恢复筛选
        pg.goto(URL + "?ev=VCT+Pacific+Stage+2&map=Sunset", wait_until="networkidle")
        pg.wait_for_timeout(900)
        check("link restores the event",
              pg.evaluate("() => S.D.events[F.ev]") == "VCT Pacific Stage 2")
        check("link restores the map",
              pg.evaluate("() => F.map >= 0 ? S.D.maps[F.map] : null") == "Sunset")

        # 14. 排序有 FLIP 过渡，且动画结束后不留内联 transform
        pg.evaluate("""() => {F.team = -1; F.map = -1; rebuild();}""")
        pg.wait_for_timeout(400)
        pg.evaluate("""() => [...document.querySelectorAll('th.sortable')]
            .find(t => t.dataset.sort === 'fbRate').click()""")
        pg.wait_for_timeout(70)
        moving = pg.evaluate("() => document.querySelectorAll('#teamRows tr.moving').length")
        check("sorting animates row positions", moving > 3, f"({moving} rows)")
        pg.wait_for_timeout(520)
        left = pg.evaluate("""() => [...document.querySelectorAll('#teamRows tr')]
            .filter(t => t.style.transform).length""")
        check("inline transforms are cleaned up", left == 0, f"({left} left)")

        # 15. 键盘可达：跳转链接存在，焦点有可见轮廓
        check("skip link exists",
              pg.evaluate("() => !!document.querySelector('a.skip')"))
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(120)
        outlined = pg.evaluate("""() => {
          const el = document.activeElement;
          return el ? getComputedStyle(el).outlineStyle : 'none';
        }""")
        check("focused element shows an outline", outlined not in ("none", ""), outlined)

        check("no js errors", not errs, str(errs))
        b.close()

    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
