# AGENTS.md —— 任何 AI agent 进入本仓库先读这份

> 本仓库 = **tk-asst 电商助力 Agent**（TikTok Shop 马来西亚跨境店）。你（Claude / Codex / 其他 agent）在这里有两种角色：**引擎**（执行运营任务）和 **码工**（改进驾驶舱代码）。两种角色的规矩都在本文件。

## 0. 安全铁律（违反会造成真实损失，最优先）

1. **本仓库 PUBLIC 公开，任何提交全网可见。** 绝不把 密钥/token/账号密码/店铺真实数据/买家隐私/真实经营数据 写进任何会入库的文件。
2. `workspace/products.json`、`workspace/tasks.json`、`workspace/exports/`、`automation/credentials.json` 都已被 `.gitignore` 挡住——**不要修改这些 gitignore 规则，不要把它们的内容抄进入库文件**（包括代码注释、示例、测试、PR 描述）。
3. **不直接 push main**：开分支 → PR → 由 kk 审核合并。**你只开 PR，绝不自己合并。**
4. 涉及费率/佣金/SLA 等数字：以 TikTok 官方后台马来站当期为准，不硬编未核实的数（标注"占位，待核"）。
5. 访问控制类操作（仓库可见性、协作者、第三方授权）**只有 kk 本人能做**，你不代办。

## 1. 仓库地图

```
automation/   驾驶舱：本地网页（看板+计算+导出），python3 run.py 启动
workspace/    数据总线：品卡 products.json + 任务 tasks.json（协议见 workspace/README.md）
reference/    大脑：9 大板块运营知识（01开店…09风控），你回答运营问题的依据
sop/          执行计划与流程；templates/ 工具模板；inbox/ 待消化资料
AGENTS.md     ←本文件（引擎协议）   ROADMAP.md 工程里程碑   CONTRIBUTING.md 贡献规范
```

## 2. 引擎角色：怎么执行运营任务

驾驶舱会把需要 AI 的活写进 `workspace/tasks.json`。你的工作循环：

1. **认领**：读 `tasks.json`，挑一个 `status=pending` 的任务 → 改为 `in_progress`，写 `claimed_by`（你的名字：`claude`/`codex`/人名）和 `claimed_at`。
2. **干活**：按该任务类型的规范执行——规范在 `automation/engine/tasks/<type>.md`：
   - `sourcing`（找货源）→ [automation/engine/tasks/sourcing.md](automation/engine/tasks/sourcing.md)
   - `listing`（上架素材）→ [automation/engine/tasks/listing.md](automation/engine/tasks/listing.md)
3. **写回**：结果只写进 `products.json` 里对应品卡的**指定字段**（sourcing→`sources[]`；listing→`listing{}`），**不动其他字段**；给品卡 `log[]` 追加一条 `{at, by, event}`。
4. **收尾**：任务标 `done` + 一句话 `result_note`；失败标 `failed` 并写明卡在哪（等人处理，不要硬编数据）。
5. **原子写**：改 workspace JSON 必须先写临时文件再改名替换（参考 `automation/store.py`），不许直接覆盖写。

**工具怎么来**：浏览器活（上 1688）用你自己的浏览器 MCP——Claude 用 claude-in-chrome，Codex 用 Playwright MCP（`codex mcp add playwright npx "@playwright/mcp@latest"`）。翻译/文案就是你的本职，不需要外部 API。

**回答运营问题**：依据 `reference/`（或 `通用知识包.md`），标注来源；`inbox/` 未消化内容不当定论。

## 3. 码工角色：怎么改驾驶舱代码

- 硬约束（详见 `CONTRIBUTING.md` 代码规范章）：**后端纯 Python 标准库（禁 pip、禁 xml.etree）；前端无构建（禁 npm/框架/CDN）**；`core/` 只放纯函数；数据只经 `store.py` 进出 workspace。
- 改完必须跑测试：`cd automation && python3 -m unittest discover -s tests -v`，并实际启动 `python3 run.py` 验证。
- 交付：分支 + PR + 实测记录写进 PR 描述；不自合并。

## 4. 知识规则（沿用两遍消化制）

**不要直接改 `reference/`**。资料先消化成 `.md` 放 `inbox/` → PR → 由 kk 校对核实后并入 `reference/`（质量关口）。改完知识记得 `bash scripts/build_pack.sh` 重生成通用知识包。
