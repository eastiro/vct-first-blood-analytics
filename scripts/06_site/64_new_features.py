"""Test the new behaviours: team dropdown scoping, agent pin, weapon top-5."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"
FIG = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics\figures")


def team_options(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('#teamSelect option')]
        .map(o => o.textContent)""")


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1700, "height": 1200})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(900)

        opts = team_options(pg)
        print(f"default team options: {len(opts)}")
        print(f"  hint: {pg.inner_text('#teamHint')}")
        print(f"  weapons rows: {len(pg.query_selector_all('#weaponRows tr'))}")

        # pick London -> team list must shrink to London teams only
        pg.evaluate("""() => {
          [...document.querySelectorAll('#eventChips .chip')]
            .find(x => x.textContent.includes('伦敦')).click();
        }""")
        pg.wait_for_timeout(700)
        opts = team_options(pg)
        print(f"\nLondon only -> team options: {len(opts)}")
        print(f"  hint: {pg.inner_text('#teamHint')}")
        print(f"  first few: {opts[1:6]}")

        # pick EMEA
        pg.evaluate("""() => {
          [...document.querySelectorAll('#eventChips .chip')]
            .find(x => x.textContent.includes('EMEA')).click();
        }""")
        pg.wait_for_timeout(700)
        opts = team_options(pg)
        print(f"\nEMEA only -> team options: {len(opts)}")
        print(f"  hint: {pg.inner_text('#teamHint')}")

        # pin an agent and check the panel switches to per-map breakdown
        pg.evaluate("""() => {
          [...document.querySelectorAll('#eventChips .chip')][0].click();
        }""")
        pg.wait_for_timeout(400)
        pg.evaluate("""() => {
          [...document.querySelectorAll('#agentChips .chip')]
            .find(x => x.textContent.trim() === '霓虹').click();
        }""")
        pg.wait_for_timeout(700)
        print(f"\nagent=霓虹 -> panel title: {pg.inner_text('#agentPanelTitle')}")
        print(f"  note: {pg.inner_text('#agentPanelNote')}")
        rows = pg.query_selector_all('#agentRows tr')
        print(f"  rows: {len(rows)}")
        for r in rows[:4]:
            print(f"    {r.inner_text().replace(chr(9),' | ')}")
        pg.screenshot(path=str(FIG / "site_agent_pin.png"), full_page=False)

        print(f"\npage errors: {errs if errs else 'none'}")
        b.close()


if __name__ == "__main__":
    main()
