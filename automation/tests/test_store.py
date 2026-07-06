"""store 单测：品卡增改/状态校验/任务生命周期/原子写与空库容错（全部在临时目录，不碰真 workspace）。"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from store import Store  # noqa: E402


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkws_")
        self.s = Store(root=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_load(self):
        data = self.s.load_products()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["products"], [])

    def test_add_and_ids(self):
        added = self.s.add_products([
            {"source_data": {"name": "品A"}, "status": "scored"},
            {"source_data": {"name": "品B"}},
        ])
        self.assertEqual([c["id"] for c in added], ["p_0001", "p_0002"])
        self.assertEqual(added[0]["status"], "scored")
        self.assertEqual(added[1]["status"], "imported")
        # 再加一批，编号接续
        more = self.s.add_products([{"source_data": {"name": "品C"}}])
        self.assertEqual(more[0]["id"], "p_0003")

    def test_update_product_and_log(self):
        self.s.add_products([{"source_data": {"name": "品A"}}])
        card = self.s.update_product("p_0001", {"status": "selected"},
                                     by="manual", event="人工勾选")
        self.assertEqual(card["status"], "selected")
        self.assertEqual(card["log"][-1]["event"], "人工勾选")

    def test_illegal_status_rejected(self):
        self.s.add_products([{"source_data": {"name": "品A"}}])
        with self.assertRaises(ValueError):
            self.s.update_product("p_0001", {"status": "flying"})

    def test_task_lifecycle(self):
        self.s.add_products([{"source_data": {"name": "品A"}}])
        t = self.s.create_task("sourcing", ["p_0001"], {"min_candidates": 2})
        self.assertEqual(t["id"], "t_0001")
        self.assertEqual(t["status"], "pending")
        t = self.s.claim_task("t_0001", by="claude")
        self.assertEqual(t["status"], "in_progress")
        self.assertEqual(t["claimed_by"], "claude")
        with self.assertRaises(ValueError):   # 不能重复认领
            self.s.claim_task("t_0001", by="codex")
        t = self.s.finish_task("t_0001", ok=True, note="写入2个货源")
        self.assertEqual(t["status"], "done")

    def test_unknown_task_type(self):
        with self.assertRaises(ValueError):
            self.s.create_task("teleport", ["p_0001"])

    def test_atomic_no_tmp_left(self):
        self.s.add_products([{"source_data": {"name": "品A"}}])
        leftovers = [f for f in os.listdir(self.tmp) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        # 文件确实是合法 JSON
        with open(self.s.products_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["products"][0]["id"], "p_0001")

    def test_schema_version_mismatch(self):
        with open(self.s.products_path, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 99, "products": []}, f)
        with self.assertRaises(ValueError):
            self.s.load_products()

    def test_summary(self):
        self.s.add_products([{"source_data": {"name": "品A"}, "status": "scored"},
                             {"source_data": {"name": "品B"}, "status": "scored"}])
        self.s.create_task("sourcing", ["p_0001"])
        sm = self.s.summary()
        self.assertEqual(sm["products_total"], 2)
        self.assertEqual(sm["by_status"]["scored"], 2)
        self.assertEqual(sm["tasks_pending"], 1)


if __name__ == "__main__":
    unittest.main()
