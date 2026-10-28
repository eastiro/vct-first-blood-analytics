"""Parse the VLR overview stat table (ovw-table) into rows.

Layout per row (mod-head defines the order):
    player | agent | R | ACS | K/D/A | +/- | KAST | ADR | HS% | FK | FD | +/-

The table repeats once per map plus once for "All maps", separated by header
blocks carrying the map name.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache\vlr_overview.html")


def clean(f: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", f)).strip()


def parse_rows(html: str) -> list[dict]:
    """Return one dict per player row, with the map section it belongs to."""
    out: list[dict] = []

    # split into map sections by the game header
    sections = re.split(r'<div class="vm-stats-game-header"', html)
    for section in sections[1:]:
        map_m = re.search(r'class="map"[^>]*>\s*([A-Za-z]+)\s*<', section)
        map_name = map_m.group(1) if map_m else "?"

        for row in re.findall(r'<div class="ovw-row">(.*?)(?=<div class="ovw-row"|</div>\s*</div>\s*</div>)',
                              section, re.S):
            if "ovw-cell" not in row:
                continue
            player = re.search(r'href="/player/\d+/([a-z0-9\-_]+)"', row)
            agents = re.findall(r'/img/vlr/game/agents/([a-z0-9_]+)\.png', row)
            cells = re.findall(r'<div class="ovw-cell[^"]*"[^>]*>(.*?)</div>',
                               row, re.S)
            cells = [clean(c) for c in cells]
            cells = [c for c in cells if c != ""]
            if not player:
                continue
            out.append({
                "map": map_name,
                "player": player.group(1),
                "agents": agents,
                "cells": cells,
            })
    return out


def main() -> None:
    html = CACHE.read_text(encoding="utf-8")
    rows = parse_rows(html)
    print(f"parsed rows: {len(rows)}\n")
    for r in rows[:14]:
        print(f"{r['map']:<8} {r['player']:<12} {r['agents']}  {r['cells']}")


if __name__ == "__main__":
    main()
