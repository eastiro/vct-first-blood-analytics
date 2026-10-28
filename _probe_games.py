"""Inspect the 'games' array of a pro match: per-map detail and round granularity."""
from __future__ import annotations

import json
from pathlib import Path

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache\match_777944.json")


def main() -> None:
    d = json.loads(CACHE.read_text(encoding="utf-8"))["data"]

    print("=" * 72)
    print("TEAMS")
    print("=" * 72)
    print(json.dumps(d["teams"], ensure_ascii=False, indent=2)[:800])

    games = d["games"]
    print(f"\n{'='*72}\nGAMES: {len(games)}\n{'='*72}")
    for gi, g in enumerate(games):
        print(f"\n--- game {gi} keys ---")
        for k, v in g.items():
            if isinstance(v, list):
                print(f"   {k:<24} list[{len(v)}]")
            elif isinstance(v, dict):
                print(f"   {k:<24} dict{tuple(v.keys())[:8]}")
            else:
                print(f"   {k:<24} {v}")

    g0 = games[0]
    print(f"\n{'='*72}\nGAME 0 SCALARS\n{'='*72}")
    for k, v in g0.items():
        if not isinstance(v, (dict, list)):
            print(f"   {k:<24} {v}")

    # hunt for round-level structures
    print(f"\n{'='*72}\nLOOKING FOR ROUND DATA\n{'='*72}")
    for k, v in g0.items():
        if isinstance(v, list) and v:
            print(f"\n{k}  (list[{len(v)}])  first element:")
            e0 = v[0]
            if isinstance(e0, dict):
                for kk, vv in e0.items():
                    t = (f"list[{len(vv)}]" if isinstance(vv, list)
                         else "dict" if isinstance(vv, dict) else type(vv).__name__)
                    print(f"     {kk:<22} {t}")
                print("     sample:", json.dumps(e0, ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
