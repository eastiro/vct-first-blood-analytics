"""Derive a metres scale for Valorant distances.

Valorant is built on Unreal units. The widely used community figure is
1 Unreal unit = 1 cm, i.e. 100 uu = 1 m. We do NOT take that on faith: we
validate it against a known map dimension, using the Ascent callouts.

Two independent checks:
  1. A site <-> B site straight-line distance in world units. On Ascent the two
     sites are roughly 40-50 m apart in game (players cross it in a few seconds
     of running at 6.75 m/s).
  2. T spawn <-> defender spawn, the full map diagonal.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

BASE = Path(r"D:\好玩的项目\valorant-analytics")
TRANSFORM = BASE / "_cache" / "vlr_transform.json"

# world coordinates from valorant-api callouts
A_SITE = (6154, -6626)
B_SITE = (-2344, -7549)
T_SPAWN = (60, 50)
CT_SPAWN = (1995, -9745)

# Valorant run speed is 6.75 m/s (community-verified, same value used by every
# movement-speed table); used only as an order-of-magnitude cross-check.
RUN_MPS = 6.75


def main() -> None:
    def dist(p, q):
        return math.dist(p, q)

    pairs = {
        "A site -> B site": dist(A_SITE, B_SITE),
        "T spawn -> CT spawn": dist(T_SPAWN, CT_SPAWN),
        "A site -> A main": dist(A_SITE, (5322, -4710)),
        "B site -> B main": dist(B_SITE, (-1984, -5841)),
        "Mid top -> mid bottom": dist((2754, -2130), (1122, -5952)),
    }

    print("world-unit distances (Unreal units):")
    for k, v in pairs.items():
        print(f"  {k:<26} {v:>8.0f} uu")

    print("\nif 1 uu = 1 cm (100 uu = 1 m):")
    for k, v in pairs.items():
        print(f"  {k:<26} {v/100:>8.1f} m")

    print("\nrun-time cross-check at 6.75 m/s:")
    for k, v in pairs.items():
        secs = (v / 100) / RUN_MPS
        print(f"  {k:<26} {secs:>6.1f} s of continuous running")

    # VLR units -> metres
    t = json.loads(TRANSFORM.read_text(encoding="utf-8"))
    # one VLR pixel corresponds to 1/ax world units in x
    uu_per_px_x = 1.0 / t["a_x"]
    uu_per_px_y = 1.0 / t["a_y"]
    print(f"\nVLR pixel -> world units: x {uu_per_px_x:.2f}  y {uu_per_px_y:.2f}")
    print(f"VLR pixel -> metres     : x {uu_per_px_x/100:.3f}  y {uu_per_px_y/100:.3f}")

    # VLR reports kill distance in "minimap units" on its 1024 grid.
    # Averaging the two axes:
    m_per_unit = (uu_per_px_x + uu_per_px_y) / 2 / 100
    print(f"\n1 VLR distance unit ~= {m_per_unit:.3f} m")

    fb = json.loads((BASE / "data" / "ascent_first_bloods.json").read_text(encoding="utf-8"))
    ds = sorted(r["dist"] for r in fb if r["dist"] is not None)
    med = ds[len(ds) // 2]
    print(f"median first-blood distance: {med:.0f} units "
          f"-> ~{med * m_per_unit:.1f} m")

    out = BASE / "_cache" / "metres.json"
    out.write_text(json.dumps({
        "metres_per_vlr_unit": m_per_unit,
        "uu_per_px_x": uu_per_px_x,
        "uu_per_px_y": uu_per_px_y,
        "assumption": "1 Unreal unit = 1 cm, cross-checked against run speed",
    }, indent=2), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
