"""Crawl first-blood data for the 2026 target events.

One HTTP request per (series, game) - the logs page renders the round
blocks for a single game, so the game id must be selected.

Two page layouts exist on vlr.gg:

  geometry     div.lg-map[data-map] carries the JSON blob: player map,
               per-event coordinates, alive snapshots, and buy-phase
               loadouts in .lg-mir.
  feed-only    (all VCT China events) the round blocks carry feed rows
               with clock / killer / victim / agents / weapon but no
               data-map, no coordinates, no loadouts.

Both are captured; `geometry` in each record says which.

Resumable: already-crawled (series_id, game_id) pairs are skipped.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from selectolax.lexbor import LexborHTMLParser  # noqa: E402

from vlrdevapi._series.replay.models import ReplayEventType  # noqa: E402
from vlrdevapi._series.replay.parser import parse_replay_data  # noqa: E402

BASE = Path(r"D:\好玩的项目\valorant-analytics")
# 默认沿用原路径；用 env 可以指向别的清单/输出，方便增量抓取
MANIFEST = Path(os.environ.get("VLR_MANIFEST", BASE / "_cache" / "manifest.json"))
OUTDIR = BASE / "data"
OUT = Path(os.environ.get("VLR_OUT", OUTDIR / "rounds.jsonl"))
FAILLOG = Path(os.environ.get("VLR_FAILLOG", BASE / "_cache" / "crawl_failures.jsonl"))

PAUSE = 1.1
TIMEOUT = 45.0
RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.vlr.gg/",
}


# --------------------------------------------------------------------------
# round winners: the fixed 24-cell strip above the game
# --------------------------------------------------------------------------
# `div.rnd-sq` cells come in pairs per round: index 2*(r-1) and 2*(r-1)+1.
# The cell carrying `mod-win` names the winning SIDE (`mod-t` = attack,
# `mod-ct` = defense); the round's band maps side -> team. Verified against
# the recorded map score, which is reconstructed exactly.

def _strip_winners(game) -> dict[int, str]:
    """Map round number -> winning side ('Attack'/'Defense')."""
    squares = game.css("div.rnd-sq")
    classes = [s.attributes.get("class") or "" for s in squares]
    out: dict[int, str] = {}
    for round_no in range(1, len(classes) // 2 + 1):
        base = 2 * (round_no - 1)
        for idx in (base, base + 1):
            if idx >= len(classes):
                continue
            cls = classes[idx]
            if "mod-win" not in cls:
                continue
            if "mod-ct" in cls:
                out[round_no] = "Defense"
            elif "mod-t" in cls:
                out[round_no] = "Attack"
    return out


def _band_sides(round_div) -> dict[str, str]:
    """Map side -> team name from one round's scoreboard band."""
    out: dict[str, str] = {}
    for el in round_div.css("span.lg-band-team"):
        cls = el.attributes.get("class") or ""
        name_el = el.css_first("span.lg-band-name")
        if name_el is None:
            continue
        name = name_el.attributes.get("title") or _clean(name_el.text())
        if "mod-atk" in cls:
            out["Attack"] = name
        elif "mod-def" in cls:
            out["Defense"] = name
    return out


# --------------------------------------------------------------------------
# feed-only fallback parser (VCT China layout)
# --------------------------------------------------------------------------

def _clean(text: str) -> str:
    return " ".join((text or "").split())


def _clock_seconds(clock: str) -> int | None:
    try:
        m, s = clock.split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def _parse_feedonly_round(round_div, team_by_side: dict[str, str]) -> dict:
    """Parse one round block that has feed rows but no data-map."""
    rows = round_div.css("div.lg-row")
    kills: list[dict] = []
    for row in rows:
        cls = row.attributes.get("class") or ""
        clock_el = row.css_first("span.lg-clock")
        clock = _clean(clock_el.text()) if clock_el else ""

        if "mod-kill" not in cls:
            continue

        sides = row.css("div.lg-side")
        killer = victim = None
        killer_agent = victim_agent = ""
        killer_side = victim_side = ""

        for side in sides:
            side_cls = side.attributes.get("class") or ""
            player = side.css_first(".lg-player")
            if player is None:
                continue
            pcls = player.attributes.get("class") or ""
            name_el = player.css_first(".lg-player-name")
            name = (name_el.attributes.get("title") or _clean(name_el.text())) if name_el else ""
            agent_el = player.css_first("img.lg-agent")
            agent = agent_el.attributes.get("title", "") if agent_el else ""
            is_victim = "mod-victim" in pcls
            is_atk = "mod-atk" in pcls
            ps = "Attack" if is_atk else "Defense"
            if is_victim:
                victim, victim_agent, victim_side = name, agent, ps
            else:
                killer, killer_agent, killer_side = name, agent, ps
            _ = side_cls

        src_el = row.css_first("span.lg-source")
        cause = src_el.attributes.get("title", "") if src_el else ""

        kills.append({
            "seq": int(row.attributes.get("data-ev") or 0),
            "clock": clock,
            "seconds": _clock_seconds(clock),
            "killer": killer,
            "killer_agent": (killer_agent or "").lower(),
            "killer_team": team_by_side.get(killer_side, ""),
            "victim": victim,
            "victim_agent": (victim_agent or "").lower(),
            "victim_team": team_by_side.get(victim_side, ""),
            "cause": cause,
            "pos_x": None, "pos_y": None,
            "from_x": None, "from_y": None,
            "distance": None,
        })

    return {
        "round": int(round_div.attributes.get("data-round") or 0),
        "attacking": team_by_side.get("Attack", ""),
        "geometry": False,
        "loadouts": [],
        "kills": kills,
    }


def _side_teams(round_div) -> dict[str, str]:
    """Map 'Attack'/'Defense' -> team name from the round's scoreboard band."""
    out: dict[str, str] = {}
    for el in round_div.css("span.lg-band-team"):
        cls = el.attributes.get("class") or ""
        name_el = el.css_first("span.lg-band-name")
        if name_el is None:
            continue
        name = name_el.attributes.get("title") or _clean(name_el.text())
        if "mod-atk" in cls:
            out["Attack"] = name
        elif "mod-def" in cls:
            out["Defense"] = name
    return out


# --------------------------------------------------------------------------
# geometry parser (wraps vlrdevapi's parse_replay_data)
# --------------------------------------------------------------------------

def _parse_geometry_rounds(dom, game_id: int) -> list[dict] | None:
    rep = parse_replay_data(dom, game_id)
    if not rep.rounds:
        return None
    game = dom.css_first(f'div.vm-stats-game[data-game-id="{game_id}"]')
    winners = _strip_winners(game) if game is not None else {}
    bands: dict[int, dict[str, str]] = {}
    if game is not None:
        for rd_div in game.css("div.lg-round"):
            rn = int(rd_div.attributes.get("data-round") or 0)
            bands[rn] = _band_sides(rd_div)

    out: list[dict] = []
    for rd in rep.rounds:
        kills = []
        for ev in rd.events:
            if ev.type is not ReplayEventType.KILL:
                continue
            kills.append({
                "seq": ev.seq,
                "clock": ev.clock,
                "seconds": ev.seconds,
                "killer": ev.actor.name if ev.actor else None,
                "killer_agent": ev.actor.agent if ev.actor else None,
                "killer_team": ev.actor.team if ev.actor else None,
                "victim": ev.victim.name if ev.victim else None,
                "victim_agent": ev.victim.agent if ev.victim else None,
                "victim_team": ev.victim.team if ev.victim else None,
                "cause": ev.cause,
                "pos_x": ev.pos_x, "pos_y": ev.pos_y,
                "from_x": ev.from_x, "from_y": ev.from_y,
                "distance": ev.distance_units,
            })
        side = winners.get(rd.round_number, "")
        sides = bands.get(rd.round_number, {})
        out.append({
            "round": rd.round_number,
            "attacking": rd.attacking,
            "winner_side": side,
            "winner_team": sides.get(side, ""),
            "geometry": True,
            "boom_at": rd.boom_at,
            "loadouts": [
                {"name": ld.name, "team": ld.team, "agent": ld.agent,
                 "weapon": ld.weapon, "armor": str(ld.armor),
                 "spent": ld.spent, "left": ld.credits_left}
                for ld in (rd.loadouts or [])
            ],
            "kills": kills,
        })
    return out


def _parse_feedonly_rounds(dom, game_id: int) -> list[dict] | None:
    game = dom.css_first(f'div.vm-stats-game[data-game-id="{game_id}"]')
    if game is None:
        return None
    round_divs = game.css("div.lg-round")
    if not round_divs:
        return None
    winners = _strip_winners(game)
    out = []
    for rd in round_divs:
        teams = _band_sides(rd)
        rec = _parse_feedonly_round(rd, teams)
        side = winners.get(rec["round"], "")
        rec["winner_side"] = side
        rec["winner_team"] = teams.get(side, "")
        if rec["kills"]:
            out.append(rec)
    return out or None


# --------------------------------------------------------------------------

def fetch(client: httpx.Client, url: str) -> str | None:
    for attempt in range(1, RETRIES + 1):
        try:
            r = client.get(url)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except Exception as exc:
            if attempt == RETRIES:
                print(f"      fetch error {type(exc).__name__}", flush=True)
        time.sleep(1.5 * attempt)
    return None


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print(f"manifest entries: {len(entries)}", flush=True)

    done: set[tuple[int, int]] = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    done.add((rec["series_id"], rec["game_id"]))
        print(f"already crawled: {len(done)}", flush=True)

    todo = [e for e in entries if (e["series_id"], e["game_id"]) not in done]
    print(f"to crawl: {len(todo)}", flush=True)

    n_geo = n_feed = n_fail = n_rounds = n_kills = 0

    with httpx.Client(trust_env=False, headers=HEADERS, timeout=TIMEOUT,
                      follow_redirects=True) as client, \
         OUT.open("a", encoding="utf-8") as fh, \
         FAILLOG.open("a", encoding="utf-8") as fh_fail:

        for i, e in enumerate(todo, 1):
            sid, gid = e["series_id"], e["game_id"]
            url = f"https://www.vlr.gg/{sid}?game={gid}&tab=logs"
            html = fetch(client, url)
            if html is None:
                n_fail += 1
                fh_fail.write(json.dumps(e) + "\n")
                fh_fail.flush()
                print(f"  [{i:>3}/{len(todo)}] FAIL {sid}/{gid} {e['map']}", flush=True)
                time.sleep(PAUSE)
                continue

            dom = LexborHTMLParser(html)
            rounds = _parse_geometry_rounds(dom, gid)
            layout = "geo"
            if rounds is None:
                rounds = _parse_feedonly_rounds(dom, gid)
                layout = "feed"
            if rounds is None:
                n_fail += 1
                fh_fail.write(json.dumps(e) + "\n")
                fh_fail.flush()
                print(f"  [{i:>3}/{len(todo)}] EMPTY {sid}/{gid} {e['map']}", flush=True)
                time.sleep(PAUSE)
                continue

            for rec in rounds:
                fh.write(json.dumps({
                    "event_id": e["event_id"],
                    "event": e["event"],
                    "region": e["region"],
                    "stage": e["stage"],
                    "phase": e["phase"],
                    "series_id": sid,
                    "game_id": gid,
                    "game_no": e["game_no"],
                    "map": e["map"],
                    "teams": e["teams"],
                    "date": e["match_date"],
                    "score": f"{e['score1']}-{e['score2']}",
                    **rec,
                }, ensure_ascii=False) + "\n")
            fh.flush()

            n_rounds += len(rounds)
            n_kills += sum(len(r["kills"]) for r in rounds)
            if layout == "geo":
                n_geo += 1
            else:
                n_feed += 1

            print(f"  [{i:>3}/{len(todo)}] {layout:<4} {e['event'][:18]:<18} "
                  f"{e['map']:<9} r={len(rounds):>2} k={sum(len(r['kills']) for r in rounds):>3} "
                  f"{e['teams'][:34]}", flush=True)
            time.sleep(PAUSE)

    print(f"\n=== done ===", flush=True)
    print(f"geometry games : {n_geo}", flush=True)
    print(f"feed-only games: {n_feed}", flush=True)
    print(f"failures       : {n_fail}", flush=True)
    print(f"rounds written : {n_rounds}", flush=True)
    print(f"kills written  : {n_kills}", flush=True)
    print(f"file           : {OUT} ({OUT.stat().st_size/1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
