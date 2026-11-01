"""Build the v5 payload: v3 + economy + player-level first bloods.

Per-round flat row (21 ints):
  0  ev       event index
  1  map      map index
  2  atkT     attacking team index
  3  defT     defending team index
  4  winT     team index that won the round
  5  killT    team index that got the first blood
  6  agent    agent index of the first-blood killer
  7  cause    cause index (weapon or ability)
  8  sec      round-clock seconds at the first blood (-1 unknown)
  9  x        first-blood victim X on the 1024 grid (-1 no coord)
 10  y        first-blood victim Y
 11  traded   1 traded back within TRADE_WINDOW, 0 not, -1 unknown
 12  compA    comp id of the first-blood team (-1 unknown)
 13  compB    comp id of the other team
 14  spendAtk attacking team credits spent this round (-1 no loadouts)
 15  spendDef defending team credits spent
 16  buyAtk   0 eco (<=1 long gun) / 1 half (2-3) / 2 full (>=4)  (-1 unknown)
 17  buyDef   同上
 18  rno      round number within the map (1-based; 1 and 13 are pistols)
 19  pkill    player index of the first-blood killer (-1 unknown)
 20  g        game index (one per map played; links rounds inside the same map)
 21  gunsAtk  attacking team long-gun count (rifles + snipers, 0-5)
 22  gunsDef  defending team long-gun count

Also emits:
  "players" : [{n: name, t: teamIdx}]   first-blood killers actually seen
  "comps"   : [[agentIdx x5], ...]
  "metaTop" : {mapIdx: [agentIdx x7]}

Buy class comes from the WEAPONS actually held, not from credits spent.
Spend is contaminated by gun retention: a team that keeps five Vandals from
the previous round spends ~0 but is fully armed. Verified by round 1 (pistol)
having a 0.0% long-gun rate in this dataset.

Long guns = Vandal, Phantom, Guardian, Bulldog, Odin, Operator, Outlaw, Marshal.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
SRC = BASE / "data" / "rounds_all.jsonl"
OUT = BASE / "data" / "site_v5.json"
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
# 次级队判定：只在一个赛事出现、且回合数低于这个阈值
FEEDER_MAX_ROUNDS = 400

LONG_GUNS = {"vandal", "phantom", "guardian", "bulldog",
             "odin", "operator", "outlaw", "marshal"}

GEOM_NOTE = (
    "vlr.gg 上没有 VCT 中国赛区（第一 / 第二赛段）的 2D 回放："
    "该赛区的比赛页面直接写着 \u201cNo 2D replay available for this match\u201d。"
    "这不是抓取错误\u2014\u2014同样在上海举办的全球冠军赛 2026 就有完整回放。"
    "中国赛区仍有击杀、英雄、武器、时间、补枪、转化率数据，只缺位置坐标和经济数据，"
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


def buy_of(team_guns: int) -> int:
    if team_guns < 0:
        return -1
    if team_guns >= 4:
        return 2
    if team_guns >= 2:
        return 1
    return 0


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

    # 次级队（挑战者队）识别。
    # 第二赛段起各赛区引入挑战者队参与季后赛席位争夺，它们只出现在一个赛事、
    # 而且只打季后赛（phase 里没有 Week N）。
    #
    # 但「是次级队」不等于「该剔除」：打进胜者组前 4（Upper Semifinals 及以后）
    # 的队伍是真的打上来了，样本也有几百回合，应当保留。
    # 只剔除「首轮就出局」的 —— 它们通常只有 88–250 回合，没人会分析。
    # 实测：14 支次级队里 4 支进了前 4（Enterprise / Sharper / Fire Flux / Joblife），
    # 其余 10 支首轮出局（含 M80 仅 88 回合）。
    DEEP_PHASES = {
        "Upper Semifinals", "Upper Final",
        "Upper Quarterfinals", "Lower Final", "Grand Final",
    }
    _team_events: dict[str, set] = defaultdict(set)
    _team_deep: dict[str, int] = defaultdict(int)
    for r in rows:
        t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
        is_deep = (r.get("phase") or "") in DEEP_PHASES
        for t in (t1, t2):
            if t:
                _team_events[t].add(r["event"])
                if is_deep:
                    _team_deep[t] += 1
    feeder = {
        t for t in teams
        if len(_team_events[t]) == 1
        and team_rounds[t] < FEEDER_MAX_ROUNDS
        and _team_deep[t] == 0          # 只剔除首轮出局的
    }
    kept_deep = {
        t for t in teams
        if len(_team_events[t]) == 1
        and team_rounds[t] < FEEDER_MAX_ROUNDS
        and _team_deep[t] > 0           # 打进前 4 的次级队，保留
    }

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

    per_map_agent = defaultdict(Counter)
    for r in rows:
        for ld in r.get("loadouts") or []:
            if ld.get("agent"):
                per_map_agent[r["map"]][ld["agent"].lower()] += 1
    meta_top = {map_idx[mp]: [ag_idx[a] for a, _ in c.most_common(META_SIZE)]
                for mp, c in per_map_agent.items()}

    # player registry: first-blood killers only, keyed by (name, team)
    player_ids: dict[tuple[str, str], int] = {}
    players: list[dict] = []

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

    out_rows = []
    stat = Counter()
    econ_unknown = 0
    game_ids: dict[tuple[int, int], int] = {}

    # 预扫：按 (series, game, team) 从击杀流收集每个选手用过的英雄。
    # 用于给没有 loadouts 的赛区（中国）补阵容。
    _seen = defaultdict(lambda: defaultdict(set))   # key -> player -> agents
    for r in rows:
        key = (r["series_id"], r["game_id"])
        for k in r.get("kills") or []:
            for role in ("killer", "victim"):
                nm = k.get(role)
                ag = k.get(f"{role}_agent")
                tm = k.get(f"{role}_team")
                if nm and ag and tm:
                    _seen[key + (tm,)][nm].add(ag.lower())
    game_comp: dict[tuple[int, int, str], set[str]] = {}
    for key, _players in _seen.items():
        if len(_players) < 5:
            continue
        # 每个选手取唯一英雄；有多个（跨图/异常）就跳过这支队
        ags = set()
        ok = True
        for nm, agset in _players.items():
            if len(agset) != 1:
                ok = False
                break
            ags |= agset
        if ok and len(ags) == 5:
            game_comp[key] = ags

    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        gkey = (r["series_id"], r["game_id"])
        if gkey not in game_ids:
            game_ids[gkey] = len(game_ids)
        g_i = game_ids[gkey]
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
        by_spend = defaultdict(int)
        by_guns = defaultdict(int)
        for ld in r.get("loadouts") or []:
            if ld.get("agent"):
                by_tag[ld["team"]].append(ld["agent"].lower())
            full_name = TAGMAP.get(ld["team"], ld["team"])
            by_spend[full_name] += ld.get("spent") or 0
            if (ld.get("weapon") or "").strip().lower() in LONG_GUNS:
                by_guns[full_name] += 1
        comp_by_name = {}
        for tag, ags in by_tag.items():
            name = TAGMAP.get(tag, tag)
            if len(ags) == 5:
                comp_by_name[name] = comp_id(ags)

        # 中国赛区没有 loadouts（vlr.gg 不给），但击杀流里每个选手都带英雄。
        # 一张图内不能换英雄，所以整张图只出现 5 个选手就足以拼出阵容。
        # 先用本回合 loadouts；缺失时回落到「本场（series+game）该队的击杀流阵容」。
        if len(comp_by_name) < 2:
            for name in (t1, t2):
                if name in comp_by_name:
                    continue
                ags = game_comp.get((r["series_id"], r["game_id"], name))
                if ags and len(ags) == 5:
                    comp_by_name[name] = comp_id(sorted(ags))

        comp_a = comp_by_name.get(kill_name, -1)
        other_name = t1 if kill_name == t2 else t2
        comp_b = comp_by_name.get(other_name, -1)

        tr = traded_state(r, fk)

        # buy class: only trustworthy when both teams' loadouts are present
        def_name = t2 if atk == t1 else t1
        if len(by_spend) == 2 and atk in by_spend and def_name in by_spend:
            s_atk, s_def = by_spend[atk], by_spend[def_name]
            g_atk, g_def = by_guns.get(atk, 0), by_guns.get(def_name, 0)
        else:
            s_atk = s_def = g_atk = g_def = -1
        if s_atk < 0:
            econ_unknown += 1
        e_atk, e_def = buy_of(g_atk), buy_of(g_def)

        rno = r.get("round")
        rno = int(rno) if isinstance(rno, int) else -1

        out_rows.append([
            ev_idx[r["event"]], map_idx[r["map"]],
            atk_i, def_i, win_i, kill_i,
            ag_idx.get((fk.get("killer_agent") or "").lower(), 0),
            ca_idx.get((fk.get("cause") or "").strip(), 0),
            int(sec) if sec is not None else -1,
            x, y, tr, comp_a, comp_b,
            s_atk, s_def, e_atk, e_def, rno,
            player_id(fk.get("killer") or "", kill_name),
            g_i, g_atk, g_def,
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
            "has_econ": any(r[16] >= 0 for r in sub),
        }

    econ_rows = [r for r in out_rows if r[16] >= 0]

    payload = {
        "meta": {
            "version": 5,
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
            "feeder_teams": len(feeder),
            "feeder_kept": len(kept_deep),
            "feeder_max_rounds": FEEDER_MAX_ROUNDS,
            "players": len(players),
            "games": len(game_ids),
            "econ_rows": len(econ_rows),
            "buy_rule": "buy class from long guns held: <=1 eco / 2-3 half / >=4 full",
            "long_guns": sorted(LONG_GUNS),
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
        "comps": comps,
        "metaTop": {str(k): v for k, v in meta_top.items()},
        "teamMeta": team_meta(teams),
        "feeder": sorted(feeder),
        "feederKept": sorted(kept_deep),
        "players": players,
        "rounds": out_rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    size = OUT.stat().st_size

    print(f"-> {OUT} ({size/1e6:.2f} MB)")
    print(f"   events {len(events)} · maps {len(maps)} · teams {len(teams)} "
          f"· agents {len(agents)} · causes {len(causes)} · comps {len(comps)} "
          f"· players {len(players)} · games {len(game_ids)}")
    print(f"\n   === per event ===")
    for e in events:
        d = per_event[e]
        geo = "geo" if d["has_geometry"] else "NO geo"
        econ = "econ" if d["has_econ"] else "NO econ"
        print(f"   {EVENT_SHORT.get(e, e):<12} {d['rounds']:>5} rounds "
              f"{d['maps']:>4} maps  fb->win {d['fb_to_win_pct']}%  {geo}  {econ}")
    print(f"\n   === headline ===")
    print(f"   first blood -> win   : {100*won/fb:.1f}%  (n={fb})")
    print(f"   traded               : {100*len(traded)/fb:.1f}% of all FB")
    print(f"     traded   -> win    : {100*tw/len(traded):.1f}%")
    print(f"     untraded -> win    : {100*uw/len(untraded):.1f}%")
    print(f"     gap                : {100*uw/len(untraded) - 100*tw/len(traded):+.1f} pp")
    print(f"   buy rows             : {len(econ_rows)} / {fb} "
          f"({100*len(econ_rows)/fb:.1f}%)  unknown {econ_unknown}")

    # sanity: relative spend beats absolute spend (Roux replication)
    tab = defaultdict(lambda: [0, 0])
    for r in econ_rows:
        s_atk, s_def = r[14], r[15]
        atk_t, def_t = r[2], r[3]
        for team, mine, theirs in ((atk_t, s_atk, s_def), (def_t, s_def, s_atk)):
            b = (mine - theirs) // 5000
            b = max(-3, min(3, b))
            tab[b][0] += 1
            if r[4] == team:
                tab[b][1] += 1
    print("\n   === spend gap (5k bands) -> round win% ===")
    for b in sorted(tab):
        a, w = tab[b]
        if a < 100:
            continue
        print(f"   {b*5:+3d}k..{b*5+5:+3d}k  n={a:5d}  win {100*w/a:.1f}%")


if __name__ == "__main__":
    main()
