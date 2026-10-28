"""List 2026 VCT events and count completed series per candidate event."""
from __future__ import annotations

import os
import sys
import time

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402

CANDIDATES = [
    (2760, "Masters Santiago 2026", "international"),
    (2682, "VCT 2026: Americas Kickoff", "americas"),
    (2685, "VCT 2026: China Kickoff", "china"),
    (2684, "VCT 2026: EMEA Kickoff", "emea"),
    (2683, "VCT 2026: Pacific Kickoff", "pacific"),
    (2860, "VCT 2026: Americas Stage 1", "americas"),
    (2864, "VCT 2026: China Stage 1", "china"),
    (2863, "VCT 2026: EMEA Stage 1", "emea"),
    (2775, "VCT 2026: Pacific Stage 1", "pacific"),
]


def main() -> None:
    c = v.VLRClient(trust_env=False)
    total = 0
    for eid, lab, _ in CANDIDATES:
        t0 = time.time()
        try:
            ms = c.event.matches(eid).matches
            done = [m for m in ms if m.status.value == "completed"]
            total += len(done)
            print(f"  {eid:<5} {lab:<28} {len(done):>3}/{len(ms):<3} completed "
                  f"({time.time()-t0:.1f}s)", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  {eid:<5} {lab:<28} ERR {type(exc).__name__}: {exc}", flush=True)
        time.sleep(0.8)
    print(f"\ntotal completed series: {total}", flush=True)


if __name__ == "__main__":
    main()
