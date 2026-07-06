"""flows —— 服务端编排层（胶水）：把 core 纯函数 + store IO 串成动作。

分层位置：core(纯函数) ← store(唯一IO) ← 本层(编排) ← server(路由)。
server.py 的每个业务路由只调这里的一个函数，保持路由层零逻辑。
"""
import base64

from core import scoring, xlsx

_SOURCE_FIELDS = ("name", "category", "price_low_myr", "price_high_myr",
                  "sales_30d", "sales_7d", "rating", "reviews", "commission_pct")
_SCORE_FIELDS = ("score", "verdict", "trend", "flags")


def import_products(store, file_b64=None, file_name="", csv_text="", params=None, by="console"):
    """导入出海匠 xlsx/csv → 打分 → 建品卡（scored）。同名品跳过（防重复导入）。"""
    if file_b64:
        raw = base64.b64decode(file_b64)
        if (file_name or "").lower().endswith(".xlsx") or raw[:2] == b"PK":
            dict_rows = scoring.rows_to_dicts(xlsx.read_rows(raw))
        else:
            dict_rows = scoring.parse_csv_text(raw.decode("utf-8-sig", "ignore"))
    elif (csv_text or "").strip():
        dict_rows = scoring.parse_csv_text(csv_text)
    else:
        return {"error": "没有可导入的数据：请选择出海匠导出的 xlsx/csv 文件"}
    if not dict_rows:
        return {"error": "解析不到数据行（表头没识别出来？确认是出海匠导出的格式）"}

    scored = scoring.score_products(dict_rows, params)
    existing = {c["source_data"].get("name") for c in store.load_products()["products"]}
    cards, skipped = [], 0
    for s in scored:
        if s["name"] in existing:
            skipped += 1
            continue
        existing.add(s["name"])
        cards.append({
            "status": "scored",
            "source_data": {k: s[k] for k in _SOURCE_FIELDS},
            "scoring": {k: s[k] for k in _SCORE_FIELDS},
        })
    added = store.add_products(cards, by=by) if cards else []
    return {"imported": len(added), "skipped_dup": skipped, "total_rows": len(scored)}


def set_status_bulk(store, pids, status, by="manual", event=None):
    """批量流转状态（勾选→selected / 退回→scored / 淘汰→dropped 等）。"""
    updated, errors = [], []
    for pid in pids:
        try:
            store.update_product(pid, {"status": status}, by=by,
                                 event=event or f"状态 → {status}")
            updated.append(pid)
        except (KeyError, ValueError) as e:
            errors.append(f"{pid}: {e}")
    return {"updated": updated, "errors": errors}


def dispatch_task(store, task_type, pids, params=None):
    """把「已选定」(sourcing) 或「已定价」(listing) 的品打包成一个引擎任务。"""
    require = {"sourcing": "selected", "listing": "priced"}.get(task_type)
    if require is None:
        return {"error": f"未知任务类型：{task_type}"}
    data = store.load_products()
    valid, wrong = [], []
    for pid in pids:
        card = store.get_product(data, pid)
        if card is None:
            wrong.append(f"{pid}(不存在)")
        elif card["status"] != require:
            wrong.append(f"{pid}({card['status']})")
        else:
            valid.append(pid)
    if not valid:
        return {"error": f"没有处于「{require}」状态的品可派发" + (f"；跳过：{'、'.join(wrong)}" if wrong else "")}

    task = store.create_task(task_type, valid, params or ({"min_candidates": 2} if task_type == "sourcing" else {}))
    if task_type == "sourcing":  # sourcing 派发即流转；listing 派发时品保持 priced，完成后由引擎置 listing_ready
        for pid in valid:
            store.update_product(pid, {"status": "sourcing"}, by="console",
                                 event=f"派发找货源任务 {task['id']}")
    return {"task": task, "count": len(valid),
            "skipped": wrong,
            "hint": f"任务 {task['id']} 已入队。让引擎认领：在 Claude Code / Codex 里说"
                    f"「按 AGENTS.md 认领并执行任务 {task['id']}」。"}
