# CHANGELOG

## v2-m1（2026-07-06）—— 驾驶舱品卡看板
- 看板 UI：导入出海匠 xlsx/csv（同名去重）→ 打分 → 状态 chips 筛选 → 勾选/全选 → 设为已选定/退回/淘汰 → 一键派发找货源任务（写 tasks.json + 复制引擎指令）。
- 状态全部持久化在 workspace/，刷新/重启不丢；打分参数抽屉（导入时可调）。
- 新增 flows.py 编排层（core纯函数+store 的胶水，server 保持零逻辑路由）；+6 个 flows 单测（共 40 测）。
- 界面按 design tokens 重做：顶栏+chips+表格+任务队列，无多余元素。

## v2-m0（2026-07-06）—— 规范与地基
- 定位升级：知识库 → **电商助力 Agent**（驾驶舱 + 引擎协议 + 大脑）。
- 新增 `AGENTS.md`（任何 agent 的引擎/码工协议，Codex 自动读取）、`ROADMAP.md`、本文件。
- 新增 `workspace/` 数据总线：品卡状态机 + 任务队列（schema v1 + 脱敏示例；真实数据不入库）。
- `automation/` 重构：v1 六步向导删除；打分/定价/合规/xlsx/凭证五个模块迁移为 `core/` 纯函数；新增 `store.py`（原子写）；最小 server/web 骨架（design tokens 就位）；`tests/` stdlib 单测。
- `CONTRIBUTING.md` 新增代码贡献规范章；上最小 CI（编译 + unittest）。
- 定价货币口径：马币 RM（fx_rmb_per_myr，默认 1.55，占位待核）。

## v1（2026-07-05 及之前）
- 知识库 9 板块（reference/ 39 文件）、旗舰执行计划、运营工作台 Excel v2、达意货代档案。
- v1 运营控制台（六步向导网页）：已由 v2 取代，代码见 git 历史（提交 01873f1 及之前）。
