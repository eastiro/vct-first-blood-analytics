"""Draw the Ascent first-blood map: heat + agent breakdown.

Coordinates are already in VLR's 1024x1024 minimap grid, so they project onto the
map image with a simple linear scale.
"""
from __future__ import annotations

import json
import urllib.request
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
FB = BASE / "data" / "ascent_first_bloods.json"
MAPIMG = BASE / "_cache" / "maps" / "ascent_minimap.png"
OUTDIR = BASE / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

BG = "#0e131b"
FG = "#e1e7ef"
MUTED = "#78869a"
ACCENT = "#FF4655"
BLUE = "#4DA3FF"


def ensure_map() -> None:
    if MAPIMG.exists():
        return
    MAPIMG.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        "https://media.valorant-api.com/maps/"
        "7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/displayicon.png",
        headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        MAPIMG.write_bytes(r.read())


def gaussian_heat(xs, ys, size=1024, sigma=34):
    """Cheap 2-D density on the 1024 grid via accumulation + blur."""
    grid = np.zeros((size // 4, size // 4), dtype=float)
    for x, y in zip(xs, ys):
        gx, gy = int(x / 4), int(y / 4)
        if 0 <= gx < grid.shape[1] and 0 <= gy < grid.shape[0]:
            grid[gy, gx] += 1.0
    s = int(sigma / 4) * 2 + 1
    ax = np.arange(-(s // 2), s // 2 + 1)
    k = np.exp(-(ax ** 2) / (2 * (sigma / 4) ** 2))
    k /= k.sum()
    grid = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, grid)
    grid = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, grid)
    return grid


def main() -> None:
    ensure_map()
    rows = json.loads(FB.read_text(encoding="utf-8"))
    print(f"first bloods: {len(rows)}")

    xs = [r["x"] for r in rows if r["x"] is not None]
    ys = [r["y"] for r in rows if r["y"] is not None]

    fig, axes = plt.subplots(1, 2, figsize=(17, 8.6), facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG)
        ax.set_xlim(0, 1024)
        ax.set_ylim(1024, 0)          # VLR: y grows downward
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#1c2330")

    # ---- left: density over the map ----
    ax = axes[0]
    img = plt.imread(MAPIMG)
    # The official icon is white-on-transparent; invert so the playable area
    # reads as light grey on the dark background.
    if img.ndim == 3 and img.shape[2] == 4:
        alpha = img[..., 3]
        base = np.ones_like(alpha) * 0.22
        base = base * alpha
    else:
        base = img[..., 0] * 0.25
    ax.imshow(base, extent=(0, 1024, 1024, 0), cmap="gray",
              vmin=0, vmax=1, alpha=0.95)
    heat = gaussian_heat(xs, ys)
    ax.imshow(heat, extent=(0, 1024, 1024, 0), cmap="inferno",
              alpha=0.62, vmin=0, vmax=heat.max() * 0.60)
    ax.scatter(xs, ys, s=14, c="#ffffff", alpha=0.55, linewidths=0)
    ax.set_title(f"Ascent — first-blood locations  (n = {len(xs)} rounds)",
                 color=FG, fontsize=15, pad=14)
    # zone labels (positions read off the official minimap)
    for label, lx, ly in [("A site", 800, 300), ("B site", 170, 330),
                          ("Mid", 500, 520), ("A main", 300, 760),
                          ("B main", 130, 700), ("T spawn", 480, 940)]:
        ax.text(lx, ly, label, color="#ffffff", fontsize=11, alpha=0.65,
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.25", fc="#0e131b", ec="none",
                          alpha=0.55))

    # ---- right: by side (attacker vs defender) ----
    ax = axes[1]
    ax.imshow(base, extent=(0, 1024, 1024, 0), cmap="gray",
              vmin=0, vmax=1, alpha=0.95)
    att = [(r["x"], r["y"]) for r in rows
           if r["x"] is not None and r["attacking"]
           and r["killer_team"] == r["attacking"]]
    dfd = [(r["x"], r["y"]) for r in rows
           if r["x"] is not None and r["attacking"]
           and r["killer_team"] != r["attacking"]]
    if att:
        ax.scatter([p[0] for p in att], [p[1] for p in att], s=42, c=ACCENT,
                   alpha=0.85, label=f"attacker {len(att)}", linewidths=0)
    if dfd:
        ax.scatter([p[0] for p in dfd], [p[1] for p in dfd], s=42, c=BLUE,
                   alpha=0.85, label=f"defender {len(dfd)}", linewidths=0,
                   marker="^")
    leg = ax.legend(facecolor="#121821", edgecolor="#1c2330", fontsize=12,
                    loc="lower left")
    for t in leg.get_texts():
        t.set_color(FG)
    ax.set_title("Who wins the opening duel", color=FG, fontsize=15, pad=14)

    fig.text(0.5, 0.035,
             "Champions 2026 (Shanghai) · 13 Ascent maps · 259 first bloods · "
             "coordinates from VLR 2D replay",
             ha="center", color=MUTED, fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    out = OUTDIR / "ascent_first_blood_map.png"
    fig.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    print(f"saved -> {out}")

    # ---- a second figure: agent / weapon / range ----
    fig2, axes2 = plt.subplots(1, 3, figsize=(18, 6.2), facecolor=BG)

    ag = Counter(r["agent"] for r in rows).most_common(9)
    a1 = axes2[0]
    a1.barh([a for a, _ in ag][::-1], [n for _, n in ag][::-1],
            color=ACCENT, alpha=0.9)
    a1.set_facecolor(BG)
    a1.tick_params(colors=FG)
    for sp in a1.spines.values():
        sp.set_color("#1c2330")
    a1.set_title("Agent that gets first blood", color=FG, fontsize=14)

    wp = Counter(r["weapon"] for r in rows).most_common(9)
    a2 = axes2[1]
    a2.barh([w for w, _ in wp][::-1], [n for _, n in wp][::-1],
            color=BLUE, alpha=0.9)
    a2.set_facecolor(BG)
    a2.tick_params(colors=FG)
    for sp in a2.spines.values():
        sp.set_color("#1c2330")
    a2.set_title("Weapon used for first blood", color=FG, fontsize=14)

    ds = [r["dist"] for r in rows if r["dist"] is not None]
    a3 = axes2[2]
    a3.hist(ds, bins=24, color="#47C97E", alpha=0.85, edgecolor="#0e131b")
    a3.axvline(np.median(ds), color=ACCENT, lw=2,
               label=f"median {np.median(ds):.0f}")
    a3.set_facecolor(BG)
    a3.tick_params(colors=FG)
    for sp in a3.spines.values():
        sp.set_color("#1c2330")
    a3.set_title("Distance of the opening duel", color=FG, fontsize=14)
    a3.set_xlabel("minimap units", color=MUTED)
    leg3 = a3.legend(facecolor="#121821", edgecolor="#1c2330")
    for t in leg3.get_texts():
        t.set_color(FG)

    fig2.tight_layout()
    out2 = OUTDIR / "ascent_first_blood_stats.png"
    fig2.savefig(out2, dpi=150, facecolor=BG, bbox_inches="tight")
    print(f"saved -> {out2}")


if __name__ == "__main__":
    main()
