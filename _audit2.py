"""Perf + narrow-viewport audit."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"D:\好玩的项目\valorant-analytics\figures\_audit")
URL = "http://127.0.0.1:8777/"


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()

        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(800)

        # time a filter click end-to-end
        t = pg.evaluate("""() => {
          const t0 = performance.now();
          document.querySelector('#mapChips .chip').click();
          return performance.now() - t0;
        }""")
        print(f"click -> render (全部地图): {t:.0f} ms")

        t = pg.evaluate("""() => {
          const t0 = performance.now();
          document.querySelectorAll('#agentRows tr')[0].click();
          return performance.now() - t0;
        }""")
        print(f"click -> render (pin agent): {t:.0f} ms")

        # redundant full scans per rebuild
        n = pg.evaluate("""() => S.raw.rounds.length""")
        print(f"rows in payload: {n}")

        pg.close()

        # narrow viewport
        pg2 = b.new_page(viewport={"width": 430, "height": 900}, device_scale_factor=2)
        pg2.goto(URL, wait_until="networkidle")
        pg2.wait_for_timeout(900)
        pg2.screenshot(path=str(OUT / "04_mobile.png"), full_page=False)
        ov = pg2.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
        print(f"mobile scrollWidth={ov['sw']} clientWidth={ov['cw']} -> "
              f"{'HORIZONTAL OVERFLOW' if ov['sw'] > ov['cw'] + 1 else 'ok'}")

        # 1024 tablet
        pg3 = b.new_page(viewport={"width": 1024, "height": 900})
        pg3.goto(URL, wait_until="networkidle")
        pg3.wait_for_timeout(800)
        pg3.screenshot(path=str(OUT / "05_1024.png"), full_page=False)
        ov = pg3.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
        print(f"1024 scrollWidth={ov['sw']} clientWidth={ov['cw']} -> "
              f"{'HORIZONTAL OVERFLOW' if ov['sw'] > ov['cw'] + 1 else 'ok'}")

        b.close()


if __name__ == "__main__":
    main()
