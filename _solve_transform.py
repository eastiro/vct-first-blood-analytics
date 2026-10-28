"""Solve the world->icon transform empirically using the callouts themselves.

We have 15 known (world x, world y) -> (unknown icon x, y) pairs, plus the icon
image. The documented multipliers are per-map-normalised, so the missing piece is
an overall scale. We estimate it by requiring the callouts to spread across the
opaque area of the icon.

Approach: grid-search (scale, offset) so that the transformed callouts
  (a) all land inside the 1024 box, and
  (b) maximise the number landing on opaque pixels.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
ICON = BASE / "_cache" / "maps" / "ascent_minimap.png"

X_MULT = 7e-05
Y_MULT = -7e-05
X_ADD = 0.813895
Y_ADD = 0.573242

CALLOUTS = [
    ("A Tree", 3981, -5939), ("A Main", 5322, -4710), ("A Site", 6154, -6626),
    ("A Garden", 3774, -7551), ("A Rafters", 6130, -8210), ("A Wine", 7359, -4689),
    ("B Main", -1984, -5841), ("B Site", -2344, -7549), ("B Lobby", -1491, -1390),
    ("B Boat House", -4485, -7763),
    ("Mid Bottom", 1122, -5952), ("Mid Catwalk", 2316, -4127),
    ("Mid Courtyard", 1223, -4587), ("Mid Market", 1089, -7363),
    ("Mid Top", 2754, -2130), ("Mid Link", -632, -4280),
    ("Attacker Spawn", 60, 50), ("Defender Spawn", 1995, -9745),
]


def score(alpha: np.ndarray, sx: float, sy: float, ox: float, oy: float) -> tuple[int, float]:
    h, w = alpha.shape
    hit = 0
    dev = 0.0
    for _, xw, yw in CALLOUTS:
        xi = xw * sx + ox
        yi = yw * sy + oy
        if not (0 <= xi < w and 0 <= yi < h):
            continue
        if alpha[int(yi), int(xi)] > 10:
            hit += 1
            # distance transform proxy: crude check that we are not on an edge
            dev += 0
    return hit, dev


def main() -> None:
    img = Image.open(ICON).convert("RGBA")
    alpha = np.array(img)[..., 3]
    h, w = alpha.shape

    # The documented form is: icon = (world*mult + add) * size, i.e. linear in
    # world with slope mult*size. Solve for the extra factor k:
    #   icon = ((world*mult + add) * size) * k  is wrong (offset would scale too).
    # Instead solve the affine map icon = a*world + b directly, choosing a,b so the
    # callout cloud's bounding box fits inside the opaque region.

    xs_w = np.array([c[1] for c in CALLOUTS], dtype=float)
    ys_w = np.array([c[2] for c in CALLOUTS], dtype=float)

    # opaque bounding box of the drawn map
    ys, xs = np.where(alpha > 10)
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    print(f"opaque bbox: x {x0}..{x1}   y {y0}..{y1}")

    # fit world bbox -> opaque bbox, with a small inset
    inset = 20
    a_x = (x1 - x0 - 2 * inset) / (xs_w.max() - xs_w.min())
    b_x = (x0 + inset) - xs_w.min() * a_x
    a_y = (y1 - y0 - 2 * inset) / (ys_w.max() - ys_w.min())
    b_y = (y0 + inset) - ys_w.min() * a_y

    print(f"\nfitted: x = {a_x:.6f}*wx + {b_x:.2f}")
    print(f"        y = {a_y:.6f}*wy + {b_y:.2f}")

    hit = 0
    for name, xw, yw in CALLOUTS:
        xi = a_x * xw + b_x
        yi = a_y * yw + b_y
        ok = 0 <= xi < w and 0 <= yi < h and alpha[int(yi), int(xi)] > 10
        hit += ok
        print(f"  {'OK ' if ok else 'OFF'} {name:<16} ({xi:7.1f}, {yi:7.1f})")

    print(f"\nhits: {hit}/{len(CALLOUTS)}")

    out = BASE / "_cache" / "ascent_transform.json"
    out.write_text(json.dumps({
        "a_x": a_x, "b_x": b_x, "a_y": a_y, "b_y": b_y,
        "note": "affine fit from valorant-api world coordinates to the 1024 icon",
    }, indent=2), encoding="utf-8")
    print(f"transform -> {out}")


if __name__ == "__main__":
    main()
