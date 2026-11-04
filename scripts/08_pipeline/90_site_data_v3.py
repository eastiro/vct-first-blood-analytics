"""Build the v4 site payload: 6 events incl. Champions Shanghai 2026.

Per-round flat row (17 ints):
  0 ev      event index
  1 map     map index
  2 atkT    attacking team index
  3 defT    defending team index
  4 winT    team index that won the round
  5 killT   team index that got the first blood
  6 agent   agent index of the first-blood killer
  7 cause   cause index (weapon or ability)
  8 sec     round-clock seconds at the first blood (-1 if unknown)
  9 x       first-blood victim X on the 1024 grid (-1 if off-map)
 10 y       first-blood victim Y
 11 traded  1 = traded back within TRADE_WINDOW, 0 = not, -1 = unknown
 12 compA   comp id of the team that got the first blood (-1 if unknown)
 13 compB   comp id of the other team
 14 snipe   1 = AWP-class first blood (Operator/Outlaw/Marshal)
            0 = a known non-AWP weapon, -1 = weapon unknown (no loadouts, e.g. China)
 15 pkill   player index of the first-blood killer (-1 unknown)
 16 vkill   player index of the first-blood VICTIM (-1 unknown)
            「尝试次数 = pkill 拿到 + vkill 被人拿」，两者合起来才能算
            一名选手参与了多少次首杀对决。

Also emits:
  "players" : [{"n": name, "t": teamIdx}, ...]
  "comps"   : [[agentIdx x5], ...]
  "metaTop" : {mapIdx: [agentIdx x7]}   top-7 agents per map, for Meta Fit
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
SRC = BASE / "data" / "rounds_all.jsonl"
OUT = BASE / "data" / "site_v3.json"
ZH = json.loads((BASE / "_cache" / "zh_names.json").read_text(encoding="utf-8"))
TAGMAP = json.loads((BASE / "_cache" / "tag_map.json").read_text(encoding="utf-8"))

EVENT_ORDER = [
    "VCT Americas Kickoff 2026",
    "VCT China Kickoff 2026",
    "VCT EMEA Kickoff 2026",
    "VCT Pacific Kickoff 2026",
    "Masters Santiago 2026",
    "VCT Americas Stage 1 2026",
    "VCT China Stage 1 2026",
    "VCT EMEA Stage 1 2026",
    "VCT Pacific Stage 1 2026",
    "Masters London 2026",
    "VCT Americas Stage 2",
    "VCT EMEA Stage 2",
    "VCT China Stage 2",
    "VCT Pacific Stage 2",
    "Champions Shanghai 2026",
]
EVENT_ZH = {
    "VCT Americas Kickoff 2026": "VCT 美洲 Kickoff 2026",
    "VCT China Kickoff 2026": "VCT 中国 Kickoff 2026",
    "VCT EMEA Kickoff 2026": "VCT EMEA Kickoff 2026",
    "VCT Pacific Kickoff 2026": "VCT 太平洋 Kickoff 2026",
    "Masters Santiago 2026": "圣地亚哥大师赛 2026",
    "VCT Americas Stage 1 2026": "VCT 美洲 第一赛段",
    "VCT China Stage 1 2026": "VCT 中国 第一赛段",
    "VCT EMEA Stage 1 2026": "VCT EMEA 第一赛段",
    "VCT Pacific Stage 1 2026": "VCT 太平洋 第一赛段",
    "Masters London 2026": "伦敦大师赛 2026",
    "VCT Americas Stage 2": "VCT 美洲 第二赛段",
    "VCT EMEA Stage 2": "VCT EMEA 第二赛段",
    "VCT China Stage 2": "VCT 中国 第二赛段",
    "VCT Pacific Stage 2": "VCT 太平洋 第二赛段",
    "Champions Shanghai 2026": "上海全球冠军赛 2026",
}
EVENT_SHORT = {
    "VCT Americas Kickoff 2026": "美洲 Kickoff",
    "VCT China Kickoff 2026": "中国 Kickoff",
    "VCT EMEA Kickoff 2026": "EMEA Kickoff",
    "VCT Pacific Kickoff 2026": "太平洋 Kickoff",
    "Masters Santiago 2026": "圣地亚哥大师赛",
    "VCT Americas Stage 1 2026": "美洲 S1",
    "VCT China Stage 1 2026": "中国 S1",
    "VCT EMEA Stage 1 2026": "EMEA S1",
    "VCT Pacific Stage 1 2026": "太平洋 S1",
    "Masters London 2026": "伦敦大师赛",
    "VCT Americas Stage 2": "美洲 S2",
    "VCT EMEA Stage 2": "EMEA S2",
    "VCT China Stage 2": "中国 S2",
    "VCT Pacific Stage 2": "太平洋 S2",
    "Champions Shanghai 2026": "上海冠军赛",
}

MIN_TEAM_ROUNDS = 20
TRADE_WINDOW = 5
META_SIZE = 7

GEOM_NOTE = (
    "vlr.gg 上没有 VCT 中国赛区（第一 / 第二赛段）的 2D 回放："
    "该赛区的比赛页面直接写着 \u201cNo 2D replay available for this match\u201d。"
    "这不是抓取错误\u2014\u2014同样在上海举办的全球冠军赛 2026 就有完整回放。"
    "中国赛区仍有击杀、英雄、武器、时间、补枪、转化率数据，只缺位置坐标，"
    "所以只出现在表格里，不出现在地图打点上。"
)


def derive_tag_map(rows) -> dict[str, str]:
    """从数据里自己推出 队伍缩写 -> 全名，补 _cache/tag_map.json 没覆盖的新队。

    每回合的 loadouts 里有 (球员, 队伍缩写)，kills 里有 (球员, 队伍全名)，
    用同一个球员把两边接起来，投票取多数。
    """
    votes: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        tag_of = {}
        for ld in r.get("loadouts") or []:
            if ld.get("name") and ld.get("team"):
                tag_of[ld["name"]] = ld["team"]
        if not tag_of:
            continue
        full_of = {}
        for k in r.get("kills") or []:
            if k.get("killer") and k.get("killer_team"):
                full_of[k["killer"]] = k["killer_team"]
            if k.get("victim") and k.get("victim_team"):
                full_of[k["victim"]] = k["victim_team"]
        for player, tag in tag_of.items():
            full = full_of.get(player)
            if full:
                votes[tag][full] += 1
    return {tag: c.most_common(1)[0][0] for tag, c in votes.items() if c}

SNIPE_GUNS = {"operator", "outlaw", "marshal"}


def killer_weapon(r, fk):
    """首杀者这一回合拿的枪。

    优先从 loadouts 里按玩家名对（那里是「本回合实际持有的武器」）；
    但中国赛区没有 loadouts，所以回落到击杀事件自带的 cause 字段 ——
    那一条记录的是「这次击杀用的是什么」，同样是武器名，
    且中国赛区有 36 种取值（含 Operator / Outlaw / Marshal），足够判断狙击首杀。
    """
    name = fk.get("killer")
    if name:
        for ld in r.get("loadouts") or []:
            if ld.get("name") == name:
                wp = (ld.get("weapon") or "").strip().lower()
                if wp:
                    return wp
    return (fk.get("cause") or "").strip().lower()


def team_meta(teams: list[str]) -> list[dict]:
    """队伍缩写 + 队标（来自 34_fetch_team_meta.py 的产出，缺失就留空）。"""
    p = BASE / "_cache" / "teams_meta.json"
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    out = []
    for t in teams:
        m = raw.get(t) or {}
        out.append({
            "tag": m.get("tag") or "",
            "logo": ("logos/" + m["file"]) if m.get("file") else "",
            "plate": bool(m.get("plate")),
            "plateLight": bool(m.get("plate_light")),
        })
    return out


def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def traded_state(r, fk):
    fk_sec = fk.get("seconds")
    killer = fk.get("killer")
    victim_team = fk.get("victim_team")
    if fk_sec is None or not killer or not victim_team:
        return -1
    for k in r["kills"]:
        if k is fk:
            continue
        sec = k.get("seconds")
        if sec is None or sec < fk_sec:
            continue
        if sec - fk_sec > TRADE_WINDOW:
            break
        if k.get("killer_team") == victim_team and k.get("victim") == killer:
            return 1
    return 0


def on_map(k):
    try:
        x, y = float(k["pos_x"]), float(k["pos_y"])
    except (KeyError, TypeError, ValueError):
        return False
    return 0.0 <= x <= 1024.0 and 0.0 <= y <= 1024.0


def main():
    rows = []
    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    print(f"round rows: {len(rows)}")

    # 补齐 tag_map 里没有的队伍缩写（新赛事会带新队）
    _derived = derive_tag_map(rows)
    _filled = {k: v for k, v in _derived.items() if k not in TAGMAP}
    if _filled:
        TAGMAP.update(_filled)
        print(f"tag_map: filled {len(_filled)} new tag(s): {_filled}")

    events = [e for e in EVENT_ORDER if any(r["event"] == e for r in rows)]
    ev_idx = {e: i for i, e in enumerate(events)}
    maps = sorted({r["map"] for r in rows})
    map_idx = {m: i for i, m in enumerate(maps)}

    ag_c = Counter()
    for r in rows:
        fk = first_kill(r)
        if fk and fk.get("killer_agent"):
            ag_c[fk["killer_agent"].lower()] += 1
        for ld in r.get("loadouts") or []:
            if ld.get("agent"):
                ag_c[ld["agent"].lower()] += 1
    agents = [a for a, _ in ag_c.most_common()]
    ag_idx = {a: i for i, a in enumerate(agents)}

    causes_c = Counter()
    for r in rows:
        fk = first_kill(r)
        if fk:
            causes_c[(fk.get("cause") or "").strip()] += 1
    causes = [c for c, _ in causes_c.most_common()]
    ca_idx = {c: i for i, c in enumerate(causes)}

    team_rounds = Counter()
    for r in rows:
        t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
        team_rounds[t1] += 1
        team_rounds[t2] += 1
    teams = sorted(t for t, n in team_rounds.items() if n >= MIN_TEAM_ROUNDS)
    team_idx = {t: i for i, t in enumerate(teams)}
    OTHER = -1

    comp_ids: dict[tuple, int] = {}
    comps: list[list[int]] = []

    def comp_id(agents_tuple):
        key = tuple(sorted(agents_tuple))
        if key in comp_ids:
            return comp_ids[key]
        cid = len(comps)
        comp_ids[key] = cid
        comps.append([ag_idx[a] for a in key])
        return cid

    players: list[dict] = []
    player_ids: dict[tuple[str, str], int] = {}

    def player_id(name: str, team: str):
        if not name:
            return -1
        key = (name, team)
        if key in player_ids:
            return player_ids[key]
        pid = len(players)
        player_ids[key] = pid
        players.append({"n": name, "t": team_idx.get(team, OTHER)})
        return pid

    per_map_agent = defaultdict(Counter)
    for r in rows:
        for ld in r.get("loadouts") or []:
            if ld.get("agent"):
                per_map_agent[r["map"]][ld["agent"].lower()] += 1
    meta_top = {map_idx[mp]: [ag_idx[a] for a, _ in c.most_common(META_SIZE)]
                for mp, c in per_map_agent.items()}

    out_rows = []
    stat = Counter()
    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
        t1i, t2i = team_idx.get(t1, OTHER), team_idx.get(t2, OTHER)
        atk = r.get("attacking") or ""
        atk_i = t1i if atk == t1 else t2i
        def_i = t2i if atk == t1 else t1i
        win = r.get("winner_team") or ""
        win_i = t1i if win == t1 else t2i if win == t2 else OTHER
        kill_name = fk.get("killer_team") or ""
        kill_i = t1i if kill_name == t1 else t2i if kill_name == t2 else OTHER

        sec = fk.get("seconds")
        x, y = (-1, -1)
        if on_map(fk):
            x = int(round(float(fk["pos_x"])))
            y = int(round(float(fk["pos_y"])))

        by_tag = defaultdict(list)
        for ld in r.get("loadouts") or []:
            if ld.get("agent"):
                by_tag[ld["team"]].append(ld["agent"].lower())
        comp_by_name = {}
        for tag, ags in by_tag.items():
            name = TAGMAP.get(tag, tag)
            if len(ags) == 5:
                comp_by_name[name] = comp_id(ags)
        comp_a = comp_by_name.get(kill_name, -1)
        other_name = t1 if kill_name == t2 else t2
        comp_b = comp_by_name.get(other_name, -1)

        tr = traded_state(r, fk)
        wp = killer_weapon(r, fk)
        snipe = 1 if wp in SNIPE_GUNS else (0 if wp else -1)

        out_rows.append([
            ev_idx[r["event"]], map_idx[r["map"]],
            atk_i, def_i, win_i, kill_i,
            ag_idx.get((fk.get("killer_agent") or "").lower(), 0),
            ca_idx.get((fk.get("cause") or "").strip(), 0),
            int(sec) if sec is not None else -1,
            x, y, tr, comp_a, comp_b,
            snipe, player_id(fk.get("killer") or "", kill_name),
            player_id(fk.get("victim") or "", fk.get("victim_team") or ""),
        ])
        stat["traded" if tr == 1 else "untraded" if tr == 0 else "unknown"] += 1

    fb = len(out_rows)
    won = sum(1 for row in out_rows if row[4] == row[5])
    traded = [row for row in out_rows if row[11] == 1]
    untraded = [row for row in out_rows if row[11] == 0]
    tw = sum(1 for r in traded if r[4] == r[5])
    uw = sum(1 for r in untraded if r[4] == r[5])

    per_event = {}
    for i, e in enumerate(events):
        sub = [r for r in out_rows if r[0] == i]
        w = sum(1 for r in sub if r[4] == r[5])
        maps_n = len({(x["series_id"], x["game_id"]) for x in rows if x["event"] == e})
        per_event[e] = {
            "rounds": len(sub),
            "maps": maps_n,
            "fb_to_win_pct": round(100*w/len(sub), 1) if sub else None,
            "has_geometry": any(r[9] >= 0 for r in sub),
        }

    payload = {
        "meta": {
            "version": 4,
            "rounds": len(rows),
            "first_bloods": fb,
            "maps_played": len({(r["series_id"], r["game_id"]) for r in rows}),
            "fb_to_win_pct": round(100*won/fb, 1) if fb else None,
            "traded_fb_pct": round(100*len(traded)/fb, 1) if fb else None,
            "traded_fb_to_win_pct": round(100*tw/len(traded), 1) if traded else None,
            "untraded_fb_to_win_pct": round(100*uw/len(untraded), 1) if untraded else None,
            "trade_window_sec": TRADE_WINDOW,
            "meta_size": META_SIZE,
            "comps": len(comps),
            "teams_shown": len(teams),
            "min_team_rounds": MIN_TEAM_ROUNDS,
            "per_event": per_event,
            "geometry_note": GEOM_NOTE,
        },
        "dict": {
            "events": events, "maps": maps, "teams": teams,
            "agents": agents, "causes": causes,
        },
        "zh": {
            "events": {e: EVENT_ZH.get(e, e) for e in events},
            "eventsShort": {e: EVENT_SHORT.get(e, e) for e in events},
            "maps": {m: ZH.get("maps", {}).get(m.lower(), m) for m in maps},
            "agents": {a: ZH["agents"].get(a, a) for a in agents},
            "causes": {c: (ZH["weapons"].get(c.lower())
                            or ZH["abilities"].get(c.lower()) or c) for c in causes},
        },
        "teamMeta": team_meta(teams),
        "players": players,
        "comps": comps,
        "metaTop": {str(k): v for k, v in meta_top.items()},
        "rounds": out_rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    size = OUT.stat().st_size

    print(f"-> {OUT} ({size/1e6:.2f} MB)")
    print(f"   events {len(events)} · maps {len(maps)} · teams {len(teams)} "
          f"· agents {len(agents)} · causes {len(causes)} · comps {len(comps)}")
    print(f"\n   === per event ===")
    for e in events:
        d = per_event[e]
        geo = "geo" if d["has_geometry"] else "NO geo"
        print(f"   {EVENT_SHORT.get(e, e):<12} {d['rounds']:>5} rounds "
              f"{d['maps']:>4} maps  fb->win {d['fb_to_win_pct']}%  {geo}")
    print(f"\n   === headline effects ===")
    print(f"   first blood -> win   : {100*won/fb:.1f}%  (n={fb})")
    print(f"   traded               : {100*len(traded)/fb:.1f}% of all FB")
    print(f"     traded   -> win    : {100*tw/len(traded):.1f}%")
    print(f"     untraded -> win    : {100*uw/len(untraded):.1f}%")
    print(f"     gap                : {100*uw/len(untraded) - 100*tw/len(traded):+.1f} pp")
    print(f"   unknown trade state  : {stat['unknown']}")


if __name__ == "__main__":
    main()
