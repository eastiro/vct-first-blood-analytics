"""Verify the site's computed trade / metafit numbers match the offline analysis."""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label} {detail}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1700, "height": 1200})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(900)

        # 默认视图 = 上海冠军赛 / 全部地图。赛事现在是必选项，没有「全部赛事」，
        # 所以这里对着离线跑出来的「冠军赛」数字核对。
        pg.evaluate("""() => {
          F.ev = S.D.events.indexOf('Champions Shanghai 2026');
          F.map = -1; F.team = -1; F.agent = -1; rebuild();
        }""")
        pg.wait_for_timeout(700)

        n = pg.evaluate("view.length")
        check("event round count", n == 1810, f"({n})")

        # 补枪面板与「首杀时刻×攻守」面板都已按用户要求删除。
        # 补枪的两个数字仍由 agg() 算出来（队伍表还在用），这里直接验算，
        # 保证删掉 UI 之后底层口径没有被顺手改坏。
        tv, uv = pg.evaluate("""() => {
          const a = agg(S.raw.rounds);
          return [100*a.tradedWon/a.traded, 100*a.untradedWon/a.untraded];
        }""")
        print(f"  traded={tv:.1f} untraded={uv:.1f} gap={uv-tv:.1f}")
        check("traded FB win% ~56.9 (season)", 56.5 <= tv <= 57.3, f"{tv:.1f}")
        check("untraded FB win% ~75.7 (season)", 75.3 <= uv <= 76.1, f"{uv:.1f}")
        check("gap ~18.8pp (season)", 18.3 <= (uv-tv) <= 19.3, f"{uv-tv:.1f}")

        # 全样本基准（15,715 回合的 71.1%）不再是一个可选视图，
        # 但仍然印在卡片里当参照系，不能丢。
        cards = pg.inner_text("#mapCards")
        check("global baseline still quoted", "71.0" in cards, cards[:60])

        # 赛事表是固定基准，不随筛选变化
        ev_rows = pg.evaluate("""() => [...document.querySelectorAll('#eventRows tr')].length""")
        check("event table keeps all 15 events", ev_rows == 15, f"({ev_rows} rows)")

        # team table now carries metafit + consistency
        hdr = pg.inner_text("#teamCompareNote")
        check("team table explains the China gap", "中国赛区" in hdr, hdr[:40])

        rows = pg.evaluate("""() => [...document.querySelectorAll('#teamRows tr')]
            .slice(0,5).map(tr => tr.innerText.split('\\t'))""")
        print("  sample team rows:")
        for r in rows[:3]:
            print("   ", r)
        check("team row has 8 columns", all(len(r) == 8 for r in rows),
              f"(widths {[len(r) for r in rows]})")

        # PRX 整季 Meta Fit ≈ 74.9%（离线口径，n=2,396 回合）。旧文档写的「PRX Meta Fit 低」
        # 是 15,715 回合那版数据的结论，样本翻倍后已不成立，所以不能再按 55–75 的宽区间放行。
        prx = pg.evaluate("""() => {
          const i = S.D.teams.indexOf('Paper Rex');
          F.team = i; rebuild();
          return {name: S.D.teams[i], agent: view.length};
        }""")
        pg.wait_for_timeout(700)
        row = pg.evaluate("""() => {
          const tr = document.querySelector('#teamRows tr');
          return tr ? tr.innerText.split('\\t') : null;
        }""")
        print(f"\n  Paper Rex row: {row}")
        check("Paper Rex row rendered", row is not None)
        if row:
            # 队伍表默认跟赛事走；这里直接按整季聚合，避免被当前赛事口径影响
            metafit = pg.evaluate("""() => {
              const a = agg(S.raw.rounds);
              const t = S.D.teams.indexOf('Paper Rex');
              const d = a.byTeam.get(t);
              return d && d.metaFitN ? (100*d.metaFitSum/d.metaFitN).toFixed(1) : null;
            }""")
            check("PRX season meta fit matches offline (74.9%)",
                  74.5 <= float(metafit) <= 75.3, metafit)

        check("no js errors", not errs, str(errs))
        b.close()

    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
