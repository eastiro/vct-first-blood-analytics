"""抓一批真实数据产品的首屏截图，用于设计参考。

只截视口（不 full_page），因为要看的是"产品第一屏长什么样"。
"""
import sys, os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
OUT = BASE / "figures" / "_ref2"
OUT.mkdir(parents=True, exist_ok=True)

# key, url, 中文标签
SITES = [
    ("stripe",      "https://stripe.com/payments",                  "Stripe 支付"),
    ("stripe-dash", "https://stripe.com/billing",                   "Stripe 计费"),
    ("linear",      "https://linear.app/",                          "Linear"),
    ("vercel",      "https://vercel.com/",                           "Vercel"),
    ("posthog",     "https://posthog.com/",                          "PostHog"),
    ("hex",         "https://hex.tech/",                             "Hex"),
    ("observable",  "https://observablehq.com/",                     "Observable"),
    ("metabase",    "https://www.metabase.com/",                     "Metabase"),
    ("plausible",   "https://plausible.io/",                         "Plausible"),
    ("amplitude",   "https://amplitude.com/",                        "Amplitude"),
    ("mixpanel",    "https://mixpanel.com/",                         "Mixpanel"),
    ("datadog",     "https://www.datadoghq.com/",                    "Datadog"),
    ("grafana",     "https://grafana.com/",                          "Grafana"),
    ("retool",      "https://retool.com/",                           "Retool"),
    ("attio",       "https://attio.com/",                            "Attio"),
    ("mercury",     "https://mercury.com/",                          "Mercury"),
    ("ramp",        "https://ramp.com/",                             "Ramp"),
    ("count",       "https://count.co/",                             "Count"),
    ("evidence",    "https://evidence.dev/",                         "Evidence"),
    ("rill",        "https://rilldata.com/",                         "Rill"),
    ("sigma",       "https://www.sigmacomputing.com/",               "Sigma"),
    ("clickhouse",  "https://clickhouse.com/",                       "ClickHouse"),
    ("motherduck",  "https://motherduck.com/",                       "MotherDuck"),
    ("tinybird",    "https://www.tinybird.co/",                      "Tinybird"),
    ("thoughtspot", "https://www.thoughtspot.com/",                  "ThoughtSpot"),
    ("tableau",     "https://www.tableau.com/",                      "Tableau"),
    ("mode",        "https://mode.com/",                             "Mode"),
    ("looker",      "https://looker.com/",                           "Looker"),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=1,
        user_agent=UA,
        locale="en-US",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    for key, url, label in SITES:
        page = ctx.new_page()
        rec = {"key": key, "url": url, "label": label}
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            rec["status"] = resp.status if resp else None
            page.wait_for_timeout(3200)
            # 关掉常见的 cookie 横幅
            for sel in ("button:has-text('Accept')", "button:has-text('Accept all')",
                        "button:has-text('I agree')", "[id*=cookie] button"):
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(timeout=1200)
                        page.wait_for_timeout(600)
                        break
                except Exception:
                    pass
            page.mouse.wheel(0, 0)
            page.wait_for_timeout(400)
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
        ok = "OK " if rec.get("file") and rec.get("bytes", 0) > 20000 else "FAIL"
        print(f"{ok} {key:12} {rec.get('status')} {rec.get('bytes',0)//1024:>4}KB  {rec.get('err','')}")
        time.sleep(0.8)

    browser.close()

(OUT / "index.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
good = [r for r in results if r.get("bytes", 0) > 20000]
print(f"\n{len(good)}/{len(results)} captured")
