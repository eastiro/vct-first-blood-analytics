"""Find candidate events: Masters 2026 + four regional Stage 2 leagues."""
from __future__ import annotations

import os
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402


def main() -> None:
    c = v.VLRClient(trust_env=False)
    res = c.event.list(tier="all", return_all=True)
    print("events:", len(res.events))

    print("\n=== name contains 'masters' ===")
    for e in res.events:
        if "masters" in e.name.lower():
            print(f"  {e.id:<6} {e.name:<50} {e.status:<10} {e.start_date} .. {e.end_date}")

    print("\n=== name contains 'champions tour 2026' ===")
    for e in res.events:
        if "champions tour 2026" in e.name.lower():
            print(f"  {e.id:<6} {e.name:<50} {e.status:<10} {e.start_date} .. {e.end_date}")

    print("\n=== name contains 'stage 2' ===")
    for e in res.events:
        if "stage 2" in e.name.lower():
            print(f"  {e.id:<6} {e.name:<50} {e.status:<10} {e.start_date} .. {e.end_date}")


if __name__ == "__main__":
    main()
