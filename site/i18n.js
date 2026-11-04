/* ==================================================================
   双语切换 / bilingual switch
   ------------------------------------------------------------------
   三个页面共用本文件。约定：

   · 字典按页面分组，键名带前缀（nav / ctl / duel / scout / ovw）
   · t(key, vars) 取当前语言，vars 用 {name} 占位
   · 数据里的专名（英雄、地图、队伍、赛事）不进字典：
     中文用 site_v3.json 的 zh 表，英文用原始英文名，走 pick()
   · 缺键直接返回键名并 console.warn，方便发现漏翻
   · 语言存 localStorage，也认 ?lang=en，方便分享链接
   ================================================================== */
(function () {
  'use strict';

  const DICT = {
    /* ---------------- 通用 ---------------- */
    'site':            { zh: '无畏契约 2026',        en: 'VALORANT 2026' },
    'site.short':      { zh: '无畏契约 2026 首杀',   en: 'VALORANT 2026 First Blood' },

    'nav.overview':    { zh: '总览',                en: 'Overview' },
    'nav.scout':       { zh: '队伍简报',            en: 'Team Brief' },
    'nav.duel':        { zh: '选手对比',            en: 'Player Comparison' },

    'ctl.event':       { zh: '赛事',                en: 'Event' },
    'ctl.map':         { zh: '地图',                en: 'Map' },
    'ctl.team':        { zh: '队伍',                en: 'Team' },
    'ctl.agent':       { zh: '英雄',                en: 'Agent' },
    'ctl.share':       { zh: '复制链接',            en: 'Copy link' },
    'ctl.copied':      { zh: '链接已复制',          en: 'Link copied' },
    'loading':         { zh: '加载中…',             en: 'Loading…' },

    'unit.round':      { zh: '回合',                en: 'rounds' },
    'unit.map':        { zh: '张地图',              en: 'maps' },
    'unit.event':      { zh: '个赛事',              en: 'events' },
    'unit.player':     { zh: '位选手',              en: 'players' },
    'unit.people':     { zh: '人',                  en: 'players' },

    'src.replay':      { zh: '数据源 vlr.gg 2D 回放', en: 'source: vlr.gg 2D replays' },
    'src.scraped':     { zh: '数据抓取自 vlr.gg 2D 回放', en: 'Scraped from vlr.gg 2D replays' },

    /* ---------------- 选手对比 duel.html ---------------- */
    'duel.title':      { zh: '选手对比 · 无畏契约 2026 首杀', en: 'Player Comparison · VALORANT 2026 First Blood' },
    'duel.h1':         { zh: '选手对比',            en: 'Player Comparison' },
    'duel.sub':        { zh: '首杀尝试',            en: 'First-blood attempts' },
    'duel.chart':      { zh: '首杀尝试',            en: 'First-blood attempts' },

    'duel.th.player':  { zh: '选手',                en: 'Player' },
    'duel.th.team':    { zh: '队伍',                en: 'Team' },
    'duel.th.tries':   { zh: '尝试',                en: 'Attempts' },
    'duel.th.fb':      { zh: '首杀',                en: 'First bloods' },
    'duel.th.rate':    { zh: '成功率',              en: 'Success' },
    'duel.th.per100':  { zh: '每百回合',            en: 'Per 100 rds' },
    'duel.th.share':   { zh: '队内占比',            en: 'Team share' },

    'duel.empty':      { zh: '这个赛事进入筛选的选手不足 2 人',
                         en: 'Fewer than 2 players qualify in this event' },

    'duel.scope':      { zh: '{ev} · 全部队伍 · {n} 人',
                         en: '{ev} · All teams · {n} players' },

    /* 图内标注：虚线是均值，必须写出来，否则读者只能猜 */
    'duel.mean':       { zh: '- - 虚线 = 均值 · 横 {x} · 纵 {y}%',
                         en: '- - dashed = mean · x {x} · y {y}%' },
    'duel.axis.x':     { zh: '首杀尝试 / 每 100 回合',
                         en: 'First-blood attempts per 100 rounds' },
    'duel.axis.y':     { zh: '首杀成功率',
                         en: 'Attempt success rate' },

    'duel.caption':    { zh: '队内首杀占比 ≥{share}% 且参与 ≥{tries} 次首杀尝试的选手'
                             + ' · 尝试次数 = 拿到的首杀 + 被别人首杀'
                             + ' · 虚线 = 这一屏 {n} 位选手的均值（横 {x}，纵 {y}%）',
                         en: "Players with ≥{share}% of their team's first bloods and ≥{tries} attempts"
                             + ' · An attempt = a first blood won or lost'
                             + ' · Dashed lines = mean of the {n} players shown (x {x}, y {y}%)' },

    'duel.sub2':       { zh: '{n} 个赛事 · {r} 回合 · 数据源 vlr.gg 2D 回放',
                         en: '{n} events · {r} rounds · source: vlr.gg 2D replays' },
    'duel.foot':       { zh: '数据抓取自 vlr.gg 2D 回放 · {n} 个赛事 · {r} 回合 · {m} 张地图',
                         en: 'Scraped from vlr.gg 2D replays · {n} events · {r} rounds · {m} maps' },

    "ovw.statConvBase": { zh: "全样本基准 {v}%", en: "League baseline {v}%" },
    "ovw.statAtk": { zh: "首杀来自进攻方", en: "First bloods taken on attack" },
    "ovw.statAtkSplit": { zh: "进攻 {atk} · 防守 {def}", en: "attack {atk} · defense {def}" },
    "ovw.statPace": { zh: "首杀中位时刻", en: "Median first-blood time" },
    "ovw.statPaceNote": { zh: "回合开局到首次击杀", en: "From round start to the opening kill" },
    "ovw.statGeo": { zh: "坐标覆盖", en: "Coordinate coverage" },
    "ovw.statGeoNote": { zh: "{n} / {total} 回合", en: "{n} of {total} rounds" },
    "ovw.shareTitle2": { zh: "复制当前筛选的链接", en: "Copy a link to the current filters" },
    "meta": { zh: "Meta Fit", en: "Meta Fit" },
    "k.roundwin": { zh: "回合胜率", en: "Round win rate" },
    "k.untraded": { zh: "首杀未被补", en: "First blood untraded" },
    "sel.allEvents": { zh: "全部赛事", en: "All events" },
    "sel.allMaps": { zh: "全部地图", en: "All maps" },
    "unit.round": { zh: "回合", en: "rounds" },
    "comp.wr": { zh: "胜率", en: "win rate" },
    "comp.tip.rounds": { zh: "{n} 回合", en: "{n} rounds" },
    "comp.tip.wr": { zh: "胜率 {v}", en: "{v} win rate" },
    /* ===== 总览 index.html ===== */
    "gl.btn": { zh: "指标说明", en: "Metric definitions" },
    "gl.title": { zh: "指标说明", en: "Metric definitions" },
    "gl.title2": { zh: "指标说明", en: "Metric definitions" },
    "ovw.agentHead": { zh: "{agent} · 共 {n} 次首杀", en: "{agent} · {n} first bloods" },
    "ovw.agentMaps": { zh: "这个英雄在哪些图拿首杀", en: "Where this agent gets first bloods" },
    "ovw.agentMaps2": { zh: "这个英雄在哪拿首杀", en: "Where this agent gets first bloods" },
    "ovw.agentTitle": { zh: "谁在拿首杀 · 英雄", en: "Who takes the first blood · by agent" },
    "ovw.agentTitle2": { zh: "谁在拿首杀 · 英雄", en: "Who takes the first blood · by agent" },
    "ovw.allShown": { zh: "共 {total} 种", en: "{total} agents" },
    "ovw.byMap": { zh: "首杀 · 按地图拆开", en: "First bloods by map" },
    "ovw.clickAgent": { zh: "点击任意英雄查看其首杀位置 · 共 {n} 个有记录", en: "Click an agent to see where it takes first bloods · {n} with records" },
    "ovw.collapse": { zh: "收起（只显示前 {n} 名）", en: "Collapse (top {n} only)" },
    "ovw.curTag": { zh: "·当前", en: " · current" },
    "ovw.empty2.b": { zh: "这个组合没有可绘制的位置", en: "Nothing to draw for this combination" },
    "ovw.empty2.l1": { zh: "当前筛选在这张图上没有首杀。", en: "No first bloods on this map in this scope." },
    "ovw.empty2.l2": { zh: "试试把「地图」切回「全部地图」，或换个队伍 / 英雄。", en: "Try switching Map back to “All maps”, or pick another team / agent." },
    "ovw.emptyCN.b": { zh: "中国赛区没有坐标数据", en: "The China league has no coordinate data" },
    "ovw.emptyCN.l1": { zh: "vlr.gg 上该赛区没有 2D 回放，无法绘制位置。", en: "vlr.gg offers no 2D replays for this league, so positions cannot be drawn." },
    "ovw.emptyCN.l2": { zh: "但这一筛选下的 {n} 个回合仍然计入", en: "The {n} rounds in this scope still count toward" },
    "ovw.emptyCN.l3": { zh: "右侧的英雄、武器与转化率统计。", en: "the agent, weapon and conversion stats on the right." },
    "ovw.eventCompare": { zh: "各赛事对比 · 固定基准", en: "Events compared · fixed baseline" },
    "ovw.expand": { zh: "展开全部 {n} 项", en: "Show all {n}" },
    "ovw.filters": { zh: "筛选", en: "Filters" },
    "ovw.fixedBase": { zh: "个赛事全样本，不随上方筛选变化）", en: " events, all rounds; not affected by the filters above)" },
    "ovw.foot1": { zh: "数据抓取自 vlr.gg 2D 回放 · {n} 个赛事", en: "Scraped from vlr.gg 2D replays · {n} events" },
    "ovw.foot2": { zh: "· {r} 回合 · {m} 张地图", en: " · {r} rounds · {m} maps" },
    "ovw.fullSeason": { zh: "整季", en: "Full season" },
    "ovw.fullSeasonN": { zh: "整季 {n} 个赛事", en: "Full season · {n} events" },
    "ovw.legendAtk": { zh: "进攻方首杀", en: "Attack-side first bloods" },
    "ovw.legendDef": { zh: "防守方首杀", en: "Defense-side first bloods" },
    "ovw.manyTeams": { zh: "（{scope} · 显示 {n} 支（≥{min} 回合）；淡化 = 不足 {thin} 回合）", en: "({scope} · {n} teams shown (≥{min} rounds); faded = under {thin} rounds)" },
    "ovw.mapMeta": { zh: "{ev} · {m} 张图 · {r} 回合", en: "{ev} · {m} maps · {r} rounds" },
    "ovw.mapMeta2": { zh: "{r} 回合 · 本图 {n} 次", en: "{r} rounds · {n} on this map" },
    "ovw.mapTableHead": { zh: "<th>地图</th><th>回合</th><th>首杀→胜</th><th>被补率</th><th>中位时刻</th>", en: "<th>Map</th><th>Rounds</th><th>FB → win</th><th>Traded</th><th>Median</th>" },
    "ovw.mapTitle": { zh: "首杀位置分布", en: "First blood positions" },
    "ovw.mapTitle2": { zh: "首杀位置分布 · {map}", en: "First blood positions · {map}" },
    "ovw.noData": { zh: "<tr><td colspan=\"3\" class=\"empty\">当前筛选下没有数据</td></tr>", en: "<tr><td colspan=\"3\" class=\"empty\">No data in this scope</td></tr>" },
    "ovw.noData2": { zh: "<tr><td colspan=\"7\" class=\"empty\">没有数据</td></tr>", en: "<tr><td colspan=\"7\" class=\"empty\">No data</td></tr>" },
    "ovw.noTeams": { zh: "<tr><td colspan=\"8\" class=\"empty\">当前筛选下没有队伍数据</td></tr>", en: "<tr><td colspan=\"8\" class=\"empty\">No team data in this scope</td></tr>" },
    "ovw.oneTeam": { zh: "（只看这一支 · {scope}）", en: "(this team only · {scope})" },
    "ovw.picked": { zh: "<span class=\"pickmark\">已选</span>", en: "<span class=\"pickmark\">selected</span>" },
    "ovw.scopeTitle": { zh: "切换：只看当前筛选 / 整季全样本", en: "Toggle: current filters / full season" },
    "ovw.shareTitle": { zh: "复制当前筛选的链接", en: "Copy a link to the current filters" },
    "ovw.site": { zh: "无畏契约 2026 首杀", en: "VALORANT 2026 First Blood" },
    "ovw.statConv": { zh: "首杀后赢下回合", en: "Rounds won after the first blood" },
    "ovw.sub1": { zh: "{e} 个赛事 · {m} 张地图 · {t} 支队伍", en: "{e} events · {m} maps · {t} teams" },
    "ovw.sub2": { zh: "· {r} 回合 · 数据源 vlr.gg 2D 回放", en: " · {r} rounds · source: vlr.gg 2D replays" },
    "ovw.teamCompare": { zh: "队伍对比", en: "Team comparison" },
    "ovw.thisEvent": { zh: "本赛事", en: "This event" },
    "ovw.thisEvent2": { zh: "本赛事", en: "This event" },
    "ovw.title": { zh: "总览 · 无畏契约 2026 首杀", en: "Overview · VALORANT 2026 First Blood" },
    "ovw.top5": { zh: "前 5 名", en: "Top 5" },
    "ovw.topShown": { zh: "前 {shown} 名 / 共 {total} 种", en: "Top {shown} of {total}" },
    "ovw.weaponTitle": { zh: "用什么拿的首杀", en: "What the first bloods come from" },
    "ovw.whoTitle": { zh: "谁在拿首杀", en: "Who takes the first blood" },
    "sel.allAgents": { zh: "<option value=\"-1\">全部英雄</option>", en: "<option value=\"-1\">All agents</option>" },
    "sel.allMaps2": { zh: "全部地图", en: "All maps" },
    "sel.allMapsN": { zh: "<option value=\"-1\">全部地图（{n} 张）</option>", en: "<option value=\"-1\">All maps ({n})</option>" },
    "sel.allTeams": { zh: "全部队伍", en: "All teams" },
    "sel.allTeamsN": { zh: "全部队伍（{n} 支）", en: "All teams ({n})" },
    "sel.eventOpt": { zh: "<option value=\"{i}\">{name}{nogeo}</option>", en: "<option value=\"{i}\">{name}{nogeo}</option>" },
    "sel.nogeo": { zh: "（无坐标）", en: " (no coordinates)" },
    "sel.onlyEvent": { zh: "仅显示 {n} 参赛的 {ev} 支队伍", en: "Only the {n} teams that played {ev}" },
    "sel.teamOpt": { zh: "{team}  ·  {n} 回合", en: "{team} · {n} rounds" },
    "skip": { zh: "跳到主内容", en: "Skip to main content" },
    "th.agent": { zh: "英雄", en: "Agent" },
    "th.atkShare": { zh: "攻方占比", en: "Attack share" },
    "th.event": { zh: "赛事", en: "Event" },
    "th.fb": { zh: "首杀", en: "First bloods" },
    "th.fbconv": { zh: "首杀→胜", en: "FB → win" },
    "th.fbrate": { zh: "首杀率", en: "FB rate" },
    "th.map": { zh: "地图", en: "Map" },
    "th.medianTime": { zh: "中位时刻", en: "Median time" },
    "th.metafit": { zh: "Meta Fit", en: "Meta Fit" },
    "th.recovery": { zh: "丢首杀→胜", en: "Recovery" },
    "th.rounds": { zh: "回合", en: "Rounds" },
    "th.share": { zh: "占比", en: "Share" },
    "th.snipe": { zh: "狙击首杀", en: "AWP first bloods" },
    "th.team": { zh: "队伍", en: "Team" },
    "th.tradedRate": { zh: "被补枪率", en: "Traded rate" },
    "th.untraded": { zh: "首杀未被补", en: "FB untraded" },
    "th.untradedWin": { zh: "未补→胜", en: "Untraded → win" },
    "th.weapon": { zh: "武器 / 技能", en: "Weapon / ability" },
    "toast.copied2": { zh: "链接已复制，可以直接发给别人", en: "Link copied — send it to anyone" },
    "toast.nocopy2": { zh: "浏览器不允许自动复制，请从地址栏复制", en: "The browser blocked the copy — copy from the address bar" },
    "toast.restored2": { zh: "已按链接恢复筛选条件", en: "Filters restored from the link" },
    /* ===== 队伍简报 scout.html ===== */
    "c.atk.main": { zh: "进攻方胜率 {v}%", en: "Attack win rate {v}%" },
    "c.avg.cmp": { zh: "平均 {v}% · {d}", en: "average {v}% · {d}" },
    "c.avg.cmp2": { zh: "平均 {v}% · {d}", en: "average {v}% · {d}" },
    "c.avg.cmp3": { zh: "平均 {v}% · {d}", en: "average {v}% · {d}" },
    "c.avg.cmp4": { zh: "平均 {v}% · {d}", en: "average {v}% · {d}" },
    "c.avg.cmp5": { zh: "平均 {v}% · {d}", en: "average {v}% · {d}" },
    "c.conc.cmp": { zh: "占队内 {share}% · 队内 {players} 人平摊各 {avg}%", en: "{share}% of the team's · an even split across {players} is {avg}% each" },
    "c.conc.main": { zh: "{name} 拿了 {n} 次首杀", en: "{name} has {n} first bloods" },
    "c.conc.med": { zh: "· 各队头名中位 {v}%", en: " · median team leader {v}%" },
    "c.def.main": { zh: "防守方胜率 {v}%", en: "Defense win rate {v}%" },
    "c.fbconv.main": { zh: "拿了首杀后赢下 {v}% 的回合", en: "Won {v}% of rounds after the first blood" },
    "c.fbrate.cmp": { zh: "每回合必有一方拿到首杀，两队平均 50%", en: "Exactly one team takes the first blood each round — 50% is the two-team average" },
    "c.fbrate.main": { zh: "首杀率 {v}%", en: "First-blood rate {v}%" },
    "c.full.main": { zh: "全买局胜率 {v}%", en: "Full-buy win rate {v}%" },
    "c.pace.cmp": { zh: "平均 {v} 秒 · {d} 秒", en: "average {v}s · {d}s" },
    "c.pace.main": { zh: "首杀中位时刻 {v} 秒", en: "Median first blood at {v}s" },
    "c.pistol.cmp": { zh: "每局必有一方赢，两队平均 50%", en: "One side wins every pistol round — 50% is the two-team average" },
    "c.pistol.main": { zh: "手枪局 {won}/{n}（{v}%）", en: "Pistol rounds {won}/{n} ({v}%)" },
    "c.traded.main": { zh: "首杀被补掉 {v}%", en: "First blood traded {v}% of the time" },
    "comp.bymap": { zh: "阵容 · 按地图", en: "Compositions · by map" },
    "comp.bytime": { zh: "阵容 · 按时间", en: "Compositions · by time" },
    "comp.col.event": { zh: "赛事", en: "Event" },
    "comp.col.map": { zh: "地图", en: "Map" },
    "comp.col.vr": { zh: "胜率 · 回合", en: "Win rate · rounds" },
    "comp.nodata": { zh: "<div class=\"small\">无数据</div>", en: "<div class=\"small\">no data</div>" },
    "comp.other": { zh: "其他 {n} 套", en: "{n} other comps" },
    "comp.other2": { zh: "其他 {n} 套", en: "{n} other comps" },
    "ctl.event": { zh: "赛事", en: "Event" },
    "ctl.map": { zh: "地图", en: "Map" },
    "ctl.pdf": { zh: "导出 PDF", en: "Export PDF" },
    "ctl.share": { zh: "复制链接", en: "Copy link" },
    "ctl.target": { zh: "目标队伍", en: "Target team" },
    "d.comp.map1": { zh: "每行一张图，按该队在这张图上的回合数排序。色块 = 该图最常用的几套阵容，", en: "One row per map, sorted by rounds played on it. Coloured blocks are the map's most-used compositions;" },
    "d.comp.map2": { zh: "灰 = 这张图上其余的阵容。悬停看阵容、份额与胜负。选一张地图可改看时间轴。", en: "grey is everything else on that map. Hover for the comp, share and record. Pick a single map to switch to the timeline." },
    "d.comp.time": { zh: "同一张图上按赛事先后排，条 = 该赛事里各阵容的份额。悬停看阵容、份额与胜负。", en: "One map, events in chronological order. Each bar is a composition's share within that event. Hover for the comp, share and record." },
    "d.conc1": { zh: "本队拿到的首杀里，队内拿得最多的那个人占了多大比例。", en: "How much of the team's first bloods the top player accounts for." },
    "d.conc2": { zh: "跟「队内平摊」比：5 个人平分是每人 20%，人数更多平分就更低。", en: "Compared with an even split: 20% each across five players; lower with a larger roster." },
    "d.conc3": { zh: "注意它和「开火点」报的是同一个数，只是一个放卡片一个放对比列表。", en: "This is the same number as “Opening concentration”, shown once as a card and once in the comparison list." },
    "d.fbconv1": { zh: "拿到首杀的回合里，最后赢下来的比例。", en: "Rounds won among those where the team took the first blood." },
    "d.fbconv2": { zh: "对比对象是当前筛选范围（同一赛事 / 同一地图）的回合加权平均：", en: "The baseline is the round-weighted average of the current scope (same event / same map):" },
    "d.fbconv3": { zh: "把该范围所有回合放一起算一个率，不是先算每队的率再平均。", en: "All rounds pooled into one rate — not an average of per-team rates." },
    "d.fbconv4": { zh: "全部赛事 + 全部地图时是 71%。", en: "Across all events and maps it is 71%." },
    "d.fbrate1": { zh: "本队拿到首杀的回合占它总回合的比例。反映打法激进还是保守，不反映强弱。", en: "Rounds where this team took the first blood, as a share of its rounds. Reflects aggression, not strength." },
    "d.fbrate2": { zh: "每回合总有一方拿到首杀，两队平均必然是 50%，所以这个数不用跟谁比。", en: "One team always gets the first blood, so the two-team average is necessarily 50% — no baseline needed." },
    "d.full1": { zh: "本回合队里持有 ≥4 把长枪的回合，也就是正常买枪的回合。", en: "Rounds where the team holds ≥4 primary rifles — i.e. a normal buy." },
    "d.full2": { zh: "长枪指 Vandal / Phantom / Guardian / Bulldog / Odin / Operator / Outlaw / Marshal。", en: "Primaries are Vandal / Phantom / Guardian / Bulldog / Odin / Operator / Outlaw / Marshal." },
    "d.full3": { zh: "不用「花了多少钱」是因为留枪会污染它：上回合保下来的枪记 0 花费，但照样能打。", en: "We do not use credits spent: saved weapons count as zero spend yet still shoot." },
    "d.meta1": { zh: "阵容里有多少个属于该图的版本英雄（每图全球选取率前 7）。", en: "How many of the five agents are meta picks for this map (top 7 by global pick rate)." },
    "d.meta2": { zh: "衡量这支队伍跟不跟版本，不衡量强弱。", en: "Measures whether the team follows the meta — not how good it is." },
    "d.pistol1": { zh: "每张图的上半场第 1 回合和下半场第 13 回合，双方都只能用手枪和基础装备。", en: "Round 1 of each half — round 1 and round 13 — where both sides are limited to pistols and basic gear." },
    "d.pistol2": { zh: "共 2 个，样本天然很小。", en: "Only two per map, so the sample is inherently small." },
    "d.traded1": { zh: "本队拿到首杀的回合里，那个首杀者被对方队友在 5 秒内反杀的比例。", en: "Share of your first bloods where the killer was avenged within 5 seconds." },
    "d.traded2": { zh: "越高说明打完首杀容易被换掉。", en: "Higher means your first bloods get traded more often." },
    "d.untraded1": { zh: "本队拿到首杀之后，那个首杀者没有被对方队友在 5 秒内反杀的比例。", en: "Share of your first bloods that were not avenged within 5 seconds." },
    "d.untraded2": { zh: "「被补枪」= 首杀者在 5 秒内被死者的队友击杀，也就是 1 换 1 回到 4v4。", en: "“Traded” means the first-blood killer was killed by a teammate of the victim within 5 seconds — a 1-for-1 back to 4v4." },
    "d.untraded3": { zh: "这个 5 秒窗口不是官方规则，是本站自己定的口径，写死在数据里。", en: "The 5-second window is our own definition, not an official rule; it is baked into the data." },
    "foot.a": { zh: "数据抓取自 vlr.gg 2D 回放 · {n} 个赛事", en: "Scraped from vlr.gg 2D replays · {n} events" },
    "foot.b": { zh: "· {n} 回合", en: " · {n} rounds" },
    "foot.c": { zh: "· {n} 张地图", en: " · {n} maps" },
    "h.econ": { zh: "经济覆盖 {v}%", en: "economy coverage {v}%" },
    "h.geo": { zh: "坐标覆盖 {v}%", en: "coordinate coverage {v}%" },
    "h.meta": { zh: "{r} 回合 · {m} 张图 · {e} 个赛事", en: "{r} rounds · {m} maps · {e} events" },
    "h.small": { zh: "样本偏小（{n} 回合）", en: "small sample ({n} rounds)" },
    "h.smallbadge": { zh: "<span style=\"color:var(--amber)\">小样本</span>", en: " <span style=\"color:var(--amber)\">small sample</span>" },
    "k.roundwin": { zh: "回合胜率", en: "Round win rate" },
    "k.untraded": { zh: "首杀未被补", en: "First blood untraded" },
    "m.atk": { zh: "进攻端", en: "Attack" },
    "m.conc": { zh: "开火点", en: "Opening concentration" },
    "m.def": { zh: "防守端", en: "Defense" },
    "m.fbconv": { zh: "首杀转化", en: "FB conversion" },
    "m.fbrate": { zh: "首杀率", en: "FB rate" },
    "m.full": { zh: "全买局", en: "Full buys" },
    "m.pace": { zh: "开局时机", en: "Opening timing" },
    "m.pistol": { zh: "手枪局", en: "Pistol rounds" },
    "m.traded": { zh: "被补率", en: "Traded rate" },
    "nav.duel": { zh: "选手对比", en: "Player Comparison" },
    "nav.overview": { zh: "总览", en: "Overview" },
    "nav.scout": { zh: "队伍简报", en: "Team Brief" },
    "p.atk": { zh: "进攻手枪", en: "Attack pistols" },
    "p.base": { zh: "· 同范围进攻方拿手枪 {v}%", en: " · attackers in this scope win {v}% of them" },
    "p.def": { zh: "防守手枪", en: "Defense pistols" },
    "p.n": { zh: "{n} 个手枪局（每张图 2 个）", en: "{n} pistol rounds (2 per map)" },
    "p.winrate": { zh: "手枪局胜率", en: "Pistol round win rate" },
    "sc.scope": { zh: "当前范围 <b>{n}</b> 回合<br>{map}", en: "Current scope <b>{n}</b> rounds<br>{map}" },
    "scout.comp": { zh: "阵容", en: "Compositions" },
    "scout.h1": { zh: "队伍简报", en: "Team Brief" },
    "scout.kpi": { zh: "核心指标", en: "Key metrics" },
    "scout.pistol": { zh: "手枪局", en: "Pistol rounds" },
    "scout.sides": { zh: "攻防分侧", en: "Attack / defense split" },
    "scout.sub": { zh: "赛前对手准备 · 基于 vlr.gg 2D 回放的回合级数据", en: "Opponent prep · round-level data from vlr.gg 2D replays" },
    "scout.timing": { zh: "首杀时刻", en: "When first blood happens" },
    "scout.title": { zh: "队伍简报 · 无畏契约 2026 首杀", en: "Team Brief · VALORANT 2026 First Blood" },
    "scout.verdict": { zh: "与当前范围的平均对比", en: "Against the current scope's average" },
    "scout.who": { zh: "谁在开火", en: "Who takes the opening duel" },
    "sel.allevents": { zh: "<option value=\"-1\">全部赛事（{n} 个）</option>", en: "<option value=\"-1\">All events ({n})</option>" },
    "sel.nEvents": { zh: "（{n} 个）", en: " ({n})" },
    "sel.nMaps": { zh: "（{n} 张）", en: " ({n})" },
    "sel.allmaps": { zh: "<option value=\"-1\">全部地图（{n} 张）</option>", en: "<option value=\"-1\">All maps ({n})</option>" },
    "sel.event": { zh: "<option value=\"{i}\">{name} · {n} 回合</option>", en: "<option value=\"{i}\">{name} · {n} rounds</option>" },
    "sel.map": { zh: "<option value=\"{i}\">{name} · {n} 回合</option>", en: "<option value=\"{i}\">{name} · {n} rounds</option>" },
    "site": { zh: "无畏契约 2026", en: "VALORANT 2026" },
    "t.conc": { zh: "首杀集中度", en: "First-blood concentration" },
    "t.fbconv": { zh: "首杀转化", en: "FB conversion" },
    "t.fbrate": { zh: "首杀率", en: "FB rate" },
    "t.full": { zh: "全买局", en: "Full buy" },
    "t.meta": { zh: "版本契合", en: "Meta fit" },
    "t.pistol": { zh: "手枪局", en: "Pistol round" },
    "t.traded": { zh: "首杀被补率", en: "Traded first-blood rate" },
    "th.agent": { zh: "主用英雄", en: "Main agent" },
    "th.fb": { zh: "首杀", en: "First bloods" },
    "th.fbconv": { zh: "首杀→胜", en: "FB → win" },
    "th.fbrate": { zh: "首杀率", en: "FB rate" },
    "th.per10": { zh: "每 10 回合", en: "Per 10 rounds" },
    "th.player": { zh: "选手", en: "Player" },
    "th.rounds": { zh: "回合", en: "Rounds" },
    "th.share": { zh: "占队内", en: "Team share" },
    "th.side": { zh: "位置", en: "Side" },
    "th.winrate": { zh: "胜率", en: "Win rate" },
    "tm.note": { zh: "中位 {v} 秒 · {n} 次有记录", en: "median {v}s · {n} recorded" },
    "toast.copied": { zh: "链接已复制，可以直接发给教练", en: "Link copied — send it straight to the coach" },
    "toast.nocopy": { zh: "浏览器不允许自动复制，请从地址栏复制", en: "The browser blocked the copy — copy from the address bar" },
    "toast.restored": { zh: "已按链接恢复筛选", en: "Filters restored from the link" },
    "v.empty": { zh: "<div class=\"vnone\">这个范围里没有可比的指标。</div>", en: "<div class=\"vnone\">No comparable metrics in this scope.</div>" },
    "v.none": { zh: "这个范围里没有可比的指标。", en: "No comparable metrics in this scope." },
    "v.title": { zh: "对比 {scope} 的平均", en: "Against the average of {scope}" },
    "w.allevents": { zh: "全部赛事", en: "all events" },
    "w.allmaps": { zh: "全部地图", en: "all maps" },
    "w.allscope": { zh: "全部赛事 · 全部地图", en: "all events · all maps" },
    "w.attacker": { zh: "进攻", en: "Attack" },
    "w.avg": { zh: "平均", en: "avg" },
    "w.bench": { zh: "基准", en: "baseline" },
    "w.defender": { zh: "防守", en: "Defense" },
    "w.flat": { zh: "平摊", en: "even split" },
    "w.nocomp": { zh: "这个赛事没有阵容数据", en: "No composition data for this event" },
    "w.nocompmap": { zh: "这张图没有阵容数据（中国赛区不提供）", en: "No composition data for this map (not provided by the China league)" },
    "w.nocompscope": { zh: "这个范围没有阵容数据（中国赛区不提供）", en: "No composition data in this scope (not provided by the China league)" },
    "w.nocoord": { zh: "无坐标数据", en: "no coordinate data" },
    "w.nodata": { zh: "无数据", en: "no data" },
    "w.noecon": { zh: "无经济数据", en: "no economy data" },
    "w.nofb": { zh: "这个范围没有首杀记录", en: "No first bloods in this scope" },
    "w.nofbrows": { zh: "<tr><td colspan=\"5\" class=\"small\">这个范围没有首杀记录</td></tr>", en: "<tr><td colspan=\"5\" class=\"small\">No first bloods in this scope</td></tr>" },
    "w.nopistol": { zh: "这个范围没有手枪局数据", en: "No pistol rounds in this scope" },
    "w.notiming": { zh: "没有时刻数据", en: "no timing data" },
    "w.roundweighted": { zh: "回合加权", en: "Round-weighted" },
    "w.small": { zh: "小样本", en: "small sample" },
  };

  const ORDER = ['zh', 'en'];
  const STORE = 'vct.lang';
  let lang = 'zh';

  function valid(x) { return ORDER.indexOf(x) >= 0; }

  function readLang() {
    try {
      const q = new URLSearchParams(location.search).get('lang');
      if (q && valid(q)) return q;
      const s = localStorage.getItem(STORE);
      if (s && valid(s)) return s;
    } catch (e) { /* 无痕模式 / file:// */ }
    return 'zh';
  }

  /* 缺键记录：测试会读 window.__i18nMissing，漏翻一个键就报出来 */
  window.__i18nMissing = [];

  function t(key, vars) {
    const e = DICT[key];
    if (!e) {
      if (window.__i18nMissing.indexOf(key) < 0) window.__i18nMissing.push(key);
      console.warn('[i18n] 缺键 missing key:', key);
      return key;
    }
    let s = e[lang] != null ? e[lang] : e.zh;
    if (vars) {
      s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
    }
    return s;
  }

  /* 专名的取法：中文查 zh 表，英文用原名 */
  function pick(zhValue, enValue) {
    return lang === 'zh' ? zhValue : enValue;
  }

  /* 静态标记：data-i18n 改文本，data-i18n-html 改 HTML，data-i18n-title 改 title */
  function applyStatic(root) {
    const scope = root || document;
    scope.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-html]').forEach(el => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    scope.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    const tb = document.querySelector('title[data-i18n]');
    if (tb) document.title = t(tb.getAttribute('data-i18n'));
  }

  function paintSwitch() {
    document.querySelectorAll('.langsw .lb').forEach(b => {
      const on = b.getAttribute('data-lang') === lang;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function buildSwitch(slot) {
    slot.innerHTML =
      '<span class="langsw" role="group" aria-label="Language / 语言">' +
      ORDER.map(l =>
        '<button type="button" class="lb" data-lang="' + l + '">' +
        (l === 'zh' ? '中' : 'EN') + '</button>').join('') +
      '</span>';
    slot.querySelectorAll('.lb').forEach(b => {
      b.addEventListener('click', () => setLang(b.getAttribute('data-lang')));
    });
  }

  function setLang(next) {
    if (!valid(next) || next === lang) return;
    lang = next;
    try { localStorage.setItem(STORE, lang); } catch (e) { /* 忽略 */ }
    try {
      const u = new URL(location.href);
      u.searchParams.set('lang', lang);
      history.replaceState(null, '', u);
    } catch (e) { /* file:// */ }
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    applyStatic();
    paintSwitch();
    window.dispatchEvent(new CustomEvent('langchange', { detail: { lang: lang } }));
  }

  function boot() {
    lang = readLang();
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    const slot = document.getElementById('langSlot');
    if (slot) buildSwitch(slot);
    applyStatic();
    paintSwitch();
  }

  window.I18N = {
    t: t,
    pick: pick,
    lang: function () { return lang; },
    setLang: setLang,
    applyStatic: applyStatic,
    dict: DICT,
  };
  window.t = t;
  window.pick = pick;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
