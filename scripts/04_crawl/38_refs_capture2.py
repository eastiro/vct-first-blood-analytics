"""第二批：真实在跑的数据界面（不是营销首页）。"""
import sys, os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(r"D:\好玩的项目\valorant-analytics")
OUT = BASE / "figures" / "_ref3"
OUT.mkdir(parents=True, exist_ok=True)

SITES = [
    ("plausible-pub", "https://plausible.io/plausible.io",                    "Plausible 公开看板"),
    ("grafana-play",  "https://play.grafana.org/",                            "Grafana Play"),
    ("understat",     "https://understat.com/league/EPL",                     "Understat 英超"),
    ("fbref",         "https://fbref.com/en/comps/9/Premier-League-Stats",    "FBref 英超"),
    ("fangraphs",     "https://www.fangraphs.com/leaders/major-league",       "FanGraphs 榜单"),
    ("tableau-pub",   "https://public.tableau.com/app/discover",              "Tableau Public"),
    ("shadcn-dash",   "https://ui.shadcn.com/examples/dashboard",             "shadcn dashboard"),
    ("tremor",        "https://tremor.so/",                                   "Tremor"),
    ("d3-gallery",    "https://observablehq.com/@d3/gallery",                 "D3 图库"),
    ("ddog-dash",     "https://www.datadoghq.com/product/dashboards/",        "Datadog 看板"),
    ("metabase-hp",   "https://www.metabase.com/",                            "Metabase"),
    ("tabler",        "https://tabler.io/preview",                            "Tabler 预览"),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900}, device_scale_factor=1,
        user_agent=UA, locale="en-US",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    for key, url, label in SITES:
        page = ctx.new_page()
        rec = {"key": key, "url": url, "label": label}
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            rec["status"] = resp.status if resp else None
            page.wait_for_timeout(4200)
            for sel in ("button:has-text('Accept all')", "button:has-text('Accept')",
                        "button:has-text('I agree')", "button:has-text('Got it')"):
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=1200); page.wait_for_timeout(700); break
                except Exception:
                    pass
            f = OUT / f"{key}.png"
            page.screenshot(path=str(f))
            rec["file"] = f.name
            rec["bytes"] = os.path.getsize(f)
            rec["title"] = page.title()[:80]
        except Exception as e:
            rec["err"] = f"{type(e).__name__}: {str(e)[:90]}"
        finally:
            page.close()
        results.append(rec)
        ok = "OK " if rec.get("bytes", 0) > 20000 else "FAIL"
        print(f"{ok} {key:14} {rec.get('status')} {rec.get('bytes',0)//1024:>4}KB  {rec.get('err','')}")
        time.sleep(0.6)
    browser.close()

(OUT / "index.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n{sum(1 for r in results if r.get('bytes',0)>20000)}/{len(results)} captured")
