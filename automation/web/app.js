/* 驾驶舱前端（M1 品卡看板）：导入 → 打分 → 勾选 → 派发。状态全部来自服务端，刷新不丢。 */
"use strict";

const $ = (s) => document.querySelector(s);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
};
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/* 状态机顺序与中文名（与 workspace/README 对齐） */
const STATUS_ORDER = ["scored", "selected", "sourcing", "sourced", "priced",
  "listing_ready", "exported", "published", "testing", "imported", "archived", "dropped"];
const STATUS_CN = {
  imported: "已导入", scored: "已打分", selected: "已选定", sourcing: "找源中",
  sourced: "有货源", priced: "已定价", listing_ready: "素材就绪", exported: "已导出",
  published: "已上架", testing: "测款中", archived: "归档", dropped: "已淘汰",
};
const VERDICT_BADGE = { "推荐": "ok", "观察": "warn", "不建议": "danger", "缺销量": "" };
/* 打分参数中文标签（key 与 core/scoring DEFAULTS 对齐） */
const PARAM_CN = {
  min_sales_30d: "近30天销量门槛", min_rating: "最低评分", min_reviews: "最低评论数",
  price_max_myr: "售价上限(RM)", trend_up_ratio: "上升趋势阈值",
};

const state = { products: [], tasks: [], filter: null, sel: new Set(), expanded: null };

function toast(msg, ms = 2600) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), ms);
}

async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt).then((x) => x.json());
  if (r && r.error) { toast("⚠️ " + r.error, 4000); throw new Error(r.error); }
  return r;
}

/* ---------- 数据 ---------- */
async function reload() {
  const [p, t] = await Promise.all([api("/api/products"), api("/api/tasks")]);
  state.products = p.products || [];
  state.tasks = t.tasks || [];
  // 勾选集合剔除已不在当前筛选的品
  render();
}

function counts() {
  const c = {};
  state.products.forEach((p) => { c[p.status] = (c[p.status] || 0) + 1; });
  return c;
}

function defaultFilter() {
  const c = counts();
  for (const s of STATUS_ORDER) if (c[s]) return s;
  return "scored";
}

/* ---------- 渲染 ---------- */
function render() {
  if (!state.filter) state.filter = location.hash.slice(1) || defaultFilter();
  renderStats(); renderChips(); renderBulk(); renderTable(); renderTasks();
}

function renderStats() {
  const c = counts();
  const total = state.products.length;
  const pend = state.tasks.filter((t) => t.status === "pending").length;
  $("#stats").textContent =
    `${total} 个品卡` + (c.selected ? ` · 已选定 ${c.selected}` : "") + (pend ? ` · 待认领任务 ${pend}` : "");
}

function renderChips() {
  const c = counts();
  const box = $("#chips");
  box.innerHTML = "";
  const mk = (key, label, n) => {
    const chip = el("span", "chip" + (state.filter === key ? " active" : ""),
      `${label} <b>${n}</b>`);
    chip.onclick = () => { state.filter = key; location.hash = key; state.sel.clear(); render(); };
    box.appendChild(chip);
  };
  mk("all", "全部", state.products.length);
  STATUS_ORDER.forEach((s) => { if (c[s]) mk(s, STATUS_CN[s], c[s]); });
}

function visibleProducts() {
  return state.filter === "all" ? state.products
    : state.products.filter((p) => p.status === state.filter);
}

function renderBulk() {
  const bar = $("#bulkbar");
  const n = state.sel.size;
  if (!n) { bar.style.display = "none"; return; }
  bar.style.display = "";
  bar.innerHTML = `已勾选 <b>${n}</b> 个：`;
  const acts = [];
  const f = state.filter;
  if (f === "scored" || f === "all") acts.push(["✓ 设为已选定", () => bulkStatus("selected", "人工勾选")]);
  if (f === "selected") {
    acts.push(["→ 派发找货源", dispatchSourcing]);
    acts.push(["↩ 退回已打分", () => bulkStatus("scored", "退回打分池")]);
  }
  if (f === "sourcing") acts.push(["↩ 退回已选定", () => bulkStatus("selected", "撤回找源")]);
  acts.push(["🗑 淘汰", () => bulkStatus("dropped", "人工淘汰"), "danger"]);
  acts.forEach(([label, fn, cls]) => {
    const b = el("button", "btn " + (cls || ""), label);
    b.onclick = fn;
    bar.appendChild(b);
  });
}

function renderTable() {
  const wrap = $("#tablewrap");
  const rows = visibleProducts();
  if (!rows.length) {
    wrap.innerHTML = `<div class="empty">这里还没有品卡——点右上「⬆ 导入出海匠」开始</div>`;
    return;
  }
  const showSources = ["sourcing", "sourced", "priced", "all"].includes(state.filter);
  const t = el("table");
  const thead = el("thead");
  const head = el("tr");
  const hcb = el("th");
  const all = el("input"); all.type = "checkbox";
  all.checked = rows.length > 0 && rows.every((p) => state.sel.has(p.id));
  all.onchange = () => { rows.forEach((p) => all.checked ? state.sel.add(p.id) : state.sel.delete(p.id)); render(); };
  hcb.appendChild(all); head.appendChild(hcb);
  ["商品名", "类目", "售价RM", "近30天销量", "趋势", "评分", "得分", "判定",
    ...(showSources ? ["货源"] : []), ...(state.filter === "all" ? ["状态"] : []), "红旗"]
    .forEach((h) => head.appendChild(el("th", null, h)));
  thead.appendChild(head);
  t.appendChild(thead);

  const tb = el("tbody");
  rows.forEach((p) => {
    const sd = p.source_data || {}, sc = p.scoring || {};
    const tr = el("tr");
    const tdcb = el("td");
    const cb = el("input"); cb.type = "checkbox"; cb.checked = state.sel.has(p.id);
    cb.onchange = () => { cb.checked ? state.sel.add(p.id) : state.sel.delete(p.id); renderBulk(); };
    tdcb.appendChild(cb); tr.appendChild(tdcb);

    const price = sd.price_low_myr != null
      ? (sd.price_high_myr != null && sd.price_high_myr !== sd.price_low_myr
        ? `${sd.price_low_myr}~${sd.price_high_myr}` : String(sd.price_low_myr)) : "—";
    const nSrc = (p.sources || []).length;
    const expandable = showSources && ["sourcing", "sourced", "priced", "listing_ready", "exported"].includes(p.status);
    const srcCell = expandable
      ? `<a href="javascript:void 0" class="srcbtn">${state.expanded === p.id ? "▾" : "▸"} ${nSrc ? nSrc + " 个" : "添加"}</a>`
      : (nSrc ? `${nSrc} 个` : "—");
    const cells = [
      `<span title="${esc(p.id)}">${esc(String(sd.name || "").slice(0, 36))}</span>`,
      esc(sd.category || ""), esc(price),
      sd.sales_30d != null ? Number(sd.sales_30d).toLocaleString() : "—",
      esc(sc.trend || "—"), sd.rating != null ? sd.rating : "—",
      `<span class="score">${sc.score != null ? sc.score : "—"}</span>`,
      `<span class="badge ${VERDICT_BADGE[sc.verdict] || ""}">${esc(sc.verdict || "—")}</span>`,
      ...(showSources ? [srcCell] : []),
      ...(state.filter === "all" ? [`<span class="badge accent">${STATUS_CN[p.status] || p.status}</span>`] : []),
    ];
    cells.forEach((c) => tr.appendChild(el("td", null, c)));
    const fl = el("td", "flags", esc((sc.flags || []).join("；") || "—"));
    fl.title = (sc.flags || []).join("\n");
    tr.appendChild(fl);
    if (expandable) {
      const btn = tr.querySelector(".srcbtn");
      if (btn) btn.onclick = () => toggleExpand(p.id);
    }
    tb.appendChild(tr);
    if (state.expanded === p.id) {
      const dtr = el("tr", "detailrow");
      const td = el("td", "detailcell");
      td.colSpan = head.children.length;
      td.innerHTML = `<div class="muted">货源对比加载中…</div>`;
      dtr.appendChild(td);
      tb.appendChild(dtr);
      loadDetail(p.id, td);
    }
  });
  t.appendChild(tb);
  wrap.innerHTML = "";
  wrap.appendChild(t);
}

function renderTasks() {
  const card = $("#tasksCard");
  if (!state.tasks.length) { card.style.display = "none"; return; }
  card.style.display = "";
  const list = $("#tasksList");
  list.innerHTML = "";
  const badge = { pending: "warn", in_progress: "accent", done: "ok", failed: "danger" };
  const cn = { pending: "待认领", in_progress: "执行中", done: "已完成", failed: "失败" };
  [...state.tasks].reverse().forEach((t) => {
    const row = el("div", "task");
    row.appendChild(el("span", "mono", esc(t.id)));
    row.appendChild(el("span", "badge accent", t.type === "sourcing" ? "找货源" : "上架素材"));
    row.appendChild(el("span", `badge ${badge[t.status] || ""}`, cn[t.status] || t.status));
    row.appendChild(el("span", "muted", `${(t.product_ids || []).length} 个品` +
      (t.claimed_by ? ` · ${esc(t.claimed_by)}` : "") +
      (t.result_note ? ` · ${esc(t.result_note)}` : "")));
    if (t.status === "pending") {
      const b = el("button", "btn", "📋 复制引擎指令");
      b.onclick = () => {
        navigator.clipboard.writeText(`按 AGENTS.md 认领并执行任务 ${t.id}`);
        toast(`已复制——去 Claude Code / Codex 里粘贴即可`);
      };
      row.appendChild(b);
    }
    list.appendChild(row);
  });
}

/* ---------- 货源展开面板（M2：对比 → 补价重 → 选定） ---------- */
function toggleExpand(pid) {
  state.expanded = state.expanded === pid ? null : pid;
  renderTable();
}

async function loadDetail(pid, td) {
  const d = await api("/api/compare", { id: pid });
  renderDetail(pid, td, d);
}

function fmtRM(v) { return v == null ? "—" : "RM" + Number(v).toFixed(2); }

function renderDetail(pid, td, d) {
  td.innerHTML = "";
  const head = el("div", "row",
    `<span class="muted">市场售价 ${d.market_price.low != null ? "RM" + d.market_price.low : "?"}` +
    `${d.market_price.high != null && d.market_price.high !== d.market_price.low ? "~" + d.market_price.high : ""}</span>` +
    `<span class="muted">｜费率为占位默认（佣金5%·手续2%·达人5%·利润20%·汇率1.55），以马来当期为准</span>`);
  td.appendChild(head);

  if ((d.sources || []).length) {
    const t = el("table", "subtable");
    t.innerHTML = `<thead><tr>
      <th>货源</th><th>链接</th><th>进货价¥</th><th>重量g</th><th>起订</th><th>发货地</th>
      <th>成本¥</th><th>折后价RM</th><th>利润RM</th><th>利润率</th><th></th></tr></thead>`;
    const tb = el("tbody");
    d.sources.forEach((s) => {
      const tr = el("tr");
      const chosen = d.chosen_source_id === s.id;
      const pr = s.pricing || {};
      tr.appendChild(el("td", "mono", esc(s.id) + (chosen ? ' <span class="badge ok">已选定</span>' : "")));
      tr.appendChild(el("td", null,
        `<a href="${esc(s.url)}" target="_blank">🔗 打开</a>` +
        (s.title ? ` <span class="muted">${esc(String(s.title).slice(0, 22))}</span>` : "")));
      // 进货价/重量可编辑（引擎常拿不到重量）
      [["price_rmb", s.price_rmb], ["weight_g", s.weight_g]].forEach(([k, v]) => {
        const cell = el("td");
        const inp = el("input"); inp.type = "number"; inp.step = "any";
        inp.value = v == null ? "" : v; inp.placeholder = "填"; inp.style.width = "72px";
        inp.onchange = async () => {
          await api("/api/sources/update", { id: pid, source_id: s.id, patch: { [k]: inp.value } });
          await reload();   // 重算对比
        };
        cell.appendChild(inp); tr.appendChild(cell);
      });
      tr.appendChild(el("td", null, s.moq != null ? String(s.moq) : "—"));
      tr.appendChild(el("td", null, esc(s.ship_from || "—")));
      if (s.pricing_error) {
        const e1 = el("td", null, "—");
        const e2 = el("td", "muted", esc(s.pricing_error)); e2.colSpan = 3;
        tr.appendChild(e1); tr.appendChild(e2);
      } else {
        tr.appendChild(el("td", null, pr.cost_rmb != null ? "¥" + pr.cost_rmb : "—"));
        tr.appendChild(el("td", null, fmtRM(pr.net_price_myr)));
        const profit = el("td", null,
          `<b style="color:${pr.profit_myr > 0 ? "var(--ok)" : "var(--danger)"}">${fmtRM(pr.profit_myr)}</b>`);
        tr.appendChild(profit);
        tr.appendChild(el("td", null, pr.profit_rate != null ? Math.round(pr.profit_rate * 100) + "%" : "—"));
      }
      const act = el("td");
      if (!chosen && !s.pricing_error) {
        const b = el("button", "btn", "✓ 选定");
        b.onclick = async () => {
          const r = await api("/api/choose", { id: pid, source_id: s.id });
          toast(`✅ 已选定 ${s.id}：折后 ${fmtRM(r.pricing.net_price_myr)}，利润 ${fmtRM(r.pricing.profit_myr)} → 已定价`);
          state.filter = "priced"; location.hash = "priced";
          await reload();
        };
        act.appendChild(b);
      }
      tr.appendChild(act);
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    td.appendChild(t);
  } else {
    td.appendChild(el("div", "muted",
      d.status === "sourcing"
        ? "引擎还没写回货源——等任务完成，或在下面手动添加你在 1688 找到的源。"
        : "还没有货源，在下面手动添加。"));
  }

  // 手动加货源（三档里的手动档）
  const form = el("div", "row srcform");
  const inputs = {};
  [["url", "1688 商品链接 *", 260], ["title", "货源名(可空)", 140],
   ["price_rmb", "进货价¥ *", 90], ["weight_g", "重量g", 80], ["ship_from", "发货地", 100]]
    .forEach(([k, ph, w]) => {
      const inp = el("input");
      inp.type = (k === "price_rmb" || k === "weight_g") ? "number" : "text";
      inp.step = "any"; inp.placeholder = ph; inp.style.width = w + "px";
      inputs[k] = inp; form.appendChild(inp);
    });
  const add = el("button", "btn", "＋ 添加货源");
  add.onclick = async () => {
    const src = {};
    Object.entries(inputs).forEach(([k, inp]) => { if (inp.value !== "") src[k] = inp.value; });
    await api("/api/sources/add", { id: pid, source: src });
    toast("✅ 货源已添加");
    await reload();
  };
  form.appendChild(add);
  td.appendChild(form);
}

/* ---------- 动作 ---------- */
async function bulkStatus(status, event) {
  const ids = [...state.sel];
  const r = await api("/api/status", { ids, status, event });
  toast(`✅ ${r.updated.length} 个品 → ${STATUS_CN[status] || status}` +
    (r.errors.length ? `；失败 ${r.errors.length}` : ""));
  state.sel.clear();
  if (status === "selected") { state.filter = "selected"; location.hash = "selected"; }
  await reload();
}

async function dispatchSourcing() {
  const ids = [...state.sel];
  const r = await api("/api/dispatch", { type: "sourcing", ids });
  toast(`🚀 ${r.hint}`, 6000);
  state.sel.clear();
  state.filter = "sourcing"; location.hash = "sourcing";
  await reload();
}

/* ---------- 导入 ---------- */
async function setupImport() {
  $("#btnImport").onclick = () => { $("#importPanel").style.display = ""; };
  $("#btnCancelImport").onclick = () => { $("#importPanel").style.display = "none"; };
  $("#paramsToggle").onclick = () => $("#paramsDrawer").classList.toggle("open");

  const defs = await api("/api/scoring-params");
  const grid = $("#paramsGrid");
  Object.entries(defs).forEach(([k, v]) => {
    const box = el("div", "p");
    box.appendChild(el("label", null, PARAM_CN[k] || k));
    const inp = el("input"); inp.type = "number"; inp.step = "any"; inp.value = v; inp.id = `param-${k}`;
    box.appendChild(inp);
    grid.appendChild(box);
  });

  $("#btnDoImport").onclick = async () => {
    const f = $("#file").files[0];
    if (!f) { toast("先选择出海匠导出的 xlsx / csv 文件"); return; }
    const params = {};
    Object.keys(defs).forEach((k) => {
      const v = $(`#param-${k}`).value;
      if (v !== "") params[k] = Number(v);
    });
    $("#importHint").textContent = "解析打分中…";
    const buf = await f.arrayBuffer();
    let bin = ""; const bytes = new Uint8Array(buf), CH = 0x8000;
    for (let i = 0; i < bytes.length; i += CH) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
    const r = await api("/api/import", { file_b64: btoa(bin), file_name: f.name, params });
    toast(`✅ 导入 ${r.imported} 个品卡` +
      (r.skipped_dup ? `，跳过重复 ${r.skipped_dup}` : "") + `（共 ${r.total_rows} 行）`);
    $("#importPanel").style.display = "none";
    $("#importHint").textContent = "选出海匠导出的 xlsx / csv（同名品自动跳过）";
    state.filter = "scored"; location.hash = "scored";
    await reload();
  };
}

/* ---------- 启动 ---------- */
(async function boot() {
  await setupImport();
  await reload();
})();
