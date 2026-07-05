"""⑤ 上架预备（可真跑：标题生成 + 合规预检）。

真·API 上架（调 TikTok Shop Product API 建商品）需授权，见 README roadmap；
本步先把「标题 + 合规检查清单」产出来，供货叮咚/手动上架前过一遍。
"""
from engine import Step, StepResult, OK

# 违禁/绝对化词（示例，可在参数里改）
DEFAULT_BANNED = ["最", "第一", "全网", "国家级", "100%", "治疗", "特效", "根治",
                  "纯天然", "顶级", "唯一", "销量第一", "假一赔十"]
# 马来跨境禁售/限售类目关键词（示例）
DEFAULT_FORBIDDEN_CAT = ["矫正眼镜", "框架眼镜", "隐形眼镜", "处方", "药品", "医疗器械",
                         "成人用品", "虚拟币", "礼品卡", "危险品", "宗教"]


def _split(v, fallback):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in v.replace("，", ",").split(",") if x.strip()]
    return fallback


class ListingPrepStep(Step):
    id = "listing"
    name = "⑤ 上架预备(标题+合规)"
    stage = "上架"
    available = True
    desc = ("按标题公式生成标题（核心词+关键词+场景+人群+规格），做发布前合规预检："
            "标题长度≤255、无违禁/绝对化词、无未授权品牌词、类目非禁售、主图≥5张。"
            "真·API 一键上架需 TikTok Shop Product API 授权（见 README，当前未接入）。")
    requires = ["真·API 上架需 TikTok Shop Product API + 店铺 OAuth 授权（未接入）"]
    inputs_help = ('输入区填 JSON：{"core_word":"除湿盒","keywords":"防潮 衣柜","scene":"雨季衣柜",'
                   '"audience":"家庭","spec":"3只装","category":"居家日用","brand":"",'
                   '"image_count":5}')
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
        core = (inputs.get("core_word") or "").strip()
        keywords = (inputs.get("keywords") or "").strip()
        scene = (inputs.get("scene") or "").strip()
        audience = (inputs.get("audience") or "").strip()
        spec = (inputs.get("spec") or "").strip()
        category = (inputs.get("category") or "").strip()
        brand = (inputs.get("brand") or "").strip()
        image_count = int(inputs.get("image_count") or 0)

        if not core:
            return StepResult(status=OK,
                              message="请在输入区给出至少 core_word（核心商品词）。",
                              data={"summary": "缺少核心词"})

        max_len = int(params["max_title_len"])
        min_img = int(params["min_images"])
        banned = _split(params.get("banned_words"), DEFAULT_BANNED)
        forbidden = _split(params.get("forbidden_categories"), DEFAULT_FORBIDDEN_CAT)
        authorized = str(params.get("brand_authorized")) == "是"

        # 标题公式：核心词 + 关键词/属性 + 场景 + 人群 + 规格
        parts = [core, keywords, scene, audience, spec]
        title = " ".join(p for p in parts if p)

        checks = []
        checks.append({"label": f"标题长度 {len(title)}/{max_len}", "ok": len(title) <= max_len,
                       "note": "超长会被截断/驳回" if len(title) > max_len else ""})

        hit_banned = [w for w in banned if w and w in title]
        checks.append({"label": "无违禁/绝对化词", "ok": not hit_banned,
                       "note": ("命中：" + "、".join(hit_banned)) if hit_banned else "通过"})

        hit_cat = [w for w in forbidden if w and (w in category or w in title)]
        checks.append({"label": "类目非禁售/限售", "ok": not hit_cat,
                       "note": ("命中：" + "、".join(hit_cat) + "（马来禁/限售，见09）") if hit_cat else "通过"})

        checks.append({"label": "品牌词合规", "ok": (not brand) or authorized,
                       "note": ("含品牌『%s』但无授权 → 侵权风险(扣分)" % brand)
                               if (brand and not authorized) else ("已授权" if brand else "无品牌词")})

        checks.append({"label": f"主图≥{min_img}张", "ok": image_count >= min_img,
                       "note": f"当前填 {image_count} 张" if image_count else "未填image_count"})

        checks.append({"label": "图片去中文/logo/水印/联系方式", "ok": True,
                       "note": "⚠️人工确认：采集的1688图必须处理干净（此项无法自动判定）"})

        passed = all(c["ok"] for c in checks)
        return StepResult(
            status=OK,
            message=("✅ 合规预检通过，可上架" if passed else "⚠️ 有未通过项，先修再上架"),
            data={"summary": title,
                  "fields": {"生成标题": title, "字符数": f"{len(title)}/{max_len}",
                             "类目": category or "(未填)"},
                  "checks": checks,
                  "notes": ["真·一键上架需接 TikTok Shop Product API（未接入）；当前产出供货叮咚/手动上架。"]},
            outputs={"listing": {"title": title, "compliance_pass": passed}},
        )
