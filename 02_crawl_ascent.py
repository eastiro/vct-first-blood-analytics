"""Crawl every Ascent replay at Champions 2026 and store normalised records.

Each replay yields, per round: attacking side, buy-phase loadouts, and the full
kill timeline with minimap coordinates. We keep only what the analysis needs and
write it as JSONL so a re-run can resume.

Rate limit: one request at a time with a pause, per VLR's stated wishes.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402
from vlrdevapi._series.replay.models import ReplayEventType  # noqa: E402

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MANIFEST = BASE / "_cache" / "ascent_manifest.json"
OUTDIR = BASE / "data"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "ascent_rounds.jsonl"

PAUSE = 1.2          # seconds between requests


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print(f"manifest entries: {len(manifest)}")

    done: set[tuple[int, int]] = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done.add((rec["series_id"], rec["game_id"]))
        print(f"already crawled: {len(done)}")

    c = v.VLRClient(trust_env=False)

    with OUT.open("a", encoding="utf-8") as fh:
        for i, entry in enumerate(manifest, 1):
            key = (entry["series_id"], entry["game_id"])
            if key in done:
                print(f"  [{i}/{len(manifest)}] skip (cached)")
                continue

            label = f"{entry['teams']} ({entry['phase']})"
            try:
                rep = c.series.replay(entry["series_id"], entry["game_id"])
            except Exception as exc:
                print(f"  [{i}/{len(manifest)}] FAIL {label}: {type(exc).__name__}")
                time.sleep(PAUSE)
                continue

            rounds = rep.rounds or []
            if not rounds:
                print(f"  [{i}/{len(manifest)}] empty {label}")
                time.sleep(PAUSE)
                continue

            n_kills = 0
            for rd in rounds:
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
                n_kills += len(kills)

                fh.write(json.dumps({
                    "series_id": entry["series_id"],
                    "game_id": entry["game_id"],
                    "phase": entry["phase"],
                    "teams": entry["teams"],
                    "map": "Ascent",
                    "round": rd.round_number,
                    "attacking": rd.attacking,
                    "boom_at": getattr(rd, "boom_at", None),
                    "loadouts": [
                        {"name": ld.name, "team": ld.team, "agent": ld.agent,
                         "weapon": ld.weapon, "armor": str(ld.armor),
                         "spent": ld.spent, "left": ld.credits_left}
                        for ld in (rd.loadouts or [])
                    ],
                    "kills": kills,
                }, ensure_ascii=False) + "\n")
            fh.flush()

            print(f"  [{i}/{len(manifest)}] OK   {label:<44} "
                  f"rounds={len(rounds):>2} kills={n_kills}")
            time.sleep(PAUSE)

    total = sum(1 for _ in OUT.open(encoding="utf-8"))
    print(f"\nwrote {total} round-rows -> {OUT}")


if __name__ == "__main__":
    main()
