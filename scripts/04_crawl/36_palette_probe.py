"""抓真实数据站的配色与版式，作为设计参考的事实依据。

对每个站点：打开首页 → 取 body/主要区块的背景色、文字色、字体 → 截图。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"D:\好玩的项目\vct-first-blood-analytics\figures\_ref")
OUT.mkdir(parents=True, exist_ok=True)

SITES = [
    ("hltv", "https://www.hltv.org/"),
    ("vlr", "https://www.vlr.gg/"),
    ("leetify", "https://leetify.com/"),
    ("ribgg", "https://rib.gg/"),
    ("tracker", "https://tracker.gg/valorant"),
    ("escharts", "https://escharts.com/"),
    ("liquipedia", "https://liquipedia.net/valorant/Main_Page"),
]

PROBE = """() => {
  const g = el => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return { bg: s.backgroundColor, color: s.color, font: s.fontFamily.slice(0, 60) };
  };
  const body = g(document.body);
  const html = g(document.documentElement);
  const header = g(document.querySelector('header, nav, .header, #header'));
  const card = g(document.querySelector('article, .card, .box, .panel, table, .match, .item'));
  const link = g(document.querySelector('a'));
  return { body, html, header, card, link, title: document.title };
}"""


def main() -> None:
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="en-US")
        for key, url in SITES:
            page = ctx.new_page()
            rec = {"key": key, "url": url}
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                rec["status"] = resp.status if resp else None
                page.wait_for_timeout(2500)
                rec.update(page.evaluate(PROBE))
                page.screenshot(path=str(OUT / f"{key}.png"))
            except Exception as e:
                rec["err"] = f"{type(e).__name__}: {e}"
            rows.append(rec)
            print(f"{key:<11} {rec.get('status')}  body={rec.get('body')}",
                  flush=True)
            page.close()
        browser.close()

    (OUT / "probe.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print("done ->", OUT / "probe.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
