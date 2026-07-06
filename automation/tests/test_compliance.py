"""core/compliance 单测：标题公式、违禁词、禁售类目、品牌授权、图数开关。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import compliance  # noqa: E402


class TestBuildTitle(unittest.TestCase):
    def test_formula(self):
        t = compliance.build_title({"core_word": "除湿盒", "keywords": "防潮 衣柜",
                                    "scene": "雨季", "audience": "家庭", "spec": "3只装"})
        self.assertEqual(t, "除湿盒 防潮 衣柜 雨季 家庭 3只装")

    def test_fallback_name(self):
        self.assertEqual(compliance.build_title({"name": "收纳盒"}), "收纳盒")


class TestCheck(unittest.TestCase):
    def test_clean_pass_no_image(self):
        r = compliance.check_listing({"core_word": "车载手机支架", "category": "汽车配件"},
                                     check_image=False)
        self.assertTrue(r["pass"])

    def test_banned_words(self):
        r = compliance.check_listing({"core_word": "最强除湿盒 全网第一"}, check_image=False)
        self.assertFalse(r["pass"])
        bad = [c for c in r["checks"] if not c["ok"]]
        self.assertTrue(any("违禁" in c["label"] for c in bad))

    def test_forbidden_category(self):
        r = compliance.check_listing({"core_word": "普通品", "category": "矫正眼镜"},
                                     check_image=False)
        self.assertFalse(r["pass"])

    def test_brand_needs_authorization(self):
        r1 = compliance.check_listing({"core_word": "手机壳", "brand": "某品牌"}, check_image=False)
        self.assertFalse(r1["pass"])
        r2 = compliance.check_listing({"core_word": "手机壳", "brand": "某品牌"},
                                      {"brand_authorized": "是"}, check_image=False)
        self.assertTrue(r2["pass"])

    def test_image_count_checked_when_on(self):
        r = compliance.check_listing({"core_word": "收纳盒", "image_count": 3})
        self.assertFalse(r["pass"])
        r2 = compliance.check_listing({"core_word": "收纳盒", "image_count": 6})
        self.assertTrue(r2["pass"])


if __name__ == "__main__":
    unittest.main()
