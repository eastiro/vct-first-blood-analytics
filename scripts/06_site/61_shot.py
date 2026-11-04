"""Screenshot the local site so the layout can be verified visually."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics\figures\site_shot.png")
URL = "http://127.0.0.1:8777/"


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1400},
                        device_scale_factor=1.4)
        msgs = []
        pg.on("console", lambda m: msgs.append(f"{m.type}: {m.text}"))
        pg.on("pageerror", lambda e: msgs.append(f"PAGEERROR: {e}"))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1200)
        pg.screenshot(path=str(OUT), full_page=True)
        print("saved", OUT, OUT.stat().st_size, "bytes")
        print("console:")
        for m in msgs[:20]:
            print("  ", m)
        if not msgs:
            print("   (clean)")
        # also grab key rendered values
        print("\nsub:", pg.inner_text("#sub"))
        print("mapMeta:", pg.inner_text("#mapMeta"))
        print("cards:", " | ".join(pg.inner_text("#mapCards").split("\n")[:12]))
        b.close()


if __name__ == "__main__":
    main()
