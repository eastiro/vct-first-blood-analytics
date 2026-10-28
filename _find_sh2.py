"""List Shanghai Masters 2024 matches and test whether replay data exists."""
from __future__ import annotations

import json
from pathlib import Path

import vlrdevapi as v

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache")


def main() -> None:
    c = v.VLRClient(trust_env=False)

    ev = c.event.list(tier="all", status="completed", return_all=True)
    for e in ev.events:
        if "Masters" in e.name and "Shanghai" in e.name:
            print(f"MATCH: id={e.id} name={e.name} region={e.region} "
                  f"{e.start_date} .. {e.end_date}")

    # The 2024 Shanghai Masters event id is 2264-ish; search by stage listing
    print("\n--- probing known candidates ---")
    for cand in (2264, 2265, 2097, 2096):
        try:
            info = c.event.info(cand)
            print(f"  {cand}: {info.name}  ({getattr(info,'region','?')})")
        except Exception as exc:
            print(f"  {cand}: ERR {type(exc).__name__}")


if __name__ == "__main__":
    main()
