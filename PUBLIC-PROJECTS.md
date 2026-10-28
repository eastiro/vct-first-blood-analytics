# 公开项目地图 · 别人是怎么做 Valorant 数据分析的

2026-10-26 整理。按「数据源 → 采集解析 → 分析 → 产品」四层看，
每一层列 2–3 个真实存在的项目，并标出**能直接借用什么**。

---

## ① 数据源层

| 来源 | 有什么 | 代价 |
|---|---|---|
| **vlr.gg 2D 回放** | 回合级事件流：KILL / PLANT / DEFUSE / BOOM / RESURRECT，1024 网格坐标、视角角度、距离、买枪 | 无官方 API，要抓；中国赛区无回放 |
| **Riot 官方 API** | `VAL-MATCH-V1` 等，需要 RSO 授权 | 赛事级数据由 GRID 代理，个人拿不到 |
| **GRID Esports** | 官方赛事数据合作方，RIB.GG 和战队用的就是它 | 商业授权 |
| **Kaggle `ryanluong1/valorant-champion-tour-2021-2026-data`** | 131 个 CSV / 84 MB，2021–2026 全赛季 | 免费，但字段是别人整理过的中间层 |
| **Kaggle `joshzeng` VCT 数据集** | 343 文件 / 563 MB | 同上，更原始 |
| **valorant-api.com** | 英雄 / 武器 / 地图素材 + 官方 `zh-CN` 名称 | 免费，你已经用了 |

> 注：Kaggle 那两个数据集本身就是抓 vlr.gg 整理的，等于别人的解析结果。
> 有用，但不能替代你自己的解析链路——简历上"我抓的"和"我下了别人的 CSV"是两回事。

---

## ② 采集 / 解析层

| 项目 | 技术栈 | 做到哪一步 | 能白拿什么 |
|---|---|---|---|
| **vlrggapi**（axsddlr / jordyvandijken） | FastAPI + requests + selectolax，Vercel 部署，300 秒缓存 | 赛事、比分、战排、选手统计 | 最经典的抓取模板；缓存与部署方式值得抄 |
| **metehansenyer/vlrgg-api** | FastAPI + httpx + Pydantic，全 async | 同上，结构更干净 | **出站限速 0.5–2 秒、并发上限 2** —— 反爬礼节的标准写法 |
| **vlrdevapi**（Vanshbordia，PyPI 3.0.0） | Python 库，Pydantic 模型，token bucket + 指数退避 | **2D 回放全事件 + 买枪矩阵** | 见下 |
| **Henrik 非官方 API** | 逆向游戏内接口 | 天梯对局、单场 round 级 player stats + kills | 200 请求 / 2 分钟 / IP；适合天梯，不是 VCT 全覆盖 |
| **valoscribe** | OpenCV + Tesseract + yt-dlp | 从 YouTube VOD 的观战 HUD 里抽事件 | **唯一能拿到「技能释放」的公开路线** |

### `vlrdevapi` 的字段（这是重点）

`series.replay(series_id, game_id)` 返回每回合的事件流，每个事件带：

```
type      KILL / PLANT / DEFUSE / BOOM / RESURRECT
site      A 或 B        ← 下包/拆包在哪个点
pos_x/y   1024 网格坐标
from_x/y  开火者位置（击杀事件）
view_angle 视角角度
distance_units  双方距离
alive     每个死伤瞬间全体存活玩家的坐标 + 朝向
```

以及 `PlayerRoundLoadout` 里的 `weapon / armor / spent / credits_left`，
和球队级的 `loadout_value` + 买枪分类（`Eco / Anti-eco / Semi-buy / Semi-rifle / Full buy`）。

> `BOOM`（炸弹爆炸）和 `RESURRECT`（复活）是**派生**事件（`derived: True`），
> vlr.gg 本身不把它们记成日志行，靠前后状态推出来。这解释了为什么覆盖率低。

---

## ③ 分析层

| 项目 | 做了什么 | 值得学的地方 |
|---|---|---|
| **VCT Erdos Institute（2024，Riot 是 stakeholder）** | 用常规赛数据预测 2023 淘汰赛结果；自己造了两个指标 `eco_rating` 和 `special_kills_rating`；每张图约 160 个特征 | 把 rating 和角色做**交互项**（"打 Controller 且 rating 1.2"）。缺点也诚实写了：特征多、样本少 |
| **UsableAI Final Project** | XGBoost 预测回合胜率，自变量是 buy category + agent comp | 局限写得比结论还好：rare comps 样本太少、没建模回合间动量、职业数据不能推广到天梯 |
| **Piyush / Champions 2024 分析** | 5 个 notebook（英雄 / 地图 / 选手 / 经济）+ PDF 报告 + Kaggle 数据集 | **最接近「作品集」的形态**：有数据、有分隔清晰的 notebook、有一份给非技术读者的 PDF |
| **Elevated（1trick.gg）** | Meta Fit 方法论 | 你已经复现了他的 r=+0.027 |
| **Roux Institute × Omnic** | 1.45 亿回合的四个独立分析 | 你已经用 15,715 职业回合复核过 |

---

## ④ 产品层

| 产品 | 功能 | 数据来源 |
|---|---|---|
| **RIB.GG** | **Match Prep**（任意队伍的球探报告：地图战绩 + 常用阵容）、Round Explorer（逐回合看回合怎么赢的）、2D 回放 + VOD 同步 + 可分享链接 | GRID（商业授权） |
| thespike.gg / escharts | 统计、赔率、赛程 | 自建 |
| **vlrinspect** | 个人 Streamlit 项目：队伍历史 / 交手记录 / 地图级统计三层爬取 | 自抓 vlr.gg |

**RIB.GG 是最直接的对标，而且它已经把「球探报告」做成产品功能了。**
它的 2D 回放 support 里还自己列了一条 known issue：
「Ability Locations Not Displayed — due to data limitations」——
就是说**连商业数据源也给不了技能落点**。这条路大家都堵着。

---

## ⑤ 三个判断

### 1. 「球探报告」不是空白

RIB.GG 的 Match Prep 已经在做同一件事。所以你的差异化不能是"我也做了一个球探报告"，
只能是**更具体的结论**或**更干净的公开数据链路**。前者你已经有了（补枪 18.7pp 的稳健性检验、
首杀转化随买枪从 89.6% 掉到 29.9%）；后者是你自己从 HTML 一路解析出来的，RIB 是买的数据。

### 2. 想在简历上放"分析"而不只是"工具"，缺的是一句可检验的话

搜到的这几个项目里，写得最像分析师的是 UsableAI 的**局限性章节**——
它敢说"rare comps 样本太少，所以这个结论不可信"。
你已经有素材了（补枪效应排除经济混杂、Meta Fit 复现、跨图极差的噪声解释），
现在缺的是把它们组织成"我提出假设 → 我怎么驳倒它 → 剩下什么"。

### 3. 你不欠数据，欠的是**没把已经解析出来的事件用上**

见下一节。

---

## ⑥ 你项目里的一个具体发现：PLANT / DEFUSE 被丢掉了

`30_crawl.py` 第 37–38 行：

```python
from vlrdevapi._series.replay.models import ReplayEventType
from vlrdevapi._series.replay.parser import parse_replay_data
```

也就是说，**你的爬虫本来就在用 vlrdevapi 的完整回放解析器**，
它返回的事件里包含 PLANT / DEFUSE / BOOM / RESURRECT，每个都带 `site`（A/B）和坐标。

然后第 221 行：

```python
if ev.type is not ReplayEventType.KILL:
    continue
```

**除了击杀，全部扔掉。**

所以：

- 「做不了 A/B 点和包点分析」这句话是错的——**数据一直在你手里，被一行过滤丢掉了**
- `boom_at` 只有 9.9% 覆盖的原因也清楚了：`BOOM` 是派生事件，vlr.gg 不直接记，
  能推出来的回合本来就少。它不是"下包时间"的可靠来源，`PLANT` 事件才是
- 修复成本：去掉那个过滤 + 在 `kills`/新字段里保留 `type/site/pos_x/pos_y`，
  然后重跑抓取（每场 1.1 秒，741 张图约 15 分钟起步）

补上之后能立刻做的三件事：

1. **A 点 / B 点的下包数与转化率**（Roux 研究里最强的一条，16pp 差距）
2. **首杀位置 → 最终包点** 的路径分析（开局在这儿开火，最后打的是哪个点）
3. **防守方反抢时间**：DEFUSE 事件带坐标和时间，能算"从下包到拆包"的时长分布

---

## ⑦ 建议的下一步顺序

1. **补 PLANT/DEFUSE** —— 成本最低、结论最硬。改一处过滤，重爬一遍。
2. **拿 Kaggle 那个 2021–2026 数据集做交叉验证** —— 免费的外部真值，
   可以校验你自己的解析有没有错（尤其是回合胜负和买枪分类）。
3. **技能释放** —— 只有 valoscribe 那条路（CV + OCR 解析 VOD），
   成本高、只覆盖有观战 HUD 的 VOD，但如果做出来就是别人没有的。
4. 别急着做预测模型。Erdos 和 UsableAI 都栽在样本量上，
   15,715 回合做回合级分析够，做"预测淘汰赛"远远不够。
