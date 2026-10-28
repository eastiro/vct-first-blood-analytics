"""Test whether VLR replay coordinates and the official icon share a frame.

Method: take the VLR first-blood points and check how many land on opaque
(non-transparent) pixels of the icon, as-is. If the two grids agree, most points
should already be inside the drawn map.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
ICON = BASE / "_cache" / "maps" / "ascent_minimap.png"
FB = BASE / "data" / "ascent_first_bloods.json"


def report(alpha: np.ndarray, pts, label: str, flip_y=False, flip_x=False):
    h, w = alpha.shape
    inside = on_map = 0
    for x, y in pts:
        if flip_x:
            x = w - 1 - x
        if flip_y:
            y = h - 1 - y
        if 0 <= x < w and 0 <= y < h:
            inside += 1
            if alpha[int(y), int(x)] > 10:
                on_map += 1
    print(f"  {label:<28} inside={inside:>3}/{len(pts)}  on-map={on_map:>3} "
          f"({on_map/len(pts)*100:>4.0f}%)")


def main() -> None:
    img = Image.open(ICON).convert("RGBA")
    alpha = np.array(img)[..., 3]
    rows = json.loads(FB.read_text(encoding="utf-8"))
    pts = [(r["x"], r["y"]) for r in rows if r["x"] is not None]
    print(f"first-blood points: {len(pts)}")

    report(alpha, pts, "as-is")
    report(alpha, pts, "flip y", flip_y=True)
    report(alpha, pts, "flip x", flip_x=True)
    report(alpha, pts, "flip both", flip_x=True, flip_y=True)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print(f"\nVLR coord range: x {min(xs):.0f}..{max(xs):.0f}  "
          f"y {min(ys):.0f}..{max(ys):.0f}")

    ys_, xs_ = np.where(alpha > 10)
    print(f"icon opaque range: x {xs_.min()}..{xs_.max()}  y {ys_.min()}..{ys_.max()}")


if __name__ == "__main__":
    main()
