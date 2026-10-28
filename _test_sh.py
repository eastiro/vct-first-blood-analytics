"""Test whether Shanghai Masters 2024 matches carry 2D replay data.

Steps:
  1. list the event's matches
  2. take one completed series
  3. fetch series.replay(series_id, game_id)
  4. report whether positions / weapons / agents come back
"""
from __future__ import annotations

import json
from pathlib import Path

import vlrdevapi as v

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache")
EVENT_ID = 1999


def main() -> None:
    c = v.VLRClient(trust_env=False)

    info = c.event.info(EVENT_ID)
    print(f"event: {info.name}  regions={getattr(info, 'regions', '?')}")
    print("attrs:", [n for n in info.model_fields])

    ms = c.event.matches(EVENT_ID)
    print(f"\ntop-level matches container: {type(ms).__name__}")
    print("attrs:", [n for n in dir(ms) if not n.startswith("_")])

    for attr in ("completed", "upcoming", "live"):
        v_ = getattr(ms, attr, None)
        if v_:
            print(f"  {attr}: {len(v_)}")
            m0 = v_[0]
            print(f"   sample: {m0}")
            break


if __name__ == "__main__":
    main()
