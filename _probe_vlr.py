"""Probe the VLR esports endpoints: events -> matches -> match detail.

Goal: find out whether professional match data includes round-level detail.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

KEY = os.environ["HDEV"]
CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache")
BASE = "https://api.henrikdev.xyz"


def get(path: str, cache_name: str | None = None) -> dict:
    if cache_name:
        f = CACHE / cache_name
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": KEY,
            "User-Agent": "valorant-analytics-research/0.1",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode("utf-8"))
    if cache_name:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / cache_name).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def main() -> None:
    print("=" * 72)
    print("1) EVENTS")
    print("=" * 72)
    ev = get("/valorant/v2/esports/vlr/events", "events.json")
    print("status:", ev.get("status"))
    data = ev.get("data", [])
    print("payload type:", type(data).__name__)
    if isinstance(data, dict):
        print("keys:", list(data.keys())[:15])
        inner = data.get("events", data)
    else:
        inner = data
    print("count:", len(inner) if hasattr(inner, "__len__") else "?")
    if inner:
        e0 = inner[0]
        print("\nfirst event keys:", list(e0.keys()))
        for k, v in e0.items():
            if not isinstance(v, (dict, list)):
                print(f"   {k:<22} {v}")


if __name__ == "__main__":
    main()
