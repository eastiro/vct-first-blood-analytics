"""把 Inter / JetBrains Mono 的 latin 子集下载到 site/fonts 并生成本地 @font-face。

为什么要自托管：fonts.googleapis.com 在国内经常打不开，页面会卡在字体请求上。
只取 latin 子集（中文走系统字体），总共 3 个 woff2。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import httpx

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
OUT = BASE / "site" / "fonts"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}
CSS_URL = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&"
           "family=JetBrains+Mono:wght@400;500&display=swap")

BLOCK_RE = re.compile(r"/\*\s*([a-z\-]+)\s*\*/\s*(@font-face[^}]*\})", re.S)
FAM_RE = re.compile(r"font-family:\s*'([^']+)'")
WGT_RE = re.compile(r"font-weight:\s*(\d+)")
URL_RE = re.compile(r"url\((https?://[^)]+\.woff2)\)")


def main() -> None:
    faces: list[str] = []
    seen: dict[str, str] = {}

    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        css = c.get(CSS_URL).text
        for m in BLOCK_RE.finditer(css):
            subset, body = m.group(1), m.group(2)
            if subset != "latin":
                continue
            fam = FAM_RE.search(body).group(1)
            wgt = WGT_RE.search(body).group(1)
            url = URL_RE.search(body).group(1)

            if url not in seen:
                fn = f"{fam.replace(' ', '')}-{hashlib.md5(url.encode()).hexdigest()[:6]}.woff2"
                data = c.get(url).content
                (OUT / fn).write_bytes(data)
                seen[url] = fn
                print(f"  {fn:<32} {len(data)/1024:5.1f} KB")

            faces.append(
                "@font-face{font-family:'%s';font-style:normal;font-weight:%s;"
                "font-display:swap;src:url('%s') format('woff2');}"
                % (fam, wgt, seen[url])
            )

    (OUT / "fonts.css").write_text("\n".join(faces) + "\n", encoding="utf-8")
    total = sum((OUT / f).stat().st_size for f in seen.values()) / 1024
    print(f"faces={len(faces)} files={len(seen)} total={total:.0f} KB")


if __name__ == "__main__":
    main()
