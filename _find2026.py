"""Find the 2026 Shanghai event and verify its matches carry 2D replay data."""
from __future__ import annotations

import vlrdevapi as v

CACHE_EVENTS = ("Shanghai", "china")


def main() -> None:
    c = v.VLRClient(trust_env=False)

    ev = c.event.list(tier="all", status="completed", return_all=True)
    print(f"completed events scanned: {len(ev.events)}")

    print("\n=== events with 'Shanghai' in the name ===")
    for e in ev.events:
        if "shanghai" in e.name.lower():
            print(f"  id={e.id:<6} {e.name:<48} region={e.region} "
                  f"{e.start_date} .. {e.end_date}")

    print("\n=== 2026 events mentioning champions / masters ===")
    for e in ev.events:
        nm = e.name.lower()
        if "2026" in nm and ("champions" in nm or "masters" in nm):
            print(f"  id={e.id:<6} {e.name:<48} region={e.region} "
                  f"{e.start_date} .. {e.end_date}")

    print("\n=== detail: Champions 2026 (2766) ===")
    try:
        info = c.event.info(2766)
        for f in info.model_fields:
            print(f"   {f:<18} {getattr(info, f, None)}")
    except Exception as exc:
        print("   ERR", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
