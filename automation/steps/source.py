"""② 找货源：把 ① 勾选的品变成 1688 找源工作清单（生成搜索链接）。

不强依赖 1688 开放平台——半自动：给每个选中品生成 1688 关键词搜索链接 + 图搜/货叮咚快捷搜同款指引，
校长点开找源、回填进货价/重量。开放平台 App Key 只是把这步升级成「全自动搜+拉价」的选项（见 🔑接口配置）。
"""
import urllib.parse

from engine import Step, StepResult, OK


class SourceStep(Step):
    id = "source"
    name = "② 找货源(1688)"
    stage = "找货源"
    available = True
    desc = ("把 ① 勾选的品变成 1688 找源清单：每个品生成 1688 关键词搜索链接（点开即搜）。"
            "跨语言找厂最准的是『图搜同款(拍立淘)』或货叮咚插件『快捷搜同款』——都不需要开放平台。"
            "1688 开放平台 App Key 只是把这步升级成『全自动搜+拉价』的选项，非必需。")
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
            kw = name[:40]
            url = "https://s.1688.com/selloffer/offer_search.htm?keywords=" + urllib.parse.quote(kw)
            rows.append({
                "商品名": name[:34],
                "类目": (p.get("类目") if isinstance(p, dict) else "") or "",
                "1688搜同款": url,
                "进货价¥": "待填", "重量g": "待填",
            })

        notes = [
            "① 关键词链接：点开直接在 1688 搜。出海匠多为英文名、中国供应商多用中文——搜不到就把关键词翻成中文，或用②图搜。",
            "② 图搜同款(拍立淘) 最准：打开 1688 → 拍立淘 → 上传该商品主图找同款（跨语言找厂最准）。",
            "③ 或直接用货叮咚插件『快捷搜同款』绑定货源（见 reference/03-商品上架，已成熟）。",
            "找到源后记下 进货价(¥) + 重量(g) → 进 ④定价 算利润；进货价>50/大件的运费红线在这一步把关。",
            ("已填 1688 App Key：后续可升级『自动图搜+拉价』（接口实现待接入）。" if has_key
             else "在 🔑接口配置 填 1688 App Key 后，本步可升级为『全自动搜+拉价』——非必需，半自动已够用。"),
        ]
        return StepResult(
            status=OK,
            message=f"为 {len(rows)} 个选中品生成 1688 找源清单——点链接去搜，回填进货价/重量。",
            data={"summary": f"{len(rows)} 个品待找源", "table": rows, "notes": notes},
            outputs={"sourcing": rows},
        )
