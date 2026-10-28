"""Audit the local site: console errors, layout shots, basic sanity."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(r"D:\好玩的项目\valorant-analytics\figures\_audit")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8777/"


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1200},
                        device_scale_factor=1)
        errs, reqfail = [], []
        pg.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.on("requestfailed", lambda r: reqfail.append(f"{r.url} :: {r.failure}"))

        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1200)

        pg.screenshot(path=str(OUT / "01_default.png"), full_page=True)

        # metrics
        info = pg.evaluate("""() => {
          const g = id => (document.getElementById(id)||{}).textContent;
          return {
            sub: g('sub'),
            kpis: g('kpis'),
            traded: g('tradedVal'), untraded: g('untradedVal'), gap: g('tradeGap'),
            mapMeta: g('mapMeta'),
            agentRows: document.querySelectorAll('#agentRows tr').length,
            teamRows: document.querySelectorAll('#teamRows tr').length,
            eventRows: document.querySelectorAll('#eventRows tr').length,
            mapChips: document.querySelectorAll('#mapChips .chip').length,
            agentChips: document.querySelectorAll('#agentChips .chip').length,
            teamOpts: document.querySelectorAll('#teamSelect option').length,
            dotsCanvas: (()=>{const c=document.getElementById('dots');
               const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
               let nz=0; for(let i=3;i<d.length;i+=4*97) if(d[i]>8) nz++;
               return nz; })(),
            dataBytes: performance.getEntriesByType('resource')
               .filter(r=>r.name.includes('site_v3')).map(r=>r.transferSize),
            loadMs: Math.round(performance.timing.loadEventEnd - performance.timing.navigationStart),
          };
        }""")
        for k, v in info.items():
            print(f"{k}: {v}")

        print("\n--- console issues ---")
        print("\n".join(errs) or "(none)")
        print("--- failed requests ---")
        print("\n".join(reqfail) or "(none)")

        # interaction: china event
        pg.get_by_text("中国", exact=False).first.click()
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / "02_china.png"), full_page=True)

        # reset, choose map, then agent drilldown
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(800)
        pg.locator("#mapChips .chip").nth(3).click()
        pg.wait_for_timeout(600)
        pg.locator("#agentRows tr").first.click()
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / "03_agent.png"), full_page=True)

        b.close()


if __name__ == "__main__":
    main()
