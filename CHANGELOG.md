# CHANGELOG

## v2-m3（2026-07-08）—— 上架素材与一键导出（代码侧）
- 品卡展开面板加「上架素材」区：展示 listing{}（马来语标题/卖点/描述/合规）；手动填素材表单（手动档，走 core.compliance 预检）→ listing_ready。
- 一键导出素材包：`exports/<品卡>/`（listing.csv 带 BOM 兼容 Excel + checklist.txt 人工核对清单 + sources.txt 选定货源/图片）并打包 .zip → exported；IO 归 store.write_export（zipfile/csv 纯 stdlib）。
- 「已定价」列批量「派发上架素材」任务（引擎按 engine/tasks/listing.md 生成马来语素材）。
- +6 单测（共 51，3.9/3.13 双绿）。素材的 AI 生成本身由引擎实跑（M2第2段+M3引擎）。

## v2-m2a（2026-07-07）—— 看板货源侧（M2 第 1 段）
- 品卡行展开货源面板：候选货源逐行**利润对比（RM，藏价自动算）**；进货价/重量可**内联补填**（引擎常拿不到重量）→ 即时重算。
- **✓ 选定货源** → 定价写进品卡 → `priced`（可重选覆盖）；已选定徽标。
- **手动加货源表单**（三档里的手动档：无引擎也能走通全程）；找源中空态提示。
- flows 新增 add_source/update_source/compare_sources/choose_source + 7 个单测（共 47 测）。

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
