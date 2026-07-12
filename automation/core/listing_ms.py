"""马来上架素材·确定性翻译（纯函数，0 依赖 0 token）。

目的：把"AI 边看边想该填什么"变成"脚本先算好、引擎照抄"，砍掉浏览器阶段的 token/时长。
- translate_sku_name_ms：用字典规则把 1688 中文 SKU 名（颜色+尺寸+【品类N件】）翻成马来，
  拿不准的词照实标 unknown（不编造），交人工/AI 复核。
- storage_box_attributes：收纳盒类目在货叮咚要选的属性值（引擎照着选，不用逐个试）。

合规铁律落地：**不翻译"可伸缩/伸缩"**——实物只是可折叠+可叠放，标"可伸缩(extendable)"属误导（校验时定的规矩）。
"""
import re

# 颜色（多字词先匹配：奶油白/素雅白 要在 白 之前）
_COLOR = [
    ("奶油白", "Krim"), ("米白", "Krim"), ("素雅白", "Putih"), ("象牙白", "Krim"),
    ("透明", "Lutsinar"), ("白色", "Putih"), ("白", "Putih"),
    ("灰色", "Kelabu"), ("灰", "Kelabu"), ("黑色", "Hitam"), ("黑", "Hitam"),
    ("粉色", "Merah Jambu"), ("粉", "Merah Jambu"), ("蓝色", "Biru"), ("蓝", "Biru"),
    ("绿色", "Hijau"), ("绿", "Hijau"), ("黄色", "Kuning"), ("黄", "Kuning"),
    ("卡其", "Khaki"), ("咖啡", "Coklat"), ("棕色", "Coklat"), ("棕", "Coklat"),
    ("米色", "Krim"),
]
# 尺寸（长词先匹配：特大号/超大号 要在 大号 之前）
_SIZE = [
    ("超大号", "Sangat Besar (XXL)"), ("特大号", "Ekstra Besar (XL)"),
    ("加大号", "Besar (L)"), ("加大", "Besar (L)"),
    ("大号", "Besar (L)"), ("中号", "Sederhana (M)"), ("小号", "Kecil (S)"),
    ("均码", "Sesuai Semua"), ("迷你", "Mini"),
]
# 品类（【】里、逗号/斜杠分隔）
_ITEM = {
    "袜子": "Stokin", "内裤": "Seluar Dalam", "内衣": "Baju Dalam", "文胸": "Coli",
    "衬衫": "Kemeja", "短袖": "Lengan Pendek", "长袖": "Lengan Panjang", "T恤": "Baju-T",
    "牛仔裤": "Seluar Jeans", "裤子": "Seluar", "裤": "Seluar", "毛衣": "Sweater",
    "卫衣": "Hoodie", "衣服": "Baju", "衣物": "Baju", "围巾": "Skarf", "帽子": "Topi",
    "杂物": "Barang", "玩具": "Mainan", "书": "Buku",
}
# 直接丢弃的营销/无意义词（含误导词 可伸缩）
_DROP = ("可伸缩", "伸缩", "可拉伸", "神器", "1个装", "个装", "1个", "可折叠")


def _match(text, table):
    """在 text 里找 table(有序[(zh,ms)]) 第一个命中的词，返回 (ms, 命中的zh) 或 (None, None)。"""
    for zh, ms in table:
        if zh in text:
            return ms, zh
    return None, None


def _translate_bracket(inner):
    """翻译【】内容，如 '袜子/内裤15件' → ('Stokin/Seluar Dalam', '15pcs', unknown[])。"""
    unknown = []
    qty = ""
    m = re.search(r"(\d+)\s*件", inner)
    if m:
        qty = m.group(1) + "pcs"
        inner = inner.replace(m.group(0), "")
    parts, out = re.split(r"[/、,，]", inner), []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        ms, hit = _match(p, list(_ITEM.items()))
        if ms:
            out.append(ms)
        else:
            unknown.append(p)
            out.append(p)  # 保留原词，标 unknown 供复核
    return "/".join(out), qty, unknown


def translate_sku_name_ms(zh_name, max_len=50):
    """1688 中文 SKU 名 → 马来 SKU 名。返回 {ms, unknown[]}。
    组成：颜色 + 尺寸 (缩写) - 品类 数量。拿不准的词放进 unknown 并保留原文。"""
    name = str(zh_name or "").strip()
    if not name:
        return {"ms": "", "unknown": []}
    unknown = []
    # 提取【】品类
    items_ms, qty, tail = "", "", ""
    mb = re.search(r"[【\[](.+?)[】\]]", name)
    if mb:
        items_ms, qty, u = _translate_bracket(mb.group(1))
        unknown += u
        name = name[:mb.start()]  # 品牌/尺寸在括号前
    color_ms, chit = _match(name, _COLOR)
    size_ms, shit = _match(name, _SIZE)
    if not color_ms and not size_ms and not items_ms:
        # 完全没识别 → 整条标 unknown，原样返回（不编造）
        return {"ms": str(zh_name or "").strip()[:max_len], "unknown": [str(zh_name or "").strip()]}
    # 头部去掉已识别的颜色/尺寸词 + 营销词 + 数字/装，剩下的中文即"没认出来的词"，照实标 unknown 不静默丢
    residual = name
    for w in [w for w in (chit, shit) if w] + list(_DROP):
        residual = residual.replace(w, "")
    residual = re.sub(r"[\d\s装可]+", "", residual)
    leftover = re.findall(r"[一-鿿]+", residual)
    head_extra = ""
    if leftover:
        unknown += leftover
        head_extra = " ".join(leftover)
    head = " ".join(x for x in (color_ms, size_ms, head_extra) if x)
    tailparts = " ".join(x for x in (items_ms, qty) if x)
    ms = (head + (" - " + tailparts if tailparts else "")).strip(" -")
    return {"ms": ms[:max_len], "unknown": unknown}


def translate_sku_names_ms(zh_names, max_len=50):
    """批量翻译，保持顺序。返回 [{zh, ms, unknown[]}]。"""
    return [dict(zh=z, **translate_sku_name_ms(z, max_len)) for z in (zh_names or [])]


def storage_box_attributes():
    """收纳盒类目在货叮咚认领/发布页要选的属性值（引擎照着选）。
    值为货叮咚下拉里的中文选项文案；confirmed=已在实操中确认存在。"""
    return {
        "品牌": {"value": "无品牌", "alt": "(Trade mark without text)", "confirmed": True},
        "材质": {"value": ["塑料材料"], "confirmed": True},
        "功能": {"value": ["可折叠的"], "confirmed": True},
        "形状": {"value": "长方形", "confirmed": True},
        "存储类型": {"value": "带盖子", "confirmed": True},
        "每包数量": {"value": "1", "confirmed": False},
        "使用": {"value": "家居", "confirmed": False},
        "风格": {"value": "现代简约", "confirmed": False},
    }
