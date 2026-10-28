"""第三批：最贴近「密集数据 + 热图」的参考。"""
import sys, os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(r"D:\好玩的项目\valorant-analytics")
OUT = BASE / "figures" / "_ref4"
OUT.mkdir(parents=True, exist_ok=True)

# key, url, viewport_h, full_page
SITES = [
    ("plausible-tall", "https://plausible.io/plausible.io", 1500, False),
    ("vlr-stats",      "https://www.vlr.gg/stats", 1100, False),
    ("understat-match","https://understat.com/match/24603", 1100, False),
    ("owid",           "https://ourworldindata.org/", 900, False),
    ("pudding",        "https://pudding.cool/", 900, False),
    ("grafana-dash",   "https://play.grafana.org/d/000000012/grafana-play-home?orgId=1", 900, False),
    ("sofascore",      "https://www.sofascore.com/", 900, False),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    for key, url, vh, fp in SITES:
        ctx = browser.new_context(
            viewport={"width": 1440, "height": vh}, device_scale_factor=1,
            user_agent=UA, locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = ctx.new_page()
        rec = {"key": key, "url": url}
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=35000)
            rec["status"] = resp.status if resp else None
            page.wait_for_timeout(5000)
            for sel in ("button:has-text('Accept all')", "button:has-text('Accept')",
                        "button:has-text('Got it')", "button:has-text('Consent')"):
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=1200); page.wait_for_timeout(800); break
                except Exception:
                    pass
            f = OUT / f"{key}.png"
            page.screenshot(path=str(f), full_page=fp)
            rec["file"] = f.name
            rec["bytes"] = os.path.getsize(f)
            rec["title"] = page.title()[:80]
        except Exception as e:
            rec["err"] = f"{type(e).__name__}: {str(e)[:100]}"
        finally:
            ctx.close()
        results.append(rec)
        ok = "OK " if rec.get("bytes", 0) > 20000 else "FAIL"
        print(f"{ok} {key:16} {rec.get('status')} {rec.get('bytes',0)//1024:>4}KB  {rec.get('err','')}")
        time.sleep(0.6)
    browser.close()

(OUT / "index.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
