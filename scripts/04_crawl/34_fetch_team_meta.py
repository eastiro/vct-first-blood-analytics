"""抓队伍元数据：官方缩写 + 队标。

对 site_v3.json 里的每支队伍：
  1) 请求 vlr.gg 搜索，拿到 team id 与 logo URL
  2) 若 _cache/tag_map.json 里没有缩写，再请求队伍页解析 team-header-tag
  3) logo 下载到 site/logos/<slug>.png（统一缩到 96px 内）

产物：_cache/teams_meta.json  =  {队名: {tag, id, logo_url, file}}
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
OUT_JSON = BASE / "_cache" / "teams_meta.json"
LOGO_DIR = BASE / "site" / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

d = json.loads((BASE / "data" / "site_v3.json").read_text(encoding="utf-8"))
TEAMS = d["dict"]["teams"]
TAGMAP = json.loads((BASE / "_cache" / "tag_map.json").read_text(encoding="utf-8"))
HAVE = {}
for tag, full in TAGMAP.items():
    HAVE.setdefault(full, tag)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "team"


def parse_search(html: str):
    """返回 [(name, team_id, logo_url)]"""
    out = []
    for m in re.finditer(
        r'href="/search/r/team/(\d+)/idx"[^>]*>(.*?)</a>', html, re.S
    ):
        tid, block = m.group(1), m.group(2)
        nm = re.search(r'search-item-title">\s*(.*?)\s*</div>', block, re.S)
        lg = re.search(r'<img src="(//owcdn\.net/[^"]+)"', block)
        if nm:
            out.append((re.sub(r"<[^>]+>", "", nm.group(1)).strip(),
                        tid, lg.group(1) if lg else None))
    return out


def parse_tag(html: str):
    m = re.search(r'team-header-tag">\s*([^<]+?)\s*</h2>', html)
    if not m:
        m = re.search(r'm-item-team-tag">\s*([^<]+?)\s*</span>', html)
    return m.group(1).strip() if m else None


def parse_header_logo(html: str):
    m = re.search(r'team-header-logo[^>]*>\s*<img src="(//owcdn\.net/[^"]+)"', html)
    if not m:
        m = re.search(r'<img src="(//owcdn\.net/img/[^"]+)"[^>]*class="team-logo"', html)
    return m.group(1) if m else None


def main():
    meta = {}
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        for i, name in enumerate(TEAMS, 1):
            rec = {"tag": HAVE.get(name), "id": None, "logo_url": None, "file": None}
            try:
                q = quote(name)
                r = c.get(f"https://www.vlr.gg/search/?q={q}&type=teams")
                cands = parse_search(r.text)
                best, best_score = None, 0.0
                for nm, tid, logo in cands:
                    if norm(nm) == norm(name):
                        best, best_score = (nm, tid, logo), 2.0
                        break
                    sc = SequenceMatcher(None, norm(nm), norm(name)).ratio()
                    if sc > best_score:
                        best, best_score = (nm, tid, logo), sc
                if best and best_score >= 0.6:
                    rec["id"], rec["logo_url"] = best[1], best[2]
                time.sleep(1.0)

                if rec["id"] and (not rec["tag"] or not rec["logo_url"]):
                    s = slug(name)
                    r2 = c.get(f"https://www.vlr.gg/team/{rec['id']}/{s}")
                    if not rec["tag"]:
                        rec["tag"] = parse_tag(r2.text)
                    rec["logo_url"] = rec["logo_url"] or parse_header_logo(r2.text)
                    time.sleep(1.0)
                elif rec["id"] and not rec["tag"]:
                    pass

                # 下载 logo
                if rec["logo_url"]:
                    url = "https:" + rec["logo_url"] if rec["logo_url"].startswith("//") else rec["logo_url"]
                    lr = c.get(url)
                    if lr.status_code == 200 and len(lr.content) > 500:
                        fn = f"{slug(name)}.png"
                        p = LOGO_DIR / fn
                        p.write_bytes(lr.content)
                        try:
                            im = Image.open(p).convert("RGBA")
                            if max(im.size) > 96:
                                im.thumbnail((96, 96), Image.LANCZOS)
                            im.save(p, "PNG", optimize=True)
                        except Exception:
                            pass
                        rec["file"] = fn
                    time.sleep(0.7)
            except Exception as e:
                rec["err"] = f"{type(e).__name__}: {e}"

            meta[name] = rec
            flag = rec["tag"] or "?"
            print(f"[{i:>2}/{len(TEAMS)}] {name:<26} {flag:<6} "
                  f"{'logo' if rec['file'] else 'NO-LOGO':<7} id={rec['id']}", flush=True)

    # 纯黑队标在暗底上看不见：算「近黑像素占比」，超过 55% 的标一个浅色底板
    for name, rec in meta.items():
        if not rec.get("file"):
            continue
        try:
            im = Image.open(LOGO_DIR / rec["file"]).convert("RGBA")
            px = [q for q in im.getdata() if q[3] > 60]
            if not px:
                continue
            dark = sum(1 for r, g, b, _ in px
                       if 0.2126 * r + 0.7152 * g + 0.0722 * b < 34) / len(px)
            rec["darkfrac"] = round(dark, 3)
            rec["plate"] = dark > 0.55
        except Exception:
            rec["plate"] = False
    print(f"plates needed: {sum(1 for v in meta.values() if v.get('plate'))}")

    OUT_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in meta.values() if v["file"])
    tags = sum(1 for v in meta.values() if v["tag"])
    print(f"\nwrote {OUT_JSON.name}: {tags}/{len(meta)} tags, {ok}/{len(meta)} logos")


if __name__ == "__main__":
    main()
