"""Render the first-blood figures for the 2026 multi-event dataset.

Outputs (figures/):
  fb_heatmap_<map>.png   per-map first-blood density over the VLR minimap
  fb_conversion.png      first blood -> round win, cut three ways
  fb_leaders.png         agent and weapon leaderboards
  fb_distance.png        opening-duel distance distribution

All labels use the official zh-CN names from _cache/zh_names.json.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from PIL import Image  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
SRC = BASE / "data" / "rounds.jsonl"
MAPDIR = BASE / "maps"
FIG = BASE / "figures"
ZH = json.loads((BASE / "_cache" / "zh_names.json").read_text(encoding="utf-8"))
FIG.mkdir(parents=True, exist_ok=True)

# ---- fonts: pick a CJK-capable family that exists on this machine --------
CJK_CANDIDATES = [
    "Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "Noto Sans CJK SC",
    "Source Han Sans SC", "PingFang SC", "DengXian", "SimSun",
]
available = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((c for c in CJK_CANDIDATES if c in available), None)
if CJK:
    plt.rcParams["font.family"] = CJK
plt.rcParams["axes.unicode_minus"] = False
print(f"font: {CJK or '<< no CJK font found >>'}")

# ---- colours -------------------------------------------------------------
BG = "#0f1923"
FG = "#e8e8e8"
ACCENT = "#ff4655"
ACCENT2 = "#22d3ee"
GRID = "#2a3540"

HEAT = LinearSegmentedColormap.from_list(
    "fb", ["#0b1a2b", "#1b4f72", "#2e86c1", "#f4d03f", "#ff4655"]
)

# 1 map unit on the 1024px minimap == 0.1395 m (derived from the
# 1024 * 7e-05 px/world-unit scale and 1 uu = 1 cm)
M_PER_UNIT = 0.1395


def load() -> list[dict]:
    rows = []
    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def first_kill(r: dict) -> dict | None:
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def zh_agent(key: str) -> str:
    return ZH["agents"].get((key or "").lower(), key or "?")


def zh_map(name: str) -> str:
    return ZH.get("maps", {}).get((name or "").lower(), name or "?")


def on_map(k: dict) -> bool:
    """Coordinates must sit inside the 1024x1024 minimap.

    Some first bloods are environmental deaths (cause "Fall", e.g. off the
    Abyss edge); their recorded position is off-map and would smear the
    heatmap, so they are excluded from the spatial views only.
    """
    try:
        x, y = float(k["pos_x"]), float(k["pos_y"])
    except (KeyError, TypeError, ValueError):
        return False
    return 0.0 <= x <= 1024.0 and 0.0 <= y <= 1024.0


def zh_cause(cause: str) -> str:
    c = (cause or "").strip()
    if not c:
        return "未知"
    low = c.lower()
    if low in ZH["weapons"]:
        return ZH["weapons"][low]
    if low in ZH["abilities"]:
        return ZH["abilities"][low]
    return c


def style_axes(ax, title: str = "", xlabel: str = "", ylabel: str = "") -> None:
    ax.set_facecolor(BG)
    if title:
        ax.set_title(title, color=FG, fontsize=13, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=FG, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=FG, fontsize=10)
    ax.tick_params(colors=FG, labelsize=9)
    for s in ax.spines.values():
        s.set_color(GRID)


# --------------------------------------------------------------------------
# per-map heatmap
# --------------------------------------------------------------------------

def plot_map_heatmap(map_name: str, rows: list[dict]) -> Path | None:
    img_path = MAPDIR / f"{map_name.lower().replace(' ', '')}.png"
    if not img_path.exists():
        print(f"  no minimap for {map_name}")
        return None

    geo = [r for r in rows if r["map"] == map_name and r.get("geometry")]
    if not geo:
        return None

    atk, dfn = [], []
    for r in geo:
        fk = first_kill(r)
        if not fk or not on_map(fk):
            continue
        attacking = r.get("attacking") or ""
        is_atk = (fk.get("killer_team") or "") == attacking
        (atk if is_atk else dfn).append((fk["pos_x"], fk["pos_y"]))

    n = len(atk) + len(dfn)
    if n < 20:
        print(f"  {map_name}: only {n} positioned first bloods, skipping")
        return None

    base = Image.open(img_path).convert("RGB")
    W, H = base.size

    fig, ax = plt.subplots(figsize=(8.4, 8.4), facecolor=BG)
    ax.imshow(base, extent=(0, W, H, 0))
    ax.set_facecolor(BG)

    allpts = atk + dfn
    xs = [p[0] for p in allpts]
    ys = [p[1] for p in allpts]
    hb = ax.hexbin(xs, ys, gridsize=30, cmap=HEAT, mincnt=1,
                   linewidths=0, alpha=0.80, bins="log",
                   extent=(0, W, 0, H))
    cb = fig.colorbar(hb, ax=ax, fraction=0.036, pad=0.02)
    cb.set_label("首杀次数", color=FG, fontsize=9)
    cb.ax.tick_params(colors=FG, labelsize=8)
    cb.outline.set_edgecolor(GRID)

    if atk:
        ax.scatter([p[0] for p in atk], [p[1] for p in atk], s=16,
                   c=ACCENT, alpha=0.55, edgecolors="none",
                   label=f"进攻方首杀 ({len(atk)})", zorder=3)
    if dfn:
        ax.scatter([p[0] for p in dfn], [p[1] for p in dfn], s=16,
                   c=ACCENT2, alpha=0.55, marker="s", edgecolors="none",
                   label=f"防守方首杀 ({len(dfn)})", zorder=3)

    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)

    events = len({(r["series_id"], r["game_id"]) for r in geo})
    rounds = len(geo)
    ax.set_title(f"{zh_map(map_name)} · 首杀位置分布\n"
                 f"{events} 张地图 / {rounds} 回合 / {n} 次首杀",
                 color=FG, fontsize=13, pad=12)
    leg = ax.legend(loc="lower left", facecolor="#1a2530", edgecolor=GRID,
                    labelcolor=FG, fontsize=9, framealpha=0.9)
    leg.get_frame().set_linewidth(0.6)

    out = FIG / f"fb_heatmap_{map_name.lower()}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  {zh_map(map_name):<8} {events:>3} maps {rounds:>5} rounds {n:>5} FB "
          f"(atk {len(atk)} / def {len(dfn)}) -> {out.name}")
    return out


# --------------------------------------------------------------------------
# conversion panel
# --------------------------------------------------------------------------

WEAPON_CLASS_ZH = {
    "pistol": "手枪", "smg": "冲锋枪", "shotgun": "霰弹枪",
    "rifle": "步枪", "sniper": "狙击枪", "lmg": "机枪",
    "melee": "近战", "ability": "技能", "unknown": "未知",
}

EVENT_ZH = {
    "Masters London 2026": "伦敦大师赛",
    "VCT Americas Stage 2": "美洲 S2",
    "VCT EMEA Stage 2": "EMEA S2",
    "VCT China Stage 2": "中国 S2",
    "VCT Pacific Stage 2": "太平洋 S2",
}


def plot_conversion(rows: list[dict]) -> Path | None:
    by_event: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    by_side: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    by_class: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})

    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        win = r.get("winner_team") or ""
        kt = fk.get("killer_team") or ""
        if not win or not kt:
            continue
        won = kt == win
        key_e = r["event"]
        by_event[key_e]["n"] += 1
        by_event[key_e]["won"] += int(won)

        attacking = r.get("attacking") or ""
        side = "进攻方" if (attacking and kt == attacking) else "防守方"
        by_side[side]["n"] += 1
        by_side[side]["won"] += int(won)

        cause = (fk.get("cause") or "").strip().lower()
        if cause in ZH["weapons"]:
            wl = cause
            cls = ("pistol" if wl in ("classic", "shorty", "frenzy", "ghost", "sheriff", "bandit")
                   else "smg" if wl in ("stinger", "spectre")
                   else "shotgun" if wl in ("bucky", "judge")
                   else "rifle" if wl in ("bulldog", "guardian", "phantom", "vandal")
                   else "sniper" if wl in ("marshal", "outlaw", "operator")
                   else "lmg" if wl in ("ares", "odin")
                   else "melee" if wl == "melee" else "unknown")
        else:
            cls = "ability"
        by_class[cls]["n"] += 1
        by_class[cls]["won"] += int(won)

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.6), facecolor=BG)
    fig.suptitle("首杀之后赢下这一回合的概率", color=FG, fontsize=16, y=1.02)

    def bar(ax, data: dict, order: list[str] | None, title: str, color: str):
        keys = order or sorted(data, key=lambda k: -data[k]["n"])
        keys = [k for k in keys if k in data and data[k]["n"] >= 20]
        rates = [100 * data[k]["won"] / data[k]["n"] for k in keys]
        ns = [data[k]["n"] for k in keys]
        ypos = np.arange(len(keys))
        ax.barh(ypos, rates, color=color, alpha=0.88, height=0.62)
        ax.set_yticks(ypos)
        ax.set_yticklabels([f"{k}  (n={n})" for k, n in zip(keys, ns)],
                           color=FG, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.axvline(50, color=GRID, lw=1, ls="--")
        for y, v in zip(ypos, rates):
            ax.text(v + 1.2, y, f"{v:.1f}%", va="center", color=FG, fontsize=8.5)
        style_axes(ax, title, "首杀方最终获胜的比例 (%)")

    ev_order = sorted(by_event, key=lambda k: by_event[k]["n"])
    ev_labeled = {EVENT_ZH.get(k, k): v for k, v in by_event.items()}
    bar(axes[0], ev_labeled, [EVENT_ZH.get(k, k) for k in ev_order],
        "按赛事", ACCENT)
    bar(axes[1], by_side, ["进攻方", "防守方"], "按首杀方阵营", ACCENT2)
    cls_order = sorted(by_class, key=lambda k: -by_class[k]["n"])
    class_labeled = {WEAPON_CLASS_ZH.get(k, k): v for k, v in by_class.items()}
    cls_order_zh = [WEAPON_CLASS_ZH.get(k, k) for k in cls_order]
    bar(axes[2], class_labeled, cls_order_zh,
        "按首杀使用的手段",
        LinearSegmentedColormap.from_list("c", ["#ff4655", "#f4d03f"])(0.5))

    for ax in axes:
        ax.set_facecolor(BG)

    fig.tight_layout()
    out = FIG / "fb_conversion.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    pool_n = sum(v["n"] for v in by_event.values())
    pool_w = sum(v["won"] for v in by_event.values())
    print(f"  conversion -> {out.name}  (pooled {100*pool_w/pool_n:.1f}% of {pool_n})")
    return out


# --------------------------------------------------------------------------
# leaderboards
# --------------------------------------------------------------------------

def plot_leaders(rows: list[dict]) -> Path | None:
    agents: Counter = Counter()
    weapons: Counter = Counter()
    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        agents[zh_agent(fk.get("killer_agent"))] += 1
        weapons[zh_cause(fk.get("cause"))] += 1

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.2), facecolor=BG)
    fig.suptitle("谁在拿首杀", color=FG, fontsize=16, y=1.0)

    total_a = sum(agents.values())
    top_a = agents.most_common(14)
    names = [k for k, _ in top_a][::-1]
    vals = [v for _, v in top_a][::-1]
    ax = axes[0]
    ax.barh(np.arange(len(names)), vals, color=ACCENT, alpha=0.9, height=0.66)
    ax.set_yticks(np.arange(len(names)))
    ax.set_yticklabels(names, color=FG, fontsize=10)
    for y, v in zip(np.arange(len(names)), vals):
        ax.text(v + max(vals) * 0.012, y, f"{v}  ({100*v/total_a:.1f}%)",
                va="center", color=FG, fontsize=8.5)
    ax.set_xlim(0, max(vals) * 1.22)
    style_axes(ax, "英雄", "首杀次数")

    total_w = sum(weapons.values())
    top_w = weapons.most_common(14)
    names = [k for k, _ in top_w][::-1]
    vals = [v for _, v in top_w][::-1]
    ax = axes[1]
    ax.barh(np.arange(len(names)), vals, color=ACCENT2, alpha=0.9, height=0.66)
    ax.set_yticks(np.arange(len(names)))
    ax.set_yticklabels(names, color=FG, fontsize=10)
    for y, v in zip(np.arange(len(names)), vals):
        ax.text(v + max(vals) * 0.012, y, f"{v}  ({100*v/total_w:.1f}%)",
                va="center", color=FG, fontsize=8.5)
    ax.set_xlim(0, max(vals) * 1.22)
    style_axes(ax, "武器 / 技能", "首杀次数")

    fig.tight_layout()
    out = FIG / "fb_leaders.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    print(f"  leaders -> {out.name}")
    print("    top agents:", agents.most_common(8))
    print("    top weapons:", weapons.most_common(8))
    return out


# --------------------------------------------------------------------------
# distance
# --------------------------------------------------------------------------

def plot_distance(rows: list[dict]) -> Path | None:
    dists = []
    per_map: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        fk = first_kill(r)
        if not fk or not fk.get("distance"):
            continue
        m = float(fk["distance"]) * M_PER_UNIT
        dists.append(m)
        per_map[r["map"]].append(m)

    if len(dists) < 50:
        print(f"  distance: only {len(dists)} samples")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(15.0, 5.8), facecolor=BG)

    ax = axes[0]
    ax.hist(dists, bins=44, color=ACCENT, alpha=0.85, edgecolor="none")
    med = statistics.median(dists)
    ax.axvline(med, color=ACCENT2, lw=2, ls="--",
               label=f"中位数 {med:.0f} 米")
    top = min(max(dists), 80)
    ax.set_xlim(0, top)
    ymax = ax.get_ylim()[1]
    ax.axvspan(0, 10, color=ACCENT2, alpha=0.09)
    ax.axvspan(35, top, color="#f4d03f", alpha=0.07)
    ax.text(5, ymax * 0.94, "贴身\n<10米", color=ACCENT2,
            fontsize=8.5, ha="center", va="top")
    ax.text(top * 0.86, ymax * 0.94, "远程\n>35米", color="#f4d03f",
            fontsize=8.5, ha="center", va="top")
    style_axes(ax, f"首杀交火距离 (n={len(dists)})",
               "击杀者与死者的间距 (米)", "回合数")
    ax.legend(facecolor="#1a2530", edgecolor=GRID, labelcolor=FG, fontsize=9,
              loc="center right")

    ax = axes[1]
    maps_sorted = sorted(per_map, key=lambda m: statistics.median(per_map[m]))
    data = [per_map[m] for m in maps_sorted]
    bp = ax.boxplot(data, vert=False, patch_artist=True, widths=0.62,
                    tick_labels=[f"{zh_map(m)}  (n={len(per_map[m])})" for m in maps_sorted])
    for patch in bp["boxes"]:
        patch.set_facecolor(ACCENT)
        patch.set_alpha(0.75)
        patch.set_edgecolor(FG)
    for part in ("whiskers", "caps", "medians"):
        for ln in bp[part]:
            ln.set_color(FG if part != "medians" else ACCENT2)
            ln.set_linewidth(1.4 if part == "medians" else 0.9)
    for flier in bp["fliers"]:
        flier.set_markerfacecolor(FG)
        flier.set_markeredgecolor(FG)
        flier.set_markersize(3)
    ax.tick_params(axis="y", colors=FG, labelsize=9)
    style_axes(ax, "各张地图的首杀距离", "间距 (米)")

    fig.tight_layout()
    out = FIG / "fb_distance.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    print(f"  distance -> {out.name}  median {med:.1f} m over {len(dists)} duels")
    return out


# --------------------------------------------------------------------------

def main() -> None:
    rows = load()
    print(f"round rows : {len(rows)}")
    print(f"maps       : {len({(r['series_id'], r['game_id']) for r in rows})}")
    print(f"events     : {sorted({r['event'] for r in rows})}")

    fb = sum(1 for r in rows if first_kill(r))
    print(f"first bloods: {fb}\n")

    print("=== per-map heatmaps ===")
    maps = sorted({r["map"] for r in rows if r.get("geometry")})
    made = []
    for m in maps:
        p = plot_map_heatmap(m, rows)
        if p:
            made.append(p)

    print("\n=== conversion ===")
    plot_conversion(rows)

    print("\n=== leaders ===")
    plot_leaders(rows)

    print("\n=== distance ===")
    plot_distance(rows)

    print(f"\nfigures in {FIG}")


if __name__ == "__main__":
    main()
