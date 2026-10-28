"""Validate the rnd-sq round-winner strip against the known map score.

Mapping hypothesis: for round r (1-based), the two strip cells are at
indices 2*(r-1) and 2*(r-1)+1; the cell carrying `mod-win` names the
winning SIDE via `mod-t` (attack) / `mod-ct` (defense), and the round's
band gives each side's team. Count wins per team and compare to the
score recorded in the manifest.
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

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MANIFEST = BASE / "_cache" / "manifest.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def round_winner(game, round_div) -> tuple[str, str]:
    """Return (winning_side, winning_team) for one round div."""
    rn = int(round_div.attributes.get("data-round") or 0)
    sides: dict[str, str] = {}
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
        if "mod-win" not in cls:
            continue
        if "mod-ct" in cls:
            win_side = "Defense"
        elif "mod-t" in cls:
            win_side = "Attack"
    return win_side, sides.get(win_side, "")


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    random.seed(7)
    sample = random.sample(entries, 14)

    ok = bad = 0
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=45,
                      follow_redirects=True) as c:
        for e in sample:
            url = f"https://www.vlr.gg/{e['series_id']}?game={e['game_id']}&tab=logs"
            try:
                html = c.get(url).text
            except Exception as exc:
                print(f"  fetch ERR {type(exc).__name__}")
                time.sleep(1.2)
                continue
            dom = LexborHTMLParser(html)
            game = dom.css_first("div.vm-stats-game.mod-active")
            if game is None:
                print("  no game div")
                time.sleep(1.2)
                continue

            counts: dict[str, int] = {}
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
            mark = "OK " if good else "MISMATCH"
            print(f"  {mark:<9} {e['map']:<9} {t1[:16]:<16} {s1}-{s2}  "
                  f"parsed {got1}-{got2}  (rounds={len(game.css('div.lg-round'))})")
            if not good:
                print(f"      full counts: {counts}")
            time.sleep(1.2)

    print(f"\nmatched {ok}/{ok+bad}")


if __name__ == "__main__":
    main()
