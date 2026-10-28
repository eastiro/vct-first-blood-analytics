"""Extract the per-player stat table from a VLR overview page.

The table is div-based. Each player block contains: name link, agent icon,
then numeric cells (ACS, K/D/A, +/-, KAST, ADR, HS%, FK, FD).
Parsing is done by walking the documented class names VLR uses.
"""
from __future__ import annotations

import re
from pathlib import Path

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache\vlr_overview.html")


def text_of(f: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", f)).strip()


def main() -> None:
    html = CACHE.read_text(encoding="utf-8")

    # Each stats row uses class "vm-stats-game-row" inside "vm-stats-game".
    rows = re.split(r'<div class="vm-stats-game-row"', html)
    print(f"rows split: {len(rows) - 1}")

    for chunk in rows[1:12]:
        name = re.search(r'href="/player/\d+/([a-z0-9\-_]+)"', chunk)
        agents = re.findall(r'/img/vlr/game/agents/([a-z0-9_]+)\.png', chunk)
        # numbers in the row
        nums = re.findall(r">\s*([0-9][0-9,./%]*)\s*<", chunk)
        print(f"\n  player={name.group(1) if name else '?':<14} "
              f"agents={agents[:2]}")
        print(f"    nums: {nums[:14]}")

    # Also: find the header order so we know what each number means
    print("\n" + "=" * 72)
    hdr = re.search(r"(<div class=\"vm-stats-game-header\".*?)</div>\s*</div>",
                    html, re.S)
    print("header block found:", bool(hdr))


if __name__ == "__main__":
    main()
