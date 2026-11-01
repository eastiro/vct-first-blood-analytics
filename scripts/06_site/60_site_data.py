"""Build the static payload for the first-blood site (flat, filterable).

Version 2: instead of pre-aggregating, emit one compact row per round so the
browser can filter by ANY combination of event / map / team / agent and
recompute every number client-side.

Shape of data/site.json
-----------------------
{
  "meta"   : {...totals and provenance...},
  "dict"   : {
     "events": ["Masters London 2026", ...],
     "maps"  : ["Sunset", ...],
     "teams" : ["Gen.G", ...],
     "agents": ["neon", ...],
     "causes": ["Vandal", ...]
  },
  "zh"     : {"events": {...}, "maps": {...}, "agents": {...}, "causes": {...}},
  "rounds" : [[ev,map,atkT,defT,winT,killT,agent,cause,sec,x,y], ...]
}

`rounds` row layout (11 small ints; -1 means absent):
  0 ev      event index
  1 map     map index
  2 atkT    attacking team index
  3 defT    defending team index
  4 winT    team index that won the round
  5 killT   team index that got the first blood
  6 agent   agent index of the first-blood killer
  7 cause   cause index (weapon or ability)
  8 sec     seconds on the round clock at the first blood
  9 x       first-blood victim X on the 1024 minimap grid (-1 if none)
 10 y       first-blood victim Y

A round always has a first blood, a winner, and an attacking side, so the
client never has to guard for missing values.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
SRC = BASE / "data" / "rounds.jsonl"
OUT = BASE / "data" / "site.json"
ZH = json.loads((BASE / "_cache" / "zh_names.json").read_text(encoding="utf-8"))

EVENT_ORDER = ["Masters London 2026", "VCT Americas Stage 2", "VCT EMEA Stage 2",
               "VCT China Stage 2", "VCT Pacific Stage 2"]
EVENT_ZH = {
    "Masters London 2026": "伦敦大师赛 2026",
    "VCT Americas Stage 2": "VCT 美洲 第二赛段",
    "VCT EMEA Stage 2": "VCT EMEA 第二赛段",
    "VCT China Stage 2": "VCT 中国 第二赛段",
    "VCT Pacific Stage 2": "VCT 太平洋 第二赛段",
}
EVENT_SHORT = {
    "Masters London 2026": "伦敦大师赛",
    "VCT Americas Stage 2": "美洲 S2",
    "VCT EMEA Stage 2": "EMEA S2",
    "VCT China Stage 2": "中国 S2",
    "VCT Pacific Stage 2": "太平洋 S2",
}
MIN_TEAM_ROUNDS = 30          # teams below this are folded into "其他队伍"


def first_kill(r: dict) -> dict | None:
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def on_map(k: dict) -> bool:
    try:
        x, y = float(k["pos_x"]), float(k["pos_y"])
    except (KeyError, TypeError, ValueError):
        return False
    return 0.0 <= x <= 1024.0 and 0.0 <= y <= 1024.0


def zh_agent(k: str) -> str:
    return ZH["agents"].get((k or "").lower(), k or "?")


def zh_cause(c: str) -> str:
    c = (c or "").strip()
    if not c:
        return "未知"
    low = c.lower()
    if low in ZH["weapons"]:
        return ZH["weapons"][low]
    if low in ZH["abilities"]:
        return ZH["abilities"][low]
    return c


def zh_map(m: str) -> str:
    return ZH.get("maps", {}).get((m or "").lower(), m or "?")


def main() -> None:
    rows = []
    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    print(f"round rows: {len(rows)}")

    # ---- which teams survive the minimum-rounds cut --------------------
    team_rounds: Counter = Counter()
    for r in rows:
        t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
        team_rounds[t1] += 1
        team_rounds[t2] += 1
    kept = {t for t, n in team_rounds.items() if n >= MIN_TEAM_ROUNDS}
    print(f"teams: {len(team_rounds)} total, {len(kept)} kept (>= {MIN_TEAM_ROUNDS} rounds)")

    # ---- dictionaries --------------------------------------------------
    events = [e for e in EVENT_ORDER if any(r["event"] == e for r in rows)]
    ev_idx = {e: i for i, e in enumerate(events)}
    maps = sorted({r["map"] for r in rows})
    map_idx = {m: i for i, m in enumerate(maps)}
    teams = sorted(kept)
    folded = {t for t in team_rounds if t not in kept}
    if folded:
        teams = teams + ["其他队伍"]
    team_idx = {t: i for i, t in enumerate(teams)}
    other = team_idx.get("其他队伍", -1)
    if folded:
        print(f"folded into 其他队伍: {sorted(folded)}")

    agents_c: Counter = Counter()
    causes_c: Counter = Counter()
    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        agents_c[(fk.get("killer_agent") or "").lower()] += 1
        causes_c[(fk.get("cause") or "").strip()] += 1
    agents = [a for a, _ in agents_c.most_common()]
    causes = [c for c, _ in causes_c.most_common()]
    ag_idx = {a: i for i, a in enumerate(agents)}
    ca_idx = {c: i for i, c in enumerate(causes)}

    # ---- emit rows -----------------------------------------------------
    out_rows: list[list[int]] = []
    skipped_no_fb = 0
    for r in rows:
        fk = first_kill(r)
        if not fk:
            skipped_no_fb += 1
            continue

        t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
        atk_name = r.get("attacking") or ""
        # the two teams of this map, by index
        t1i = team_idx.get(t1, other)
        t2i = team_idx.get(t2, other)
        atk_i = t1i if atk_name == t1 else t2i
        def_i = t2i if atk_name == t1 else t1i

        win_name = r.get("winner_team") or ""
        win_i = t1i if win_name == t1 else t2i if win_name == t2 else other

        kill_name = fk.get("killer_team") or ""
        kill_i = t1i if kill_name == t1 else t2i if kill_name == t2 else other

        sec = fk.get("seconds")
        if on_map(fk):
            x, y = int(round(float(fk["pos_x"]))), int(round(float(fk["pos_y"])))
        else:
            x = y = -1

        out_rows.append([
            ev_idx[r["event"]],
            map_idx[r["map"]],
            atk_i,
            def_i,
            win_i,
            kill_i,
            ag_idx.get((fk.get("killer_agent") or "").lower(), 0),
            ca_idx.get((fk.get("cause") or "").strip(), 0),
            int(sec) if sec is not None else -1,
            x,
            y,
        ])

    # ---- totals used by the header -------------------------------------
    fb = len(out_rows)
    won = sum(1 for row in out_rows if row[4] == row[5])
    geo = sum(1 for row in out_rows if row[9] >= 0)

    dists = []
    for r in rows:
        fk = first_kill(r)
        if fk and fk.get("distance"):
            dists.append(float(fk["distance"]) * 0.1395)
    dists.sort()
    median_d = round(dists[len(dists) // 2], 1) if dists else None

    payload = {
        "meta": {
            "rounds": len(rows),
            "maps_played": len({(r["series_id"], r["game_id"]) for r in rows}),
            "first_bloods": fb,
            "fb_to_win_pct": round(100.0 * won / fb, 1) if fb else None,
            "median_fb_distance_m": median_d,
            "distance_samples": len(dists),
            "geometry_rounds": geo,
            "skipped_no_first_blood": skipped_no_fb,
            "min_team_rounds": MIN_TEAM_ROUNDS,
            "teams_total": len(team_rounds),
            "teams_shown": len(kept),
            "geometry_note": (
                "vlr.gg 上没有 VCT 中国赛区的 2D 回放：该赛区只有击杀记录，"
                "没有坐标。中国赛区仍计入所有英雄 / 武器 / 时间 / 转化率统计，"
                "只是不出现在地图打点上。"
            ),
        },
        "dict": {
            "events": events,
            "maps": maps,
            "teams": teams,
            "agents": agents,
            "causes": causes,
        },
        "zh": {
            "events": {e: EVENT_ZH.get(e, e) for e in events},
            "eventsShort": {e: EVENT_SHORT.get(e, e) for e in events},
            "maps": {m: zh_map(m) for m in maps},
            "agents": {a: zh_agent(a) for a in agents},
            "causes": {c: zh_cause(c) for c in causes},
        },
        "rounds": out_rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")

    size = OUT.stat().st_size
    print(f"-> {OUT} ({size/1e6:.2f} MB)")
    print(f"   events {len(events)} · maps {len(maps)} · teams {len(teams)} "
          f"· agents {len(agents)} · causes {len(causes)}")
    print(f"   rounds {len(out_rows)} · with geometry {geo} · median dist {median_d} m")
    print("\n   top 12 teams by rounds:")
    for t, n in team_rounds.most_common(12):
        print(f"     {t[:28]:<28} {n:>5} rounds  {'kept' if t in kept else 'folded'}")


if __name__ == "__main__":
    main()
