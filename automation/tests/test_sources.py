"""货源侧 flows 单测：手动加源/编辑补重量/利润对比/选定→priced（临时目录）。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flows  # noqa: E402
from store import Store  # noqa: E402

CSV = """商品名,商品评分,商品三级分类,最低售价,最高售价,近7天销量,近 30 天销量,评论数
好品A,4.8,收纳架,RM12.90,RM15.90,4200,9800,320
"""


class TestSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkws_")
        self.s = Store(root=self.tmp)
        flows.import_products(self.s, csv_text=CSV)
        flows.set_status_bulk(self.s, ["p_0001"], "selected")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _add(self, **kw):
        src = {"url": "https://detail.1688.com/offer/1.html", "price_rmb": 8.5}
        src.update(kw)
        return flows.add_source(self.s, "p_0001", src)

    def test_add_source_becomes_sourced(self):
        r = self._add(weight_g=220, ship_from="广东东莞")
        self.assertEqual(r["source"]["id"], "s1")
        card = self.s.get_product(self.s.load_products(), "p_0001")
        self.assertEqual(card["status"], "sourced")
        # 第二个源编号递增
        r2 = self._add(url="https://detail.1688.com/offer/2.html", price_rmb=7.0)
        self.assertEqual(r2["source"]["id"], "s2")

    def test_add_source_validation(self):
        self.assertIn("error", flows.add_source(self.s, "p_0001", {"price_rmb": 8}))
        self.assertIn("error", flows.add_source(self.s, "p_0001", {"url": "x"}))
        self.assertIn("error", flows.add_source(self.s, "p_0001",
                                                {"url": "x", "price_rmb": "abc"}))
        self.assertIn("error", flows.add_source(self.s, "p_9999",
                                                {"url": "x", "price_rmb": 8}))

    def test_update_source_fill_weight(self):
        self._add()  # 无重量
        cmp1 = flows.compare_sources(self.s, "p_0001")
        self.assertIn("缺重量", cmp1["sources"][0]["pricing_error"])
        flows.update_source(self.s, "p_0001", "s1", {"weight_g": "220"})
        cmp2 = flows.compare_sources(self.s, "p_0001")
        self.assertNotIn("pricing_error", cmp2["sources"][0])
        self.assertGreater(cmp2["sources"][0]["pricing"]["profit_myr"], 0)

    def test_compare_orders_and_market_price(self):
        self._add(weight_g=220)
        self._add(url="https://detail.1688.com/offer/2.html", price_rmb=6.0, weight_g=200)
        cmp = flows.compare_sources(self.s, "p_0001")
        self.assertEqual(cmp["market_price"]["low"], 12.9)
        p1 = cmp["sources"][0]["pricing"]["net_price_myr"]
        p2 = cmp["sources"][1]["pricing"]["net_price_myr"]
        self.assertGreater(p1, p2)  # 更贵的源折后价更高

    def test_choose_source_sets_priced(self):
        self._add(weight_g=220)
        r = flows.choose_source(self.s, "p_0001", "s1")
        self.assertNotIn("error", r)
        card = self.s.get_product(self.s.load_products(), "p_0001")
        self.assertEqual(card["status"], "priced")
        self.assertEqual(card["chosen_source_id"], "s1")
        self.assertGreater(card["pricing"]["profit_myr"], 0)
        self.assertIn("params_used", card["pricing"])

    def test_choose_requires_weight(self):
        self._add()  # 无重量
        r = flows.choose_source(self.s, "p_0001", "s1")
        self.assertIn("error", r)
        self.assertIn("error", flows.choose_source(self.s, "p_0001", "s9"))


if __name__ == "__main__":
    unittest.main()
