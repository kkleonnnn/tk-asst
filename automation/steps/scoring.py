"""① 选品打分（可真跑）。

输入：候选品（CSV 文本或 JSON 列表），每行一个候选品。
逻辑：按硬指标给每个候选品打分 + 红旗标记，排序输出。
说明：自动「拉」选品数据需 TikTok/第三方 API（见 README roadmap）；当前由人把候选品喂进来打分。
"""
import csv
import io

from engine import Step, StepResult, OK

# 列名别名：兼容中英文表头
ALIASES = {
    "name":         ["name", "名称", "商品", "商品名", "product", "款式"],
    "growth":       ["growth", "增长", "销量增长", "近30天增长", "近30天销量增长"],
    "likes":        ["likes", "点赞", "视频点赞", "达人视频点赞"],
    "price_usd":    ["price_usd", "客单价", "售价", "price", "客单价usd"],
    "purchase_rmb": ["purchase_rmb", "进货价", "采购价", "purchase", "进货价rmb"],
    "weight_g":     ["weight_g", "重量", "重量g", "weight", "克重"],
}


def _pick(row, key):
    for a in ALIASES[key]:
        for col in row:
            if col.strip().lower() == a.lower():
                return row[col]
    return None


def _num(v, default=0.0):
    if v is None:
        return default
    s = str(v).strip().replace(",", "")
    if s == "":
        return default
    pct = s.endswith("%")
    s = s.rstrip("%")
    try:
        n = float(s)
    except ValueError:
        return default
    return n / 100.0 if pct else n


def _growth_frac(v):
    """增长率归一化：'50%'→0.5；'50'→0.5（>1 视为百分数）；'0.5'→0.5。"""
    if v is None:
        return 0.0
    s = str(v).strip()
    if s.endswith("%"):
        return _num(s)
    n = _num(s)
    return n / 100.0 if n > 1 else n


class SelectScoreStep(Step):
    id = "select"
    name = "① 选品打分"
    stage = "选品"
    available = True
    desc = ("把候选品（自己从数据罗盘/商品机会/竞品扒来的）按硬指标打分排序，"
            "自动打红旗（进货价超上限、大件、客单价不在区间、增长/点赞不达标）。"
            "满分 7：增长达标+2、点赞达标+2、客单价在区间+1、进货价合规+1、重量合规+1。")
    requires = ["自动拉榜单数据需 TikTok Shop API 或第三方(FastMoss/EchoTik)API —— 当前由人工喂候选品"]
    inputs_help = ("在下方粘贴 CSV（第一行表头，支持中/英文列名：名称,增长,点赞,客单价,进货价,重量），"
                   "或粘贴 JSON 列表。增长可写 50% 或 0.5。示例见 samples/candidates.csv。")
    params = [
        {"key": "min_growth", "label": "最低近30天增长", "type": "number", "default": 0.5,
         "help": "0.5=50%。低于此判不达标（招商经验阈值，仅参考）"},
        {"key": "min_likes", "label": "达人视频最低点赞", "type": "number", "default": 10000,
         "help": "低于此判不达标"},
        {"key": "price_min_usd", "label": "客单价下限(USD)", "type": "number", "default": 15},
        {"key": "price_max_usd", "label": "客单价上限(USD)", "type": "number", "default": 30,
         "help": "轻小标品好测款，$15–30 起步"},
        {"key": "max_purchase_rmb", "label": "进货价上限(元)", "type": "number", "default": 50,
         "help": "🔴 超过要慎重：马来运费高，进货价高的品利润被吃光"},
        {"key": "max_weight_g", "label": "重量上限(克)", "type": "number", "default": 500,
         "help": "🔴 超过=大件，运费杀手"},
    ]

    def _parse(self, inputs):
        if isinstance(inputs.get("candidates"), list):
            return inputs["candidates"]
        raw = (inputs.get("candidates_csv") or inputs.get("text") or "").strip()
        if not raw:
            return []
        # 尝试 JSON
        if raw[0] in "[{":
            import json
            data = json.loads(raw)
            return data if isinstance(data, list) else [data]
        # 否则按 CSV
        return list(csv.DictReader(io.StringIO(raw)))

    def run(self, inputs, params, config):
        rows = self._parse(inputs)
        if not rows:
            return StepResult(status=OK, message="没有候选品输入。请在输入区粘贴 CSV 或 JSON。",
                              data={"summary": "0 个候选品"})

        min_growth = float(params["min_growth"])
        min_likes = float(params["min_likes"])
        pmin = float(params["price_min_usd"])
        pmax = float(params["price_max_usd"])
        max_purchase = float(params["max_purchase_rmb"])
        max_weight = float(params["max_weight_g"])

        scored = []
        for r in rows:
            name = _pick(r, "name") or "(未命名)"
            growth = _growth_frac(_pick(r, "growth"))
            likes = _num(_pick(r, "likes"))
            price = _num(_pick(r, "price_usd"))
            purchase = _num(_pick(r, "purchase_rmb"))
            weight = _num(_pick(r, "weight_g"))

            score = 0
            flags = []
            hard_block = False
            if growth >= min_growth:
                score += 2
            else:
                flags.append(f"增长{growth*100:.0f}%<{min_growth*100:.0f}%")
            if likes >= min_likes:
                score += 2
            else:
                flags.append(f"点赞{likes:.0f}<{min_likes:.0f}")
            if pmin <= price <= pmax:
                score += 1
            elif price > 0:
                flags.append(f"客单价${price:.0f}不在[{pmin:.0f},{pmax:.0f}]")
            if purchase <= max_purchase:
                score += 1
            else:
                flags.append(f"🔴进货价{purchase:.0f}元>{max_purchase:.0f}(运费风险)")
                hard_block = True
            if weight <= max_weight:
                score += 1
            else:
                flags.append(f"🔴大件{weight:.0f}g>{max_weight:.0f}(运费杀手)")
                hard_block = True

            if hard_block:
                verdict = "🔴必复核(硬指标超限)"
            elif score >= 5:
                verdict = "✅推荐"
            elif score >= 3:
                verdict = "🟡观察"
            else:
                verdict = "⛔不建议"

            scored.append({
                "名称": name, "增长": f"{growth*100:.0f}%", "点赞": f"{likes:.0f}",
                "客单价$": f"{price:.1f}", "进货价¥": f"{purchase:.1f}", "重量g": f"{weight:.0f}",
                "得分": score, "判定": verdict, "红旗": "；".join(flags) or "—",
                "_score": score, "_hard": hard_block,
            })

        scored.sort(key=lambda x: (not x["_hard"], x["_score"]), reverse=True)
        for s in scored:
            s.pop("_score", None); s.pop("_hard", None)
        rec = [s for s in scored if s["判定"] == "✅推荐"]
        return StepResult(
            status=OK,
            message=f"共 {len(scored)} 个候选，✅推荐 {len(rec)} 个。",
            data={"summary": f"{len(scored)} 个候选品已打分排序",
                  "table": scored,
                  "notes": ["阈值为招商经验值，仅供排序参考，最终以官方后台实时数据 + 你的判断为准。"]},
            outputs={"selected": rec or scored[:1]},
        )
