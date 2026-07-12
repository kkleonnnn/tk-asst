"""listing_ms 单测：中文 SKU→马来 确定性翻译 + 属性默认值。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import listing_ms as L  # noqa: E402

# 实操验证过的 9 个变体 → 期望马来名（与线上收尾一致）
NINE = [
    ("奶油白小号1个装可伸缩【袜子/内裤15件】", "Krim Kecil (S) - Stokin/Seluar Dalam 15pcs"),
    ("素雅白小号1个装可伸缩【袜子/内裤15件】", "Putih Kecil (S) - Stokin/Seluar Dalam 15pcs"),
    ("奶油白中号1个装可伸缩【内裤20件】", "Krim Sederhana (M) - Seluar Dalam 20pcs"),
    ("素雅白中号1个装可伸缩【内裤20件】", "Putih Sederhana (M) - Seluar Dalam 20pcs"),
    ("奶油白大号1个装可伸缩【衬衫/短袖20件】", "Krim Besar (L) - Kemeja/Lengan Pendek 20pcs"),
    ("素雅白大号1个装可伸缩【衬衫/短袖20件】", "Putih Besar (L) - Kemeja/Lengan Pendek 20pcs"),
    ("素雅白特大号1个装可伸缩【牛仔裤10件】", "Putih Ekstra Besar (XL) - Seluar Jeans 10pcs"),
    ("奶油白超大号1个装可伸缩【毛衣10件】", "Krim Sangat Besar (XXL) - Sweater 10pcs"),
    ("素雅白超大号1个装可伸缩【毛衣10件】", "Putih Sangat Besar (XXL) - Sweater 10pcs"),
]


class TestListingMs(unittest.TestCase):
    def test_nine_exact(self):
        for zh, want in NINE:
            r = L.translate_sku_name_ms(zh)
            self.assertEqual(r["ms"], want, zh)
            self.assertEqual(r["unknown"], [], zh)
            self.assertLessEqual(len(r["ms"]), 50)

    def test_drop_misleading_extendable(self):
        # 可伸缩=误导词，不能出现在马来名里（不能翻成 extendable/teleskopik）
        r = L.translate_sku_name_ms("奶油白大号可伸缩【毛衣10件】")
        self.assertNotIn("伸缩", r["ms"])
        for bad in ("extend", "telesk", "tarik"):
            self.assertNotIn(bad, r["ms"].lower())

    def test_unknown_flagged_not_dropped(self):
        # 认不出的颜色/尺寸/品类要进 unknown，且不静默丢失
        r = L.translate_sku_name_ms("土豪金巨无霸【床单3件】")
        self.assertTrue(r["unknown"])
        self.assertIn("床单", r["unknown"])
        self.assertIn("土豪金巨无霸", r["unknown"])

    def test_no_bracket_and_empty(self):
        self.assertEqual(L.translate_sku_name_ms("蓝色中号")["ms"], "Biru Sederhana (M)")
        self.assertEqual(L.translate_sku_name_ms(""), {"ms": "", "unknown": []})
        self.assertEqual(L.translate_sku_name_ms(None), {"ms": "", "unknown": []})

    def test_batch_keeps_order_and_shape(self):
        out = L.translate_sku_names_ms([z for z, _ in NINE])
        self.assertEqual(len(out), 9)
        self.assertEqual(out[6]["zh"], NINE[6][0])
        self.assertEqual(out[6]["ms"], NINE[6][1])

    def test_max_len_truncates(self):
        r = L.translate_sku_name_ms("奶油白超大号【毛衣10件】", max_len=10)
        self.assertLessEqual(len(r["ms"]), 10)

    def test_attributes_confirmed_keys(self):
        a = L.storage_box_attributes()
        for k in ("品牌", "材质", "功能", "形状", "存储类型"):
            self.assertIn(k, a)
            self.assertTrue(a[k]["confirmed"])
        self.assertEqual(a["材质"]["value"], ["塑料材料"])
        self.assertEqual(a["功能"]["value"], ["可折叠的"])


if __name__ == "__main__":
    unittest.main()
