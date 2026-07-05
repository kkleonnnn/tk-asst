"""④ 定价 / 利润（可真跑）—— 藏价 + 利润核算。

复刻货叮咚「售价利润率」藏价逻辑 + 02 定价公式：
    售价 = 采购价 + 运费 + 货代费 + 达人佣金 + 利润 + 平台佣金 + 交易手续费
把成本+目标利润前置藏进售价，倒推「折后价(结算价)」与「折前展示价」。

⚠️ 所有费率默认值都是占位示例，务必去 TikTok 学习中心核马来站当期值再用。
"""
from engine import Step, StepResult, OK, ERROR


def _f(params, key):
    return float(params.get(key) or 0)


class PricingStep(Step):
    id = "pricing"
    name = "④ 定价 / 利润"
    stage = "定价"
    available = True
    desc = ("按采购价+重量+各项费率，算出「折前展示价 / 折后结算价 / 单件利润 / 利润率」。"
            "利润<0 或 费率+利润率≥100% 会报红。若填了竞品/目标售价，还会反算在该价位的实际利润。")
    requires = ["费率需你去 TikTok 学习中心核『马来站当期』值（下方默认是占位示例，勿照抄）"]
    inputs_help = ('输入区填 JSON，如：{"purchase_price_rmb": 20, "weight_g": 300, '
                   '"target_sell_price_usd": 0}（target_sell_price_usd 可选：填了就反算该价位利润）。'
                   "也可留空，用下方参数里的默认试算。")
    params = [
        {"key": "purchase_price_rmb", "label": "采购价(元/件)", "type": "number", "default": 20,
         "help": "输入区没给就用这个"},
        {"key": "weight_g", "label": "重量(克)", "type": "number", "default": 300,
         "help": "务必准，直接影响头程运费与藏价"},
        {"key": "freight_rmb_per_kg", "label": "头程跨境运费(元/kg)", "type": "number", "default": 0,
         "help": "查『马来官方运价表』填；0=暂不计"},
        {"key": "agent_fee_rmb", "label": "货代费(元/件)", "type": "number", "default": 2,
         "help": "达意货代打包贴单送官仓 2 元/单(量大可谈)；超规(三边和≥220cm 或 ≥10kg)+1 元；特殊耗材另计"},
        {"key": "fx_rmb_per_usd", "label": "汇率(元/美元)", "type": "number", "default": 7.2,
         "help": "TikTok 东南亚按 USD 结算，成本从人民币折算"},
        {"key": "commission_rate", "label": "平台佣金率(%)", "type": "number", "default": 5,
         "help": "⚠️马来当期需核，新商可能免佣期"},
        {"key": "transaction_fee_rate", "label": "交易手续费率(%)", "type": "number", "default": 2,
         "help": "⚠️以官方为准"},
        {"key": "ecom_service_rate", "label": "电商增长服务费率(%)", "type": "number", "default": 0,
         "help": "⚠️以官方为准，无则填0"},
        {"key": "influencer_rate", "label": "达人佣金藏价(%)", "type": "number", "default": 5,
         "help": "藏几个点=打算给达人几个点；实付高于此差额吃自己利润"},
        {"key": "target_profit_rate", "label": "目标利润率(%)", "type": "number", "default": 20,
         "help": "占折后结算价的比例"},
        {"key": "discount_n", "label": "折扣N(填7=打7折)", "type": "number", "default": 7,
         "help": "货叮咚口径：填7→店铺后台做30%off；填6→40%off。必设，否则易亏"},
        {"key": "other_cost_usd", "label": "其他成本(USD/件)", "type": "number", "default": 0},
    ]

    def run(self, inputs, params, config):
        purchase = float(inputs.get("purchase_price_rmb") or params["purchase_price_rmb"])
        weight = float(inputs.get("weight_g") or params["weight_g"])
        freight_kg = _f(params, "freight_rmb_per_kg")
        agent = _f(params, "agent_fee_rmb")
        fx = float(params["fx_rmb_per_usd"]) or 7.2
        commission = _f(params, "commission_rate") / 100
        transaction = _f(params, "transaction_fee_rate") / 100
        ecom = _f(params, "ecom_service_rate") / 100
        influencer = _f(params, "influencer_rate") / 100
        profit_r = _f(params, "target_profit_rate") / 100
        discount_n = float(params["discount_n"]) or 10
        other = _f(params, "other_cost_usd")

        # 成本（USD/件）
        freight_rmb = weight / 1000.0 * freight_kg
        cost_rmb = purchase + freight_rmb + agent
        cost_usd = cost_rmb / fx + other

        fees_frac = commission + transaction + ecom + influencer
        denom = 1 - fees_frac - profit_r
        checks = []
        if denom <= 0:
            return StepResult(
                status=ERROR,
                message=f"费率合计({fees_frac*100:.1f}%)+利润率({profit_r*100:.0f}%)≥100%，无法定价，请下调。",
            )

        # 藏价倒推：折后结算价 net，使 成本 + 各费(净价%) + 利润(净价%) = net
        net = cost_usd / denom
        list_price = net / (discount_n / 10.0)   # 折前展示价
        profit_usd = profit_r * net
        fees_usd = fees_frac * net

        checks.append({"label": f"单件利润 ${profit_usd:.2f}（利润率 {profit_r*100:.0f}%）",
                       "ok": profit_usd > 0, "note": "藏价法：利润率按你设定值达成"})
        checks.append({"label": "已设折扣", "ok": discount_n < 10,
                       "note": f"填{discount_n:.0f}→店铺后台做 {(10-discount_n)*10:.0f}% off（藏价≠最终价，后台仍要做折扣）"})

        fields = {
            "成本合计(¥/件)": f"{cost_rmb:.2f}  (采购{purchase:.1f}+头程{freight_rmb:.2f}+货代{agent:.1f})",
            "成本(USD)": f"{cost_usd:.2f}",
            "折前展示价(USD)": f"{list_price:.2f}",
            "折后结算价(USD)": f"{net:.2f}",
            "平台各项费(USD)": f"{fees_usd:.2f}  (佣金+手续费+增长费+达人{fees_frac*100:.1f}%)",
            "单件利润(USD)": f"{profit_usd:.2f}",
            "利润率": f"{profit_r*100:.0f}%",
        }

        notes = ["费率均为占位示例，务必核马来当期（学习中心）。",
                 "达人佣金藏5%但实付15% → 多的10%从利润里扣。"]

        # 竞品/目标售价反算
        target = float(inputs.get("target_sell_price_usd") or 0)
        if target > 0:
            t_fees = fees_frac * target
            t_profit = target - cost_usd - t_fees
            t_margin = t_profit / target if target else 0
            fields["【反算】目标售价(USD)"] = f"{target:.2f}"
            fields["【反算】该价位利润(USD)"] = f"{t_profit:.2f}"
            fields["【反算】该价位利润率"] = f"{t_margin*100:.1f}%"
            checks.append({"label": f"按竞品/目标价 ${target:.2f} 卖仍盈利",
                           "ok": t_profit > 0,
                           "note": f"利润 ${t_profit:.2f} / {t_margin*100:.1f}%"})

        return StepResult(
            status=OK,
            message=f"折后结算价 ${net:.2f}，单件利润 ${profit_usd:.2f}（{profit_r*100:.0f}%）。",
            data={"summary": f"折前 ${list_price:.2f} / 折后 ${net:.2f} / 利润 ${profit_usd:.2f}",
                  "fields": fields, "checks": checks, "notes": notes},
            outputs={"pricing": {"list_price_usd": round(list_price, 2),
                                 "net_price_usd": round(net, 2),
                                 "profit_usd": round(profit_usd, 2)}},
        )
