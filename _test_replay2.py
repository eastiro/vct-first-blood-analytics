"""Pull one Champions 2026 match and test series.replay()."""
from __future__ import annotations

import os

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402

EVENT_ID = 2766


def show(obj, name, limit=25):
    print(f"\n--- {name} ---")
    if hasattr(obj, "model_fields"):
        for f in type(obj).model_fields:
            val = getattr(obj, f, None)
            if isinstance(val, list):
                print(f"   {f:<16} list[{len(val)}]")
            elif not isinstance(val, (dict,)) and val is not None:
                print(f"   {f:<16} {val}")
    else:
        print("   ", obj)


def main() -> None:
    c = v.VLRClient(trust_env=False)
    ms = c.event.matches(EVENT_ID)
    matches = ms.matches
    print(f"matches: {len(matches)}")

    m = matches[-1]
    show(m, "last match")

    m_id = getattr(m, "id", None)
    print(f"\n=== series.info({m_id}) ===")
    info = c.series.info(m_id)
    show(info, "series info")

    games = getattr(info, "games", None) or []
    print(f"\ngames: {len(games)}")
    for g in games:
        print("   ", {f: getattr(g, f, None) for f in type(g).model_fields})

    if not games:
        return

    gid = getattr(games[0], "id", None) or getattr(games[0], "game_id", None)
    print(f"\n=== series.replay({m_id}, {gid}) ===")
    rep = c.series.replay(m_id, gid)
    show(rep, "replay")


if __name__ == "__main__":
    main()
