"""Ascent first-blood analysis — Chinese labels, metres with a readable yardstick.

Design notes from review:
  * base map is VLR's own minimap, so coordinates align 100%
  * Chinese names come from valorant-api's official zh-CN strings
  * distances in metres, explained with map landmarks instead of abstract units
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
FB = BASE / "data" / "ascent_first_bloods.json"
NAMES = BASE / "_cache" / "zh_names.json"
OUTDIR = BASE / "figures"

BG = "#0d1117"
PANEL = "#11161f"
FG = "#e6edf3"
MUTED = "#8b949e"
RED = "#FF4655"
BLUE = "#4DA3FF"
GREEN = "#3fb950"

M_PER_UNIT = 0.1395
SITE_A = (208, 294)
SITE_B = (872, 315)


def setup_cjk() -> None:
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in {f.name for f in font_manager.fontManager.ttflist}:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return
    raise SystemExit("no CJK font")


def load_base() -> np.ndarray:
    img = Image.open(MAP).convert("RGBA")
    bg = Image.new("RGBA", img.size, (13, 17, 23, 255))
    bg.alpha_composite(img)
    return np.array(bg)


def assert_on_map(arr: np.ndarray, pts) -> None:
    alpha = arr[..., 3]
    bad = sum(
        1 for x, y in pts
        if not (0 <= int(x) < arr.shape[1] and 0 <= int(y) < arr.shape[0])
        or alpha[int(y), int(x)] < 200
    )
    print(f"off-map points: {bad}/{len(pts)}")
    if bad:
        raise SystemExit("alignment broken")


def zh(mapping: dict, key: str | None) -> str:
    if not key:
        return "—"
    return mapping.get(str(key).lower(), str(key))


def main() -> None:
    setup_cjk()
    names = json.loads(NAMES.read_text(encoding="utf-8"))
    agent_zh, weapon_zh = names["agents"], names["weapons"]

    base = load_base()
    rows = json.loads(FB.read_text(encoding="utf-8"))
    pts = [(r["x"], r["y"]) for r in rows if r["x"] is not None]
    assert_on_map(base, pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    x0, x1 = min(xs) - 55, max(xs) + 55
    y0, y1 = min(ys) - 55, max(ys) + 55
    x0, x1 = min(x0, 140), max(x1, 950)
    y0, y1 = min(y0, 225), max(y1, 775)

    fig = plt.figure(figsize=(15.5, 7.4), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1], wspace=0.10,
                          left=0.01, right=0.99, top=0.90, bottom=0.11)

    # ---------- left: hexbin density ----------
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
        ax.text(sx, sy - 28, lab, color=FG, fontsize=12, ha="center",
                fontweight="bold")

    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#30363d")
    ax.set_title(f"亚海悬城 · 首杀位置分布（{len(xs)} 个首杀）",
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
    ax2.scatter([p[0] for p in att], [p[1] for p in att], s=56, c=RED,
                alpha=0.85, linewidths=0, label=f"进攻方先拿首杀　{len(att)}")
    ax2.scatter([p[0] for p in dfd], [p[1] for p in dfd], s=52, c=BLUE,
                alpha=0.85, linewidths=0, marker="s",
                label=f"防守方先拿首杀　{len(dfd)}")
    leg = ax2.legend(facecolor=PANEL, edgecolor="#30363d", fontsize=11,
                     loc="upper right")
    for t in leg.get_texts():
        t.set_color(FG)
    for (sx, sy), lab in ((SITE_A, "A 点"), (SITE_B, "B 点")):
        ax2.text(sx, sy - 28, lab, color=FG, fontsize=10, ha="center", alpha=0.75)
    ax2.set_xlim(x0, x1)
    ax2.set_ylim(y1, y0)
    ax2.set_xticks([])
    ax2.set_yticks([])
    for sp in ax2.spines.values():
        sp.set_color("#30363d")
    pct = len(dfd) / max(1, len(att) + len(dfd)) * 100
    ax2.set_title(f"首杀归属（防守方 {pct:.1f}%）", color=FG, fontsize=16, pad=12)

    fig.text(0.5, 0.022,
             "数据：2026 上海冠军赛 · 13 场亚海悬城 · 259 个首杀　|　"
             "坐标取自 VLR 逐回合 2D 回放　|　英雄与武器中文名取自官方国服译名",
             ha="center", color=MUTED, fontsize=10)

    out = OUTDIR / "ascent_首杀热力图.png"
    fig.savefig(out, dpi=160, facecolor=BG, bbox_inches="tight")
    print(f"saved -> {out}")
    plt.close(fig)

    make_stats(rows, agent_zh, weapon_zh)


def make_stats(rows, agent_zh, weapon_zh) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.8), facecolor=BG)

    ag = Counter(zh(agent_zh, r["agent"]) for r in rows).most_common(9)
    a1 = axes[0]
    a1.barh([a for a, _ in ag][::-1], [n for _, n in ag][::-1], color=RED, alpha=0.9)
    for i, (_, n) in enumerate(reversed(ag)):
        a1.text(n + 0.5, i, str(n), va="center", color=FG, fontsize=10)
    a1.set_title("拿下首杀的英雄", color=FG, fontsize=14, pad=10)

    wp = Counter(zh(weapon_zh, r["weapon"]) for r in rows).most_common(9)
    a2 = axes[1]
    a2.barh([w for w, _ in wp][::-1], [n for _, n in wp][::-1], color=BLUE, alpha=0.9)
    for i, (_, n) in enumerate(reversed(wp)):
        a2.text(n + 0.5, i, str(n), va="center", color=FG, fontsize=10)
    a2.set_title("拿下首杀的武器", color=FG, fontsize=14, pad=10)

    ds = [r["dist"] * M_PER_UNIT for r in rows if r["dist"] is not None]
    a3 = axes[2]
    a3.hist(ds, bins=22, color=GREEN, alpha=0.85, edgecolor=BG)
    med = float(np.median(ds))
    a3.axvline(med, color=RED, lw=2.2, label=f"中位数 {med:.0f} 米")

    # a landing yardstick instead of abstract units
    a3.axvspan(0, 10, color=MUTED, alpha=0.10)
    a3.text(5, a3.get_ylim()[1] * 0.94, "贴身\n<10 米", ha="center", va="top",
            color=MUTED, fontsize=9)
    a3.axvspan(35, 60, color=MUTED, alpha=0.10)
    a3.text(47, a3.get_ylim()[1] * 0.94, "远距离\n>35 米", ha="center", va="top",
            color=MUTED, fontsize=9)

    a3.set_title("首杀交火距离", color=FG, fontsize=14, pad=10)
    a3.set_xlabel("距离（米）　参考：A 点到 B 点约 86 米，全图对角线约 100 米",
                  color=MUTED, fontsize=9)
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
