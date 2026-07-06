/* 驾驶舱前端（M0 骨架）：只渲染工作台汇总。组件函数式组织，M1 扩展为品卡看板。 */
"use strict";

const $ = (s) => document.querySelector(s);

async function loadWorkspace() {
  const box = $("#ws");
  try {
    const r = await fetch("/api/workspace").then((x) => x.json());
    if (r.error) { box.innerHTML = `<span class="badge warn">${r.error}</span>`; return; }
    const rows = [
      ["品卡总数", r.products_total],
      ["按状态", Object.entries(r.by_status || {}).map(([k, v]) => `${k}:${v}`).join("　") || "（空）"],
      ["待认领任务", r.tasks_pending],
      ["执行中任务", r.tasks_in_progress],
    ];
    box.innerHTML = rows.map(([k, v]) => `<div class="k">${k}</div><div>${v}</div>`).join("");
  } catch (e) {
    box.innerHTML = `<span class="badge warn">无法连接服务：${e}</span>`;
  }
}

loadWorkspace();
