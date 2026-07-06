# 任务规范 · sourcing（找货源）

> 引擎协议总则见根目录 `AGENTS.md` §2（认领→干活→写回→收尾→原子写）。本文件只讲 sourcing 任务怎么干。

## 目标
给任务里的每个品卡（`product_ids`），在 **1688** 找到 **≥2 个可用候选货源**，写进品卡 `sources[]`，品卡状态推到 `sourced`。

## 输入
- 品卡 `source_data`：商品名（多为英文/马来文）、类目、售价区间 RM、TikTok 链接（如有）。
- 任务 `params.min_candidates`（默认 2）。

## 怎么找（按优先级）
1. **图搜同款（最准）**：拿到商品主图（TikTok 商品页/出海匠），在 1688 用图片搜索（拍立淘）。用你的浏览器 MCP 操作（Claude→claude-in-chrome；Codex→Playwright MCP）。
2. **译中文再搜**：把商品名翻成**中文核心词**（你自己翻，不用外部 API），在 1688 关键词搜索。英文名直搜基本无效。
3. 没有浏览器能力时：把翻好的中文关键词和建议写进 `result_note`，任务标 `failed`，等人/其他引擎接手。

## 筛选标准（不合格的不要写入）
- **支持一件代发**（无货源模式必需）；48h 内发货为佳。
- 进货价合理：结合品卡售价区间倒推——**粗验：进货价(元) × 1.55 ≈ RM 成本，不得逼近售价**；>50 元或大件(>500g)要在 notes 标注运费风险。
- 发货地：**离广东东莞越近越好**（达意仓在东莞洪梅）。
- 店铺信誉：回头率/评分/年限可见则记录。

## 写回（只动这些字段）
对每个品卡：
1. `sources[]` 追加候选（字段见 `workspace/schema/products.schema.json` 的 sources 定义）：
   `id`(s1/s2 递增)、`url`、`title`、`price_rmb`、`weight_g`(拿不到填 null 并在 notes 说明)、
   `moq`、`ship_from`、`supports_dropship`、`seller_rating`、`notes`、`added_by`(你的名字)、`added_at`。
2. 品卡 `status` → `sourced`；`log[]` 追加一条（写清找到几个、用什么方式找的）。
3. 全部品卡处理完 → 任务 `done` + `result_note`；部分失败照实写明哪几个品没找到源。

## 红线
- **不许编造**价格/重量/链接——拿不到就 null + notes 说明。
- 不写任何账号/登录信息进文件。
- 重量拿不准时在 notes 标注"重量为估计值，采购前向源头确认实重"（重量直接影响运费与利润）。
