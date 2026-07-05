"""⑤ 上架预备（可真跑：标题生成 + 合规预检）。

两种模式：
- 批量模式：给 ①②带来的每个品用「商品名(+类目)」生成标题 + 跑合规预检，出一张清单。
- 单品模式：输入区给 JSON（core_word/keywords/...）精细生成一个。

真·API 上架（调 TikTok Shop Product API 建商品）需授权，见 README；本步先把「标题+合规清单」产出来，供货叮咚/手动上架前过一遍。
"""
from engine import Step, StepResult, OK

DEFAULT_BANNED = ["最", "第一", "全网", "国家级", "100%", "治疗", "特效", "根治",
                  "纯天然", "顶级", "唯一", "销量第一", "假一赔十"]
DEFAULT_FORBIDDEN_CAT = ["矫正眼镜", "框架眼镜", "隐形眼镜", "处方", "药品", "医疗器械",
                         "成人用品", "虚拟币", "礼品卡", "危险品", "宗教"]


def _split(v, fallback):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in v.replace("，", ",").split(",") if x.strip()]
    return fallback


def _gen(d, params, check_image=True):
    """按给定字段生成标题 + 合规检查。返回 (title, checks, passed)。check_image=False 时跳过主图张数检查（批量阶段还没图）。"""
    core = (d.get("core_word") or d.get("商品名") or "").strip()
    keywords = (d.get("keywords") or "").strip()
    scene = (d.get("scene") or "").strip()
    audience = (d.get("audience") or "").strip()
    spec = (d.get("spec") or "").strip()
    category = (d.get("category") or d.get("类目") or "").strip()
    brand = (d.get("brand") or "").strip()
    image_count = int(d.get("image_count") or 0)

    max_len = int(params["max_title_len"])
    min_img = int(params["min_images"])
    banned = _split(params.get("banned_words"), DEFAULT_BANNED)
    forbidden = _split(params.get("forbidden_categories"), DEFAULT_FORBIDDEN_CAT)
    authorized = str(params.get("brand_authorized")) == "是"

    title = " ".join(p for p in [core, keywords, scene, audience, spec] if p)
    checks = []
    checks.append({"label": f"标题长度 {len(title)}/{max_len}", "ok": len(title) <= max_len,
                   "note": "超长会被截断/驳回" if len(title) > max_len else ""})
    hit_banned = [w for w in banned if w and w in title]
    checks.append({"label": "无违禁/绝对化词", "ok": not hit_banned,
                   "note": ("命中：" + "、".join(hit_banned)) if hit_banned else "通过"})
    hit_cat = [w for w in forbidden if w and (w in category or w in title)]
    checks.append({"label": "类目非禁售/限售", "ok": not hit_cat,
                   "note": ("命中：" + "、".join(hit_cat) + "（马来禁/限售）") if hit_cat else "通过"})
    checks.append({"label": "品牌词合规", "ok": (not brand) or authorized,
                   "note": ("含品牌『%s』但无授权 → 侵权风险" % brand) if (brand and not authorized)
                           else ("已授权" if brand else "无品牌词")})
    if check_image:
        checks.append({"label": f"主图≥{min_img}张", "ok": image_count >= min_img,
                       "note": f"当前填 {image_count} 张" if image_count else "未填 image_count"})
    passed = all(c["ok"] for c in checks)
    return title, checks, passed


class ListingPrepStep(Step):
    id = "listing"
    name = "⑤ 上架预备(标题+合规)"
    stage = "上架"
    available = True
    desc = ("默认【批量】给 ①②带来的每个品用商品名(+类目)生成标题 + 合规预检（标题长度/违禁词/禁售类目/图≥5）。"
            "也可在输入区给 JSON 精细生成单个。真·API 一键上架需 TikTok Shop Product API 授权（当前未接入）。")
    requires = ["真·API 上架需 TikTok Shop Product API + 店铺 OAuth 授权（未接入）"]
    inputs_help = ('默认用 ①②带来的品批量生成。单个精细做就填 JSON：{"core_word":"除湿盒","keywords":"防潮 衣柜",'
                   '"scene":"雨季衣柜","audience":"家庭","spec":"3只装","category":"居家日用","image_count":5}')
    params = [
        {"key": "max_title_len", "label": "标题最大字符", "type": "number", "default": 255},
        {"key": "min_images", "label": "主图最少张数", "type": "number", "default": 5,
         "help": "少于5张曝光转化偏低"},
        {"key": "banned_words", "label": "违禁/绝对化词(逗号分隔)", "type": "textarea",
         "default": "，".join(DEFAULT_BANNED)},
        {"key": "forbidden_categories", "label": "禁售/限售类目词(逗号分隔)", "type": "textarea",
         "default": "，".join(DEFAULT_FORBIDDEN_CAT)},
        {"key": "brand_authorized", "label": "已有品牌授权?", "type": "select",
         "default": "否", "options": ["否", "是"], "help": "无授权时标题出现品牌词会被判侵权"},
    ]

    def run(self, inputs, params, config):
        products = inputs.get("selected")
        if isinstance(products, list) and products and not (inputs.get("core_word") or "").strip():
            return self._batch(products, params)
        return self._single(inputs, params)

    def _batch(self, products, params):
        rows = []
        for p in products:
            d = p if isinstance(p, dict) else {"商品名": str(p)}
            title, checks, passed = _gen(d, params, check_image=False)
            bad = [c["label"] for c in checks if not c["ok"]]
            rows.append({"商品名": (d.get("商品名") or d.get("core_word") or "")[:22],
                         "生成标题": title[:60], "字符数": len(title),
                         "合规": "✅" if passed else "⚠️", "问题": "；".join(bad) or "—"})
        okn = sum(1 for r in rows if r["合规"] == "✅")
        return StepResult(
            status=OK,
            message=f"批量生成 {len(rows)} 个标题；合规通过 {okn} 个、待修 {len(rows)-okn} 个。",
            data={"summary": f"{len(rows)} 个品标题+合规", "table": rows,
                  "notes": ["批量用商品名当核心词、类目做禁售检查；标题可再进单品模式精修(加场景/人群/规格)。",
                            "批量只做文本级合规(标题长度/违禁词/禁售类目)；主图张数等实际上架时再确认。",
                            "真·一键上架需接 TikTok Shop Product API（未接入）；当前产出供货叮咚/手动上架。"]},
            outputs={"listing": [{"商品名": r["商品名"], "标题": r["生成标题"], "合规": r["合规"]} for r in rows]},
        )

    def _single(self, inputs, params):
        if not (inputs.get("core_word") or "").strip():
            return StepResult(status=OK, message="请在输入区给出至少 core_word（核心商品词），或先在①②选品带入批量。",
                              data={"summary": "缺核心词"})
        title, checks, passed = _gen(inputs, params)
        return StepResult(
            status=OK,
            message=("✅ 合规预检通过，可上架" if passed else "⚠️ 有未通过项，先修再上架"),
            data={"summary": title,
                  "fields": {"生成标题": title, "字符数": f"{len(title)}/{params['max_title_len']}",
                             "类目": (inputs.get("category") or inputs.get("类目") or "(未填)")},
                  "checks": checks,
                  "notes": ["真·一键上架需接 TikTok Shop Product API（未接入）；当前产出供货叮咚/手动上架。"]},
            outputs={"listing": {"title": title, "compliance_pass": passed}},
        )
