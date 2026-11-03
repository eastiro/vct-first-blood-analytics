# 交接文档 · 首杀分析网站

给接手改这个项目的 agent。

视觉规范、参考站点、以及「哪些是刻意不做的」都写在 `DESIGN.md` 里。

现在是两个页面，各自独立，共用同一份数据思路：

| 页面 | 作用 | 数据 |
|---|---|---|
| `site/index.html` | 全局基准（首杀按武器/攻防/时间/队伍拆开）+ 可排序队伍榜 + 赛段对比 | `data/site_v3.json` |
| `site/scout.html` | **队伍报告**（选队+选图出报告，页面上就叫「队伍报告」） | `data/site_v5.json` |

**数据范围（2026-10-26 起）：2026 全季 15 个赛事 / 1,545 张图 / 32,786 回合 /
228,904 次击杀 / 63 支队伍 / 12 张地图（新增 Bind、Corrode）。**

`site_v5.json` 是 `site_v3.json` 的超集（多了买枪、球员、回合序号、比赛序号），
但 `index.html` 仍读 v3，**没有迁移**，两套并存。改 v3 行结构会同时影响两个页面。

**v3 行结构在 2026-10-26 从 14 个字段扩到 16 个**（只往后追加，旧索引不变）：

```
14  snipe   1 = 首杀用的是狙击枪（Operator / Outlaw / Marshal）
15  pkill   首杀者的球员索引（-1 未知）
```

同时 payload 顶层多了 `"players": [{"n": 名字, "t": 队伍索引}]`（410 人）。
前端用到的是 `r[14]`（狙击首杀列）和 `r[15]`（球探页的首杀集中度）。

### 数据从哪来（现在有三份源 + 一份合并结果）

```
data/rounds.jsonl            13,905 回合   最早抓的 4 个赛事
data/rounds_champions.jsonl   1,810 回合   上海冠军赛
data/rounds_2026_add.jsonl   17,071 回合   Kickoff×4 + 圣地亚哥 + Stage1×4
        ↓  97_finalize_year.py 合并去重
data/rounds_all.jsonl        32,786 回合   站点构建的唯一输入
```

**⚠️ 去重键是 `(series_id, game_id, round)`。每行是一个回合，不是一张图。**
用 `(series_id, game_id)` 去重会把 32,786 行压成 1,545 行（踩过）。

### 队伍缩写与队标

```
34_fetch_team_meta.py  →  _cache/teams_meta.json  +  site/logos/<slug>.png
                               ↓  90 / 93 构建时读
                     site_v3.json / site_v5.json 的 "teamMeta"（与 dict.teams 同序）
```

`teamMeta[i] = {tag: "BLG", logo: "logos/bilibili-gaming.png", plate: false}`。

- **缩写**优先用 `_cache/tag_map.json`（从 loadout 的队标推出来的，和击杀流的全名对上），
  缺的（中国赛区没有 loadout）再从 vlr 队伍页的 `team-header-tag` 抓。现在 63/63。
- **队标**从 vlr 搜索页拿到 `owcdn.net` 的图，缩到 96px 存本地（共 548 KB）。
- **`plate`**：纯黑队标在暗底上会看不见（PRX / VIT / ZETA 等 21 支），构建时算「近黑像素占比 > 55%」
  打上这个标，前端会垫一块浅色底板。重抓队标后重跑 `34_fetch_team_meta.py` 会自动重算。
- 前端用 `teamCell(t)` 统一渲染（`site/index.html`），球探页的队标在 `renderHead`。

加新赛事：`20b_manifest_2026.py` 建清单 → 用 env 指向新清单跑 `30_crawl.py`
（`VLR_MANIFEST` / `VLR_OUT` / `VLR_FAILLOG`）→ 把新文件加进 `97_finalize_year.py` 的 `SOURCES`。

---

## 一、怎么看

```bash
cd "D:\好玩的项目\vct-first-blood-analytics\site"
python -m http.server 8777 --bind 127.0.0.1
# 打开 http://127.0.0.1:8777
```

**纯静态，没有构建步骤，没有框架，没有 npm。**
`index.html` 约 1200 行，`scout.html` 约 900 行，都是内联 CSS + JS，改完刷新就行。

---

## 一之二、购买分档（v5 新增，别用花费分档）

**不要用 `spent` 判断买枪强度。** `spent` 是本回合花掉的信用点，
上回合保下来的 Vandal 记 0 花费，所以「花费低的回合」经常是满配。

正确定义（`93_site_data_v5.py` 的 `LONG_GUNS`）：

```
长枪 = Vandal Phantom Guardian Bulldog Odin Operator Outlaw Marshal
全买 ≥4 把 / 半买 2-3 把 / eco ≤1 把
```

用花费分档会算出「全买 vs eco 只有 54.8%」，用长枪数分档是 81.0%。
手枪局长枪率 0.0%，可以拿这个当字段校验。

**页面上只报「全买局」，不再报 eco 局胜率**（2026-11-03 删的）。
原因：这三档的边界是长枪把数，但 eco 这个名字承诺的是「存钱」。
实测 eco 档里 12% 是 4 把以上 Stinger / Spectre 的强起，6.9% 全队花了 8,000 以上，
名字和内容对不上。底层 `buyAtk / buyDef` 字段还在，要用来做别的分析随时能取，
只是别在界面上叫它 eco。细节见 `DESIGN.md` 第八节。

---

## 二、目录结构

```
D:\好玩的项目\vct-first-blood-analytics\
├── site\
│   ├── index.html          ← 唯一要改的文件
│   ├── data\
│   │   └── site_v3.json    ← 数据（0.65 MB，前端 fetch）
│   └── maps\               ← 10 张 VLR 小地图 PNG（1024×1024）
├── data\
│   ├── rounds_all.jsonl    ← 全量原始数据 15,715 行（改数据时才用）
│   └── site_v3.json        ← 同 site/data/site_v3.json 的源
├── _cache\
│   └── tag_map.json        ← 队伍缩写→全名映射（51 条）
├── figures\                ← matplotlib 出的静态图
├── RESULTS.md              ← 完整结论文档
└── 90_site_data_v3.py      ← 生成 site_v3.json 的脚本
```

---

## 三、数据格式（改前端必读）

`site_v3.json` 结构：

```jsonc
{
  "meta": { rounds, first_bloods, maps_played, fb_to_win_pct,
            traded_fb_pct, traded_fb_to_win_pct, untraded_fb_to_win_pct,
            trade_window_sec, meta_size, comps, teams_shown,
            per_event: { "<eventName>": {rounds, maps, fb_to_win_pct, has_geometry} },
            geometry_note },
  "dict": { events:[], maps:[], teams:[], agents:[], causes:[] },   // 索引 → 英文 key
  "zh":   { events:{}, eventsShort:{}, maps:{}, agents:{}, causes:{} }, // 英文 key → 中文
  "comps":   [ [agentIdx×5], ... ],          // 248 套阵容
  "metaTop": { "<mapIdx>": [agentIdx×7] },   // 每张图的版本英雄 top7
  "rounds":  [ [14 个整数], ... ]             // 15,715 行
}
```

**`rounds` 每行 14 个整数，索引固定：**

| idx | 含义 | 说明 |
|---|---|---|
| 0 | event | 赛事索引 |
| 1 | map | 地图索引 |
| 2 | atkT | 进攻方队伍索引 |
| 3 | defT | 防守方队伍索引 |
| 4 | winT | 赢下这回合的队伍 |
| 5 | killT | 拿到首杀的队伍 |
| 6 | agent | 首杀英雄索引 |
| 7 | cause | 首杀武器/技能索引 |
| 8 | sec | 首杀发生在第几秒（-1 = 未知） |
| 9 | x | 首杀位置 X（0–1024，-1 = 无坐标） |
| 10 | y | 首杀位置 Y |
| 11 | traded | 1=首杀被补掉，0=没被补，-1=未知 |
| 12 | compA | 拿首杀那队的阵容 id（-1=无数据） |
| 13 | compB | 另一队的阵容 id |

**约定：**
- `-1` 一律表示"没有/未知"，前端不要假设非空。
- team 索引 `-1` 表示该队不在显示列表里（出场 < 20 回合），聚合时要跳过。
- **中国赛区 x/y 全是 -1**（vlr.gg 没给 2D 回放）。它的其他字段都有值。

---

## 四、已有的交互逻辑（别改坏）

```
F = { ev, map, team, agent }
// ev 是必选项（0-5），没有 -1。赛事是入口，其余三个 -1 = 全部
```

- `recompute()` 遍历 `rounds` 过滤 → 存进 `view[]` → `renderAll()`
- `agg()` 一趟聚合出所有统计
- `rebuild()` = `syncChips` → `buildMapChips` → `buildTeamSelect` → `buildAgentChips` → `recompute`
- `S.eventStats` 在 boot 时算好，是六个赛事的**固定基准**，不随筛选变化

**几个刻意的设计（改动前务必理解）：**

1. **赛事是必选项，没有「全部赛事」。** 换赛事时地图会按新图池重建，
   旧地图不在新图池里就自动回落到「全部地图」。15 个赛事里国际赛事用金色 chip 区分。
2. **队伍表默认「本赛事」，跟着上面的赛事 / 地图 / 英雄筛选走。** 这也是用户明确要求的：
   整季榜看着不动。右上角有「本赛事 / 整季」切换，切到整季后按钮文字变成「整季」。
   **注意整季榜的可信度有限**：首杀率的跨赛段相关只有 +0.16，S1 前 5 名到 S2 只剩 1 支
   还在前 5（见 `CONCLUSIONS.md` 第八节）。所以整季只适合当风格描述，不是实力预测。
3. **队伍表所有列都可点表头排序**，默认按回合数降序。表下方那条
   `#teamReliability` 写着每列的分半信度（首杀率 0.46 最稳，多打少丢 0.10 是噪声），
   改指标时别把这段删了——它是防止读者过度解读的唯一提示。
4. **队伍表最后一列是「狙击首杀」，不是「阵容一致性」。** 2026-10-26 换的：
   阵容一致性和胜率的相关是 **−0.25**（负的），测的其实是地图池大小；
   狙击首杀占比跨赛段 r=0.81，是所有候选列里最稳的一个。
   再想加列时先做一次分半 + 跨赛段信度，别凭直觉。
5. **页面最底部是「第一赛段 → 第二赛段」面板**（`renderStage`），跟着当前赛事的赛区走；
   国际赛事（大师赛/冠军赛）自动合并成「全部赛区」。核心是三个数：
   跨赛段相关 r、回归斜率、扣除回归均值后还剩哪些队是真变化。
   **残差用斜率算，不要用 r**（用 r 会算出大于原始变化的值，踩过）。
6. **地图选项按图池收缩。** 上海冠军赛只有 7 张图（无微风/裂变/深海），
   伦敦只有 7 张（无幽邃/天枢/日落）。现在全季有 12 张图，别写死数量。
7. **默认是「全部地图」，这样队伍表里的队数才和下拉框的队数对得上。**
   之前默认跳单张图，下拉说 16 支、表里只有 10 支，是用户实际踩到的坑。
8. **「全部地图」不画点，改画「按地图拆开的首杀表」**（`renderMapTable`）。
   10 张图共用一个 1024 网格，叠起来没有意义；点表里任意一行会跳到那张图的打点。
9. **英雄面板在"选定英雄"时切换成"这个英雄在哪张图拿首杀"**，
   并且**故意忽略地图筛选**（否则只剩一行）。
10. **队伍表在选了单一队伍时只显示那一队**，否则对手会混进来。
11. **队伍表里不足 40 回合的行整行淡化**（`tr.thinrow`）。
12. **队伍对比表是整页宽度，不在左右分栏里。** 8 列挤在半栏里列宽不够；
    `各赛事对比` 仍留在右栏，刚好把左右两栏的高度配平。
13. **筛选条 `position:sticky` 吸顶**，但 `max-width:900px` 以下关掉——
    手机上筛选条有一屏的一半高，吸顶会永远看不到内容。
14. **字体自托管在 `site/fonts/`**（`fonts.css` + 2 个 woff2，78 KB），
    不引 Google CDN：国内打不开，页面会卡在字体请求上。中文走系统字体。
15. **主题是浅色（纸白），不是深色。** 2026-10-26 从深色整体换成浅色，
    依据是实测了 VLR / RIB.GG / Leetify / Liquipedia 的配色（见 `DESIGN.md` 与
    `figures/_ref/probe.json`）。改主题只需要动两个页面的 `:root` 色板。
16. **浅色下队标要反过来处理。** 深色主题给纯黑队标垫白底（`plate`），
    浅色主题要给**纯白队标**垫深底（`plateLight`，TL / G2 / M80 三支）。
    两个字段都在 `teamMeta` 里，前端 `.plt` / `.pltl` 两个 class 分别对应。
17. **小地图有两套**：`site/maps/`（深色原图）与 `site/maps/light/`（反相生成）。
    浅色主题用 `maps/light/`，`renderMap` 里的路径别改回去。
18. **交互层**（2026-10-27 加）：命令面板 `/` 或 `⌘K`、URL 状态同步、排序 FLIP、KPI 数字滚动。
    这些都在 `site/index.html` 的「交互层」那一段，和渲染逻辑解耦，删掉不影响出数。
    - `syncURL()` 在 `recompute()` 末尾调用；`readURL()` 在 `boot()` 里、默认值之后调用。
    - `countUp()` **首屏不播**（`from == null` 直接 return），否则测试读到中间值会挂。
    - FLIP 动画结束必须清掉 `style.transform`，否则 hover 背景会被 transform 层叠住。
19. **队伍报告页也有 URL 状态**：`?team=...&map=...&ev=...`，配合头部的「复制链接」。
    测试 `94_verify_scout.py` 会切换下拉框，URL 会跟着变，这是预期行为。
20. **筛选条是下划线 tab，不是药丸。** 2026-10-27 改的：`.chip` 没有背景/描边/圆角，
    选中态是 2px 下划线（`box-shadow:inset 0 -2px 0`）。国际赛事只改文字颜色为金色。
    改回填充式药丸会让整页立刻变回模板样，别改。
21. **数据条画在单元格背景里**（`td.barcell{background-image + background-size:var(--w)}`），
    从**右侧**起铺、数字压在条上。不要改回 `::after` 画线——`::after` 会盖在文字上面。
22. **命令面板已整个删除**（2026-10-27）。筛选项就在屏幕上，63 支队的规模不需要搜索，
    那是"为技术力而技术力"。别再加回来。设计依据见 `DESIGN-REFS.html`。
23. **补枪面板是这一页的主角**，全宽、在筛选条正下方（`.panel.hero`）。
    两条横条按 0–100 同一把尺子铺（`#tradedBar` / `#untradedBar` 的 `style.width`），
    17→75 的长度差就是那 18.3 个百分点。别再把它塞回右栏变成三个数字。
24. **英雄是下拉（`#agentSelect`），不是 chip。** 33 个 chip 铺两行纯属噪音。
    选项随范围收缩（`agentsInScope()`），落在范围外会自动回落「全部英雄」。
25. **窄屏筛选默认收起**（`#fbody` + `#ftoggle`，`@media max-width:760px`）。
    手机上摊开是 532px 高，等于看不见内容；收起后 42px，摘要由 `updateFilterSummary()` 写。
26. **「可利用倾向」不写建议。** 每条只有「发生了什么 + 联赛基准」两段，
    例如「拿了首杀后赢下 73.4% 的回合 / 联赛 71.0% · +2.4pp」。
    **不要加回"建议怎么打"的段落**——那是替用户下结论，也是这页 AI 感的主要来源。
    测试 `94_verify_scout.py` 有两条按钮级断言：`.vtext` 必须为 0、文案里不许出现
    建议/应该/别指望/惩罚/准备。
27. **赛事和地图的回合数是联动的**（`facetCounts(except)`）。
    算赛事时排除赛事自己的筛选，算地图时排除地图自己的——否则选完地图，
    赛事选项的回合数会全变 0。副作用是正确行为：选「日落之城」后 PRX 只剩 2 个赛事。
28. **队伍报告的下拉是按队伍生成的**（`fillScopeSelects()`）。
    换队伍时必须重建，否则会出现"Paper Rex + 中国第二赛段"这种不存在的组合。
    选中项如果不在新范围里会回落到「全部赛事 / 全部地图」。
    **测试里要先选队伍、再选赛事**，反过来选不到（`94_verify_scout.py` 已按这个顺序写）。
   20 回合算出「阵容一致性 100%」没有意义，别让它看起来和大队一样可信。


---

## 五、已知的坑

### ⚠️ 绝对不要用 PowerShell 改这个项目的源文件

```powershell
# 会毁掉文件！中文全变乱码，UTF-8 → GBK 往返
Set-Content -Encoding utf8 xxx.py
Get-Content ... | Set-Content ...
```

已经踩了三次。**用 `edit` / `write` 工具，或者 Python。**

### 其他

- 服务器有时会被关掉（机器休眠）。重开即可，端口 8777。
- `x`/`y` 有 21 个点在 0–1024 之外（"Fall" 摔死），已在前端过滤。
- 队伍缩写（`GEN`）和全名（`Gen.G`）不同，靠 `_cache/tag_map.json` 映射。

---

## 六、测试

改完跑这两个，都是 Playwright：

```bash
cd "D:\好玩的项目\vct-first-blood-analytics"
python 35_download_fonts.py    # 拉 Inter / JetBrains Mono 的 latin 子集到 site/fonts/
python 65_ui_regress.py        # 43 项：UI 交互 + 队标 + 下拉联动 + 链接恢复 + 排序动画
python 92_verify_champions.py  # 17 项：冠军赛数据 + 术语表 + 15 个赛事下拉项
python 91_verify_metrics.py    # 11 项：指标数值与离线分析一致
python 94_verify_scout.py      # 66 项：队伍报告数值 + 阵容时间轴与离线重算一致
```

`94_verify_scout.py` 会重算 PRX / 日落之城的每一个数字并和页面比对，
包括补枪面板（**必须只用「本队拿到首杀」的回合**，否则差值会算成负数）。

阵容面板的行维度是跟着地图选择器变的（2026-11-03）：
「全部地图」→ 一行一张图；选定一张图 → 一行一个赛事，按时间先后排。
`94` 里两组断言分别校验这两个维度，还额外校验「同一套阵容在所有行同色」
（时间轴靠颜色认走势，撞色就看不出变化了）。

改了统计逻辑的话，`91_verify_metrics.py` 会检查前端算出来的
57.0% / 75.6% / 18.7pp 是否还和离线 `85_trade_sensitivity.py` 对得上。

---

## 七、如果你想改数据（不是页面）

```bash
python 90_site_data_v3.py     # 从 rounds_all.jsonl 重建 site_v3.json
# 记得复制到 site/data/：
copy data\site_v3.json site\data\site_v3.json
```

改 `rounds` 行的结构必须同步改 `60_site_data` 之外的**所有**下游脚本，慎动。

---

## 八、当前页面的指标口径

| 指标 | 定义 |
|---|---|
| 首杀→胜 | 拿首杀方赢下回合的比例。**全局基准 71.1%** |
| 被补枪 | 首杀者被死者队友 **5 秒内**击杀 |
| 被补→胜 / 没被补→胜 | 57.0% vs 75.6%，**差 18.7pp，全数据最强变量** |
| Meta Fit | 阵容里属该图 top7 版本英雄的比例 |
| 阵容一致性 | 最常用阵容的回合占比 |
| 首杀未被补 | 该队拿的首杀里没被补掉的比例 |

这些口径在页面的术语表（`GLOSSARY` 数组）里都有中文解释，改口径记得同步改文案。
