"""① 选品打分（纯函数）——出海匠导出的市场数据 → 结构化打分结果。

输入：二维行（来自 core.xlsx.read_rows 或 CSV），自动跳过"数据导出自出海匠"横幅、识别表头。
输出：结构化英文键 dict 列表（可直接落进品卡 source_data + scoring）。
打分（满分7）：销量达标+2、趋势上升+2/持平+1、评分达标+1、评论达标+1、售价不过高+1。
⚠️ 出海匠只有市场数据；进货价/重量/运费/利润在 货源(sources) 与 定价(pricing) 阶段补。
"""
import csv
import io
import re

# 列名别名（出海匠真实表头 + 常见叫法）；匹配时去空格小写后精确比对
ALIASES = {
    "name":       ["商品名", "名称", "商品名称", "name", "title"],
    "rating":     ["商品评分", "评分", "rating"],
    "category":   ["商品三级分类", "商品二级分类", "商品一级分类", "类目", "category"],
    "price_low":  ["最低售价", "售价", "客单价", "price"],
    "price_high": ["最高售价"],
    "commission": ["佣金比例", "佣金", "commission"],
    "sales7":     ["近7天销量", "7天销量", "近7日销量"],
    "sales30":    ["近30天销量", "30天销量", "月销量", "近30日销量"],
    "salestotal": ["总销量"],
    "reviews":    ["评论数", "评论", "reviews"],
}

DEFAULTS = {
    "min_sales_30d": 100,     # 近30天销量门槛（招商经验值，按类目调）
    "min_rating": 4.5,        # 最低商品评分
    "min_reviews": 20,        # 最低评论数
    "price_max_myr": 100,     # 售价上限 RM（马来偏低价市场）
    "trend_up_ratio": 1.1,    # 近7天日均÷近30天日均 ≥ 此值算上升
}


def _norm(s):
    return "".join(str(s).split()).lower()


def _pick(d, key):
    for a in ALIASES[key]:
        na = _norm(a)
        for k, v in d.items():
            if _norm(k) == na:
                return v
    return None


def _num(v):
    """清洗数字：去 RM/¥/%/逗号等，返回 float；空/非数返回 None。"""
    if v is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(v))
    if s in ("", ".", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def rows_to_dicts(rows):
    """二维行 → dict 列表：跳过横幅行（非空格数<3），首个≥3非空格的行为表头。"""
    rows = [r for r in rows if r]
    hidx = None
    for i, r in enumerate(rows):
        if sum(1 for c in r if str(c).strip()) >= 3:
            hidx = i
            break
    if hidx is None:
        return []
    header = rows[hidx]
    out = []
    for r in rows[hidx + 1:]:
        if not any(str(c).strip() for c in r):
            continue
        out.append({header[i]: (r[i] if i < len(r) else "") for i in range(len(header))})
    return out


def parse_csv_text(text):
    """CSV 文本 → dict 列表（同样跳横幅）。"""
    return rows_to_dicts(list(csv.reader(io.StringIO(text))))


def score_products(dict_rows, params=None):
    """打分主函数。返回按（得分, 近30天销量）降序的结构化列表。"""
    p = dict(DEFAULTS)
    p.update({k: v for k, v in (params or {}).items() if v not in (None, "")})
    min_sales = float(p["min_sales_30d"])
    min_rating = float(p["min_rating"])
    min_reviews = float(p["min_reviews"])
    price_max = float(p["price_max_myr"])
    trend_up = float(p["trend_up_ratio"])

    out = []
    for d in dict_rows:
        name = _pick(d, "name") or "(未命名)"
        rating = _num(_pick(d, "rating"))
        pl = _num(_pick(d, "price_low"))
        ph = _num(_pick(d, "price_high"))
        s7 = _num(_pick(d, "sales7"))
        s30 = _num(_pick(d, "sales30"))
        if s30 is None:
            s30 = _num(_pick(d, "salestotal"))
        rev = _num(_pick(d, "reviews"))

        score = 0
        flags = []
        # 销量
        if s30 is not None:
            if s30 >= min_sales:
                score += 2
            else:
                flags.append(f"近30天销量{s30:g}<{min_sales:g}")
        else:
            flags.append("缺销量数据")
        # 趋势：仅在 7天<30天（真实区分）时可判；同值(出海匠常见)不可判不加分
        if s7 is not None and s30 and s30 > 0 and s7 < s30:
            ratio = (s7 / 7) / (s30 / 30)
            if ratio >= trend_up:
                score += 2
                trend = "↑上升"
            elif ratio >= 0.9:
                score += 1
                trend = "→持平"
            else:
                trend = "↓下降"
                flags.append("趋势↓")
        elif s7 is not None and s30 and s7 >= s30:
            trend = "—(近7≈30天)"
        else:
            trend = "—"
        # 评分
        if rating is not None:
            if rating >= min_rating:
                score += 1
            else:
                flags.append(f"评分{rating:g}<{min_rating:g}")
        else:
            flags.append("缺评分")
        # 评论
        if rev is not None and rev >= min_reviews:
            score += 1
        elif rev is not None:
            flags.append(f"评论{rev:g}<{min_reviews:g}")
        # 售价上限
        if pl is not None and pl > price_max:
            flags.append(f"售价RM{pl:g}>{price_max:g}(不易走量)")
        elif pl is not None:
            score += 1

        if s30 is None:
            verdict = "缺销量"
        elif score >= 5:
            verdict = "推荐"
        elif score >= 3:
            verdict = "观察"
        else:
            verdict = "不建议"

        out.append({
            "name": str(name),
            "category": str(_pick(d, "category") or ""),
            "price_low_myr": pl, "price_high_myr": ph,
            "sales_30d": s30, "sales_7d": s7,
            "rating": rating, "reviews": rev,
            "commission_pct": _num(_pick(d, "commission")),
            "score": score, "verdict": verdict, "trend": trend, "flags": flags,
        })

    out.sort(key=lambda x: (x["score"], x["sales_30d"] or 0), reverse=True)
    return out
