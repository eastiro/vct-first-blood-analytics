"""Probe one professional match: does it carry round-level detail?"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

KEY = os.environ["HDEV"]
CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache")
BASE = "https://api.henrikdev.xyz"


def get(path: str, cache_name: str) -> dict:
    f = CACHE / cache_name
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": KEY,
                 "User-Agent": "valorant-analytics-research/0.1",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode("utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def main() -> None:
    ev = get("/valorant/v2/esports/vlr/events", "events.json")
    events = ev["data"]
    target = next((e for e in events if e["id"] == 3166), events[0])
    print(f"event: {target['title']}  (id={target['id']}, region={target['region']})")

    ms = get(f"/valorant/v2/esports/vlr/events/{target['id']}/matches",
             f"matches_{target['id']}.json")
    print("matches status:", ms.get("status"))
    mdata = ms.get("data", [])
    print("match count:", len(mdata))
    if mdata:
        m0 = mdata[0]
        print("\nfirst match keys:", list(m0.keys()))
        print(json.dumps(m0, ensure_ascii=False, indent=2)[:1200])

    if not mdata:
        return

    mid = m0.get("match_id") or m0.get("id")
    print(f"\n{'='*72}\nMATCH DETAIL  id={mid}\n{'='*72}")
    md = get(f"/valorant/v2/esports/vlr/matches/{mid}", f"match_{mid}.json")
    d = md.get("data", {})
    print("top keys:", list(d.keys()) if isinstance(d, dict) else type(d).__name__)
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, list):
                print(f"   {k:<24} list[{len(v)}]")
            elif isinstance(v, dict):
                print(f"   {k:<24} dict({len(v)})")
            else:
                print(f"   {k:<24} {v}")
        for key in ("rounds", "economy", "stats", "performance"):
            if key in d and d[key]:
                print(f"\n--- {key} sample ---")
                print(json.dumps(d[key][0] if isinstance(d[key], list) else d[key],
                                 ensure_ascii=False, indent=2)[:900])


if __name__ == "__main__":
    main()
