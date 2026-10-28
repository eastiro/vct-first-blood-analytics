"""Find the Shanghai Champions event and list its matches."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import vlrdevapi as v

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache")


def main() -> None:
    c = v.VLRClient(trust_env=False)

    ev = c.event.list(tier="all", status="completed", return_all=True)
    print(f"completed events: {len(ev.events)}")
    print("fields:", [n for n in dir(ev.events[0]) if not n.startswith('_')])

    hits = []
    for e in ev.events:
        name = getattr(e, "name", "") or ""
        title = getattr(e, "title", "") or ""
        blob = f"{name} {title}"
        if any(k in blob.lower() for k in ("champions", "masters", "shanghai", "seoul")):
            hits.append(e)

    print(f"\ncandidate big events: {len(hits)}")
    for e in hits[:40]:
        eid = getattr(e, "id", getattr(e, "event_id", "?"))
        nm = getattr(e, "name", getattr(e, "title", "?"))
        dates = getattr(e, "dates", "")
        print(f"  id={eid:<7} {nm}   {dates}")


if __name__ == "__main__":
    main()
