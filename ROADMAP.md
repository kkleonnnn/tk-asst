# ROADMAP —— tk-asst v2 工程里程碑（进度唯一事实源）

> v2 定位：**电商助力 Agent** = 驾驶舱（automation/ 网页看板）+ 引擎（任何 agent 按 AGENTS.md 协议干活）+ 大脑（reference/ 知识库），数据总线 `workspace/`。
> 规则：每里程碑一个分支 → PR → main；完成定义（DoD）= 冒烟测试过 + 实测记录进 PR + 文档同步。

| 里程碑 | 交付 | 验收标准 | 状态 |
|---|---|---|---|
| **M0 规范与地基** | AGENTS.md（引擎协议）/ ROADMAP / CONTRIBUTING 代码规范章 / workspace schema+示例 / `core/` 纯函数迁移 / `store.py` / 最小 server+web 骨架 / unittest / CI | `python3 -m unittest` 全绿（3.9 与 3.14 双跑）；schema 定稿；v1 向导代码删除 | ✅ 本 PR |
| **M1 驾驶舱看板** | 品卡看板 UI（design tokens）：导入出海匠 xlsx → 打分 → 勾选 → 状态列展示；参数抽屉；任务派发按钮（写 tasks.json） | 从导入到 selected 全程网页完成且刷新不丢；界面元素≤必要集 | ⬜ |
| **M2 引擎首闭环（sourcing）** | 引擎按协议认领 sourcing 任务（Claude 浏览器 MCP 实跑一轮）→ 写回候选货源 → 看板出多货源利润对比（RM）→ 人选定 → priced | 真实跑通 ≥3 个品的「派发→引擎→写回→对比→选定」；Codex 侧协议文档可执行（校长机配置说明就绪） | ⬜ |
| **M3 素材与导出（listing）** | 引擎生成马来语标题/卖点/描述/SKU + 合规检查 + 图片收集 → `exports/` 素材包（zip）一键导出 | ≥1 个品产出可直接用于手动上架的素材包；合规检查通过 | ⬜ |
| **M4 测款看板** | published/testing 状态列：7/14/28 天计数提醒、"今天该动谁"；旧文档引用清理；给校长的新版使用说明（替换旧 Codex prompt） | 测款提醒按天正确；文档无 v1 残留引用 | ⬜ |

## 已定的默认决策（2026-07-06，kk 批准）
- `automation/` 保留原名不改 console/；v1 淘汰代码直接删（git 历史即档案）；上最小 CI。
- 后端纯 stdlib、前端无构建 —— 硬约束不动摇。
- 每个 AI 环节三档：手动档（人填）/ Codex 档（协议）/ Claude 档（全自动含浏览器）。

## 里程碑之外的挂起项（时机到再做）
- 1688 开放平台 API 接入（App Key 就绪且引擎半自动不够用时）
- 网页内嵌 Claude API（校长要独立全自动时）
- TikTok Shop Product API 自动上架（Partner 资质通过后）

*更新规则：每合并一个里程碑 PR，更新状态列 + CHANGELOG.md 记一笔 + 打 tag（v2-m0 …）。*
