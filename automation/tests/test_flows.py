"""flows 编排层单测：导入建卡/去重、批量流转、任务派发（临时目录，不碰真 workspace）。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flows  # noqa: E402
from store import Store  # noqa: E402

CSV = """数据导出自出海匠
商品名,商品评分,商品三级分类,最低售价,最高售价,近7天销量,近 30 天销量,评论数
好品A,4.8,收纳架,RM12.90,RM15.90,4200,9800,320
差品B,3.0,女装,RM39.00,RM49.00,100,900,5
"""


class TestFlows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkws_")
        self.s = Store(root=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_import_creates_scored_cards(self):
        r = flows.import_products(self.s, csv_text=CSV)
        self.assertEqual(r["imported"], 2)
        prods = self.s.load_products()["products"]
        self.assertEqual(len(prods), 2)
        self.assertTrue(all(p["status"] == "scored" for p in prods))
        best = next(p for p in prods if p["source_data"]["name"] == "好品A")
        self.assertEqual(best["scoring"]["verdict"], "推荐")
        self.assertEqual(best["source_data"]["price_low_myr"], 12.9)

    def test_import_dedupe_by_name(self):
        flows.import_products(self.s, csv_text=CSV)
        r2 = flows.import_products(self.s, csv_text=CSV)
        self.assertEqual(r2["imported"], 0)
        self.assertEqual(r2["skipped_dup"], 2)
        self.assertEqual(len(self.s.load_products()["products"]), 2)

    def test_import_empty_error(self):
        self.assertIn("error", flows.import_products(self.s, csv_text=""))
        self.assertIn("error", flows.import_products(self.s, csv_text="只有一列"))

    def test_bulk_status(self):
        flows.import_products(self.s, csv_text=CSV)
        r = flows.set_status_bulk(self.s, ["p_0001", "p_0002"], "selected")
        self.assertEqual(len(r["updated"]), 2)
        r2 = flows.set_status_bulk(self.s, ["p_0001", "p_9999"], "dropped")
        self.assertEqual(r2["updated"], ["p_0001"])
        self.assertEqual(len(r2["errors"]), 1)

    def test_dispatch_sourcing_only_selected(self):
        flows.import_products(self.s, csv_text=CSV)
        # 全是 scored，不可派发
        r = flows.dispatch_task(self.s, "sourcing", ["p_0001"])
        self.assertIn("error", r)
        # 选定后派发成功，品卡 → sourcing
        flows.set_status_bulk(self.s, ["p_0001"], "selected")
        r2 = flows.dispatch_task(self.s, "sourcing", ["p_0001", "p_0002"])
        self.assertEqual(r2["count"], 1)
        self.assertEqual(r2["task"]["type"], "sourcing")
        self.assertTrue(any("p_0002" in w for w in r2["skipped"]))
        card = self.s.get_product(self.s.load_products(), "p_0001")
        self.assertEqual(card["status"], "sourcing")
        # 任务在队列里 pending
        tasks = self.s.load_tasks()["tasks"]
        self.assertEqual(tasks[0]["status"], "pending")
        self.assertEqual(tasks[0]["product_ids"], ["p_0001"])

    def test_dispatch_unknown_type(self):
        self.assertIn("error", flows.dispatch_task(self.s, "teleport", ["p_0001"]))


if __name__ == "__main__":
    unittest.main()
