"""Interaction test: event filter, map switch, and the no-geometry case."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"
FIG = Path(r"D:\好玩的项目\vct-first-blood-analytics\figures")


def count_drawn(pg) -> int:
    """Count non-transparent pixels on the dots canvas."""
    return pg.evaluate("""() => {
      const cv = document.getElementById('dots');
      const d = cv.getContext('2d').getImageData(0,0,1024,1024).data;
      let n = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
      return n;
    }""")


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1400})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(800)

        print(f"default map={pg.inner_text('#mapMeta')}")
        print(f"  painted px: {count_drawn(pg)}")

        # switch to a different map (dispatch, since chips are divs swapped on render)
        pg.evaluate("""() => {
          const c = [...document.querySelectorAll('#mapChips .chip')]
                     .find(x => x.dataset.map === 'Ascent');
          c.click();
        }""")
        pg.wait_for_timeout(700)
        print(f"ascent   -> {pg.inner_text('#mapMeta')}  painted={count_drawn(pg)}")

        # filter to Pacific (has geometry)
        pg.evaluate("document.querySelectorAll('#eventChips .chip')[5].click()")
        pg.wait_for_timeout(700)
        print(f"pacific  -> {pg.inner_text('#mapMeta')}  painted={count_drawn(pg)}")

        # filter to China (no geometry)
        pg.evaluate("document.querySelectorAll('#eventChips .chip')[4].click()")
        pg.wait_for_timeout(700)
        print(f"china    -> {pg.inner_text('#mapMeta')}  painted={count_drawn(pg)}")
        pg.evaluate("window.scrollTo(0,0)")
        pg.screenshot(path=str(FIG / "site_china_nogeo.png"), full_page=False)

        print(f"\npage errors: {errs if errs else 'none'}")
        b.close()


if __name__ == "__main__":
    main()
