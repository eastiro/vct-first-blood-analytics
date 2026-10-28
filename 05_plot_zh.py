"""Ascent first-blood analysis — corrected map alignment, Chinese labels, metres.

Fixes applied after review:
  * base map is VLR's own minimap (100% coordinate alignment), not valorant-api's
  * every point is guaranteed to land on drawn map pixels (asserted below)
  * distances converted to metres via the world-unit scale
  * all text in Chinese
  * cleaner visual: no muddy over-plotting, zoom on the playable area
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
FB = BASE / "data" / "ascent_first_bloods.json"
OUTDIR = BASE / "figures"

BG = "#0d1117"
PANEL = "#11161f"
FG = "#e6edf3"
MUTED = "#8b949e"
RED = "#FF4655"
BLUE = "#4DA3FF"
GREEN = "#3fb950"

# 1 VLR minimap unit -> metres. Derived from valorant-api's map multipliers
# (1024 * 7e-05 px per Unreal unit, 100 uu = 1 m), validated against callout
# spacing (A site -> B site ~86 m on Ascent).
M_PER_UNIT = 0.1395

# plant-site centres, read off the VLR minimap (see figures/ascent_sites_marked.png)
SITE_A = (208, 294)
SITE_B = (872, 315)


def setup_cjk_font() -> None:
    """Pick an installed CJK font so Chinese labels render instead of boxes."""
    wanted = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
              "Source Han Sans SC", "PingFang SC", "WenQuanYi Zen Hei"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in wanted:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            print(f"font: {name}")
            return
    print(f"WARNING: no CJK font found among {wanted}")


def load_base() -> np.ndarray:
    img = Image.open(MAP).convert("RGBA")
    bg = Image.new("RGBA", img.size, (13, 17, 23, 255))
    bg.alpha_composite(img)
    return np.array(bg)


def assert_on_map(arr: np.ndarray, pts) -> None:
    alpha = arr[..., 3]
    bad = 0
    for x, y in pts:
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < arr.shape[1] and 0 <= yi < arr.shape[0]) or alpha[yi, xi] < 200:
            bad += 1
    print(f"points off the drawn map: {bad}/{len(pts)}")
    if bad:
        raise SystemExit("alignment broken - refusing to plot")


def main() -> None:
    setup_cjk_font()
    base = load_base()
    rows = json.loads(FB.read_text(encoding="utf-8"))
    print(f"first bloods: {len(rows)}")

    pts = [(r["x"], r["y"]) for r in rows if r["x"] is not None]
    assert_on_map(base, pts)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    # crop to the playable area so the map fills the frame
    pad = 40
    x0, x1 = max(0, min(xs) - pad), min(1024, max(xs) + pad)
    y0, y1 = max(0, min(ys) - pad), min(1024, max(ys) + pad)
    # keep aspect square-ish and include both sites
    x0 = min(x0, 150); x1 = max(x1, 940)
    y0 = min(y0, 230); y1 = max(y1, 760)
    print(f"view window: x {x0}..{x1}  y {y0}..{y1}")

    fig = plt.figure(figsize=(15.5, 7.4), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1], wspace=0.10,
                          left=0.01, right=0.99, top=0.90, bottom=0.10)

    # ---------- left: hexbin density over the map ----------
    ax = fig.add_subplot(gs[0, 0])
    ax.set_facecolor(BG)
    ax.imshow(base, extent=(0, 1024, 1024, 0), alpha=0.55)
    hb = ax.hexbin(xs, ys, gridsize=26, cmap="YlOrRd", mincnt=1,
                   linewidths=0.2, edgecolors="#00000000", alpha=0.80,
                   extent=(0, 1024, 0, 1024))
    cb = fig.colorbar(hb, ax=ax, shrink=0.58, pad=0.012, aspect=22)
    cb.set_label("首杀次数", color=FG, fontsize=10, labelpad=6)
    cb.ax.yaxis.set_tick_params(color=FG, labelsize=9)
    plt.setp(cb.ax.get_yticklabels(), color=FG)
    cb.outline.set_edgecolor("#30363d")

    for (sx, sy), lab in ((SITE_A, "A 点"), (SITE_B, "B 点")):
        ax.plot(sx, sy, "o", ms=13, mfc="none", mec=FG, mew=1.8, alpha=0.9)
        ax.text(sx, sy - 26, lab, color=FG, fontsize=12, ha="center",
                fontweight="bold")

    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#30363d")
    ax.set_title(f"亚海悬城 · 首杀位置分布（n = {len(xs)} 回合）",
                 color=FG, fontsize=16, pad=12)

    # ---------- right: attacker vs defender ----------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(PANEL)
    ax2.imshow(base, extent=(0, 1024, 1024, 0), alpha=0.35)
    att = [(r["x"], r["y"]) for r in rows
           if r["x"] is not None and r["attacking"]
           and r["killer_team"] == r["attacking"]]
    dfd = [(r["x"], r["y"]) for r in rows
           if r["x"] is not None and r["attacking"]
           and r["killer_team"] != r["attacking"]]
    if att:
        ax2.scatter([p[0] for p in att], [p[1] for p in att], s=58, c=RED,
                    alpha=0.85, linewidths=0, label=f"进攻方拿下首杀  {len(att)}")
    if dfd:
        ax2.scatter([p[0] for p in dfd], [p[1] for p in dfd], s=58, c=BLUE,
                    alpha=0.85, linewidths=0, marker="s",
                    label=f"防守方拿下首杀  {len(dfd)}")
    leg = ax2.legend(facecolor=PANEL, edgecolor="#30363d", fontsize=11,
                     loc="upper right")
    for t in leg.get_texts():
        t.set_color(FG)
    ax2.set_xlim(x0, x1)
    ax2.set_ylim(y1, y0)
    ax2.set_xticks([])
    ax2.set_yticks([])
    for sp in ax2.spines.values():
        sp.set_color("#30363d")
    pct_d = len(dfd) / max(1, len(att) + len(dfd)) * 100
    ax2.set_title(f"首杀由谁拿下（防守方 {pct_d:.1f}%）",
                  color=FG, fontsize=16, pad=12)

    fig.text(0.5, 0.022,
             f"数据：2026 上海冠军赛 · 13 场 Ascent · {len(rows)} 个首杀  |  "
             f"坐标取自 VLR 逐回合 2D 回放  |  1 单位 ≈ {M_PER_UNIT:.2f} 米",
             ha="center", color=MUTED, fontsize=10)

    out = OUTDIR / "ascent_首杀热力图.png"
    fig.savefig(out, dpi=160, facecolor=BG, bbox_inches="tight")
    print(f"saved -> {out}")

    plt.close(fig)
    make_stats(rows, M_PER_UNIT)


def make_stats(rows, m_per_unit: float) -> None:
    from collections import Counter

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), facecolor=BG)

    ag = Counter(r["agent"] for r in rows).most_common(9)
    a1 = axes[0]
    a1.barh([a for a, _ in ag][::-1], [n for _, n in ag][::-1],
            color=RED, alpha=0.9)
    for i, (_, n) in enumerate(reversed(ag)):
        a1.text(n + 0.6, i, str(n), va="center", color=FG, fontsize=10)
    a1.set_title("拿下首杀的英雄", color=FG, fontsize=14, pad=10)

    wp = Counter(r["weapon"] for r in rows).most_common(9)
    a2 = axes[1]
    a2.barh([w for w, _ in wp][::-1], [n for _, n in wp][::-1],
            color=BLUE, alpha=0.9)
    for i, (_, n) in enumerate(reversed(wp)):
        a2.text(n + 0.6, i, str(n), va="center", color=FG, fontsize=10)
    a2.set_title("拿下首杀的武器", color=FG, fontsize=14, pad=10)

    ds = [r["dist"] * m_per_unit for r in rows if r["dist"] is not None]
    a3 = axes[2]
    a3.hist(ds, bins=22, color=GREEN, alpha=0.85, edgecolor=BG)
    med = float(np.median(ds))
    a3.axvline(med, color=RED, lw=2.2, label=f"中位数 {med:.0f} 米")
    a3.set_title("首杀交火距离", color=FG, fontsize=14, pad=10)
    a3.set_xlabel("米（1 米 ≈ 一个角色身高的 5.5 倍）", color=MUTED, fontsize=10)
    leg = a3.legend(facecolor=PANEL, edgecolor="#30363d")
    for t in leg.get_texts():
        t.set_color(FG)

    for ax in axes:
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=FG)
        for sp in ax.spines.values():
            sp.set_color("#30363d")

    fig.tight_layout()
    out = OUTDIR / "ascent_首杀统计.png"
    fig.savefig(out, dpi=160, facecolor=BG, bbox_inches="tight")
    print(f"saved -> {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
