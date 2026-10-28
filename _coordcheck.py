"""Work out the transform between VLR minimap coordinates and the official map.

valorant-api documents, per map:
    world -> icon:  x_icon = (x_world * xMultiplier + xScalarToAdd) * iconW
                    y_icon = (y_world * yMultiplier + yScalarToAdd) * iconH

VLR's replay coordinates use its own 1024 grid. We test which of the plausible
transforms puts the callouts in the right place, by checking that the known
callout positions land inside drawn (non-transparent) pixels of the icon.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = Path(r"D:\好玩的项目\valorant-analytics")
CACHE = BASE / "_cache"
ICON = CACHE / "maps" / "ascent_minimap.png"

X_MULT = 7e-05
Y_MULT = -7e-05
X_ADD = 0.813895
Y_ADD = 0.573242


def world_to_icon(xw: float, yw: float, w: int, h: int) -> tuple[float, float]:
    xi = (xw * X_MULT + X_ADD) * w
    yi = (yw * Y_MULT + Y_ADD) * h
    return xi, yi


def main() -> None:
    img = Image.open(ICON).convert("RGBA")
    w, h = img.size
    alpha = np.array(img)[..., 3]
    print(f"icon {w}x{h}, opaque pixels: {(alpha > 10).sum()} "
          f"({(alpha > 10).mean()*100:.1f}%)")

    callouts = [
        # name, super region, world x, world y
        ("A Tree", "A", 3981, -5939),
        ("A Main", "A", 5322, -4710),
        ("A Site", "A", 6154, -6626),
        ("A Garden", "A", 3774, -7551),
        ("A Rafters", "A", 6130, -8210),
        ("B Main", "B", -1984, -5841),
        ("B Site", "B", -2344, -7549),
        ("B Lobby", "B", -1491, -1390),
        ("Mid Bottom", "Mid", 1122, -5952),
        ("Mid Catwalk", "Mid", 2316, -4127),
        ("Mid Courtyard", "Mid", 1223, -4587),
        ("Mid Market", "Mid", 1089, -7363),
        ("Mid Top", "Mid", 2754, -2130),
        ("Attacker Spawn", "AS", 60, 50),
        ("Defender Spawn", "DS", 1995, -9745),
    ]

    print("\nworld -> official icon coordinates:")
    pts = []
    for name, sup, xw, yw in callouts:
        xi, yi = world_to_icon(xw, yw, w, h)
        inside = 0 <= xi < w and 0 <= yi < h
        opaque = inside and alpha[int(yi), int(xi)] > 10
        pts.append((name, sup, xi, yi, opaque))
        flag = "OK " if opaque else "OFF"
        print(f"  {flag} {name:<16} ({sup:<3}) -> ({xi:7.1f}, {yi:7.1f})")

    good = sum(1 for p in pts if p[4])
    print(f"\ncallouts landing on opaque map pixels: {good}/{len(pts)}")

    out = CACHE / "ascent_callouts.json"
    out.write_text(json.dumps(
        [{"name": n, "region": s, "x": x, "y": y} for n, s, x, y, _ in pts],
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"callouts -> {out}")


if __name__ == "__main__":
    main()
