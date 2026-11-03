# 无畏契约 2026 · 首杀分析

**线上站点 → https://eastiro.github.io/vct-first-blood-analytics/**

从 [vlr.gg](https://www.vlr.gg) 的 2D 回放里提取 **32,786 个回合**的首杀事件，
做成一个只讲首杀的静态站点：首杀发生在哪、谁拿的、用什么拿的、拿到之后赢不赢。

**15 个赛事 · 1,545 张地图 · 32,786 回合 · 228,904 次击杀 · 63 支队伍**

---

## 跑起来

线上版由 GitHub Pages 从 `site/` 直接发布，纯静态、无构建步骤。

本地跑：

```bash
cd site
python -m http.server 8777 --bind 127.0.0.1
# 打开 http://127.0.0.1:8777/
```

推送 `site/` 的改动到 `master` 会自动重新部署（见 `.github/workflows/pages.yml`）。

三个页面：

| 页面 | 文件 | 内容 |
|---|---|---|
| **总览** | `site/index.html` | 首杀位置分布、英雄与武器、队伍与赛事对比 |
| **队伍简报** | `site/scout.html` | 单队的赛前对手准备报告，可导出 PDF |
| **选手对比** | `site/duel.html` | 谁参与首杀对决多、谁赢得多 |

页面直接读 `site/data/site_v3.json` 与 `site/data/site_v5.json`（共 3.9 MB），
不需要任何后端。

---

## 目录

```
site/               静态站点（GitHub Pages 发布的就是这个目录）
  data/             站点读的数据（派生结果）
  fonts/ maps/ logos/

.github/workflows/
  pages.yml         推送 site/ 后自动部署到 Pages

data/               分析用的数据
  site_v3.json      站点主数据
  site_v5.json      站点数据（含阵容）
  analysis.json     汇总指标

scripts/            全部脚本，按流水线阶段分目录
  01_recon/         最早的爬虫原型（只针对 Ascent）
  02_probe/         摸清 vlr.gg 回放结构
  03_manifest/      抓取清单与中文化
  04_crawl/         正式抓取
  05_analyse/       补枪、经济、分侧等分析
  06_site/          建站与 UI 测试
  07_study/         深入检验（补枪敏感度、Meta Fit）
  08_pipeline/      现役管线 + 回归测试

docs/               结论、设计、交接文档
figures/            图表与截图
  charts/ maps/ site/ reference/ history/ deslop/

maps/               12 张地图的俯视底图
```

---

## 重新生成数据

原始抓取数据（`data/rounds*.jsonl`，220 MB）不在仓库里——超过 GitHub 单文件
100 MB 上限。需要的话重新跑：

```bash
python scripts/04_crawl/30_crawl.py            # 从 vlr.gg 重抓
python scripts/08_pipeline/90_site_data_v3.py  # 生成 site_v3.json
python scripts/08_pipeline/93_site_data_v5.py  # 生成 site_v5.json
```

脚本用绝对路径常量定位仓库根目录，与当前工作目录无关，在任何位置都能运行。

---

## 测试

```bash
python scripts/08_pipeline/91_verify_metrics.py    # 12 项
python scripts/08_pipeline/92_verify_champions.py  # 17 项
python scripts/06_site/65_ui_regress.py            # 39 项
python scripts/08_pipeline/94_verify_scout.py      # 46 项
```

共 114 项断言，用 Playwright 打开真实页面，把每个数字和离线重算的结果逐项比对。

---

## 几个关键定义

| 术语 | 定义 |
|---|---|
| 首杀 | 一个回合里的第一次击杀 |
| 补枪 | 首杀发生后 **5 秒内**，死者的队友击杀首杀者 |
| 首杀→胜 | 拿到首杀的一方赢下该回合的比例（全季 **71.0%**） |
| Meta Fit | 阵容 5 个英雄里有几个是该图全球选取率前 7 的版本英雄 |

**基准口径**：一律用**回合加权平均**——把当前筛选范围内的所有回合放在一起算一个率。
同一赛事、同一地图各自对应各自的平均，不拿全季平均去比单张图。

---

## 一个统计上要小心的地方

「被补枪的首杀」和「没被补枪的首杀」胜率差 **18.8 个百分点**
（56.9% vs 75.7%），但这个差距**不是补枪技巧**，而是人数差：

- 首杀未被补 → 5v4
- 首杀被补掉 → 4v4

数据里 4v4 的胜率恰好是 **49.9%**。所以那 18.8pp 比的是「多一个人」，
不是「会补枪」。补枪真正有信息量的是**时机**：补得越快，首杀方越吃亏
（0 秒补 53.4% → 5 秒补 61.3%）。

---

## 中国赛区缺坐标

vlr.gg 上 VCT 中国赛区（第一 / 第二赛段）的比赛页面写着
“No 2D replay available for this match”，没有提供回放数据。
所以中国赛区有击杀、英雄、武器、时间、补枪数据，**没有位置坐标与经济数据**，
不出现在地图打点上。这不是抓取失败——同在上海办的全球冠军赛 2026 就有完整回放。

---

## 文档

| 文件 | 内容 |
|---|---|
| [CONCLUSIONS.md](docs/CONCLUSIONS.md) | 全季结论，以及这些榜单有多少可信 |
| [RESULTS.md](docs/RESULTS.md) | 分赛事的基准数字 |
| [AUDIT.md](docs/AUDIT.md) | 数据口径自查 |
| [TEAMS.md](docs/TEAMS.md) | 队伍名单与缩写 |
| [DESIGN.md](docs/DESIGN.md) | 视觉决策与去模板化规则 |
| [DESIGN-REFS.html](docs/DESIGN-REFS.html) | 参考站截图逐条对照（独立页面） |
| [HANDOFF.md](docs/HANDOFF.md) | 交接说明 |
| [PORTFOLIO.md](docs/PORTFOLIO.md) | 项目说明 |

---

## 许可

数据版权归 vlr.gg 与各赛事方。代码可自由参考。
