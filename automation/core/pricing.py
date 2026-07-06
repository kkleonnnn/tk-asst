"""④ 定价 / 利润（纯函数）——藏价倒推 + 利润核算，货币口径马币 RM。

公式（源自 reference/02、03 货叮咚藏价逻辑）：
    售价 = 采购价 + 运费 + 货代费 + 达人佣金 + 利润 + 平台佣金 + 交易手续费
把成本+目标利润前置藏进售价，倒推「折后结算价(net)」与「折前展示价(list)」。
⚠️ 费率默认值为占位示例，以 TikTok 学习中心马来站当期为准。
"""

DEFAULTS = {
    "freight_rmb_per_kg": 0,     # 头程跨境运费(元/kg)，查马来官方运价表；0=暂不计
    "agent_fee_rmb": 2,          # 达意货代 2 元/单(量大可谈)；超规(三边≥220cm或≥10kg)+1
    "fx_rmb_per_myr": 1.55,      # 1 马币≈人民币（占位，随实时汇率调）
    "commission_rate": 5,        # 平台佣金%（⚠️马来当期需核，新商可能免佣）
    "transaction_fee_rate": 2,   # 交易手续费%（⚠️以官方为准）
    "ecom_service_rate": 0,      # 电商增长服务费%
    "influencer_rate": 5,        # 达人佣金藏价%（藏几个点=打算给达人几个点）
    "target_profit_rate": 20,    # 目标利润率%（占折后结算价）
    "discount_n": 7,             # 折扣N：填7=店铺后台做30%off（必设，否则易亏）
    "other_cost_myr": 0,         # 其他成本 RM/件
}


def _merged(params):
    p = dict(DEFAULTS)
    p.update({k: v for k, v in (params or {}).items() if v not in (None, "")})
    return p


def price_one(purchase_rmb, weight_g, params=None):
    """单品藏价。返回 (结果dict, None) 或 (None, 错误说明)。金额均为 RM（成本另附 RMB）。"""
    p = _merged(params)
    freight_kg = float(p["freight_rmb_per_kg"])
    agent = float(p["agent_fee_rmb"])
    fx = float(p["fx_rmb_per_myr"]) or 1.55
    fees_frac = (float(p["commission_rate"]) + float(p["transaction_fee_rate"])
                 + float(p["ecom_service_rate"]) + float(p["influencer_rate"])) / 100
    profit_r = float(p["target_profit_rate"]) / 100
    discount_n = float(p["discount_n"]) or 10

    freight_rmb = float(weight_g) / 1000.0 * freight_kg
    cost_rmb = float(purchase_rmb) + freight_rmb + agent
    cost_myr = cost_rmb / fx + float(p["other_cost_myr"])

    denom = 1 - fees_frac - profit_r
    if denom <= 0:
        return None, (f"费率合计({fees_frac*100:.1f}%)+利润率({profit_r*100:.0f}%)≥100%，"
                      "无法定价，请下调")
    net = cost_myr / denom
    return {
        "cost_rmb": round(cost_rmb, 2), "freight_rmb": round(freight_rmb, 2),
        "cost_myr": round(cost_myr, 2),
        "net_price_myr": round(net, 2),                       # 折后结算价（买家实付）
        "list_price_myr": round(net / (discount_n / 10.0), 2),  # 折前展示价
        "profit_myr": round(profit_r * net, 2),
        "profit_rate": profit_r,
        "fees_myr": round(fees_frac * net, 2), "fees_frac": fees_frac,
        "discount_off_pct": round((10 - discount_n) * 10),    # 后台应做的折扣力度
        "params_used": p,
    }, None


def margin_at_price(target_myr, purchase_rmb, weight_g, params=None):
    """反算：按给定售价(RM，如竞品价)卖，利润是多少。"""
    p = _merged(params)
    fx = float(p["fx_rmb_per_myr"]) or 1.55
    freight_rmb = float(weight_g) / 1000.0 * float(p["freight_rmb_per_kg"])
    cost_myr = (float(purchase_rmb) + freight_rmb + float(p["agent_fee_rmb"])) / fx \
        + float(p["other_cost_myr"])
    fees_frac = (float(p["commission_rate"]) + float(p["transaction_fee_rate"])
                 + float(p["ecom_service_rate"]) + float(p["influencer_rate"])) / 100
    profit = float(target_myr) - cost_myr - fees_frac * float(target_myr)
    return {
        "target_myr": round(float(target_myr), 2),
        "profit_myr": round(profit, 2),
        "profit_rate": round(profit / float(target_myr), 4) if target_myr else 0,
    }


def price_sources(purchase_weight_list, params=None):
    """批量：对(进货价,重量)列表逐个藏价——用于一个品的多货源利润对比。
    入参：[{"id":..., "purchase_rmb":..., "weight_g":...}, ...]
    返回：[{"id":..., **price_one结果 或 "error":...}, ...]
    """
    out = []
    for item in purchase_weight_list:
        res, err = price_one(item.get("purchase_rmb"), item.get("weight_g") or 0, params)
        row = {"id": item.get("id")}
        if err:
            row["error"] = err
        else:
            row.update(res)
        out.append(row)
    return out
