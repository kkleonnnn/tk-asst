"""① 选品打分（可真跑）—— 基于出海匠导出的市场数据打分。

输入：上传出海匠导出的 xlsx / csv（也支持粘贴 CSV / JSON）。自动识别出海匠表头
（会跳过第一行的“数据导出自出海匠”横幅），把每个商品按市场信号打分排序。

⚠️ 出海匠是“市场数据”，本步只评【市场吸引力】：近30天销量 / 趋势 / 评分 / 评论 / 售价。
   进货价、重量、运费、利润这些【货源/成本】数据出海匠没有——运费红线(进货价>50/大件)
   和利润，顺移到 ②找货源(1688) + ④定价 去判。
"""
import base64
import csv
import io
import json
import re

from engine import Step, StepResult, OK
from engine.xlsx import read_rows

# 列名别名（出海匠真实表头 + 常见叫法）；匹配时两边都去空格并小写后精确比对
ALIASES = {
    "name":       ["商品名", "名称", "商品名称", "name", "title"],
    "rating":     ["商品评分", "评分", "rating"],
    "cat":        ["商品三级分类", "商品二级分类", "商品一级分类", "类目", "category"],
    "price_low":  ["最低售价", "售价", "客单价", "price"],
    "price_high": ["最高售价"],
    "commission": ["佣金比例", "佣金", "commission"],
    "logistics":  ["物流费用", "运费"],
    "sales7":     ["近7天销量", "7天销量", "近7日销量"],
    "sales30":    ["近30天销量", "30天销量", "月销量", "近30日销量"],
    "salestotal": ["总销量"],
    "gmv30":      ["近30天销售额", "30天销售额"],
    "reviews":    ["评论数", "评论", "reviews"],
    "creator":    ["达人出单率"],
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
    """清洗数字：去掉 RM/¥/%/逗号/空格等，返回 float；空/非数返回 None。"""
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
    """好看地显示数字：整数不带小数。"""
    if x is None:
        return "—"
    return f"{x:g}"


class SelectScoreStep(Step):
    id = "select"
    name = "① 选品打分"
    stage = "选品"
    available = True
    desc = ("上传出海匠导出的 xlsx/csv，按市场信号打分排序：近30天销量、销量趋势(近7天日均÷近30天日均)、"
            "评分、评论数、售价。满分 7：销量达标+2、趋势上升+2/持平+1、评分达标+1、评论达标+1、售价不过高+1。"
            "⚠️ 进货价/重量/运费/利润出海匠没有 → 顺移到 ②找货源 + ④定价 判。")
    requires = ["数据来自出海匠导出（市场数据）；进货价/重量/运费/利润需 ②找货源(1688) 与 ④定价 补齐"]
    inputs_help = ("上传出海匠导出的 xlsx（或 csv）——会自动跳过“数据导出自出海匠”横幅、识别表头。"
                   "也可粘贴 CSV/JSON。识别的列：商品名/商品评分/最低售价/最高售价/近7天销量/近30天销量/"
                   "评论数/佣金比例 等。示例见 samples/candidates.csv。")
    params = [
        {"key": "min_sales_30d", "label": "近30天销量门槛", "type": "number", "default": 100,
         "help": "低于此判需求不足（招商经验值，按类目自行调）"},
        {"key": "min_rating", "label": "最低商品评分", "type": "number", "default": 4.5,
         "help": "低于此口碑存疑"},
        {"key": "min_reviews", "label": "最低评论数", "type": "number", "default": 20,
         "help": "评论太少=验证不足"},
        {"key": "price_max_myr", "label": "售价上限(RM)", "type": "number", "default": 100,
         "help": "马来偏低价市场，售价过高不易走量；按类目调"},
        {"key": "trend_up_ratio", "label": "上升趋势阈值", "type": "number", "default": 1.1,
         "help": "近7天日均÷近30天日均 ≥ 此值算上升"},
    ]

    def _rows_to_dicts(self, rows):
        rows = [r for r in rows if r]
        hidx = None
        for i, r in enumerate(rows):
            if sum(1 for c in r if str(c).strip()) >= 3:  # 跳过横幅，定位表头
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

    def _parse(self, inputs):
        if isinstance(inputs.get("candidates"), list):
            return inputs["candidates"]
        fb = inputs.get("file_b64")
        if fb:
            raw = base64.b64decode(fb)
            fname = (inputs.get("file_name") or "").lower()
            if fname.endswith(".xlsx") or raw[:2] == b"PK":  # xlsx 是 zip，PK 开头
                return self._rows_to_dicts(read_rows(raw))
            text = raw.decode("utf-8-sig", "ignore")
            return self._rows_to_dicts(list(csv.reader(io.StringIO(text))))
        raw = (inputs.get("candidates_csv") or inputs.get("text") or "").strip()
        if not raw:
            return []
        if raw[0] in "[{":
            data = json.loads(raw)
            return data if isinstance(data, list) else [data]
        return self._rows_to_dicts(list(csv.reader(io.StringIO(raw))))

    def run(self, inputs, params, config):
        rows = self._parse(inputs)
        if not rows:
            return StepResult(status=OK, message="没有数据。请上传出海匠导出的 xlsx/csv，或粘贴 CSV/JSON。",
                              data={"summary": "0 个商品"})

        min_sales = float(params["min_sales_30d"])
        min_rating = float(params["min_rating"])
        min_reviews = float(params["min_reviews"])
        price_max = float(params["price_max_myr"])
        trend_up = float(params["trend_up_ratio"])

        scored = []
        for d in rows:
            name = _pick(d, "name") or "(未命名)"
            cat = _pick(d, "cat") or ""
            rating = _num(_pick(d, "rating"))
            pl = _num(_pick(d, "price_low"))
            ph = _num(_pick(d, "price_high"))
            s7 = _num(_pick(d, "sales7"))
            s30 = _num(_pick(d, "sales30"))
            if s30 is None:
                s30 = _num(_pick(d, "salestotal"))
            rev = _num(_pick(d, "reviews"))
            comm = _num(_pick(d, "commission"))

            p = 0
            flags = []
            # 销量
            if s30 is not None:
                if s30 >= min_sales:
                    p += 2
                else:
                    flags.append(f"近30天销量{s30:g}<{min_sales:g}")
            else:
                flags.append("缺销量数据")
            # 趋势：只在有真实 7 天/30 天且 7天<30天时判；同值(出海匠常见)不可判、不加分
            if s7 is not None and s30 and s30 > 0 and s7 < s30:
                ratio = (s7 / 7) / (s30 / 30)
                if ratio >= trend_up:
                    p += 2; trend = "↑上升"
                elif ratio >= 0.9:
                    p += 1; trend = "→持平"
                else:
                    trend = "↓下降"; flags.append("趋势↓")
            elif s7 is not None and s30 and s7 >= s30:
                trend = "—(近7≈30天)"
            else:
                trend = "—"
            # 评分
            if rating is not None:
                if rating >= min_rating:
                    p += 1
                else:
                    flags.append(f"评分{rating:g}<{min_rating:g}")
            else:
                flags.append("缺评分")
            # 评论
            if rev is not None and rev >= min_reviews:
                p += 1
            elif rev is not None:
                flags.append(f"评论{rev:g}<{min_reviews:g}")
            # 售价上限
            if pl is not None and pl > price_max:
                flags.append(f"售价RM{pl:g}>{price_max:g}(不易走量)")
            elif pl is not None:
                p += 1

            if s30 is None:
                verdict = "⚠️缺销量"
            elif p >= 5:
                verdict = "✅推荐"
            elif p >= 3:
                verdict = "🟡观察"
            else:
                verdict = "⛔不建议"

            scored.append({
                "商品名": str(name)[:30], "类目": cat,
                "售价RM": (f"{pl:g}~{ph:g}" if (pl is not None and ph is not None) else _g(pl)),
                "近30天销量": (f"{s30:g}" if s30 is not None else "—"),
                "趋势": trend, "评分": _g(rating), "评论": _g(rev), "佣金%": _g(comm),
                "得分": p, "判定": verdict, "红旗": "；".join(flags) or "—",
                "_p": p, "_s30": s30 or 0,
            })

        scored.sort(key=lambda x: (x["_p"], x["_s30"]), reverse=True)
        for s in scored:
            s.pop("_p", None); s.pop("_s30", None)
        rec = [s for s in scored if s["判定"] == "✅推荐"]
        return StepResult(
            status=OK,
            message=f"共 {len(scored)} 个商品，✅推荐 {len(rec)} 个（数据缺失的已标注）。",
            data={"summary": f"{len(scored)} 个商品已按市场吸引力打分排序",
                  "table": scored,
                  "notes": [
                      "出海匠=市场数据；本步只评『市场吸引力』(销量/趋势/评分/评论/售价)。",
                      "进货价/重量/运费/利润出海匠没有 → 到 ②找货源(1688) 拿货源价+重量、④定价 算利润；运费红线(进货价>50/大件)在那两步判。",
                      "售价为马来 MYR；趋势=近7天日均÷近30天日均。阈值为经验值，可在参数区调，以官方后台实时数据为准。"]},
            outputs={"selected": [{"商品名": s["商品名"], "售价RM": s["售价RM"], "类目": s["类目"]}
                                  for s in (rec or scored[:5])]},
        )
