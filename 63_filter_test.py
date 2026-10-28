"""Verify that every filter drives every panel."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"
FIG = Path(r"D:\好玩的项目\valorant-analytics\figures")


def snap(pg, label: str) -> None:
    kpi = " ".join(pg.inner_text("#kpis").split())
    meta = pg.inner_text("#mapMeta")
    first_agent = pg.inner_text("#agentRows").split("\n")[0] if pg.inner_text("#agentRows") else "-"
    first_team = pg.inner_text("#teamRows").split("\n")[0] if pg.inner_text("#teamRows") else "-"
    print(f"\n[{label}]")
    print(f"  kpi   : {kpi}")
    print(f"  map   : {meta}")
    print(f"  agent1: {first_agent}")
    print(f"  team1 : {first_team}")


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1400})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(900)

        snap(pg, "default (all events, one map)")

        # pick a specific team
        pg.evaluate("""() => {
          const c = [...document.querySelectorAll('#teamChips .chip')]
                     .find(x => x.textContent.trim() === 'Gen.G');
          c.click();
        }""")
        pg.wait_for_timeout(600)
        snap(pg, "team = Gen.G")
        pg.screenshot(path=str(FIG / "site_team_filter.png"), full_page=False)

        # now add an agent filter on top
        pg.evaluate("""() => {
          const c = [...document.querySelectorAll('#agentChips .chip')]
                     .find(x => x.textContent.trim() === '霓虹');
          c.click();
        }""")
        pg.wait_for_timeout(600)
        snap(pg, "team = Gen.G + agent = 霓虹")

        # clear every filter, then pick China (no geometry for that event)
        for chips in ("#agentChips", "#teamChips", "#eventChips"):
            pg.evaluate(
                "sel => document.querySelector(sel + ' .chip').click()", chips)
            pg.wait_for_timeout(250)
        pg.evaluate("""() => {
          const c = [...document.querySelectorAll('#eventChips .chip')]
                     .find(x => x.textContent.includes('中国'));
          c.click();
        }""")
        pg.wait_for_timeout(600)
        snap(pg, "event = 中国 S2 only")
        painted = pg.evaluate("""() => {
          const d = document.getElementById('dots').getContext('2d')
                      .getImageData(0,0,1024,1024).data;
          let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>8) n++;
          return n;
        }""")
        overlay = pg.evaluate(
            "document.getElementById('emptyState').classList.contains('show')")
        print(f"  painted px: {painted}")
        print(f"  empty overlay shown: {overlay}")
        pg.screenshot(path=str(FIG / "site_china_filter.png"), full_page=False)

        print(f"\npage errors: {errs if errs else 'none'}")
        b.close()


if __name__ == "__main__":
    main()
