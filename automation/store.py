"""store —— workspace/ 数据总线的唯一读写层（原子写 + schema 版本）。

规则（CONTRIBUTING 代码规范章）：
- 所有对 products.json / tasks.json 的读写必须经本模块，写入=临时文件+os.replace（原子）。
- core/ 不得 import 本模块（core 是纯函数层）。
"""
import json
import os
import tempfile
import zipfile
from datetime import datetime

SCHEMA_VERSION = 1

STATUSES = ["imported", "scored", "selected", "sourcing", "sourced", "priced",
            "listing_ready", "exported", "published", "testing", "archived", "dropped"]
TASK_TYPES = ["sourcing", "listing"]
TASK_STATUSES = ["pending", "in_progress", "done", "failed"]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Store:
    def __init__(self, root=None):
        # 默认 workspace 在仓库根（automation 的上一级）
        here = os.path.dirname(os.path.abspath(__file__))
        self.root = root or os.path.join(os.path.dirname(here), "workspace")
        self.products_path = os.path.join(self.root, "products.json")
        self.tasks_path = os.path.join(self.root, "tasks.json")
        self.exports_dir = os.path.join(self.root, "exports")

    # ---------- 底层读写 ----------
    def _load(self, path, key):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"schema_version": SCHEMA_VERSION, "updated_at": now(), key: []}
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"{os.path.basename(path)} schema_version="
                             f"{data.get('schema_version')} 与当前 {SCHEMA_VERSION} 不符，需迁移")
        data.setdefault(key, [])
        return data

    def _save(self, path, data):
        """原子写：临时文件 + os.replace，中途失败不会写坏总线。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data["schema_version"] = SCHEMA_VERSION
        data["updated_at"] = now()
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return data

    def load_products(self):
        return self._load(self.products_path, "products")

    def save_products(self, data):
        return self._save(self.products_path, data)

    def load_tasks(self):
        return self._load(self.tasks_path, "tasks")

    def save_tasks(self, data):
        return self._save(self.tasks_path, data)

    # ---------- 品卡 ----------
    @staticmethod
    def _next_id(items, prefix):
        mx = 0
        for it in items:
            try:
                mx = max(mx, int(str(it.get("id", "")).split("_")[1]))
            except (IndexError, ValueError):
                continue
        return f"{prefix}_{mx + 1:04d}"

    def add_products(self, cards, by="console"):
        """新增品卡（自动编号/时间戳/日志）。cards: [{source_data, scoring?, status?}]"""
        data = self.load_products()
        added = []
        for c in cards:
            pid = self._next_id(data["products"] + added, "p")
            card = {
                "id": pid, "status": c.get("status", "imported"),
                "created_at": now(), "updated_at": now(),
                "source_data": c["source_data"],
                "scoring": c.get("scoring", {}),
                "sources": [], "chosen_source_id": None,
                "pricing": {}, "listing": {}, "export": {},
                "publish": {"published_at": None, "tiktok_product_id": None},
                "testing": {"listed_at": None, "notes": []},
                "log": [{"at": now(), "by": by, "event": f"创建品卡（{c.get('status', 'imported')}）"}],
            }
            added.append(card)
        data["products"].extend(added)
        self.save_products(data)
        return added

    def get_product(self, data, pid):
        for c in data["products"]:
            if c["id"] == pid:
                return c
        return None

    def update_product(self, pid, patch, by="console", event=None):
        """浅合并 patch 到品卡；status 必须合法；自动记日志。"""
        data = self.load_products()
        card = self.get_product(data, pid)
        if card is None:
            raise KeyError(f"品卡不存在：{pid}")
        if "status" in patch and patch["status"] not in STATUSES:
            raise ValueError(f"非法状态：{patch['status']}")
        card.update(patch)
        card["updated_at"] = now()
        card.setdefault("log", []).append(
            {"at": now(), "by": by, "event": event or f"更新字段：{'/'.join(patch.keys())}"})
        self.save_products(data)
        return card

    # ---------- 任务 ----------
    def create_task(self, task_type, product_ids, params=None, by="console"):
        if task_type not in TASK_TYPES:
            raise ValueError(f"未知任务类型：{task_type}")
        data = self.load_tasks()
        task = {
            "id": self._next_id(data["tasks"], "t"),
            "type": task_type, "product_ids": list(product_ids),
            "status": "pending", "created_at": now(),
            "claimed_by": None, "claimed_at": None, "done_at": None,
            "params": params or {}, "result_note": "",
        }
        data["tasks"].append(task)
        self.save_tasks(data)
        return task

    def claim_task(self, tid, by):
        data = self.load_tasks()
        for t in data["tasks"]:
            if t["id"] == tid:
                if t["status"] != "pending":
                    raise ValueError(f"任务 {tid} 状态为 {t['status']}，不可认领")
                t.update({"status": "in_progress", "claimed_by": by, "claimed_at": now()})
                self.save_tasks(data)
                return t
        raise KeyError(f"任务不存在：{tid}")

    def finish_task(self, tid, ok, note=""):
        data = self.load_tasks()
        for t in data["tasks"]:
            if t["id"] == tid:
                t.update({"status": "done" if ok else "failed",
                          "done_at": now(), "result_note": note})
                self.save_tasks(data)
                return t
        raise KeyError(f"任务不存在：{tid}")

    # ---------- 素材包导出（store owns exports_dir 的 IO） ----------
    def write_export(self, folder_name, files):
        """把 {文件名: 文本内容} 写进 exports/<folder_name>/，再打包同名 .zip。
        .csv 用 utf-8-sig（Excel/WPS 打开中文马来文不乱码）。返回 (folder_rel, zip_rel)。"""
        folder = os.path.join(self.exports_dir, folder_name)
        os.makedirs(folder, exist_ok=True)
        for fn, content in files.items():
            enc = "utf-8-sig" if fn.lower().endswith(".csv") else "utf-8"
            with open(os.path.join(folder, fn), "w", encoding=enc) as f:
                f.write(content)
        zip_path = folder + ".zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in files:
                z.write(os.path.join(folder, fn), arcname=os.path.join(folder_name, fn))
        rel = lambda p: os.path.relpath(p, self.root)  # noqa: E731
        return rel(folder), rel(zip_path)

    # ---------- 看板汇总 ----------
    def summary(self):
        prods = self.load_products()["products"]
        tasks = self.load_tasks()["tasks"]
        by_status = {}
        for c in prods:
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        return {
            "products_total": len(prods),
            "by_status": by_status,
            "tasks_pending": sum(1 for t in tasks if t["status"] == "pending"),
            "tasks_in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
        }
