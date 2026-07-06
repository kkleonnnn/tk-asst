"""core/scoring 单测：横幅跳过、别名列、打分与红旗、趋势同值不误判。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import scoring  # noqa: E402


class TestRowsToDicts(unittest.TestCase):
    def test_banner_skipped(self):
        rows = [["数据导出自出海匠"],
                ["商品名", "商品评分", "近 30 天销量"],
                ["测试品", "4.8", "5000"]]
        out = scoring.rows_to_dicts(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["商品名"], "测试品")

    def test_empty(self):
        self.assertEqual(scoring.rows_to_dicts([]), [])


class TestScore(unittest.TestCase):
    def _mk(self, **kw):
        base = {"商品名": "品A", "商品评分": "4.8", "最低售价": "RM12.90",
                "最高售价": "RM15.90", "近7天销量": "4200", "近 30 天销量": "9800",
                "评论数": "320", "佣金比例": "8%"}
        base.update(kw)
        return base

    def test_good_product_recommended(self):
        r = scoring.score_products([self._mk()])[0]
        self.assertEqual(r["verdict"], "推荐")
        self.assertEqual(r["score"], 7)
        self.assertEqual(r["trend"], "↑上升")   # 4200/7 ÷ 9800/30 ≈ 1.84
        self.assertEqual(r["price_low_myr"], 12.9)

    def test_trend_same_value_not_up(self):
        """出海匠常见：近7天=近30天（同值）→ 不可判趋势、不加分。"""
        r = scoring.score_products([self._mk(近7天销量="9800")])[0]
        self.assertIn("近7≈30天", r["trend"])
        self.assertEqual(r["score"], 5)  # 少了趋势 2 分

    def test_flags_and_downgrade(self):
        r = scoring.score_products([self._mk(商品评分="3.9", 评论数="5",
                                             近7天销量="100", **{"近 30 天销量": "900"})])[0]
        self.assertIn("趋势↓", r["flags"])
        self.assertTrue(any("评分" in f for f in r["flags"]))
        self.assertTrue(any("评论" in f for f in r["flags"]))

    def test_price_cap_flag(self):
        r = scoring.score_products([self._mk(最低售价="RM128")])[0]
        self.assertTrue(any("不易走量" in f for f in r["flags"]))

    def test_missing_sales(self):
        d = self._mk()
        d.pop("近7天销量"); d.pop("近 30 天销量")
        r = scoring.score_products([d])[0]
        self.assertEqual(r["verdict"], "缺销量")

    def test_sorted_by_score_then_sales(self):
        rows = [self._mk(商品名="低分", 商品评分="3.0", 评论数="1"),
                self._mk(商品名="高分")]
        out = scoring.score_products(rows)
        self.assertEqual(out[0]["name"], "高分")

    def test_params_override(self):
        r = scoring.score_products([self._mk()], {"min_sales_30d": 99999})[0]
        self.assertTrue(any("近30天销量" in f for f in r["flags"]))


if __name__ == "__main__":
    unittest.main()
