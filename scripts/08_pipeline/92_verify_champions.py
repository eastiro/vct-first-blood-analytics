"""Verify Champions 2026 coverage and the glossary."""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/?lang=zh"
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

        def pick_sel(sel, label):
            i = pg.evaluate("""([s, lab]) => [...document.querySelectorAll(s + ' option')]
                .findIndex(o => o.textContent.includes(lab))""", [sel, label])
            assert i >= 0, f"{sel} 里没有 {label}"
            pg.select_option(sel, index=i)

        opts = pg.evaluate("""() => [...document.querySelectorAll('#eventSelect option')]
            .map(o => o.textContent.trim())""")
        print("  events:", opts[:3], "...")
        check("15 events incl. Champions", len(opts) == 15,  # 全赛季 15 个赛事，赛事是必选项
              f"({len(opts)} options)")

        check("Champions option present",
              any("上海全球冠军赛" in c for c in opts))
        check("Champions is NOT marked no-coords",
              not any("上海全球冠军赛" in c and "无坐标" in c for c in opts))
        # 2026 年中国赛区有三个赛事（Kickoff / S1 / S2），全都没有 2D 回放
        check("only China events marked no-coords",
              sum(1 for c in opts if "无坐标" in c) == 3
              and all("中国" in c for c in opts if "无坐标" in c),
              str([c for c in opts if "无坐标" in c]))

        # select Champions; also clear the map filter so we see the whole event
        pick_sel("#eventSelect", "上海全球冠军赛")
        pg.wait_for_timeout(600)
        pg.select_option("#mapSelect", index=0)
        pg.wait_for_timeout(700)
        n = pg.evaluate("view.length")
        geo = pg.evaluate("view.reduce((s,r)=>s+(r[9]>=0?1:0),0)")
        print(f"  Champions: {n} rounds, {geo} with coords")
        check("Champions has 1810 rounds", n == 1810, f"({n})")
        # 2 rounds are environmental "Fall" deaths with off-map coordinates
        check("Champions has ~full geometry", geo >= 1800, f"({geo}/1810)")

        # 打点只在选定单张地图时绘制；「全部地图」走按图拆分的表
        pg.select_option("#mapSelect", index=1)
        pg.wait_for_timeout(600)
        painted = pg.evaluate("""() => {
          const d = document.getElementById('dots').getContext('2d')
                      .getImageData(0,0,1024,1024).data;
          let k=0; for(let i=3;i<d.length;i+=4) if(d[i]>8) k++;
          return k;
        }""")
        check("Champions draws on the map", painted > 1000, f"({painted} px)")

        # glossary
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(700)
        btn = pg.query_selector("#glossBtn")
        check("glossary button exists", btn is not None)
        btn.click()
        pg.wait_for_timeout(400)
        shown = pg.evaluate("document.getElementById('gloss').classList.contains('show')")
        check("glossary opens", shown is True)
        items = pg.query_selector_all("#gloss .gitem")
        check("glossary has entries", len(items) >= 8, f"({len(items)} entries)")
        txt = pg.inner_text("#gloss")
        for term in ("Meta Fit", "狙击首杀", "补枪", "中国赛区"):
            check(f"glossary explains {term}", term in txt)

        # hover a header term
        pg.hover("th.gloss[data-key='metafit']")
        pg.wait_for_timeout(400)
        tip_shown = pg.evaluate("document.getElementById('tip').classList.contains('show')")
        check("hover tooltip appears", tip_shown is True)
        tip_txt = pg.inner_text("#tip")
        check("tooltip mentions Meta Fit", "版本" in tip_txt, tip_txt[:40])

        check("no js errors", not errs, str(errs))
        b.close()

    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
