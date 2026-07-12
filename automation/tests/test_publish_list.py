"""发布清单单测：ready 品汇出 CSV + Option-A 步骤；广东判定/非广东标记。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flows  # noqa: E402
from store import Store  # noqa: E402

CSV = """商品名,商品评分,商品三级分类,最低售价,最高售价,近7天销量,近 30 天销量,评论数
广东品,4.8,收纳架,RM12,RM16,4000,9000,300
外省品,4.7,家居,RM10,RM20,3000,8000,200
"""


class TestPublishList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkws_")
        self.s = Store(root=self.tmp)
        flows.import_products(self.s, csv_text=CSV)
        flows.set_status_bulk(self.s, ["p_0001", "p_0002"], "selected")
        flows.add_source(self.s, "p_0001", {"url": "https://detail.1688.com/offer/1.html",
                         "price_rmb": 8, "weight_g": 300, "ship_from": "广东东莞"})
        flows.add_source(self.s, "p_0002", {"url": "https://detail.1688.com/offer/2.html",
                         "price_rmb": 6, "weight_g": 200, "ship_from": "江苏徐州"})
        flows.choose_source(self.s, "p_0001", "s1")
        flows.choose_source(self.s, "p_0002", "s1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_guangdong_helper(self):
        self.assertTrue(flows._is_guangdong("广东东莞"))
        self.assertTrue(flows._is_guangdong("东莞洪梅"))
        self.assertTrue(flows._is_guangdong("深圳"))
        self.assertFalse(flows._is_guangdong("江苏徐州"))
        self.assertFalse(flows._is_guangdong("安徽合肥"))
        self.assertFalse(flows._is_guangdong(""))

    def test_publish_list_flags_non_guangdong(self):
        r = flows.publish_list(self.s)
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["non_guangdong"], ["外省品"])  # 江苏徐州 → 非广东
        folder = os.path.join(self.tmp, r["folder"])
        csv = open(os.path.join(folder, "发布清单.csv"), encoding="utf-8-sig").read()
        self.assertIn("1688.com/offer/1.html", csv)
        self.assertIn("🚩", csv)                 # 外省品被标旗
        steps = open(os.path.join(folder, "操作步骤.txt"), encoding="utf-8").read()
        self.assertIn("采集", steps)
        self.assertIn("保存并发布", steps)

    def test_publish_list_empty(self):
        s2 = Store(root=tempfile.mkdtemp(prefix="tkws2_"))
        self.assertIn("error", flows.publish_list(s2))


if __name__ == "__main__":
    unittest.main()
