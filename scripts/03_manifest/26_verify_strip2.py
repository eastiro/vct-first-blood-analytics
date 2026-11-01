"""Re-verify the strip using the explicit game-id selector (not .mod-active).

Also prints which game ids the page advertises so a missing game is obvious.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from selectolax.lexbor import LexborHTMLParser  # noqa: E402

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
MANIFEST = BASE / "_cache" / "manifest.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def round_winner(game, round_div):
    rn = int(round_div.attributes.get("data-round") or 0)
    sides = {}
    for el in round_div.css("span.lg-band-team"):
        cls = el.attributes.get("class") or ""
        name_el = el.css_first("span.lg-band-name")
        nm = (name_el.attributes.get("title") or name_el.text(strip=True)) if name_el else ""
        if "mod-atk" in cls:
            sides["Attack"] = nm
        elif "mod-def" in cls:
            sides["Defense"] = nm
    squares = game.css("div.rnd-sq")
    a = 2 * (rn - 1)
    win_side = ""
    for idx in (a, a + 1):
        if idx >= len(squares):
            continue
        cls = squares[idx].attributes.get("class") or ""
        if "mod-win" in cls:
            win_side = "Defense" if "mod-ct" in cls else "Attack" if "mod-t" in cls else ""
    return win_side, sides.get(win_side, "")


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    random.seed(7)
    sample = random.sample(entries, 16)

    ok = bad = 0
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=45,
                      follow_redirects=True) as c:
        for e in sample:
            gid = e["game_id"]
            url = f"https://www.vlr.gg/{e['series_id']}?game={gid}&tab=logs"
            try:
                html = c.get(url).text
            except Exception as exc:
                print(f"  fetch ERR {type(exc).__name__}")
                time.sleep(1.2)
                continue
            dom = LexborHTMLParser(html)
            game = dom.css_first(f'div.vm-stats-game[data-game-id="{gid}"]')
            gids = [d.attributes.get("data-game-id")
                    for d in dom.css("div.vm-stats-game")]
            if game is None:
                print(f"  NO GAME DIV for gid={gid}; page has {gids}")
                time.sleep(1.2)
                continue

            counts = {}
            for rd in game.css("div.lg-round"):
                _, team = round_winner(game, rd)
                if team:
                    counts[team] = counts.get(team, 0) + 1

            t1, t2 = (e["teams"].split(" vs ") + ["", ""])[:2]
            s1, s2 = e["score1"], e["score2"]
            got1, got2 = counts.get(t1, 0), counts.get(t2, 0)
            good = (got1, got2) == (s1, s2)
            ok += good
            bad += (not good)
            print(f"  {'OK ' if good else 'MISMATCH':<9} {e['map']:<9} "
                  f"{t1[:16]:<16} {s1}-{s2}  parsed {got1}-{got2}  "
                  f"(rounds={len(game.css('div.lg-round'))})")
            if not good:
                print(f"      counts={counts} page gids={gids}")
            time.sleep(1.2)

    print(f"\nmatched {ok}/{ok+bad}")


if __name__ == "__main__":
    main()
