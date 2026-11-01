"""Is the missing geometry China-specific, or stage/playoff-specific?

Checks geometry availability by stage for China Stage 2, and samples a few
other China events (Stage 1, Kickoff, Champions 2026) as controls.
"""
from __future__ import annotations

import os
import sys
import time

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
import vlrdevapi as v  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CONTROL_EVENTS = {
    2766: "Champions 2026 (Shanghai)",
    2978: "VCT 2026 China S2",
}

# Try to locate the China Stage 1 / Kickoff events by name.
def find_china_events(c) -> dict[int, str]:
    res = c.event.list(tier="all", return_all=True)
    out = {}
    for e in res.events:
        nm = e.name
        low = nm.lower()
        if "china" in low and "2026" in low and "game changers" not in low:
            out[e.id] = nm
    return out


def main() -> None:
    c = v.VLRClient(trust_env=False)

    china = find_china_events(c)
    print("=== China 2026 events found ===")
    for eid, nm in sorted(china.items()):
        print(f"  {eid:<6} {nm}")

    targets = dict(CONTROL_EVENTS)
    # add China Stage 1 / Kickoff if present
    for eid, nm in china.items():
        if eid in targets:
            continue
        if "stage 1" in nm.lower() or "kickoff" in nm.lower():
            targets[eid] = nm

    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as hc:
        for eid, name in targets.items():
            print("\n" + "=" * 74)
            print(f"{eid}  {name}")
            try:
                ms = c.event.matches(eid).matches
            except Exception as exc:
                print("  matches ERR", type(exc).__name__)
                continue
            done = [m for m in ms if m.status.value == "completed"]
            by_stage: dict[str, list] = {}
            for m in done:
                by_stage.setdefault(m.stage, []).append(m)
            print(f"  completed series: {len(done)}  stages: {list(by_stage)}")

            for stage, group in by_stage.items():
                sample = group[:2]
                for m in sample:
                    try:
                        info = c.series.info(m.match_id)
                        games = [g for g in (info.games or []) if g.played]
                    except Exception as exc:
                        print(f"    {m.match_id} info ERR {type(exc).__name__}")
                        time.sleep(1.0)
                        continue
                    if not games:
                        continue
                    g = games[0]
                    url = f"https://www.vlr.gg/{m.match_id}?game={g.game_id}&tab=logs"
                    try:
                        r = hc.get(url)
                        geo = "data-map" in r.text
                        rows = r.text.count('class="lg-row')
                    except Exception as exc:
                        print(f"    {m.match_id} fetch ERR {type(exc).__name__}")
                        time.sleep(1.2)
                        continue
                    print(f"    {stage:<22} {m.match_id:<7} {g.map_name:<9} "
                          f"geo={'YES' if geo else 'NO ':<3} rows={rows}")
                    time.sleep(1.2)


if __name__ == "__main__":
    main()
