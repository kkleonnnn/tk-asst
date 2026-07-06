"""core/pricing 单测：RM 口径藏价、反算、批量、费率超限报错。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import pricing  # noqa: E402


class TestPriceOne(unittest.TestCase):
    def test_basic_rm(self):
        res, err = pricing.price_one(20, 300)
        self.assertIsNone(err)
        # 成本 = 20 + 0运费 + 2货代 = 22 元 → /1.55 ≈ RM14.19
        self.assertAlmostEqual(res["cost_rmb"], 22.0, places=2)
        self.assertAlmostEqual(res["cost_myr"], 14.19, places=1)
        # 藏价：net = cost / (1 - 12%费 - 20%利) = cost/0.68
        self.assertAlmostEqual(res["net_price_myr"], 20.87, places=1)
        self.assertGreater(res["profit_myr"], 0)
        self.assertEqual(res["discount_off_pct"], 30)  # 填7 → 30% off

    def test_freight_by_weight(self):
        res, _ = pricing.price_one(20, 1000, {"freight_rmb_per_kg": 15})
        self.assertAlmostEqual(res["freight_rmb"], 15.0, places=2)

    def test_over_100pct_error(self):
        res, err = pricing.price_one(20, 300, {"commission_rate": 60, "target_profit_rate": 50})
        self.assertIsNone(res)
        self.assertIn("100%", err)

    def test_margin_at_price_loss(self):
        """竞品价低于成本 → 利润为负（反算要能暴露亏损）。"""
        m = pricing.margin_at_price(10, 20, 300)  # 成本≈RM14.19 > 售价10
        self.assertLess(m["profit_myr"], 0)

    def test_price_sources_batch(self):
        out = pricing.price_sources([
            {"id": "s1", "purchase_rmb": 8, "weight_g": 90},
            {"id": "s2", "purchase_rmb": 12, "weight_g": 220},
        ])
        self.assertEqual(len(out), 2)
        self.assertNotIn("error", out[0])
        self.assertLess(out[0]["net_price_myr"], out[1]["net_price_myr"])  # 便宜货源折后价更低


if __name__ == "__main__":
    unittest.main()
