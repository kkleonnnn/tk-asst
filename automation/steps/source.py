"""② 找货源：把 ① 勾选的品变成 1688 找源工作清单。

⚠️ 现实：出海匠导出多为**英文商品名**，而 1688 是中文平台——**直接拿英文名搜基本搜不到中国供应商**。
所以每个品给三条路（按靠谱程度）：① 图搜同款(拍立淘，最准) ② 译成中文再搜 ③ 清理后的关键词直搜(兜底)。
不需要 1688 开放平台；App Key 只是把这步升级成「全自动搜+拉价」的选项。
"""
import re
import urllib.parse

from engine import Step, StepResult, OK

_UNITS = {"pcs", "pc", "pack", "packs", "set", "sets", "piece", "pieces",
          "ml", "cm", "mm", "kg", "g", "l", "inch", "in", "pair", "pairs"}


def _clean_kw(name):
    """把杂乱英文标题清成核心关键词：去数量(90/100pcs)、型号、标点、单位词，取前几个词。"""
    s = re.sub(r"\d+\s*/\s*\d+", " ", name)          # "90/100pcs" 这类数量
    s = re.sub(r"[^\w一-鿿]+", " ", s)         # 标点 → 空格
    toks = []
    for t in s.split():
        if re.fullmatch(r"\d+", t):
            continue                                    # 纯数字丢掉
        if t.lower() in _UNITS:
            continue
        toks.append(t)
    return " ".join(toks[:5]) or name


class SourceStep(Step):
    id = "source"
    name = "② 找货源(1688)"
    stage = "找货源"
    available = True
    desc = ("把 ① 勾选的品变成 1688 找源清单。出海匠多为英文名，直接搜 1688 基本搜不到中国供应商——"
            "所以每个品给三条路：图搜同款(拍立淘，最准) / 译成中文再搜 / 关键词直搜(兜底)。"
            "不需要开放平台；App Key 只是『全自动搜+拉价』的升级。")
    requires = []
    inputs_help = ('默认用 ① 勾选的品（自动带过来）。也可粘贴 JSON 列表覆盖，如 '
                   '[{"商品名":"除湿盒"},{"商品名":"车载手机支架"}]。')
    params = []

    def run(self, inputs, params, config):
        sel = inputs.get("selected")
        if not sel and isinstance(inputs.get("candidates"), list):
            sel = inputs["candidates"]
        if not sel:
            return StepResult(status=OK,
                              message="还没有选中的品。请先到 ① 勾选想做的品再进来，或在输入区粘贴 JSON 列表。",
                              data={"summary": "0 个待找源"})

        creds = (config.get("_credentials") or {}).get("ali_1688") or {}
        has_key = any(v for v in creds.values())

        rows = []
        for p in sel:
            name = (p.get("商品名") or p.get("name") or "").strip() if isinstance(p, dict) else str(p).strip()
            if not name:
                continue
            kw = _clean_kw(name)
            enc = urllib.parse.quote(name)
            rows.append({
                "商品名": name[:34],
                "类目": (p.get("类目") if isinstance(p, dict) else "") or "",
                "图搜同款(最准)": "https://s.1688.com/youyuan/index.htm",
                "译中文再搜": "https://fanyi.baidu.com/#en/zh/" + enc,
                "关键词直搜(兜底)": "https://s.1688.com/selloffer/offer_search.htm?keywords=" + urllib.parse.quote(kw),
                "进货价¥": "待填", "重量g": "待填",
            })

        notes = [
            "❗ 英文名直接搜 1688 基本搜不到中国供应商。靠谱顺序如下：",
            "① 图搜同款(拍立淘)最准：去该商品的 TikTok 页存下主图 → 点「图搜同款」上传图片找同款（或在 1688 首页点搜索框的相机图标）。",
            "② 或点「译中文再搜」把名字翻成中文 → 复制中文关键词到 1688 搜。",
            "③ 「关键词直搜」用清理后的英文词直搜，命中率低，仅兜底。",
            "④ 也可直接用货叮咚插件「快捷搜同款」绑定货源（见 reference/03-商品上架，已成熟）。",
            "找到源后记 进货价(¥)+重量(g) → 进 ④定价 算利润；进货价>50/大件的运费红线在这一步把关。",
            ("已填 1688 App Key：后续可升级『自动图搜+拉价』（接口实现待接入）。" if has_key
             else "在 🔑接口配置 填 1688 App Key 后，本步可升级为『全自动搜+拉价』——非必需。"),
        ]
        return StepResult(
            status=OK,
            message=f"为 {len(rows)} 个选中品生成找源清单。英文名直搜多半搜不到——优先用『图搜同款』或『译中文再搜』。",
            data={"summary": f"{len(rows)} 个品待找源", "table": rows, "notes": notes},
            outputs={"sourcing": rows},
        )
