# 协作指南：知识怎么喂、代码怎么改

> 本文两部分：**第一部分 知识贡献**（喂料/消化，不需要写代码）；**第二部分 代码贡献规范**（改驾驶舱 automation/ 的规矩，人和 AI 都要遵守）。
> 先读根目录 `README.md` 了解全局；AI agent 另读 `AGENTS.md`。

## 一、喂料（任何人、任何工具都能做）

把原始资料放进 `inbox/`：
- 可以建日期子文件夹，例如 `inbox/2026-06-21/`。
- **命名格式：`日期 主题 原标题`**
  - 日期：如 `2026-06-21`
  - 主题：按资料所属板块/来源，用 `_` 连接层级，例如 `运营全流程_选品分析_选品洞察`
  - 例：`2026-06-21 运营全流程_发布商品 商品优化指南.pdf`
- **三条铁律**：①标来源+日期 ②一条只讲一件事 ③**绝不放账号密码/API key/买家隐私/店铺真实数据**——⚠️ 本仓库 **PUBLIC 公开**，`.md` 会随 git 全网可见。

> 📌 **原件（PDF/图片/Excel 等）只留在你本地，不会进 git**（已被 `.gitignore` 挡住，避免仓库膨胀）。
> 想把内容同步给对方/交给整合：**自己先用 AI 把它消化成 `.md`**（见第二节）放进 inbox——`.md` 会随 git 同步。

## 二、两遍消化制（第一遍人人可做，最终整合归 kk）

**第一遍消化（任何人、任何模型）**：把你准备的资料，**本地用你自己的 AI 先消化一遍** → 产出结构化 `.md`（提炼要点、标来源/日期、注明建议归入哪个板块）→ 丢进 `inbox/` → push / PR（`.md` 随 git 同步）。**不限模型、不限人。**

**最终整合（kk）**：kk 把 inbox 的这些 `.md` **校对、去重、核实、规范化**后并入 `reference/` 对应板块（建议用 Opus 4.8+ 把关，纠正第一遍的错与营销水分），审 PR、合并 main，并在 `reference/_消化日志.md` 记一笔。

> 为什么分两遍：第一遍**众包**减轻 kk 负担；最终整合是**质量关口**，保证 `reference/` 干净可信。
> **其他人不直接改 `reference/`**——只把第一遍 `.md` 交到 `inbox/`；`reference/` 由 kk 整合。

## 三、提 PR + 合并 main（正式生效的关口）

**资料消化进 reference/ 后，不会自动生效，必须走这一步：**
1. 把改动提一个 **Pull Request**（不要直接推 main）。
2. 对方会**收到通知**，看一眼后**合并到 main**——这才算"正式迭代"。
3. 另一方 `git pull` 即可拿到最新知识。

> 不写代码也能提 PR：用 **GitHub 网页**（编辑 `.md` → 选择"新建分支并发起 PR"）或 **GitHub Desktop**，全程点鼠标。

## 四、消费（任何 AI 都能做）
把 `reference/` 或 `通用知识包.md` 喂给任何 AI 当上下文，让它回答运营问题、起草 listing/话术、做选品/大促/数据分析建议。详见 `README.md` 的「给非 Claude AI 的使用说明」。

## 五、生成通用知识包
改完 reference 后，跑一下脚本重新生成给其他 AI 用的整合文件：
```bash
bash scripts/build_pack.sh   # 生成/更新 通用知识包.md
```

## 目录速查
| 文件夹 | 放什么 |
|---|---|
| `inbox/` | 待消化的原始资料（大文件只留本地） |
| 已消化的原件 | 本地留在各自批次目录（如 `inbox/2026-06-21/`），不入库；想清爽可 kk 整合后自行移入本地 `inbox/_已消化/`（可选、非强制） |
| `reference/` | 已消化、已核实的正式知识（按 01–09 板块） |

---

# 第二部分 · 代码贡献规范（automation/ 驾驶舱）

> 适用于所有改代码的人和 AI（Claude / Codex）。里程碑与验收见 `ROADMAP.md`；引擎协议见 `AGENTS.md`。

## 一、架构硬约束（不容商量）

1. **零依赖铁律**：后端**纯 Python 标准库**——禁 `pip install` 任何包；**禁用 `xml.etree`**（部分 Python 缺 pyexpat 会崩，解析 XML 用正则，见 `core/xlsx.py` 先例）。前端**无构建**——禁 npm/打包器/前端框架/CDN 外链，只有 `index.html + styles.css + app.js` 三个静态文件。
2. **分层**：`core/` 只放**纯函数**（dict 进、dict 出，不碰文件/网络/时间）→ `store.py` 是唯一读写 `workspace/` 的地方（原子写：临时文件+改名）→ `server.py` 只做路由和 IO 粘合 → `web/` 只做渲染。
3. **AI 不写进代码**：翻译/找货源/生成文案等智能活一律走引擎协议（`workspace/tasks.json` + `AGENTS.md`），代码里不内嵌任何模型调用。
4. **数据**：`workspace/` 是唯一状态源；JSON 带 `schema_version`；改 schema = 升版本 + 更新 `workspace/schema/` + CHANGELOG 记一笔。真实经营数据永不入库。
5. **前端规范**：`styles.css` 顶部集中定义 design tokens（颜色/间距/圆角/字号 CSS 变量），组件样式只引用 token；`app.js` 按组件函数组织。界面原则：每屏只留当前步骤必要元素。

## 二、流程

- **分支**：里程碑开分支（`m1-console` 等）→ PR → main。kk 可直推小修；**其他人/AI 一律 PR 且不自己合并**。
- **完成定义（DoD）**：`cd automation && python3 -m unittest discover -s tests -v` 全绿 + 本地 `python3 run.py` 实测 + 实测记录写进 PR 描述 + 相关文档同步。
- **CI**：GitHub Actions 自动跑 编译+单测（`.github/workflows/ci.yml`），PR 红了不合并。
- **提交安全自查**：提交前 `git status` 确认没带入 `workspace/products.json`、`tasks.json`、`exports/`、`credentials.json`、`__pycache__`。
- **风格**：中文注释与文档；snake_case；每个 `core/` 模块配最小 unittest。
