"""Locate the plant-site markers on VLR's Ascent map.

On VLR's minimaps the bomb sites are drawn as a small diamond/square outline,
and spawns as circles. Rather than guess from crops, we find the distinctive
bright outline clusters and report their centres, then crop each candidate for a
human to confirm.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
OUT = BASE / "figures"


def main() -> None:
    img = Image.open(MAP).convert("RGBA")
    arr = np.array(img)
    alpha = arr[..., 3]
    rgb = arr[..., :3].astype(int)

    # bright, low-saturation pixels = the drawn outlines/markers
    lum = rgb.mean(axis=2)
    bright = (lum > 150) & (alpha > 10)
    print(f"bright pixels: {bright.sum()}")

    # connected components via simple flood fill (no scipy available)
    seen = np.zeros_like(bright, dtype=bool)
    h, w = bright.shape
    comps = []
    for y in range(h):
        for x in range(w):
            if not bright[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            pts = []
            while stack:
                cy, cx = stack.pop()
                pts.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and bright[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if len(pts) >= 12:
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                comps.append({
                    "n": len(pts),
                    "cx": sum(xs) / len(xs),
                    "cy": sum(ys) / len(ys),
                    "w": max(xs) - min(xs) + 1,
                    "h": max(ys) - min(ys) + 1,
                })

    comps.sort(key=lambda c: -c["n"])
    print(f"components >=12px: {len(comps)}")
    print("\ntop 25 by size (cx, cy, w x h):")
    for c in comps[:25]:
        print(f"  ({c['cx']:6.1f}, {c['cy']:6.1f})  {c['w']:>3} x {c['h']:<3}  n={c['n']}")

    bg = Image.new("RGBA", img.size, (14, 19, 27, 255))
    bg.alpha_composite(img)
    rgbimg = bg.convert("RGB")

    # crop around the 8 biggest compact components
    compact = [c for c in comps if 6 <= c["w"] <= 60 and 6 <= c["h"] <= 60][:8]
    for i, c in enumerate(compact):
        x0 = max(0, int(c["cx"]) - 60)
        y0 = max(0, int(c["cy"]) - 60)
        crop = rgbimg.crop((x0, y0, x0 + 120, y0 + 120))
        crop = crop.resize((360, 360), Image.LANCZOS)
        p = OUT / f"marker_{i}_{int(c['cx'])}_{int(c['cy'])}.png"
        crop.save(p)
        print(f"  crop -> {p.name}  ({c['w']}x{c['h']})")


if __name__ == "__main__":
    main()
