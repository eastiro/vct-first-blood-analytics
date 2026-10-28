"""Fit an ISOTROPIC transform from world units to the VLR 1024 grid.

A map projection cannot scale x and y differently, so we constrain:
    x_px = k * x_world + bx
    y_px = k * y_world + by
with one shared k. We grid-search k, bx, by so that the official callouts land on
drawn map pixels, then convert k to metres.

Reference point: valorant-api's own xMultiplier/yMultiplier have equal magnitude
(7e-05), i.e. 1024 * 7e-05 = 0.0717 px per world unit => 13.95 uu per px.
That is the scale we expect to recover.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
VLRMAP = BASE / "_cache" / "maps" / "vlr_ascent.png"

CALLOUTS = [
    ("A Tree", 3981, -5939), ("A Lobby", 4489, -3014), ("A Main", 5322, -4710),
    ("A Site", 6154, -6626), ("A Garden", 3774, -7551), ("A Rafters", 6130, -8210),
    ("A Wine", 7359, -4689), ("A Window", 4023, -8181),
    ("B Lobby", -1491, -1390), ("B Main", -1984, -5841), ("B Site", -2344, -7549),
    ("B Boat House", -4485, -7763),
    ("Mid Bottom", 1122, -5952), ("Mid Catwalk", 2316, -4127),
    ("Mid Courtyard", 1223, -4587), ("Mid Market", 1089, -7363),
    ("Mid Top", 2754, -2130), ("Mid Link", -632, -4280),
    ("Mid Pizza", 1802, -7262), ("Mid Cubby", 3387, -5130),
    ("Attacker Spawn", 60, 50), ("Defender Spawn", 1995, -9745),
]

UU_PER_M = 100.0          # 1 Unreal unit = 1 cm
OFFICIAL_K = 1024 * 7e-05  # px per world unit, from valorant-api multipliers


def main() -> None:
    img = Image.open(VLRMAP).convert("RGBA")
    arr = np.array(img)
    walkable = (arr[..., 3] > 10) | (arr[..., :3].mean(axis=2) > 10)
    h, w = walkable.shape

    xs_w = np.array([c[1] for c in CALLOUTS], float)
    ys_w = np.array([c[2] for c in CALLOUTS], float)

    best = None
    # search k around the official value
    for k in np.arange(0.055, 0.095, 0.0005):
        # offsets anchored so the callout bbox centres on the map
        for bx in np.arange(380, 520, 2.0):
            for by in np.arange(420, 560, 2.0):
                hit = 0
                for xw, yw in zip(xs_w, ys_w):
                    xi = k * xw + bx
                    yi = k * yw + by
                    if 0 <= xi < w and 0 <= yi < h and walkable[int(yi), int(xi)]:
                        hit += 1
                if best is None or hit > best[0]:
                    best = (hit, k, bx, by)

    hit, k, bx, by = best
    print(f"best isotropic fit: {hit}/{len(CALLOUTS)}")
    print(f"  k  = {k:.5f} px per world unit")
    print(f"  bx = {bx:.1f}   by = {by:.1f}")
    print(f"  (official reference k = {OFFICIAL_K:.5f})")

    uu_per_px = 1.0 / k
    m_per_px = uu_per_px / UU_PER_M
    print(f"\n  {uu_per_px:.2f} world units per px")
    print(f"  {m_per_px:.4f} m per px")

    print("\ncallout placement:")
    for name, xw, yw in CALLOUTS:
        xi, yi = k * xw + bx, k * yw + by
        ok = 0 <= xi < w and 0 <= yi < h and walkable[int(yi), int(xi)]
        print(f"  {'OK ' if ok else 'OFF'} {name:<16} ({xi:6.0f}, {yi:6.0f})")

    out = BASE / "_cache" / "vlr_transform.json"
    out.write_text(json.dumps({
        "k": float(k), "b_x": float(bx), "b_y": float(by),
        "uu_per_px": float(uu_per_px),
        "metres_per_px": float(m_per_px),
        "hits": hit, "total": len(CALLOUTS),
        "official_k": OFFICIAL_K,
    }, indent=2), encoding="utf-8")
    print(f"\n-> {out}")

    # what the median first blood looks like in metres
    fb = json.loads((BASE / "data" / "ascent_first_bloods.json").read_text(encoding="utf-8"))
    ds = sorted(r["dist"] for r in fb if r["dist"] is not None)
    med = ds[len(ds) // 2]
    print(f"\nmedian first-blood distance {med:.0f} px -> {med * m_per_px:.1f} m")
    print(f"p25 {ds[len(ds)//4]:.0f} px -> {ds[len(ds)//4]*m_per_px:.1f} m")
    print(f"p75 {ds[len(ds)*3//4]:.0f} px -> {ds[len(ds)*3//4]*m_per_px:.1f} m")


if __name__ == "__main__":
    main()
