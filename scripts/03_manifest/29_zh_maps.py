"""Fetch official zh-CN map names from valorant-api and merge into the cache."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
CACHE = BASE / "_cache" / "zh_names.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    en = get("https://valorant-api.com/v1/maps")["data"]
    zh = get("https://valorant-api.com/v1/maps?language=zh-CN")["data"]

    zh_by_uuid = {m["uuid"]: m.get("displayName", "") for m in zh}
    maps: dict[str, str] = {}
    for m in en:
        name = m.get("displayName") or ""
        if not name:
            continue
        maps[name.lower()] = zh_by_uuid.get(m["uuid"], name)

    payload = json.loads(CACHE.read_text(encoding="utf-8"))
    payload["maps"] = maps
    CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== map names ===")
    for k in ("ascent", "breeze", "fracture", "haven", "lotus", "pearl",
              "split", "sunset", "abyss", "summit", "bind", "corrode"):
        print(f"  {k:<10} -> {maps.get(k, '<<MISSING>>')}")
    print(f"\ntotal maps: {len(maps)}")


if __name__ == "__main__":
    main()
