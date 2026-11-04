"""赛段对比：S1 vs S2 各队首杀指标变化 + 跨赛段稳定性检验。

回答两个问题：
  1. 哪些队在第一赛段 → 第二赛段之间真的变了？
  2. 「整季榜」到底有没有用？—— 用 S1 预测 S2 的能力来量。
     （随机分半信度是上界；跨赛段相关才是真正的可迁移性。）
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

# 重定向/管道输出到文件时，stdout 按系统 locale 编码（中文 Windows = GBK），
# 遇到 LEVIATÁN 的「Á」这类不在 GBK 里的字符会 UnicodeEncodeError，脚本直接中断。
# 控制台直出（isatty）不受影响，这里只把重定向走的输出固定成 UTF-8。
if not sys.stdout.isatty() and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
d = json.loads((BASE / "data" / "site_v3.json").read_text(encoding="utf-8"))
R, D = d["rounds"], d["dict"]
EV = D["events"]
TEAMS = D["teams"]

# 赛事 -> 赛段标签
STAGE = {}
for i, e in enumerate(EV):
    if "Kickoff" in e:
        STAGE[i] = ("KICKOFF", e.split()[1])
    elif "Stage 1" in e:
        STAGE[i] = ("S1", e.split()[1])
    elif "Stage 2" in e:
        STAGE[i] = ("S2", e.split()[1])
    elif "Masters" in e:
        STAGE[i] = ("MASTERS", "INTL")
    elif "Champions" in e:
        STAGE[i] = ("CHAMPIONS", "INTL")

REGION_ZH = {"Americas": "美洲", "China": "中国", "EMEA": "EMEA", "Pacific": "太平洋"}


def empty():
    return dict(n=0, win=0, fb=0, fbw=0, ag=0, agw=0, tr=0, untr=0,
                comps=defaultdict(int), compN=0)


def add(m, r, t):
    m["n"] += 1
    w = (r[4] == t)
    if w:
        m["win"] += 1
    if r[5] == t:
        m["fb"] += 1
        if w:
            m["fbw"] += 1
        if r[11] == 1:
            m["tr"] += 1
        elif r[11] == 0:
            m["untr"] += 1
    elif r[5] >= 0:
        m["ag"] += 1
        if w:
            m["agw"] += 1
    # 本队阵容：拿到首杀的是 compA，否则 compB
    cid = r[12] if r[5] == t else r[13]
    if cid >= 0:
        m["comps"][cid] += 1
        m["compN"] += 1


# team-stage -> metrics ; team-stage-region
per = defaultdict(empty)
for r in R:
    ev = r[0]
    stg = STAGE.get(ev)
    if not stg:
        continue
    for t in (r[2], r[3]):
        if t < 0:
            continue
        add(per[(t, stg[0])], r, t)


def val(m, key, need=40):
    if key == "fbRate":
        return 100 * m["fb"] / m["n"] if m["n"] >= 60 else None
    if key == "fbConv":
        return 100 * m["fbw"] / m["fb"] if m["fb"] >= need else None
    if key == "recovery":
        return 100 * m["agw"] / m["ag"] if m["ag"] >= need else None
    if key == "winRate":
        return 100 * m["win"] / m["n"] if m["n"] >= 60 else None
    if key == "compCons":
        return 100 * max(m["comps"].values()) / m["compN"] if m["compN"] >= 40 else None
    if key == "topCompShare":
        return 100 * max(m["comps"].values()) / m["compN"] if m["compN"] >= 40 else None
    raise KeyError(key)


KEYS = [("fbRate", "首杀率"), ("fbConv", "首杀转化"),
        ("recovery", "丢首杀后胜"), ("winRate", "胜率"), ("compCons", "阵容一致性")]


def corr(xs, ys):
    if len(xs) < 4:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else None


print("=" * 78)
print("1. S1 -> S2 跨赛段稳定性（同赛段同队的指标能否互相预测）")
print("=" * 78)
print(f"{'指标':<16} {'跨赛段 r':>9} {'队数':>5}   解读")
stage_pairs = []
for key, lab in KEYS:
    xs, ys = [], []
    for t, name in enumerate(TEAMS):
        a = per.get((t, "S1"))
        b = per.get((t, "S2"))
        if not a or not b:
            continue
        va, vb = val(a, key), val(b, key)
        if va is None or vb is None:
            continue
        xs.append(va)
        ys.append(vb)
        if key == "fbRate":
            stage_pairs.append((name, va, vb, a["n"], b["n"]))
    r = corr(xs, ys)
    if r is None:
        continue
    解读 = "可迁移" if r >= 0.5 else ("弱" if r >= 0.3 else "不可迁移")
    print(f"{lab:<16} {r:>+9.3f} {len(xs):>5}   {解读}")

print()
print("=" * 78)
print("2. 随机分半信度 vs 跨赛段（同一批队，看环境漂移有多大）")
print("=" * 78)


def halves(seed, stage_filter=None):
    rnd = random.Random(seed)
    a, b = defaultdict(empty), defaultdict(empty)
    for r in R:
        stg = STAGE.get(r[0])
        if not stg:
            continue
        if stage_filter and stg[0] != stage_filter:
            continue
        for t in (r[2], r[3]):
            if t < 0:
                continue
            add(a[(t, 0)] if rnd.random() < 0.5 else b[(t, 0)], r, t)
    return a, b


for key, lab in KEYS:
    vals = []
    for s in range(10):
        a, b = halves(s, "S1")
        xs, ys = [], []
        for k in a:
            va, vb = val(a[k], key), val(b[k], key)
            if va is not None and vb is not None:
                xs.append(va)
                ys.append(vb)
        r = corr(xs, ys)
        if r is not None:
            vals.append(r)
    if not vals:
        continue
    m = st.mean(vals)
    sb = 2 * m / (1 + m) if m > -1 else float("nan")
    print(f"{lab:<16} S1 内部随机分半 r_full ≈ {sb:+.3f}   (n={len(xs)} 队-半)")

print()
print("=" * 78)
print("3. 首杀率：S1 -> S2 逐队变化（按变化幅度排序）")
print("=" * 78)
print(f"{'队伍':<24} {'S1':>8} {'S2':>8} {'变化':>8} {'S1n':>5} {'S2n':>5}")
rows = []
for name, v1, v2, n1, n2 in stage_pairs:
    rows.append((v2 - v1, name, v1, v2, n1, n2))
rows.sort(reverse=True)
for dv, name, v1, v2, n1, n2 in rows:
    flag = " " if abs(dv) < 3 else ("▲" if dv > 0 else "▼")
    print(f"{name:<24} {v1:>7.1f}% {v2:>7.1f}% {dv:>+7.1f} {flag} {n1:>4} {n2:>5}")

print()
print("=" * 78)
print("4. 各赛区 S1/S2 平均首杀率、转化率（环境层面有没有整体漂移）")
print("=" * 78)
print(f"{'赛区':<10} {'S1 回合':>8} {'S1 首杀→胜':>11} {'S2 回合':>8} {'S2 首杀→胜':>11} {'差':>7}")
for reg in ("Americas", "China", "EMEA", "Pacific"):
    row = {}
    for stg in ("S1", "S2"):
        n = fbw = 0
        for r in R:
            s = STAGE.get(r[0])
            if not s or s[0] != stg or s[1] != reg:
                continue
            n += 1
            if r[5] >= 0 and r[4] == r[5]:
                fbw += 1
        row[stg] = (n, 100 * fbw / n if n else 0)
    n1, v1 = row["S1"]
    n2, v2 = row["S2"]
    print(f"{REGION_ZH[reg]:<10} {n1:>8} {v1:>10.1f}% {n2:>8} {v2:>10.1f}% {v2-v1:>+6.1f}")

print()
print("=" * 78)
print("5. 阵容一致性：它到底测到了什么")
print("=" * 78)


def comp_profile(stage):
    out = {}
    for t, name in enumerate(TEAMS):
        m = per.get((t, stage))
        if not m or m["compN"] < 100:
            continue
        share = 100 * max(m["comps"].values()) / m["compN"]
        out[t] = (name, share, m["compN"], m["n"])
    return out


print("S1 阵容一致性最高的 5 支 / 最低的 5 支（≥100 个有阵容记录的回合）")
p1 = comp_profile("S1")
if p1:
    srt = sorted(p1.values(), key=lambda x: -x[1])
    print("  最高:")
    for name, sh, cn, n in srt[:5]:
        print(f"    {name:<24} {sh:>5.1f}%  (回合 {n})")
    print("  最低:")
    for name, sh, cn, n in srt[-5:]:
        print(f"    {name:<24} {sh:>5.1f}%  (回合 {n})")

print()
print("阵容一致性 vs 胜率（S1，≥100 回合）")
xs, ys = [], []
for t, (name, sh, cn, n) in p1.items():
    m = per[(t, "S1")]
    if m["n"] >= 100:
        xs.append(sh)
        ys.append(100 * m["win"] / m["n"])
r = corr(xs, ys)
print(f"  r = {r:+.3f}  (n={len(xs)} 队)")

print()
print("阵容一致性 S1 -> S2 跨赛段")
xs, ys = [], []
# TEAMS 是队名列表，per 的键是队伍索引，必须用 enumerate 取索引（同第 118 行）
for t, _name in enumerate(TEAMS):
    a = per.get((t, "S1"))
    b = per.get((t, "S2"))
    if not a or not b:
        continue
    va, vb = val(a, "compCons"), val(b, "compCons")
    if va is None or vb is None:
        continue
    xs.append(va)
    ys.append(vb)
r = corr(xs, ys)
if r is None:
    print(f"  r = n/a  (有效队数 {len(xs)}，不足 4 支或方差为 0)")
else:
    print(f"  r = {r:+.3f}  (n={len(xs)} 队，≥40 回合)")

print()
print("有多少队的「一致性」其实是 3 场以内打出来的？")
allm = []
for (t, stage), m in per.items():
    if stage not in ("S1", "S2") or m["compN"] < 40:
        continue
    allm.append((TEAMS[t], stage, m["n"], 100 * max(m["comps"].values()) / m["compN"]))
allm.sort(key=lambda x: -x[3])
print(f"  共 {len(allm)} 个队-赛段")
print(f"  一致性 = 100% 的：{sum(1 for x in allm if x[3] > 99.5)} 个")
print(f"  其中回合数 < 80 的：{sum(1 for x in allm if x[3] > 99.5 and x[2] < 80)} 个")
