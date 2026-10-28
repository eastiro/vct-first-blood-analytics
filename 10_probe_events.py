"""Probe the vlrdevapi surface + list Masters events.

ASCII-only source (console encoding safety).
"""
from __future__ import annotations

import os
import sys
import inspect

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402
from vlrdevapi import event as ev_mod, series as se_mod  # noqa: E402


def main() -> None:
    print("event module:", [m for m in dir(ev_mod) if not m.startswith("_")])
    print("series module:", [m for m in dir(se_mod) if not m.startswith("_")])
    print()

    for name in ("list", "info", "matches", "search"):
        fn = getattr(ev_mod, name, None)
        if fn is None:
            continue
        try:
            print(f"--- event.{name}{inspect.signature(fn)}")
            doc = inspect.getdoc(fn) or ""
            print("\n".join(doc.splitlines()[:18]))
        except Exception as exc:
            print("  ERR", exc)
        print()

    c = v.VLRClient(trust_env=False)
    print("client methods:", [m for m in dir(c) if not m.startswith("_")])


if __name__ == "__main__":
    main()
