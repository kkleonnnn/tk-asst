# automation/ —— tk-asst 驾驶舱（v2）

本地网页：**品卡看板 + 确定性计算 + 人工决策 + 素材导出**。需要"脑子"的活（找货源/翻译/素材）不在这里做——派发成任务由引擎执行（协议见根目录 `AGENTS.md`，数据总线见 `../workspace/README.md`）。

## 启动（零依赖，只要有 Python 3）
```bash
cd automation
python3 run.py        # 自动打开 http://127.0.0.1:8765/
```

## 目录
```
automation/
├── run.py            # 一键启动
├── server.py         # 薄 HTTP 层：路由 + IO 粘合（不写业务逻辑）
├── store.py          # workspace/ 唯一读写层（原子写 + schema 版本 + 品卡/任务操作）
├── core/             # 纯函数（dict进dict出，不碰文件/网络/时间）
│   ├── scoring.py    #   ① 选品打分（出海匠数据 → 结构化打分）
│   ├── pricing.py    #   ④ 藏价/利润（货币口径马币 RM；含多货源对比、竞品价反算）
│   ├── compliance.py #   ⑤ 标题公式 + 文本级合规（违禁词/禁售类目/品牌授权）
│   ├── xlsx.py       #   xlsx 解析（纯正则，禁 xml.etree——expat 坑）
│   └── creds.py      #   凭证管理（真凭证存 credentials.json，已 gitignore）
├── engine/tasks/     # 引擎任务规范（sourcing.md 找货源 / listing.md 上架素材）
├── web/              # 前端三件套（无构建）：index.html / styles.css(design tokens) / app.js
├── tests/            # stdlib unittest（cd automation && python3 -m unittest discover -s tests）
└── samples/          # 脱敏样例
```

## 开发规矩（详见 `../CONTRIBUTING.md` 第二部分）
- **零依赖铁律**：后端纯 stdlib（禁 pip、禁 xml.etree）；前端无构建（禁 npm/框架/CDN）。
- **分层**：core 纯函数 ← store 唯一碰 workspace ← server 只做路由 ← web 只做渲染。
- **改完必测**：单测全绿 + `python3 run.py` 实测，记录写进 PR。
- 换肤/界面精修：只改 `web/styles.css` 顶部的 design tokens。

## 网页怎么用（M1 看板）
1. 右上「⬆ 导入出海匠」→ 选 xlsx/csv →（可选：⚙ 调打分参数）→ 导入并打分（同名品自动去重）。
2. 状态 chips 筛选（已打分/已选定/找源中…）；勾选品 → 批量条出现：**设为已选定 / 退回 / 淘汰**。
3. 「已选定」列勾选 → **→ 派发找货源**：任务进队列，点「📋 复制引擎指令」到 Claude Code / Codex 粘贴执行（引擎按 `../AGENTS.md` 干活并写回）。
4. 一切状态存 `../workspace/`，刷新/隔天打开都在。

## 当前进度
M0 地基 ✅ → M1 品卡看板 ✅ → M2 引擎首闭环（sourcing 实跑+多货源利润对比）施工中。里程碑见 `../ROADMAP.md`。
v1 六步向导已废弃（代码在 git 历史，提交 `01873f1` 及之前）。
