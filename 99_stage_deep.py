"""赛段深挖：区分「真的变了」和「回归均值」，并检验候选替代表格列。"""
from __future__ import annotations

import json
import math
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r"D:\好玩的项目\valorant-analytics")
rows = [json.loads(l) for l in (BASE / "data" / "rounds_all.jsonl").open(encoding="utf-8")]
d = json.loads((BASE / "data" / "site_v3.json").read_text(encoding="utf-8"))
D = d["dict"]
TAG = json.loads((BASE / "_cache" / "tag_map.json").read_text(encoding="utf-8"))


def stage_of(ev: str):
    if "Kickoff" in ev:
        return "KICKOFF", ev.split()[1]
    if "Stage 1" in ev:
        return "S1", ev.split()[1]
    if "Stage 2" in ev:
        return "S2", ev.split()[1]
    if "Masters" in ev:
        return "MASTERS", "INTL"
    if "Champions" in ev:
        return "CHAMP", "INTL"
    return None, None


def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


LONG = {"operator", "outlaw", "marshal"}

M = defaultdict(lambda: dict(n=0, win=0, fb=0, fbw=0, ag=0, agw=0,
                              secs=[], players=Counter(), sniper=0))

for r in rows:
    stg = stage_of(r.get("event", ""))
    if not stg[0]:
        continue
    fk = first_kill(r)
    fb_team = TAG.get(fk.get("killer_team"), fk.get("killer_team")) if fk else None
    if fk:
        # loadout weapon of killer
        wp = ""
        for ld in (r.get("loadouts") or []):
            if ld.get("name") == fk.get("killer"):
                wp = (ld.get("weapon") or "").strip().lower()
                break
    teams = [x.strip() for x in str(r.get("teams") or "").split(" vs ") if x.strip()]
    for t in teams:
        if not t:
            continue
        m = M[(t, stg[0])]
        m["n"] += 1
        won = (r.get("winner_team") == t)
        if won:
            m["win"] += 1
        if fb_team == t:
            m["fb"] += 1
            if won:
                m["fbw"] += 1
            if fk.get("killer"):
                m["players"][fk["killer"]] += 1
            if wp in LONG:
                m["sniper"] += 1
            s = fk.get("seconds")
            if s is not None and s >= 0:
                m["secs"].append(s)
        elif fb_team:
            m["ag"] += 1
            if won:
                m["agw"] += 1

teams = sorted({k[0] for k in M})
print("teams with data:", len(teams))

S1 = {t: M[(t, "S1")] for t in teams if (t, "S1") in M}
S2 = {t: M[(t, "S2")] for t in teams if (t, "S2") in M}
both = [t for t in teams if t in S1 and t in S2 and S1[t]["n"] >= 150 and S2[t]["n"] >= 150]
print("teams in both S1 & S2 (>=150 rounds each):", len(both))


def fbrate(m):
    return 100 * m["fb"] / m["n"]


def conv(m):
    return 100 * m["fbw"] / m["fb"] if m["fb"] >= 100 else None


def corr(x, y):
    if len(x) < 4:
        return None
    mx, my = st.mean(x), st.mean(y)
    n = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dd = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return n / dd if dd else None


def slope(x, y):
    mx, my = st.mean(x), st.mean(y)
    den = sum((a - mx) ** 2 for a in x)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / den if den else None


print()
print("=" * 76)
print("A. 回归均值诊断：Δ = S2 - S1 对 (S1 - 50) 回归")
print("=" * 76)
x = [fbrate(S1[t]) - 50 for t in both]
y = [fbrate(S2[t]) - fbrate(S1[t]) for t in both]
sl = slope(x, y)
print(f"  斜率 = {sl:+.3f}   (纯噪声应 ≈ -1.00，完全稳定应 ≈ 0.00)")
print(f"  Δ 的标准差 = {st.pstdev(y):.2f}pp")
print("  → 斜率越接近 -1，说明「变化」越只是回归均值")

r_obs = corr([fbrate(S1[t]) for t in both], [fbrate(S2[t]) for t in both])
print(f"  S1 vs S2 原始相关 r = {r_obs:+.3f}")

print()
print("=" * 76)
print("B. 扣掉回归均值之后，谁真的变了（残差排序）")
print("=" * 76)
print(f"  {'队伍':<24} {'S1':>7} {'S2':>7} {'原始Δ':>7} {'预期Δ':>7} {'残差':>7}")
res = []
for t in both:
    v1, v2 = fbrate(S1[t]), fbrate(S2[t])
    exp = (r_obs or 0) * (v1 - 50) + 50
    res.append((v2 - exp, t, v1, v2, v2 - v1, exp - v1))
res.sort(reverse=True)
for item in res[:6] + [("",)] + res[-6:]:
    if len(item) == 1:
        print("  " + "-" * 62)
        continue
    dv, t, v1, v2, raw, exp = item
    print(f"  {t:<24} {v1:>6.1f}% {v2:>6.1f}% {raw:>+6.1f} {exp:>+6.1f} {dv:>+6.1f}")

print()
print("=" * 76)
print("C. 候选替代表格列：稳定性 vs 信息量")
print("=" * 76)


def top_share(m):
    if not m["players"] or m["fb"] < 80:
        return None
    return 100 * m["players"].most_common(1)[0][1] / m["fb"]


def med_sec(m):
    if len(m["secs"]) < 80:
        return None
    return st.median(m["secs"])


def snipe(m):
    if m["fb"] < 80:
        return None
    return 100 * m["sniper"] / m["fb"]


cands = [("首杀集中度", top_share), ("首杀中位时刻", med_sec), ("狙击首杀占比", snipe)]


def half_stats(seed, stg="S1"):
    rnd = random.Random(seed)
    A, B = defaultdict(lambda: dict(fb=0, players=Counter(), secs=[], sniper=0)), \
           defaultdict(lambda: dict(fb=0, players=Counter(), secs=[], sniper=0))
    for r in rows:
        st = stage_of(r.get("event", ""))
        if st[0] != stg:
            continue
        fk = first_kill(r)
        if not fk:
            continue
        fbt = TAG.get(fk.get("killer_team"), fk.get("killer_team"))
        wp = ""
        for ld in (r.get("loadouts") or []):
            if ld.get("name") == fk.get("killer"):
                wp = (ld.get("weapon") or "").strip().lower()
                break
        m = A[fbt] if rnd.random() < 0.5 else B[fbt]
        m["fb"] += 1
        if fk.get("killer"):
            m["players"][fk["killer"]] += 1
        if wp in LONG:
            m["sniper"] += 1
        s = fk.get("seconds")
        if s is not None and s >= 0:
            m["secs"].append(s)
    return A, B


print(f"  {'指标':<14} {'S1 内部分半':>12} {'S1->S2 跨赛段':>14} {'与胜率相关':>11}")
for name, fn in cands:
    vals = []
    for s in range(10):
        A, B = half_stats(s)
        xs, ys = [], []
        for t in A:
            if t not in B:
                continue
            a, b = fn(A[t]), fn(B[t])
            if a is not None and b is not None:
                xs.append(a)
                ys.append(b)
        rr = corr(xs, ys)
        if rr is not None:
            vals.append(rr)
    half = st.mean(vals) if vals else float("nan")
    full = 2 * half / (1 + half) if vals and half > -1 else float("nan")

    xs, ys = [], []
    for t in both:
        a, b = fn(S1[t]), fn(S2[t])
        if a is not None and b is not None:
            xs.append(a)
            ys.append(b)
    cross = corr(xs, ys)

    wx, wy = [], []
    for t in both:
        a = fn(S1[t])
        if a is not None:
            wx.append(a)
            wy.append(100 * S1[t]["win"] / S1[t]["n"])
    rc = corr(wx, wy)
    print(f"  {name:<14} {full:>+12.3f} {(cross if cross else float('nan')):>+14.3f} "
          f"{(rc if rc else float('nan')):>+11.3f}")

print()
print("=" * 76)
print("D. 各赛区 S1 / S2 最高与最低（首杀率，≥150 回合）")
print("=" * 76)
REG = {"Americas": "美洲", "China": "中国", "EMEA": "EMEA", "Pacific": "太平洋"}
# 用 site_v3 的 event 索引做分区（赛事名里有赛区）
R2, EV = d["rounds"], D["events"]
TEAMIDX = {n: i for i, n in enumerate(D["teams"])}
agg = defaultdict(lambda: [0, 0])
for r in R2:
    e = EV[r[0]]
    if "Stage 1" in e:
        reg, stg = e.split()[1], "S1"
    elif "Stage 2" in e:
        reg, stg = e.split()[1], "S2"
    else:
        continue
    for t in (r[2], r[3]):
        if t < 0:
            continue
        k = (reg, stg, D["teams"][t])
        agg[k][0] += 1
        if r[5] == t:
            agg[k][1] += 1

for reg, zh in REG.items():
    out = []
    for stg in ("S1", "S2"):
        pool = [(nm, 100 * fb / n, n) for (rr, ss, nm), (n, fb) in agg.items()
                if rr == reg and ss == stg and n >= 150]
        pool.sort(key=lambda x: -x[1])
        out.append((stg, pool))
    print(f"  {zh}:")
    for stg, pool in out:
        if not pool:
            continue
        top = ", ".join(f"{n} {v:.0f}%" for n, v, _ in pool[:3])
        bot = ", ".join(f"{n} {v:.0f}%" for n, v, _ in pool[-3:])
        print(f"    {stg}  高: {top}")
        print(f"         低: {bot}")
