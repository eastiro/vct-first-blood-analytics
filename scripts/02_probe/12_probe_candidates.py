"""Inspect candidate events: stages + match counts + date ranges."""
from __future__ import annotations

import os
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402

CANDIDATES = {
    2760: "Masters Santiago 2026",
    2765: "Masters London 2026",
    2976: "VCT 2026 EMEA Stage 2",
    2977: "VCT 2026 Americas Stage 2",
    2978: "VCT 2026 China Stage 2",
    2776: "VCT 2026 Pacific Stage 2",
}


def main() -> None:
    c = v.VLRClient(trust_env=False)
    for eid, label in CANDIDATES.items():
        print("=" * 70)
        print(f"{eid}  {label}")
        try:
            info = c.event.info(eid)
            print("  fields:", list(info.model_fields))
            for f in ("name", "status", "prize", "dates", "region", "location"):
                if hasattr(info, f):
                    print(f"  {f}: {getattr(info, f)!r}")
        except Exception as exc:
            print("  info ERR", type(exc).__name__, exc)
        try:
            st = c.event.stages(eid)
            print("  stages:", st)
        except Exception as exc:
            print("  stages ERR", type(exc).__name__, exc)
        try:
            ms = c.event.matches(eid)
            print("  matches:", len(ms.matches))
            if ms.matches:
                m0 = ms.matches[0]
                print("  match fields:", list(m0.model_fields))
                print("  sample:", m0)
        except Exception as exc:
            print("  matches ERR", type(exc).__name__, exc)
        print()


if __name__ == "__main__":
    main()
