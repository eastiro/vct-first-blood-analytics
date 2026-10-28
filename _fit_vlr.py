"""Fit world coordinates onto the VLR 1024 grid, then derive a metres scale.

We know 18 official callouts in world (Unreal) units. We fit the affine map
world -> VLR-1024 so that every callout lands on drawn (opaque) map pixels.
That both validates the frame and gives us units-per-pixel.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
VLRMAP = BASE / "_cache" / "maps" / "vlr_ascent.png"

CALLOUTS = [
    ("A Tree", "A", 3981, -5939), ("A Lobby", "A", 4489, -3014),
    ("A Main", "A", 5322, -4710), ("A Site", "A", 6154, -6626),
    ("A Garden", "A", 3774, -7551), ("A Rafters", "A", 6130, -8210),
    ("A Wine", "A", 7359, -4689), ("A Window", "A", 4023, -8181),
    ("B Lobby", "B", -1491, -1390), ("B Main", "B", -1984, -5841),
    ("B Site", "B", -2344, -7549), ("B Boat House", "B", -4485, -7763),
    ("Mid Bottom", "Mid", 1122, -5952), ("Mid Catwalk", "Mid", 2316, -4127),
    ("Mid Courtyard", "Mid", 1223, -4587), ("Mid Market", "Mid", 1089, -7363),
    ("Mid Top", "Mid", 2754, -2130), ("Mid Link", "Mid", -632, -4280),
    ("Mid Pizza", "Mid", 1802, -7262), ("Mid Cubby", "Mid", 3387, -5130),
    ("Attacker Spawn", "AS", 60, 50), ("Defender Spawn", "DS", 1995, -9745),
]


def main() -> None:
    img = Image.open(VLRMAP).convert("RGBA")
    arr = np.array(img)
    alpha = arr[..., 3]
    lum = arr[..., :3].mean(axis=2)
    walkable = (alpha > 10) | (lum > 10)
    h, w = walkable.shape

    xs_w = np.array([c[2] for c in CALLOUTS], float)
    ys_w = np.array([c[3] for c in CALLOUTS], float)

    ys, xs = np.where(walkable)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"VLR map walkable bbox: x {x0}..{x1}  y {y0}..{y1}")

    best = None
    for pad_x in range(0, 120, 4):
        for pad_y in range(0, 120, 4):
            ax = (x1 - x0 - 2 * pad_x) / (xs_w.max() - xs_w.min())
            bx = (x0 + pad_x) - xs_w.min() * ax
            ay = (y1 - y0 - 2 * pad_y) / (ys_w.max() - ys_w.min())
            by = (y0 + pad_y) - ys_w.min() * ay
            hit = 0
            for _, _, xw, yw in CALLOUTS:
                xi, yi = ax * xw + bx, ay * yw + by
                if 0 <= xi < w and 0 <= yi < h and walkable[int(yi), int(xi)]:
                    hit += 1
            if best is None or hit > best[0]:
                best = (hit, ax, bx, ay, by, pad_x, pad_y)

    hit, ax, bx, ay, by, px, py = best
    print(f"best fit: {hit}/{len(CALLOUTS)}  pad=({px},{py})")
    print(f"  x_vlr = {ax:.6f} * x_world + {bx:.2f}")
    print(f"  y_vlr = {ay:.6f} * y_world + {by:.2f}")

    print("\ncallout placement:")
    for name, sup, xw, yw in CALLOUTS:
        xi, yi = ax * xw + bx, ay * yw + by
        ok = 0 <= xi < w and 0 <= yi < h and walkable[int(yi), int(xi)]
        print(f"  {'OK ' if ok else 'OFF'} {name:<16} ({sup:<3}) "
              f"-> ({xi:6.0f}, {yi:6.0f})")

    # scale: world units per VLR pixel
    upx = 1.0 / ax
    upy = 1.0 / ay
    print(f"\nworld units per pixel: x {upx:.2f}  y {upy:.2f}")

    out = BASE / "_cache" / "vlr_transform.json"
    out.write_text(json.dumps({
        "a_x": ax, "b_x": bx, "a_y": ay, "b_y": by,
        "world_units_per_px_x": upx, "world_units_per_px_y": upy,
        "hits": hit, "total": len(CALLOUTS),
    }, indent=2), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
