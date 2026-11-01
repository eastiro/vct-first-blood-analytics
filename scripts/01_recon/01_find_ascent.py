"""Find every Ascent map played at Champions 2026 (Shanghai).

Writes a manifest of (series_id, game_id) so the crawl step is resumable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402

EVENT_ID = 2766
OUT = Path(r"D:\好玩的项目\vct-first-blood-analytics\_cache\ascent_manifest.json")
TARGET_MAP = "Ascent"


def main() -> None:
    c = v.VLRClient(trust_env=False)
    matches = c.event.matches(EVENT_ID).matches
    print(f"matches in event: {len(matches)}")

    found = []
    for i, m in enumerate(matches, 1):
        mid = m.match_id
        phase = getattr(m, "phase", "")
        teams = getattr(m, "teams", [])
        label = " vs ".join(getattr(t, "name", "?") for t in teams)
        try:
            info = c.series.info(mid)
        except Exception as exc:
            print(f"  [{i:>2}/{len(matches)}] {mid} ERR {type(exc).__name__}")
            continue

        games = getattr(info, "games", []) or []
        for g in games:
            if not g.played:
                continue
            if (g.map_name or "").lower() == TARGET_MAP.lower():
                found.append({
                    "series_id": mid,
                    "game_id": g.game_id,
                    "phase": phase,
                    "teams": label,
                    "score1": g.team1_score,
                    "score2": g.team2_score,
                    "duration": g.duration_seconds,
                })
                print(f"  [{i:>2}/{len(matches)}] {phase:<14} {label:<34} "
                      f"{TARGET_MAP} {g.team1_score}-{g.team2_score}")
                break
        else:
            print(f"  [{i:>2}/{len(matches)}] {phase:<14} {label:<34} -")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAscent maps found: {len(found)}")
    print(f"manifest -> {OUT}")


if __name__ == "__main__":
    main()
