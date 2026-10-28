"""Pull the Champions 2026 Grand Final and test series.replay()."""
from __future__ import annotations

import os

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402

EVENT_ID = 2766


def fields(obj):
    return type(obj).model_fields if hasattr(obj, "model_fields") else []


def show(obj, name):
    print(f"\n--- {name} ---")
    for f in fields(obj):
        val = getattr(obj, f, None)
        if isinstance(val, list):
            print(f"   {f:<16} list[{len(val)}]")
        elif val is not None:
            print(f"   {f:<16} {val}")


def main() -> None:
    c = v.VLRClient(trust_env=False)
    matches = c.event.matches(EVENT_ID).matches
    gf = [m for m in matches if getattr(m, "phase", "") == "Grand Final"]
    m = gf[0] if gf else matches[-1]
    show(m, "match")
    mid = m.match_id

    teams = getattr(m, "teams", [])
    print("\nteams:", [(getattr(t, 'name', '?'), getattr(t, 'score', '?')) for t in teams])

    info = c.series.info(mid)
    show(info, "series.info")

    games = getattr(info, "games", None) or []
    print(f"\ngames: {len(games)}")
    for g in games:
        print("   ", {f: getattr(g, f, None) for f in fields(g)})


if __name__ == "__main__":
    main()
