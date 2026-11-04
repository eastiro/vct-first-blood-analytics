"""Merge + sanity-check the full 2026 season into data/rounds_all.jsonl.

IMPORTANT: every line in these files is ONE ROUND, not one map.
The dedupe key is therefore (series_id, game_id, round).

Sources (output ordering is re-sorted, so order here does not matter):
  data/rounds.jsonl           4 events crawled first (13,905 rounds)
  data/rounds_champions.jsonl Champions Shanghai (1,810 rounds)
  data/rounds_2026_add.jsonl  Kickoff x4 + Masters Santiago + Stage 1 x4 (17,071)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
SRC = BASE / "data" / "rounds_all.jsonl"
SOURCES = [
    BASE / "data" / "rounds.jsonl",
    BASE / "data" / "rounds_champions.jsonl",
    BASE / "data" / "rounds_2026_add.jsonl",
]

ORDER = [
    "VCT Americas Kickoff 2026", "VCT China Kickoff 2026",
    "VCT EMEA Kickoff 2026", "VCT Pacific Kickoff 2026",
    "Masters Santiago 2026",
    "VCT Americas Stage 1 2026", "VCT China Stage 1 2026",
    "VCT EMEA Stage 1 2026", "VCT Pacific Stage 1 2026",
    "Masters London 2026",
    "VCT Americas Stage 2", "VCT EMEA Stage 2",
    "VCT China Stage 2", "VCT Pacific Stage 2",
    "Champions Shanghai 2026",
]


def main() -> None:
    rows = []
    for path in SOURCES:
        if not path.exists():
            print(f"!! missing {path.name}")
            continue
        n0 = len(rows)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        print(f"  {path.name:<26} +{len(rows)-n0:>6} rows")
    print(f"rows read: {len(rows)}")

    seen = set()
    out, dup = [], 0
    for r in rows:
        key = (r["series_id"], r["game_id"], r.get("round"))
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        out.append(r)
    print(f"duplicate rounds dropped: {dup}   unique rounds: {len(out)}")

    unk = {r["event"] for r in out if r["event"] not in ORDER}
    if unk:
        print("!! events not in ORDER:", sorted(unk))

    out.sort(key=lambda r: (
        ORDER.index(r["event"]) if r["event"] in ORDER else 99,
        r.get("date") or "",
        r["series_id"], r["game_no"], r.get("round") or 0))

    ev = defaultdict(lambda: dict(maps=set(), rounds=0, kills=0,
                                  geo=0, load=0, teams=set()))
    for r in out:
        e = ev[r["event"]]
        e["maps"].add(r["game_id"])
        e["rounds"] += 1
        ks = r.get("kills") or []
        e["kills"] += len(ks)
        if r.get("loadouts"):
            e["load"] += 1
        if any(k.get("pos_x") is not None for k in ks):
            e["geo"] += 1
        for t in (r.get("teams") or "").split(" vs "):
            if t.strip():
                e["teams"].add(t.strip())

    print("\n=== per event ===")
    tm_all = set()
    for e in ORDER:
        if e not in ev:
            print(f"  {e:<28} MISSING")
            continue
        d = ev[e]
        tm_all |= d["teams"]
        print(f"  {e:<28} {len(d['maps']):>3} maps {d['rounds']:>6} rounds "
              f"geo {100*d['geo']/max(d['rounds'],1):>5.1f}% "
              f"load {100*d['load']/max(d['rounds'],1):>5.1f}% "
              f"{len(d['teams']):>2} teams")

    tr = sum(d["rounds"] for d in ev.values())
    tk = sum(d["kills"] for d in ev.values())
    print(f"\nTOTAL {len({(r['series_id'], r['game_id']) for r in out})} maps / "
          f"{tr} rounds / {tk} kills / {len(tm_all)} teams")

    print("\n=== per map (maps played) ===")
    for m, n in Counter(r["map"] for r in out).most_common():
        print(f"  {m:<10} {n:>4}")

    SRC.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                   encoding="utf-8")
    print(f"\nrewrote {SRC} ({SRC.stat().st_size/1e6:.1f} MB, {len(out)} rows)")


if __name__ == "__main__":
    main()
