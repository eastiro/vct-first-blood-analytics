"""Test expand/collapse and click-to-pick."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8777/"
FIG = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics\figures")


def rows(pg, sel):
    return pg.query_selector_all(sel + " tr")


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1700, "height": 1100})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(900)

        print(f"agent chips: {len(pg.query_selector_all('#agentChips .chip'))}")
        print(f"weapon rows (collapsed): {len(rows(pg,'#weaponRows'))}")
        print(f"agent rows (collapsed):  {len(rows(pg,'#agentRows'))}")
        print(f"weapon more btn visible: "
              f"{pg.evaluate('!document.getElementById(\"weaponMore\").hidden')}")
        print(f"weapon more text: {pg.inner_text('#weaponMore')}")
        print(f"weapon note: {pg.inner_text('#weaponNote')}")

        # expand weapons
        pg.click("#weaponMore")
        pg.wait_for_timeout(500)
        print(f"\nafter expand -> weapon rows: {len(rows(pg,'#weaponRows'))}")
        print(f"  btn: {pg.inner_text('#weaponMore')}")
        print(f"  note: {pg.inner_text('#weaponNote')}")

        # collapse again
        pg.click("#weaponMore")
        pg.wait_for_timeout(400)
        print(f"after collapse -> weapon rows: {len(rows(pg,'#weaponRows'))}")

        # click an agent row to pin it
        pg.click("#agentRows tr.pickable:nth-child(1)")
        pg.wait_for_timeout(700)
        print(f"\nafter clicking top agent:")
        print(f"  F.agent = {pg.evaluate('F.agent')}")
        print(f"  title: {pg.inner_text('#agentPanelTitle')}")
        print(f"  note:  {pg.inner_text('#agentPanelNote')}")
        print(f"  rows:  {len(rows(pg,'#agentRows'))}")

        # agent chips should still show scope list
        print(f"  chips now: {len(pg.query_selector_all('#agentChips .chip'))}")

        # switch to London: chips should shrink
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(700)
        before = len(pg.query_selector_all('#agentChips .chip'))
        pg.evaluate("""() => {[...document.querySelectorAll('#eventChips .chip')]
            .find(x=>x.textContent.includes('伦敦')).click();}""")
        pg.wait_for_timeout(700)
        after = len(pg.query_selector_all('#agentChips .chip'))
        print(f"\nagent chips: all={before} -> London={after}")

        # select a team and check chips shrink further
        pg.select_option("#teamSelect", index=1)
        pg.wait_for_timeout(700)
        after2 = len(pg.query_selector_all('#agentChips .chip'))
        print(f"agent chips: London+team={after2}")
        pg.screenshot(path=str(FIG / "site_expand.png"), full_page=False)

        print(f"\npage errors: {errs if errs else 'none'}")
        b.close()


if __name__ == "__main__":
    main()
