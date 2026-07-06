"""⑤ 上架合规（纯函数）——标题生成 + 文本级合规预检。

规则源自 reference/03（标题公式/禁绝对化）与 09（马来禁限售）。
真·图片检查（去中文水印等）无法纯文本判定，由引擎 listing 任务人工/AI 把关。
"""

DEFAULT_BANNED = ["最", "第一", "全网", "国家级", "100%", "治疗", "特效", "根治",
                  "纯天然", "顶级", "唯一", "销量第一", "假一赔十"]
DEFAULT_FORBIDDEN_CAT = ["矫正眼镜", "框架眼镜", "隐形眼镜", "处方", "药品", "医疗器械",
                         "成人用品", "虚拟币", "礼品卡", "危险品", "宗教"]

DEFAULTS = {
    "max_title_len": 255,
    "min_images": 5,
    "banned_words": DEFAULT_BANNED,
    "forbidden_categories": DEFAULT_FORBIDDEN_CAT,
    "brand_authorized": False,
}


def _as_list(v, fallback):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in v.replace("，", ",").split(",") if x.strip()]
    return fallback


def build_title(fields):
    """标题公式：核心词 + 关键词/属性 + 场景 + 人群 + 规格。fields 缺哪个跳哪个。"""
    parts = [fields.get("core_word") or fields.get("name") or "",
             fields.get("keywords") or "", fields.get("scene") or "",
             fields.get("audience") or "", fields.get("spec") or ""]
    return " ".join(p.strip() for p in parts if p and p.strip())


def check_listing(fields, params=None, check_image=True):
    """合规预检。返回 {"title", "checks":[{label,ok,note}], "pass"}。
    check_image=False 时跳过主图张数（批量阶段还没图）。"""
    p = dict(DEFAULTS)
    p.update({k: v for k, v in (params or {}).items() if v not in (None, "")})
    max_len = int(p["max_title_len"])
    banned = _as_list(p["banned_words"], DEFAULT_BANNED)
    forbidden = _as_list(p["forbidden_categories"], DEFAULT_FORBIDDEN_CAT)
    authorized = p["brand_authorized"] in (True, "是", "true", "True", 1)

    title = fields.get("title") or build_title(fields)
    category = (fields.get("category") or "").strip()
    brand = (fields.get("brand") or "").strip()

    checks = []
    checks.append({"label": f"标题长度 {len(title)}/{max_len}", "ok": len(title) <= max_len,
                   "note": "超长会被截断/驳回" if len(title) > max_len else ""})
    hit_b = [w for w in banned if w and w in title]
    checks.append({"label": "无违禁/绝对化词", "ok": not hit_b,
                   "note": ("命中：" + "、".join(hit_b)) if hit_b else "通过"})
    hit_c = [w for w in forbidden if w and (w in category or w in title)]
    checks.append({"label": "类目非禁售/限售", "ok": not hit_c,
                   "note": ("命中：" + "、".join(hit_c) + "（马来禁/限售，见 reference/09）") if hit_c else "通过"})
    checks.append({"label": "品牌词合规", "ok": (not brand) or authorized,
                   "note": (f"含品牌『{brand}』但无授权 → 侵权风险") if (brand and not authorized)
                           else ("已授权" if brand else "无品牌词")})
    if check_image:
        n = int(fields.get("image_count") or 0)
        min_img = int(p["min_images"])
        checks.append({"label": f"主图≥{min_img}张", "ok": n >= min_img,
                       "note": f"当前 {n} 张" if n else "未提供图片数"})
    return {"title": title, "checks": checks, "pass": all(c["ok"] for c in checks)}
