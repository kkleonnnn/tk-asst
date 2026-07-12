"""publish_recipe 单测：把"该填什么"算齐，SKU 走确定性翻译，卡点进 warnings。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flows  # noqa: E402
from store import Store  # noqa: E402

CSV = """商品名,商品评分,商品三级分类,最低售价,最高售价,近7天销量,近 30 天销量,评论数
广东品,4.8,收纳盒,RM12,RM16,4000,9000,300
外省品,4.7,家居,RM10,RM20,3000,8000,200
"""


class TestPublishRecipe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkwsr_")
        self.s = Store(root=self.tmp)
        flows.import_products(self.s, csv_text=CSV)
        flows.set_status_bulk(self.s, ["p_0001", "p_0002"], "selected")
        flows.add_source(self.s, "p_0001", {"url": "https://detail.1688.com/offer/1.html",
                         "price_rmb": 7.2, "weight_g": 350, "ship_from": "广东东莞"})
        flows.add_source(self.s, "p_0002", {"url": "https://detail.1688.com/offer/2.html",
                         "price_rmb": 6, "weight_g": None, "ship_from": "江苏徐州"})
        flows.choose_source(self.s, "p_0001", "s1")
        flows.choose_source(self.s, "p_0002", "s1")
        flows.set_listing(self.s, "p_0001", {
            "title_ms": "Kotak Penyimpanan Baju Boleh Lipat",
            "desc_ms": "Kemaskan almari anda.",
            "selling_points_ms": ["Jimat ruang"]})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_recipe_core_fields(self):
        r = flows.publish_recipe(self.s, "p_0001")
        self.assertEqual(r["source_url"], "https://detail.1688.com/offer/1.html")
        self.assertTrue(r["guangdong"])
        self.assertEqual(r["title_ms"], "Kotak Penyimpanan Baju Boleh Lipat")
        self.assertEqual(r["weight_g"], 350)
        self.assertIn("材质", r["attributes"])
        self.assertEqual(r["warnings"], [])          # 广东 + 有文案 + 有重量
        self.assertIsNone(r["sku_names_ms"])

    def test_recipe_with_variants(self):
        r = flows.publish_recipe(self.s, "p_0001", variant_names=[
            "奶油白小号1个装可伸缩【袜子/内裤15件】", "素雅白超大号1个装可伸缩【毛衣10件】"])
        self.assertEqual(len(r["sku_names_ms"]), 2)
        self.assertEqual(r["sku_names_ms"][0]["ms"], "Krim Kecil (S) - Stokin/Seluar Dalam 15pcs")
        self.assertEqual(r["warnings"], [])          # 无 unknown 词

    def test_variants_unknown_go_to_warnings(self):
        r = flows.publish_recipe(self.s, "p_0001", variant_names=["土豪金【床单3件】"])
        self.assertTrue(any("复核" in w for w in r["warnings"]))

    def test_non_guangdong_and_missing_listing_warn(self):
        r = flows.publish_recipe(self.s, "p_0002")   # 江苏 + 无 listing + 无重量
        self.assertFalse(r["guangdong"])
        joined = " ".join(r["warnings"])
        self.assertIn("非广东", joined)
        self.assertIn("标题", joined)
        self.assertIn("重量", joined)

    def test_missing_product(self):
        self.assertIn("error", flows.publish_recipe(self.s, "nope"))


if __name__ == "__main__":
    unittest.main()
