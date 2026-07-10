"""M3 flows 单测：手动填素材→listing_ready、导出素材包(文件+zip)→exported。"""
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flows  # noqa: E402
from store import Store  # noqa: E402

CSV = """商品名,商品评分,商品三级分类,最低售价,最高售价,近7天销量,近 30 天销量,评论数
好品A,4.8,收纳架,RM12.90,RM15.90,4200,9800,320
"""


class TestExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tkws_")
        self.s = Store(root=self.tmp)
        flows.import_products(self.s, csv_text=CSV)
        flows.set_status_bulk(self.s, ["p_0001"], "selected")
        flows.add_source(self.s, "p_0001",
                         {"url": "https://detail.1688.com/offer/1.html", "price_rmb": 8.5, "weight_g": 220})
        flows.choose_source(self.s, "p_0001", "s1")  # → priced

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _card(self):
        return self.s.get_product(self.s.load_products(), "p_0001")

    def test_set_listing_ready_and_compliance(self):
        r = flows.set_listing(self.s, "p_0001", {
            "title_ms": "Kotak Penyimpanan Kalis Lembap 3pcs",
            "selling_points_ms": "Jimat ruang, Kalis air, Mudah simpan",
            "desc_ms": "Kotak penyimpanan untuk almari.",
        })
        self.assertNotIn("error", r)
        card = self._card()
        self.assertEqual(card["status"], "listing_ready")
        self.assertEqual(len(card["listing"]["selling_points_ms"]), 3)
        self.assertTrue(card["listing"]["compliance"]["pass"])

    def test_set_listing_catches_banned_word(self):
        flows.set_listing(self.s, "p_0001", {"title_ms": "全网第一 收纳盒"})
        comp = self._card()["listing"]["compliance"]
        self.assertFalse(comp["pass"])
        self.assertTrue(any("违禁" in i for i in comp["issues"]))

    def test_set_listing_requires_title(self):
        self.assertIn("error", flows.set_listing(self.s, "p_0001", {"desc_ms": "x"}))

    def test_export_requires_listing(self):
        self.assertIn("error", flows.export_product(self.s, "p_0001"))  # 还没素材

    def test_export_builds_package(self):
        flows.set_listing(self.s, "p_0001", {"title_ms": "Kotak Penyimpanan 3pcs"})
        r = flows.export_product(self.s, "p_0001")
        self.assertNotIn("error", r)
        # 文件与 zip 都在
        folder = os.path.join(self.tmp, r["folder"])
        for fn in ("listing.csv", "checklist.txt", "sources.txt"):
            self.assertTrue(os.path.exists(os.path.join(folder, fn)), fn)
        zpath = os.path.join(self.tmp, r["zip"])
        self.assertTrue(zipfile.is_zipfile(zpath))
        with zipfile.ZipFile(zpath) as z:
            self.assertEqual(len(z.namelist()), 3)
        # listing.csv 含马来语标题 + BOM（Excel 兼容）
        with open(os.path.join(folder, "listing.csv"), "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Kotak Penyimpanan", raw.decode("utf-8-sig"))
        # sources.txt 含选定货源链接
        with open(os.path.join(folder, "sources.txt"), encoding="utf-8") as f:
            self.assertIn("1688.com/offer/1.html", f.read())
        # 状态 → exported，路径回填
        card = self._card()
        self.assertEqual(card["status"], "exported")
        self.assertEqual(card["export"]["path"], r["zip"])


if __name__ == "__main__":
    unittest.main()
