"""Verify that Champions 2026 (Shanghai) carries 2D replay data.

The environment ships NO_PROXY with a bracketed IPv6 literal that httpx cannot
parse; vlrdevapi builds httpx clients in worker threads, so we must repair the
variable at process level before any client is created.
"""
from __future__ import annotations

import os

# --- environment repair (must happen before importing httpx via vlrdevapi) ---
for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402

EVENT_ID = 2766  # Valorant Champions 2026, Shanghai


def dump(obj, name: str) -> None:
    print(f"\n--- {name} ---")
    try:
        fields = type(obj).model_fields
    except AttributeError:
        fields = [n for n in dir(obj) if not n.startswith("_")][:30]
    for f in fields:
        print(f"   {f:<18} {getattr(obj, f, None)}")


def main() -> None:
    c = v.VLRClient(trust_env=False)

    ms = c.event.matches(EVENT_ID)
    print(f"container: {type(ms).__name__}")

    completed = getattr(ms, "completed", None) or []
    print(f"completed: {len(completed)}")
    if not completed:
        return

    m = completed[-1]
    dump(m, "last completed match")

    m_id = getattr(m, "id", None)
    print(f"\nmatch id = {m_id}")

    try:
        s = c.series.info(m_id)
        dump(s, "series.info")
    except Exception as exc:
        print("series.info ERR:", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
