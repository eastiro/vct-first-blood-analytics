"""Team-level first-blood leaderboards + how much of it is signal."""
from __future__ import annotations

import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

BASE = Path(r"D:\好玩的项目\valorant-analytics")
d = json.loads((BASE / "data" / "site_v3.json").read_text(encoding="utf-8"))
R, D = d["rounds"], d["dict"]
TEAMS = D["teams"]
MIN_ROUNDS = 200

# ---------------------------------------------------------------- per team
T = {}
for t, name in enumerate(TEAMS):
    T[t] = dict(name=name, n=0, win=0, fbFor=0, fbWon=0, fbAgainst=0, fbAgainstWon=0,
                fbUntraded=0, fbUntradedLost=0, downUntraded=0, downUntradedWon=0,
                fbTraded=0, fbTradedWon=0)

for r in R:
    ev, mp, atkT, defT, winT, killT, ag, ca, sec, x, y, tr, compA, compB = r
    for t in (atkT, defT):
        if t < 0 or t not in T:
            continue
        tm = T[t]
        tm["n"] += 1
        won = (winT == t)
        if won:
            tm["win"] += 1
        if killT == t:
            tm["fbFor"] += 1
            if won:
                tm["fbWon"] += 1
            if tr == 1:
                tm["fbTraded"] += 1
                if won:
                    tm["fbTradedWon"] += 1
            elif tr == 0:
                tm["fbUntraded"] += 1
                if not won:
                    tm["fbUntradedLost"] += 1
        elif killT >= 0:
            tm["fbAgainst"] += 1
            if won:
                tm["fbAgainstWon"] += 1
            if tr == 0:
                tm["downUntraded"] += 1
                if won:
                    tm["downUntradedWon"] += 1


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (100 * max(0, c - h), 100 * min(1, c + h))


rows = []
for t, tm in T.items():
    if tm["n"] < MIN_ROUNDS:
        continue
    rows.append(dict(
        t=t, name=tm["name"], n=tm["n"],
        win=100 * tm["win"] / tm["n"],
        fbRate=100 * tm["fbFor"] / tm["n"],
        fbConv=100 * tm["fbWon"] / tm["fbFor"] if tm["fbFor"] else None,
        comeback=100 * tm["fbAgainstWon"] / tm["fbAgainst"] if tm["fbAgainst"] else None,
        # clean man-advantage thrown away: got FB, nobody traded it, still lost
        choke=100 * tm["fbUntradedLost"] / tm["fbUntraded"] if tm["fbUntraded"] else None,
        # clean man-down win: lost FB, it was not traded, still won
        downWin=100 * tm["downUntradedWon"] / tm["downUntraded"] if tm["downUntraded"] else None,
        fbFor=tm["fbFor"], fbAgainst=tm["fbAgainst"],
        fbUntraded=tm["fbUntraded"], downUntraded=tm["downUntraded"],
    ))

rows.sort(key=lambda r: -r["n"])
print(f"teams with >= {MIN_ROUNDS} rounds: {len(rows)}  "
      f"(total team-rounds {sum(r['n'] for r in rows)})")

# league baseline
allfb = sum(r["fbFor"] for r in rows)
allw = sum(r["n"] for r in rows)
print(f"league FB rate {100*allfb/allw:.1f}%  "
      f"(every round has exactly one FB, so 50% is the ceiling for any team)")

BASE_CONV = 71.1
BASE_COMEBACK = 100 - BASE_CONV
BASE_CHOKE = 100 - 75.6
BASE_DOWNWIN = 100 - 75.6
print(f"baselines: conv {BASE_CONV}%  comeback {BASE_COMEBACK:.1f}%  "
      f"choke {BASE_CHOKE:.1f}%  man-down win {BASE_DOWNWIN:.1f}%")


def board(key, title, hi=True, k=6, fmt="{:.1f}%", extra=""):
    v = [r for r in rows if r[key] is not None]
    v.sort(key=lambda r: -r[key] if hi else r[key])
    print(f"\n=== {title} ===")
    for r in v[:k]:
        lo, hi_ = wilson(
            round(r[key] / 100 * (r["fbFor"] if key == "fbConv" else
                                  r["fbAgainst"] if key == "comeback" else
                                  r["fbUntraded"] if key == "choke" else
                                  r["downUntraded"] if key == "downWin" else r["n"])),
            (r["fbFor"] if key == "fbConv" else
             r["fbAgainst"] if key == "comeback" else
             r["fbUntraded"] if key == "choke" else
             r["downUntraded"] if key == "downWin" else r["n"]))
        print(f"  {r['name']:<24} {fmt.format(r[key]):>7}  "
              f"[{lo:.0f},{hi_:.0f}]  n={r['fbFor'] if key=='fbConv' else r['fbAgainst'] if key=='comeback' else r['fbUntraded'] if key=='choke' else r['downUntraded'] if key=='downWin' else r['n']}")
    if not hi:
        print(f"  ... 反向 (最高):")
        for r in v[-3:][::-1]:
            print(f"  {r['name']:<24} {fmt.format(r[key]):>7}")


board("fbRate", "首杀率最高 (每回合抢到开局交火)", hi=True)
board("fbRate", "首杀率最低", hi=False, k=3)
board("fbConv", "首杀转化率最高 (拿到首杀后赢下回合)", hi=True)
board("fbConv", "首杀转化率最低", hi=False, k=6)
board("comeback", "丢掉首杀后仍赢下回合 · 最高 (逆风能力)", hi=True)
board("comeback", "丢掉首杀后仍赢下回合 · 最低", hi=False, k=3)
board("choke", "拿到干净人数优势还输掉 · 最高 (把握不住)", hi=True)
board("downWin", "干净的 4v5 残局翻盘率 · 最高", hi=True)

# ---------------------------------------------------------------- quadrants
print("\n=== 首杀率 × 转化率 四象限 (相对联赛均值) ===")
m_rate = st.mean(r["fbRate"] for r in rows)
m_conv = st.mean(r["fbConv"] for r in rows if r["fbConv"])
print(f"  means: rate {m_rate:.1f}%  conv {m_conv:.1f}%")
qs = defaultdict(list)
for r in rows:
    if r["fbConv"] is None:
        continue
    qs[(r["fbRate"] >= m_rate, r["fbConv"] >= m_conv)].append(r)
labels = {(True, True): "高首杀 高转化", (True, False): "高首杀 低转化",
          (False, True): "低首杀 高转化", (False, False): "低首杀 低转化"}
for k in [(True, True), (True, False), (False, True), (False, False)]:
    g = sorted(qs[k], key=lambda r: -r["n"])[:4]
    print(f"  {labels[k]:<12} ({len(qs[k])} 队): "
          + ", ".join(f"{r['name']}({r['fbRate']:.0f}/{r['fbConv']:.0f})" for r in g))

# ---------------------------------------------------------------- reliability
print("\n=== 这些榜单有多少是真信号 ===")


def split_half(seed=7):
    rnd = random.Random(seed)
    a, b = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for r in R:
        ev, mp, atkT, defT, winT, killT = r[0], r[1], r[2], r[3], r[4], r[5]
        if killT < 0 or killT not in T or T[killT]["n"] < MIN_ROUNDS:
            continue
        tgt = a if rnd.random() < 0.5 else b
        tgt[killT][0] += 1
        if winT == killT:
            tgt[killT][1] += 1
    pairs = []
    for t in a:
        if a[t][0] >= 60 and b[t][0] >= 60:
            pairs.append((100 * a[t][1] / a[t][0], 100 * b[t][1] / b[t][0]))
    return pairs


def corr(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0


cs = []
for s in range(12):
    p = split_half(s)
    if len(p) >= 15:
        cs.append(corr([x for x, _ in p], [y for _, y in p]))
print(f"  首杀转化率 分半信度: r = {st.mean(cs):+.3f}  "
      f"(12 次随机拆分, n={len(cs)}, 范围 {min(cs):+.2f}..{max(cs):+.2f})")

# split-half for FB rate
def split_half_rate(seed=7):
    rnd = random.Random(seed)
    a, b = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for r in R:
        for t in (r[2], r[3]):
            if t < 0 or t not in T or T[t]["n"] < MIN_ROUNDS:
                continue
            tgt = a if rnd.random() < 0.5 else b
            tgt[t][0] += 1
            if r[5] == t:
                tgt[t][1] += 1
    out = []
    for t in a:
        if a[t][0] >= 100 and b[t][0] >= 100:
            out.append((100 * a[t][1] / a[t][0], 100 * b[t][1] / b[t][0]))
    return out


cs2 = [corr(*zip(*[(x, y) for x, y in split_half_rate(s)])) for s in range(8)]
print(f"  首杀率     分半信度: r = {st.mean(cs2):+.3f}")

# overdispersion: observed sd vs binomial sd
obs = [r["fbConv"] for r in rows if r["fbConv"]]
exp = [100 * math.sqrt(0.711 * 0.289 / r["fbFor"]) for r in rows if r["fbConv"]]
print(f"  首杀转化率 跨队 sd = {st.pstdev(obs):.2f}pp, "
      f"纯随机期望 sd = {st.mean(exp):.2f}pp  →  "
      f"过度离散 {st.pstdev(obs)/st.mean(exp):.2f}×")
