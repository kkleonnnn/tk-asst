# workspace/ —— 数据总线（驾驶舱与引擎的共同状态源）

> tk-asst v2 的核心协议：**驾驶舱（automation/ 网页）和引擎（任何 AI agent）都读写这里的文件**，互不直连。
> ⚠️ **本目录的真实经营数据不入库**（`products.json` / `tasks.json` / `exports/` 已被 `.gitignore` 挡住）——本仓库 PUBLIC 公开。入库的只有本说明、`schema/`（数据模式）、`examples/`（脱敏示例）。

## 文件一览

| 文件 | 是什么 | 谁写 | 入库? |
|---|---|---|---|
| `products.json` | **品库**：每个商品一张「品卡」，从导入到测款全生命周期 | 驾驶舱（导入/打分/选源/定价）＋引擎（货源/素材） | ❌ 真实数据 |
| `tasks.json` | **任务队列**：驾驶舱派发给引擎的待办（找货源/做素材） | 驾驶舱创建，引擎认领/完成 | ❌ |
| `exports/` | 上架素材包输出（每品一个 zip/目录） | 引擎/驾驶舱 | ❌ |
| `schema/` | 上述文件的 JSON Schema（协议定义） | kk 维护 | ✅ |
| `examples/` | 脱敏示例（学格式用） | kk 维护 | ✅ |

## 品卡状态机

```
imported → scored → selected → sourcing → sourced → priced
        → listing_ready → exported → published → testing → archived
（任意阶段可 → dropped 淘汰）
```

| 状态 | 含义 | 谁推进 |
|---|---|---|
| `imported` | 从出海匠导入，未打分 | 驾驶舱 |
| `scored` | 已打分 | 驾驶舱 |
| `selected` | 人工勾选决定做 | **人** |
| `sourcing` | 已派发找货源任务 | 驾驶舱 |
| `sourced` | 已有 ≥1 个候选货源（`sources[]` 有货） | **引擎/人** |
| `priced` | 人选定货源（`chosen_source_id`）且利润已算（`pricing`） | 人＋驾驶舱 |
| `listing_ready` | 素材已生成（`listing`） | **引擎** |
| `exported` | 素材包已导出（`export`） | 驾驶舱 |
| `published` | 人工已上架 TikTok（`publish`） | **人** |
| `testing` | 测款期（7/14/28 天节奏看板） | 驾驶舱提醒＋人决策 |
| `archived` / `dropped` | 放量归档 / 淘汰 | 人 |

## 任务生命周期（引擎协议核心）

```
pending →（引擎认领 claimed_by/claimed_at）→ in_progress → done / failed
```

引擎执行规则（任何 agent 必须遵守，详见根目录 `AGENTS.md`）：
1. 读 `tasks.json`，挑一个 `pending` 任务 → 写 `status=in_progress` + `claimed_by`（如 `claude`/`codex`/人名）+ `claimed_at`。
2. 按 `automation/engine/tasks/<type>.md` 的任务规范干活。
3. 结果**只写进品卡的对应字段**（sourcing 任务→`sources[]`；listing 任务→`listing{}`），**不碰其他字段**。
4. 给品卡 `log[]` 追加一条记录，任务标 `done` + `result_note`（失败标 `failed` 并写明原因）。
5. **原子写**：先写临时文件再改名（`store.py` 已封装；手工/其他 agent 改文件也必须如此），避免写坏总线。

## 一次完整流转（示例）

```
1. 驾驶舱：导入出海匠 xlsx → 100 张品卡(imported→scored) → 人勾 5 个(selected)
2. 驾驶舱：一键派发找货源 → tasks.json 里 1 条 sourcing 任务(含5个品) → 品卡置 sourcing
3. 引擎(Claude/Codex/人)：认领 → 上 1688 找源 → 每品写回 2-3 个候选(sources[]) → 品卡置 sourced
4. 驾驶舱：人对比利润(自动算) → 选定货源 → 品卡置 priced → 派发 listing 任务
5. 引擎：生成马来语标题/卖点/描述+合规+图 → 写回 listing{} → 置 listing_ready
6. 驾驶舱：一键导出素材包 exports/p_0001/ → exported → 人上架 → published → 进入 testing 看板
```

Schema 版本：所有文件带 `schema_version`（当前 **1**）。改协议 = 升版本 + 更新 `schema/` + 在 `CHANGELOG.md` 记一笔。
