"""Probe: China Stage 2 returned 0 rounds. Test alternate game id conventions."""
from __future__ import annotations

import os
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402
from vlrdevapi._series.replay.models import ReplayEventType  # noqa: E402


def probe(c, series_id: int, game_arg) -> None:
    try:
        rep = c.series.replay(series_id, game_arg)
    except Exception as exc:
        print(f"  game={game_arg!r:<8} ERR {type(exc).__name__}: {exc}")
        return
    print(f"  game={game_arg!r:<8} rounds={rep.num_rounds:<3} "
          f"team1={rep.team1!r} team2={rep.team2!r} game_id={rep.game_id}")


def main() -> None:
    c = v.VLRClient(trust_env=False)

    print("=== China Stage 2 series 701025 ===")
    for arg in (1, 2, 3, 273938, 273939, 273940):
        probe(c, 701025, arg)

    print("\n=== China Stage 2, another series (random group match) ===")
    ms = c.event.matches(2978).matches
    print("  total matches:", len(ms))
    for m in ms[:6]:
        teams = " vs ".join(t.name for t in m.teams)
        print(f"   {m.match_id} {m.stage:<12} {teams}")
        for arg in (1, 2):
            probe(c, m.match_id, arg)
        print()

    print("\n=== compare: EMEA Stage 2 series 712803 with index args ===")
    for arg in (1, 2, 3):
        probe(c, 712803, arg)


if __name__ == "__main__":
    main()
