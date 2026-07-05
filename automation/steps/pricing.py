"""④ 定价 / 利润（可真跑）—— 藏价 + 利润核算。

两种模式：
- 批量模式：接 ①②带来的品清单（carry.selected，②里填了进货价/重量），逐个算折后价/利润。
- 单品模式：输入区给 JSON（purchase_price_rmb/weight_g）单独试算，含竞品价反算。

复刻货叮咚「售价利润率」藏价逻辑 + 02 定价公式：
    售价 = 采购价 + 运费 + 货代费 + 达人佣金 + 利润 + 平台佣金 + 交易手续费
⚠️ 费率默认值都是占位示例，务必去 TikTok 学习中心核马来站当期值再用。
"""
import re

from engine import Step, StepResult, OK, ERROR


def _f(params, key):
    return float(params.get(key) or 0)


def _num(v):
    if v is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(v))
    if s in ("", ".", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _g(x):
    return "—" if x is None else f"{x:g}"


def _price_one(purchase, weight, params):
    """核心藏价计算。返回 (dict, None) 或 (None, 错误说明)。"""
    freight_kg = _f(params, "freight_rmb_per_kg")
    agent = _f(params, "agent_fee_rmb")
    fx = float(params.get("fx_rmb_per_usd") or 7.2) or 7.2
    commission = _f(params, "commission_rate") / 100
    transaction = _f(params, "transaction_fee_rate") / 100
    ecom = _f(params, "ecom_service_rate") / 100
    influencer = _f(params, "influencer_rate") / 100
    profit_r = _f(params, "target_profit_rate") / 100
    discount_n = float(params.get("discount_n") or 10) or 10
    other = _f(params, "other_cost_usd")

    freight_rmb = weight / 1000.0 * freight_kg
    cost_rmb = purchase + freight_rmb + agent
    cost_usd = cost_rmb / fx + other
    fees_frac = commission + transaction + ecom + influencer
    denom = 1 - fees_frac - profit_r
    if denom <= 0:
        return None, f"费率合计({fees_frac*100:.1f}%)+利润率({profit_r*100:.0f}%)≥100%，无法定价"
    net = cost_usd / denom
    return {
        "cost_rmb": cost_rmb, "cost_usd": cost_usd, "freight_rmb": freight_rmb, "agent": agent,
        "net": net, "list_price": net / (discount_n / 10.0),
        "profit_usd": profit_r * net, "fees_usd": fees_frac * net,
        "fees_frac": fees_frac, "profit_r": profit_r, "discount_n": discount_n,
    }, None


class PricingStep(Step):
    id = "pricing"
    name = "④ 定价 / 利润"
    stage = "定价"
    available = True
    desc = ("默认【批量】给 ①②带来的品算利润（先在 ② 里填好每个品的进货价/重量）。"
            "也可在输入区给 JSON 单品试算：算折前/折后价+单件利润，可填竞品价反算。"
            "利润<0 或 费率+利润率≥100% 会报红。")
    requires = ["费率需你去 TikTok 学习中心核『马来站当期』值（下方默认是占位示例，勿照抄）"]
    inputs_help = ('默认用 ①②带来的品批量算（②里填了进货价/重量的才算）。'
                   '单品试算就填 JSON：{"purchase_price_rmb": 20, "weight_g": 300, "target_sell_price_usd": 0}。')
    params = [
        {"key": "purchase_price_rmb", "label": "采购价(元/件)", "type": "number", "default": 20,
         "help": "仅单品模式用；批量取②里填的进货价"},
        {"key": "weight_g", "label": "重量(克)", "type": "number", "default": 300,
         "help": "仅单品模式用；批量取②里填的重量"},
        {"key": "freight_rmb_per_kg", "label": "头程跨境运费(元/kg)", "type": "number", "default": 0,
         "help": "查『马来官方运价表』填；0=暂不计"},
        {"key": "agent_fee_rmb", "label": "货代费(元/件)", "type": "number", "default": 2,
         "help": "达意货代打包贴单送官仓 2 元/单(量大可谈)；超规(三边和≥220cm 或 ≥10kg)+1 元"},
        {"key": "fx_rmb_per_usd", "label": "汇率(元/美元)", "type": "number", "default": 7.2},
        {"key": "commission_rate", "label": "平台佣金率(%)", "type": "number", "default": 5,
         "help": "⚠️马来当期需核，新商可能免佣期"},
        {"key": "transaction_fee_rate", "label": "交易手续费率(%)", "type": "number", "default": 2,
         "help": "⚠️以官方为准"},
        {"key": "ecom_service_rate", "label": "电商增长服务费率(%)", "type": "number", "default": 0},
        {"key": "influencer_rate", "label": "达人佣金藏价(%)", "type": "number", "default": 5,
         "help": "藏几个点=打算给达人几个点；实付高于此差额吃自己利润"},
        {"key": "target_profit_rate", "label": "目标利润率(%)", "type": "number", "default": 20},
        {"key": "discount_n", "label": "折扣N(填7=打7折)", "type": "number", "default": 7,
         "help": "货叮咚口径：填7→店铺后台做30%off。必设，否则易亏"},
        {"key": "other_cost_usd", "label": "其他成本(USD/件)", "type": "number", "default": 0},
    ]

    def run(self, inputs, params, config):
        products = inputs.get("selected")
        # 只要输入区没显式给单品参数，且有①②带来的品 → 批量
        if (isinstance(products, list) and products
                and inputs.get("purchase_price_rmb") is None and inputs.get("weight_g") is None):
            return self._batch(products, params)
        return self._single(inputs, params)

    def _batch(self, products, params):
        rows, priced, ok = [], [], 0
        for p in products:
            name = (p.get("商品名") or p.get("name") or "(未命名)") if isinstance(p, dict) else str(p)
            pur = _num(p.get("进货价") if isinstance(p, dict) else None)
            wt = _num(p.get("重量") if isinstance(p, dict) else None)
            if pur is None or wt is None:
                rows.append({"商品名": str(name)[:24], "采购¥": _g(pur), "重量g": _g(wt),
                             "折后价$": "—", "单件利润$": "—", "利润率": "—", "备注": "缺进货价/重量 → 回②填"})
                continue
            res, err = _price_one(pur, wt, params)
            if err:
                rows.append({"商品名": str(name)[:24], "采购¥": f"{pur:g}", "重量g": f"{wt:g}",
                             "折后价$": "—", "单件利润$": "—", "利润率": "—", "备注": err})
                continue
            good = res["profit_usd"] > 0
            ok += 1 if good else 0
            rows.append({"商品名": str(name)[:24], "采购¥": f"{pur:g}", "重量g": f"{wt:g}",
                         "折后价$": f"{res['net']:.2f}", "单件利润$": f"{res['profit_usd']:.2f}",
                         "利润率": f"{res['profit_r']*100:.0f}%", "备注": ("✅" if good else "⛔亏")})
            priced.append({"商品名": name, "net_price_usd": round(res["net"], 2),
                           "profit_usd": round(res["profit_usd"], 2)})
        filled = [r for r in rows if r["折后价$"] != "—"]
        return StepResult(
            status=OK,
            message=f"批量定价 {len(rows)} 个（来自①②带来的品）；已算 {len(filled)} 个、缺价 {len(rows)-len(filled)} 个。",
            data={"summary": f"{len(rows)} 个品定价", "table": rows,
                  "notes": ["缺进货价/重量的：回 ② 找货源那步，在表里把进货价/重量填上再回来。",
                            "费率均为占位示例，务必核马来当期（学习中心）。折后价=买家结算价，藏价后店铺后台仍要做折扣。"]},
            outputs={"pricing": priced},
        )

    def _single(self, inputs, params):
        purchase = float(inputs.get("purchase_price_rmb") or params["purchase_price_rmb"])
        weight = float(inputs.get("weight_g") or params["weight_g"])
        res, err = _price_one(purchase, weight, params)
        if err:
            return StepResult(status=ERROR, message=err + "，请下调费率/利润率。")

        net, list_price = res["net"], res["list_price"]
        profit_usd, fees_usd, fees_frac = res["profit_usd"], res["fees_usd"], res["fees_frac"]
        checks = [
            {"label": f"单件利润 ${profit_usd:.2f}（利润率 {res['profit_r']*100:.0f}%）",
             "ok": profit_usd > 0, "note": "藏价法：利润率按你设定值达成"},
            {"label": "已设折扣", "ok": res["discount_n"] < 10,
             "note": f"填{res['discount_n']:.0f}→店铺后台做 {(10-res['discount_n'])*10:.0f}% off（藏价≠最终价）"},
        ]
        fields = {
            "成本合计(¥/件)": f"{res['cost_rmb']:.2f}  (采购{purchase:.1f}+头程{res['freight_rmb']:.2f}+货代{res['agent']:.1f})",
            "成本(USD)": f"{res['cost_usd']:.2f}",
            "折前展示价(USD)": f"{list_price:.2f}", "折后结算价(USD)": f"{net:.2f}",
            "平台各项费(USD)": f"{fees_usd:.2f}  (佣金+手续费+增长费+达人{fees_frac*100:.1f}%)",
            "单件利润(USD)": f"{profit_usd:.2f}", "利润率": f"{res['profit_r']*100:.0f}%",
        }
        notes = ["费率均为占位示例，务必核马来当期（学习中心）。",
                 "达人佣金藏5%但实付15% → 多的10%从利润里扣。"]
        target = float(inputs.get("target_sell_price_usd") or 0)
        if target > 0:
            t_profit = target - res["cost_usd"] - fees_frac * target
            fields["【反算】目标售价(USD)"] = f"{target:.2f}"
            fields["【反算】该价位利润(USD)"] = f"{t_profit:.2f}"
            fields["【反算】该价位利润率"] = f"{(t_profit/target*100) if target else 0:.1f}%"
            checks.append({"label": f"按竞品/目标价 ${target:.2f} 卖仍盈利", "ok": t_profit > 0,
                           "note": f"利润 ${t_profit:.2f}"})
        return StepResult(
            status=OK,
            message=f"折后结算价 ${net:.2f}，单件利润 ${profit_usd:.2f}（{res['profit_r']*100:.0f}%）。",
            data={"summary": f"折前 ${list_price:.2f} / 折后 ${net:.2f} / 利润 ${profit_usd:.2f}",
                  "fields": fields, "checks": checks, "notes": notes},
            outputs={"pricing": [{"net_price_usd": round(net, 2), "profit_usd": round(profit_usd, 2)}]},
        )
