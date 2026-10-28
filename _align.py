"""Check alignment of VLR replay coordinates against VLR's OWN minimap."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
ICON = BASE / "_cache" / "maps" / "vlr_ascent.png"
FB = BASE / "data" / "ascent_first_bloods.json"


def main() -> None:
    img = Image.open(ICON).convert("RGBA")
    arr = np.array(img)
    alpha = arr[..., 3]
    lum = arr[..., :3].mean(axis=2)
    h, w = alpha.shape
    print(f"image {w}x{h}  mode RGBA")
    print(f"alpha>10: {(alpha > 10).mean()*100:.1f}%   "
          f"lum>20: {(lum > 20).mean()*100:.1f}%")

    rows = json.loads(FB.read_text(encoding="utf-8"))
    pts = [(r["x"], r["y"]) for r in rows if r["x"] is not None]
    print(f"points: {len(pts)}")

    for label, mask in (
        ("alpha>10", alpha > 10),
        ("lum>20", lum > 20),
        ("lum>10", lum > 10),
        ("any (alpha>10 or lum>10)", (alpha > 10) | (lum > 10)),
    ):
        hit = 0
        for x, y in pts:
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h and mask[yi, xi]:
                hit += 1
        print(f"  {label:<26} on-map {hit:>3}/{len(pts)} "
              f"({hit/len(pts)*100:>5.1f}%)")

    # where do the misses cluster?
    miss = [(x, y) for x, y in pts
            if not (0 <= int(x) < w and 0 <= int(y) < h and lum[int(y), int(x)] > 10)]
    if miss:
        mx = [p[0] for p in miss]
        my = [p[1] for p in miss]
        print(f"\nmisses: {len(miss)}  x {min(mx):.0f}..{max(mx):.0f}  "
              f"y {min(my):.0f}..{max(my):.0f}")


if __name__ == "__main__":
    main()
