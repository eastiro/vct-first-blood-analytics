"""Build English -> official Chinese name maps for agents and weapons.

We align by UUID rather than by name, so translated names cannot mismatch.
Sources: valorant-api.com (Riot's own asset service).
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
OUT = BASE / "_cache" / "zh_names.json"


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    agents_en = get("https://valorant-api.com/v1/agents")["data"]
    agents_zh = get("https://valorant-api.com/v1/agents?language=zh-CN")["data"]
    weapons_en = get("https://valorant-api.com/v1/weapons")["data"]
    weapons_zh = get("https://valorant-api.com/v1/weapons?language=zh-CN")["data"]

    zh_a = {a["uuid"]: a["displayName"] for a in agents_zh}
    zh_w = {w["uuid"]: w["displayName"] for w in weapons_zh}

    agent_map: dict[str, str] = {}
    for a in agents_en:
        if not a.get("isPlayableCharacter"):
            continue
        key = a["displayName"].lower()
        agent_map[key] = zh_a.get(a["uuid"], a["displayName"])

    weapon_map: dict[str, str] = {}
    for w in weapons_en:
        weapon_map[w["displayName"].lower()] = zh_w.get(w["uuid"], w["displayName"])

    # ability names that show up as kill causes, plus map/round wording
    extra = {
        "headhunter": "爆头专家",          # Chamber's signature pistol
        "tour de force": "狙击专家",        # Chamber's ultimate
        "blade storm": "风暴之刃",          # Jett ultimate
        "hunter's fury": "猎手之怒",        # Sova ultimate
        "overdrive": "超载",                # Neon ultimate
        "showstopper": "一锤定音",          # Raze ultimate
        "raze": "雷兹",
    }

    payload = {
        "agents": agent_map,
        "weapons": {**weapon_map, **extra},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"agents mapped : {len(agent_map)}")
    print(f"weapons mapped: {len(payload['weapons'])}")
    print("\nsample agents:")
    for k in ("chamber", "neon", "jett", "sova", "omen", "sage", "cypher",
              "phoenix", "yoru", "vyse", "waylay"):
        print(f"   {k:<12} -> {agent_map.get(k, '??')}")
    print("\nsample weapons:")
    for k in ("phantom", "vandal", "operator", "ghost", "outlaw", "sheriff",
              "classic", "spectre", "judge", "odin", "marshal", "guardian",
              "bulldog", "stinger", "frenzy", "bandit"):
        print(f"   {k:<12} -> {payload['weapons'].get(k, '??')}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
