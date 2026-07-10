"""flows —— 服务端编排层（胶水）：把 core 纯函数 + store IO 串成动作。

分层位置：core(纯函数) ← store(唯一IO) ← 本层(编排) ← server(路由)。
server.py 的每个业务路由只调这里的一个函数，保持路由层零逻辑。
"""
import base64
import re

from core import compliance, pricing, scoring, xlsx
from store import now

_SOURCE_FIELDS = ("name", "category", "price_low_myr", "price_high_myr",
                  "sales_30d", "sales_7d", "rating", "reviews", "commission_pct")
_SCORE_FIELDS = ("score", "verdict", "trend", "flags")
# 货源条目允许写入/编辑的字段（schema sources[] 对齐）
_SRC_EDITABLE = ("url", "title", "price_rmb", "weight_g", "moq", "ship_from",
                 "supports_dropship", "seller_rating", "notes")
_SRC_NUMERIC = ("price_rmb", "weight_g", "moq")


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


# ==================== 货源侧（M2：手动档 + 对比 + 选定） ====================

def _clean_source_fields(source):
    """清洗货源字段：只留白名单，数字字段转 float（空→None）。返回 (dict, err)。"""
    out = {}
    for k in _SRC_EDITABLE:
        if k not in source:
            continue
        v = source[k]
        if k in _SRC_NUMERIC:
            if v in (None, ""):
                out[k] = None
                continue
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                return None, f"{k} 必须是数字"
        else:
            out[k] = v
    return out, None


def add_source(store, pid, source, by="manual"):
    """给品卡手动添加一个候选货源（引擎走文件协议直写，不经此）。≥1 个货源后品卡 → sourced。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    fields, err = _clean_source_fields(source)
    if err:
        return {"error": err}
    if not (fields.get("url") or "").strip():
        return {"error": "货源至少要有 1688 链接（url）"}
    if fields.get("price_rmb") is None:
        return {"error": "货源至少要有进货价（price_rmb，元）"}

    sources = list(card.get("sources") or [])
    mx = 0
    for s in sources:
        m = re.match(r"s(\d+)$", str(s.get("id", "")))
        if m:
            mx = max(mx, int(m.group(1)))
    entry = {"id": f"s{mx + 1}", "title": "", "weight_g": None, "moq": None,
             "ship_from": None, "supports_dropship": None, "seller_rating": None,
             "notes": "", **fields, "added_by": by, "added_at": now()}

    patch = {"sources": sources + [entry]}
    if card["status"] in ("selected", "sourcing"):
        patch["status"] = "sourced"
    store.update_product(pid, patch, by=by, event=f"添加货源 {entry['id']}（{by}）")
    return {"source": entry, "count": len(sources) + 1}


def update_source(store, pid, source_id, patch, by="manual"):
    """编辑货源字段（典型：引擎没拿到重量，人工补上）。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    fields, err = _clean_source_fields(patch)
    if err:
        return {"error": err}
    sources = list(card.get("sources") or [])
    for s in sources:
        if s.get("id") == source_id:
            s.update(fields)
            store.update_product(pid, {"sources": sources}, by=by,
                                 event=f"编辑货源 {source_id}：{'/'.join(fields.keys())}")
            return {"source": s}
    return {"error": f"货源不存在：{source_id}"}


def compare_sources(store, pid, params=None):
    """多货源利润对比：对每个候选货源藏价试算（RM）。缺价/缺重量的行给出缺什么。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    rows = []
    for s in (card.get("sources") or []):
        row = dict(s)
        if s.get("price_rmb") is None:
            row["pricing_error"] = "缺进货价"
        elif s.get("weight_g") in (None, ""):
            row["pricing_error"] = "缺重量——运费算不了，点重量格补上"
        else:
            res, err = pricing.price_one(s["price_rmb"], s["weight_g"], params)
            if err:
                row["pricing_error"] = err
            else:
                row["pricing"] = {k: res[k] for k in
                                  ("net_price_myr", "list_price_myr", "profit_myr",
                                   "profit_rate", "cost_rmb", "discount_off_pct")}
        rows.append(row)
    return {"id": pid, "name": (card.get("source_data") or {}).get("name", ""),
            "status": card["status"], "chosen_source_id": card.get("chosen_source_id"),
            "market_price": {"low": (card.get("source_data") or {}).get("price_low_myr"),
                             "high": (card.get("source_data") or {}).get("price_high_myr")},
            "sources": rows}


def choose_source(store, pid, source_id, params=None, by="manual"):
    """人工选定货源：算定价写进品卡 → priced。可重选（覆盖）。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    src = next((s for s in (card.get("sources") or []) if s.get("id") == source_id), None)
    if src is None:
        return {"error": f"货源不存在：{source_id}"}
    if src.get("price_rmb") is None or src.get("weight_g") in (None, ""):
        return {"error": "该货源缺进货价或重量，先补齐再选定"}
    res, err = pricing.price_one(src["price_rmb"], src["weight_g"], params)
    if err:
        return {"error": err}
    store.update_product(pid, {
        "chosen_source_id": source_id,
        "pricing": {k: res[k] for k in ("net_price_myr", "list_price_myr",
                                        "profit_myr", "profit_rate")} | {"params_used": res["params_used"]},
        "status": "priced",
    }, by=by, event=f"选定货源 {source_id}：折后 RM{res['net_price_myr']}，利润 RM{res['profit_myr']}")
    return {"id": pid, "chosen_source_id": source_id, "pricing": res}


# ==================== 上架素材侧（M3：手动填素材 + 导出打包） ====================

_LISTING_TEXT = ("title_ms", "title_en", "desc_ms")
_LISTING_LIST = ("selling_points_ms", "sku_names")


def set_listing(store, pid, listing, by="manual"):
    """手动/前端填上架素材（引擎走文件协议直写不经此）。写 listing{} + 跑合规 → listing_ready。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    lst = dict(card.get("listing") or {})
    for k in _LISTING_TEXT:
        if k in listing:
            lst[k] = (listing[k] or "").strip()
    for k in _LISTING_LIST:
        if k in listing:
            v = listing[k]
            lst[k] = v if isinstance(v, list) else [x.strip() for x in str(v).replace("，", ",").split(",") if x.strip()]
    if not (lst.get("title_ms") or lst.get("title_en")):
        return {"error": "至少要有马来语或英文标题（title_ms / title_en）"}
    sd = card.get("source_data") or {}
    chk = compliance.check_listing(
        {"title": lst.get("title_ms") or lst.get("title_en"), "category": sd.get("category", "")},
        check_image=False)
    lst["compliance"] = {"pass": chk["pass"],
                         "issues": [c["label"] + "：" + c["note"] for c in chk["checks"] if not c["ok"]]}
    lst.setdefault("images", [])
    lst["generated_by"] = by
    lst["generated_at"] = now()
    store.update_product(pid, {"listing": lst, "status": "listing_ready"}, by=by,
                         event=f"填写上架素材（{by}）：{'合规通过' if chk['pass'] else '有合规问题'}")
    return {"listing": lst}


def _safe_name(s, fallback):
    s = re.sub(r"[^\w一-鿿-]+", "_", str(s or "")).strip("_")
    return (s[:40] or fallback)


def export_product(store, pid, by="console"):
    """把有素材的品卡打包成上架素材包（listing.csv + 核对清单 + 货源），→ exported。"""
    data = store.load_products()
    card = store.get_product(data, pid)
    if card is None:
        return {"error": f"品卡不存在：{pid}"}
    lst = card.get("listing") or {}
    if not (lst.get("title_ms") or lst.get("title_en")):
        return {"error": "还没有上架素材——先「派发上架素材任务」给引擎，或在展开面板手动填素材"}
    sd = card.get("source_data") or {}
    pr = card.get("pricing") or {}
    chosen = next((s for s in (card.get("sources") or []) if s.get("id") == card.get("chosen_source_id")), None)

    def esc(v):
        return '"' + str(v if v is not None else "").replace('"', '""') + '"'
    csv_rows = [
        ("字段", "内容"),
        ("商品名(原)", sd.get("name", "")),
        ("类目", sd.get("category", "")),
        ("马来语标题", lst.get("title_ms", "")),
        ("英文标题", lst.get("title_en", "")),
        ("卖点", " / ".join(lst.get("selling_points_ms") or [])),
        ("详情描述", lst.get("desc_ms", "")),
        ("SKU", " / ".join(lst.get("sku_names") or [])),
        ("折前展示价RM", pr.get("list_price_myr", "")),
        ("折后结算价RM", pr.get("net_price_myr", "")),
        ("单件利润RM", pr.get("profit_myr", "")),
    ]
    listing_csv = "\n".join(esc(a) + "," + esc(b) for a, b in csv_rows) + "\n"

    comp = lst.get("compliance") or {}
    checklist = [f"# 上架前人工核对 · {sd.get('name','')}", ""]
    checklist.append("[ ] 合规：" + ("✅ 预检通过" if comp.get("pass") else "⚠️ " + "；".join(comp.get("issues") or ["见下"])))
    checklist += [
        "[ ] 主图 ≥ 5 张，且已去中文/水印/联系方式/品牌 Logo（图片翻译不做，人工处理）",
        "[ ] 类目选对（选错会被下架）",
        "[ ] 定价：套定价模板后，店铺后台仍需做对应折扣（藏价≠最终价）",
        "[ ] 发货：出单后货叮咚采购派单 → 达意货代（打包费2元/单）送东莞官仓，守 72h 入仓",
        "[ ] 费率占位需核马来当期（佣金/交易费/汇率），利润以实际为准",
    ]
    checklist_txt = "\n".join(checklist) + "\n"

    src_lines = ["# 选定货源", ""]
    if chosen:
        src_lines += [f"链接：{chosen.get('url','')}",
                      f"进货价：¥{chosen.get('price_rmb','')}",
                      f"重量：{chosen.get('weight_g','')} g",
                      f"发货地：{chosen.get('ship_from','') or '—'}",
                      f"起订量：{chosen.get('moq','') or '—'}"]
    else:
        src_lines.append("（未选定货源）")
    imgs = lst.get("images") or []
    src_lines += ["", "# 图片（需人工处理后使用）"] + (imgs if imgs else ["（引擎未收集到图片，去货源页/TikTok页自行取图）"])
    sources_txt = "\n".join(src_lines) + "\n"

    folder_name = f"{pid}_{_safe_name(sd.get('name'), pid)}"
    folder_rel, zip_rel = store.write_export(folder_name, {
        "listing.csv": listing_csv, "checklist.txt": checklist_txt, "sources.txt": sources_txt})
    store.update_product(pid, {"export": {"path": zip_rel, "exported_at": now()}, "status": "exported"},
                         by=by, event=f"导出素材包 {zip_rel}")
    return {"folder": folder_rel, "zip": zip_rel, "files": ["listing.csv", "checklist.txt", "sources.txt"]}
