"""Final verification pass over every deliverable."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label} {detail}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


print("=== data integrity ===")
rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))
check("round rows > 13000", len(rows) > 13000, f"({len(rows)})")
check("every round has kills", all(r.get("kills") for r in rows))
check("every round has winner_team", all(r.get("winner_team") for r in rows))
check("every kill has a killer", all(k.get("killer") for r in rows for k in r["kills"]))
check("every round has an attacking team", all(r.get("attacking") for r in rows))

geo = [r for r in rows if r.get("geometry")]
feed = [r for r in rows if not r.get("geometry")]
check("geometry rounds have loadouts", all(r.get("loadouts") for r in geo),
      f"({len(geo)} rounds)")
check("feed rounds have none", all(not r.get("loadouts") for r in feed),
      f"({len(feed)} rounds)")

# Coords outside the 0..1024 grid exist in the raw feed: environmental
# "Fall" deaths (off the Abyss edge) plus 2 kills whose victim stood just
# past the minimap crop. None of them may reach a spatial output.
bad = 0
bad_fall = 0
for r in geo:
    for k in r["kills"]:
        x, y = k.get("pos_x"), k.get("pos_y")
        if x is None or y is None:
            continue
        if not (0 <= x <= 1024 and 0 <= y <= 1024):
            if (k.get("cause") or "").strip().lower() == "fall":
                bad_fall += 1
            else:
                bad += 1
check("off-grid raw coords are rare and explained", (bad + bad_fall) <= 25,
      f"({bad} edge kills + {bad_fall} Fall deaths)")

# the site payload must contain only in-grid points
oob = 0
for m in json.loads((BASE / "data" / "site.json").read_text(encoding="utf-8"))["maps"]:
    for p in m["heat"]:
        if not (0 <= p[0] <= 1024 and 0 <= p[1] <= 1024):
            oob += 1
check("site heat points all in grid", oob == 0, f"({oob} out of range)")

print("\n=== names are official ===")
zh = json.loads((BASE / "_cache" / "zh_names.json").read_text(encoding="utf-8"))
for en, expected in [
    ("headhunter", "金牌猎头"), ("tour de force", "孤高火力"),
    ("blade storm", "飓刃"), ("hunter's fury", "狂猎之怒"),
    ("phantom", "幻影"), ("vandal", "狂徒"), ("operator", "冥驹"),
    ("chamber", "尚勃勒"), ("neon", "霓虹"), ("jett", "捷风"),
]:
    got = zh["abilities"].get(en) or zh["weapons"].get(en) or zh["agents"].get(en)
    check(f"{en}", got == expected, f"-> {got}")

check("ascent -> 亚海悬城", zh.get("maps", {}).get("ascent") == "亚海悬城",
      f"-> {zh.get('maps', {}).get('ascent')}")

print("\n=== site payload ===")
site = json.loads((BASE / "data" / "site.json").read_text(encoding="utf-8"))
check("5 events", len(site["events"]) == 5)
check("10 maps", len(site["maps"]) == 10)
check("heat points > 10000", sum(len(m["heat"]) for m in site["maps"]) > 10000)
check("payload under 1 MB", (BASE / "data" / "site.json").stat().st_size < 1_000_000,
      f"({(BASE / 'data'/'site.json').stat().st_size/1e6:.2f} MB)")
missing_img = [m["image"] for m in site["maps"]
               if not (BASE / "site" / m["image"]).exists()]
check("every map image exists", not missing_img, str(missing_img))
check("meta fb_to_win in 70-72", 70 <= site["meta"]["fb_to_win_pct"] <= 72,
      f"({site['meta']['fb_to_win_pct']}%)")

print("\n=== figures ===")
figs = sorted((BASE / "figures").glob("fb_*.png"))
check("at least 13 fb figures", len(figs) >= 13, f"({len(figs)})")
check("site screenshot exists", (BASE / "figures" / "site_shot.png").exists())

print(f"\n{'='*50}\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
