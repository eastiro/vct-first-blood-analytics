"""Build the full EN -> official zh-CN name map, including ABILITIES.

Kill causes can be weapons, abilities, or ultimates. Instead of hand
translating the ability names, pull them from valorant-api (Riot's asset
service) and align by UUID, exactly as for agents and weapons.
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
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    agents_en = get("https://valorant-api.com/v1/agents")["data"]
    agents_zh = get("https://valorant-api.com/v1/agents?language=zh-CN")["data"]
    weapons_en = get("https://valorant-api.com/v1/weapons")["data"]
    weapons_zh = get("https://valorant-api.com/v1/weapons?language=zh-CN")["data"]

    zh_agents = {a["uuid"]: a for a in agents_zh}
    zh_weapons = {w["uuid"]: w for w in weapons_zh}

    agent_map: dict[str, str] = {}
    ability_map: dict[str, str] = {}

    for a in agents_en:
        if not a.get("isPlayableCharacter"):
            continue
        zh = zh_agents.get(a["uuid"], {})
        agent_map[a["displayName"].lower()] = zh.get("displayName", a["displayName"])

        zh_ab_by_uuid = {ab["slot"]: ab for ab in (zh.get("abilities") or [])}
        for ab in (a.get("abilities") or []):
            en_name = (ab.get("displayName") or "").strip()
            if not en_name:
                continue
            zh_ab = zh_ab_by_uuid.get(ab.get("slot"), {})
            zh_name = (zh_ab.get("displayName") or "").strip()
            if zh_name:
                ability_map[en_name.lower()] = zh_name
                if zh_name != en_name:
                    pass
            # the API sometimes names the ult differently from the kill feed
            if ab.get("slot") == "Ultimate" and zh_name:
                ability_map.setdefault(en_name.lower(), zh_name)

    weapon_map: dict[str, str] = {}
    for w in weapons_en:
        zh = zh_weapons.get(w["uuid"], {})
        weapon_map[w["displayName"].lower()] = zh.get("displayName", w["displayName"])

    payload = {
        "agents": agent_map,
        "weapons": weapon_map,
        "abilities": ability_map,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"agents   : {len(agent_map)}")
    print(f"weapons  : {len(weapon_map)}")
    print(f"abilities: {len(ability_map)}")

    print("\n=== ability checks (kill-feed causes) ===")
    for k in ("headhunter", "tour de force", "blade storm", "hunter's fury",
              "overdrive", "showstopper", "paint shells", "blast pack",
              "snake bite", "recon bolt", "shock bolt", "incendiary",
              "nanoswarm", "butterfly knives", "knife", "hunters fury"):
        print(f"  {k:<20} -> {ability_map.get(k, '<<MISSING>>')}")

    print("\n=== weapon checks ===")
    for k in ("phantom", "vandal", "operator", "ghost", "outlaw", "sheriff",
              "classic", "spectre", "bandit", "marshal", "guardian", "bulldog",
              "stinger", "frenzy", "judge", "odin", "ares", "shorty", "bucky"):
        print(f"  {k:<12} -> {weapon_map.get(k, '<<MISSING>>')}")

    print("\n=== agent checks ===")
    for k in ("chamber", "neon", "jett", "sova", "omen", "sage", "cypher",
              "phoenix", "yoru", "vyse", "waylay", "raze", "killjoy", "fade"):
        print(f"  {k:<12} -> {agent_map.get(k, '<<MISSING>>')}")

    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
