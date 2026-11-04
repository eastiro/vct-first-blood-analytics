"""双语切换的回归测试。

守三类问题：
1. 漏翻：切到英文后页面里还留着中文（数据里的专名除外）
2. 字典缺键：页面渲染时调用了不存在的键
3. 切换不重渲染：canvas / 下拉框 / 汇总文案停在旧语言
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
URL = "http://127.0.0.1:8777"

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


CJK = re.compile(r"[\u4e00-\u9fff]")

# 允许在英文界面里出现的中文：都是数据里的专名，不该翻译
ALLOW_CJK = {
    "无畏契约",          # 只在中文模式出现，英文模式不该有
}

PAGES = [
    ("index.html", "ovw"),
    ("scout.html", "scout"),
    ("duel.html", "duel"),
]


def main() -> None:
    with sync_playwright() as pw:
        b = pw.chromium.launch()

        for page_file, tag in PAGES:
            print(f"\n=== {page_file} ===")
            pg = b.new_page(viewport={"width": 1440, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append("console:" + m.text)
                  if m.type == "error" else None)

            pg.goto(f"{URL}/{page_file}?lang=zh", wait_until="networkidle")
            pg.wait_for_timeout(1600)

            zh_title = pg.title()
            zh_h1 = pg.inner_text("h1").replace("\n", " ")
            zh_body = pg.inner_text("body")

            check("starts in Chinese", pg.evaluate("I18N.lang()") == "zh",
                  pg.evaluate("document.documentElement.lang"))
            check("Chinese page has Chinese text", bool(CJK.search(zh_body)))

            # 切到英文
            pg.click('.lb[data-lang="en"]')
            pg.wait_for_timeout(1800)

            en_title = pg.title()
            en_h1 = pg.inner_text("h1").replace("\n", " ")
            en_body = pg.inner_text("body")

            check("switches to English", pg.evaluate("I18N.lang()") == "en",
                  pg.evaluate("document.documentElement.lang"))
            check("html lang attribute follows",
                  pg.evaluate("document.documentElement.lang") == "en")
            check("title is translated", en_title != zh_title, en_title)
            check("h1 is translated", en_h1 != zh_h1, en_h1)
            # URL 由 syncURL() 在 recompute 末尾写入，给一拍再读
            pg.wait_for_timeout(400)
            check("URL carries lang", "lang=en" in pg.evaluate("location.search"), pg.evaluate("location.search"))
            check("choice is remembered",
                  pg.evaluate("localStorage.getItem('vct.lang')") == "en")

            # 漏翻检查：扫 DOM 里所有文本节点。
            # 「中」是语言按钮自身，属于设计的一部分，排除。
            leftovers = pg.evaluate(r"""() => {
              const out = [];
              const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
              let n;
              while (n = w.nextNode()) {
                const s = (n.textContent || '').trim();
                if (!s || !/[\u4e00-\u9fff]/.test(s)) continue;
                const el = n.parentElement;
                if (!el || el.closest('.langsw') || el.tagName === 'SCRIPT') continue;
                out.push(s.slice(0, 60));
              }
              return out;
            }""")
            check("no Chinese left in the English page", not leftovers,
                  f"({len(leftovers)}) " + " | ".join(leftovers[:4]))

            # 字典缺键
            missing = pg.evaluate("() => window.__i18nMissing || []")
            check("no missing dictionary keys", not missing, str(missing[:5]))

            # 模板里裸写 t('key') 会原样输出成文字（少了 ${}）。扫一遍实际渲染的
            # 文本里有没有这种残留。
            bare = pg.evaluate(r"""() => {
              const out = [];
              const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
              let n;
              while (n = w.nextNode()) {
                const s = (n.textContent || '').trim();
                const el = n.parentElement;
                if (el && el.tagName === 'SCRIPT') continue;   // 脚本文本不算
                if (/t\('[a-z0-9._]+'\)/.test(s)) out.push(s.slice(0, 50));
              }
              return out;
            }""")
            check("no unescaped t() calls rendered as text", not bare, str(bare[:3]))

            check("no js errors", not errs, str(errs[:3]))

            # 刷新后保持
            pg.reload(wait_until="networkidle")
            pg.wait_for_timeout(1200)
            check("language survives a reload", pg.evaluate("I18N.lang()") == "en",
                  pg.title())

            # 切回中文并确认完全恢复
            pg.click('.lb[data-lang="zh"]')
            pg.wait_for_timeout(1500)
            check("switches back to Chinese", pg.evaluate("I18N.lang()") == "zh")
            back = pg.inner_text("h1").replace("\n", " ")
            check("Chinese h1 restored", back == zh_h1, back)

            pg.close()

        # 字典自检：所有键都有 zh 和 en
        print("\n=== dictionary ===")
        d = json.loads(pg.evaluate if False else "{}")
        dic = b.new_page()
        dic.goto(f"{URL}/duel.html?lang=zh", wait_until="networkidle")
        dic.wait_for_timeout(900)
        stats = dic.evaluate("""() => {
            const d = I18N.dict;
            const keys = Object.keys(d);
            const noZh = keys.filter(k => !d[k].zh);
            const noEn = keys.filter(k => !d[k].en);
            const same = keys.filter(k => d[k].zh === d[k].en);
            return {n: keys.length, noZh, noEn, same};
        }""")
        check("dictionary has entries", stats["n"] >= 200, f"({stats['n']} keys)")
        check("every key has Chinese", not stats["noZh"], str(stats["noZh"][:5]))
        check("every key has English", not stats["noEn"], str(stats["noEn"][:5]))
        dic.close()
        b.close()

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
