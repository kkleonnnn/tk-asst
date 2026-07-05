"""需授权/未接入的步骤（框架占位）。

available=False，run() 返回 BLOCKED —— 流水线跑到这里「暂停并报错说明」（需求里的"遇到阻塞报错暂停"）。
每个步骤声明 provider（对应 🔑接口配置 的凭证分组）：
  - 凭证已填 → 提示"凭证就位，接口实现待接入"（框架 v1 尚未写真实调用）
  - 凭证缺失 → 提示去接口配置填什么
等 kk 拿到授权后，把对应类的 available 改 True、run() 换成真实 API 调用即可。
"""
from engine import Step, StepResult, BLOCKED


class _Gated(Step):
    available = False
    provider = None        # 对应 creds 分组：ali_1688 / tiktok_shop / freight
    how_to_unblock = ""

    def _creds_filled(self, config):
        creds = (config.get("_credentials") or {}).get(self.provider or "", {}) or {}
        return any(v for v in creds.values())

    def run(self, inputs, params, config):
        filled = self._creds_filled(config)
        if filled:
            msg = "⏸ 凭证已在「🔑 接口配置」填好，但该接口的自动化实现尚未接入（v1 框架占位）。当前请人工完成本步。"
        else:
            msg = "⏸ 未接入且缺凭证，流水线在此暂停。" + self.how_to_unblock
        data = self._extra_data()
        data["notes"] = [self.how_to_unblock,
                         ("凭证状态：✅已填（待接入实现）" if filled
                          else "凭证状态：⬜ 未填 → 去左侧「🔑 接口配置」填入"),
                         "人工做完这步后，可从下一步继续跑。"]
        return StepResult(status=BLOCKED, message=msg, data=data)

    def _extra_data(self):
        return {"summary": "需授权/接口，暂由人工完成"}


class SourceStep(_Gated):
    id = "source"
    name = "② 找货源(1688)"
    stage = "找货源"
    provider = "ali_1688"
    desc = ("给潜力款在 1688 找可一件代发的源头，确认进货价/重量/发货时效。"
            "自动『图搜同款+拉商详』需 1688 开放平台 API。")
    requires = ["1688 开放平台：企业资质认证 + 创建应用 + App Key（图搜同款/商品详情/一件代发接口）"]
    how_to_unblock = ("去 open.1688.com 完成企业资质认证并创建应用拿 App Key，"
                      "接入『图搜同款/商品详情』接口后本步可自动找源；"
                      "当前请人工在 1688 找源，把货源链接/进货价/重量回填到下一步。")


class CollectStep(_Gated):
    id = "collect"
    name = "③ 采集"
    stage = "采集"
    provider = "ali_1688"
    desc = ("把 1688 货源采集成 TikTok 草稿商品（标题/图/SKU 标准化）。"
            "货叮咚 ERP 的插件已经在做这件事；自建采集需 1688 商详 API（爬虫违规且易坏，不建议）。")
    requires = ["1688 商品详情 API（同②的 App Key）；或继续用货叮咚插件手动采集/认领"]
    how_to_unblock = ("推荐继续用货叮咚插件完成采集+认领（它已成熟）；"
                      "若要自动化，接 1688 商详 API 拉字段后在此生成草稿。"
                      "无论哪种，采集图务必去中文/logo/水印。")


class FulfillStep(_Gated):
    id = "fulfill"
    name = "⑥ 发货(达意货代)"
    stage = "发货"
    provider = "freight"
    desc = ("出单后闭环：货叮咚采购派单到1688 → 达意云仓「签收→过机扫码分拣→拆包验货→打包(称重/全程录像)"
            "→贴单→出库过检→当天多批次送东莞官方仓」→ 守72h入仓 → 平台物流到马来。达意与货叮咚 ERP 无缝对接。")
    requires = ["达意货代系统 dyhd.huoyuanjiawms.com 注册 + TikTok 店铺绑定授权 + 账户充值；或继续用货叮咚采购派单人工闭环"]
    how_to_unblock = ("当前用货叮咚『采购派单(官方API/插件)』+ 达意云仓人工闭环（打包费 2 元/单，量大可谈）；"
                      "全自动需打通 订单→采购→物流 三段接口。发货 SLA 见 reference/04。")

    def _extra_data(self):
        return {
            "summary": "达意货代云仓 · 人工闭环（框架占位）",
            "fields": {
                "货代系统": "dyhd.huoyuanjiawms.com（与货叮咚 ERP 对接）",
                "打包收费": "TikTok 自送仓 2 元/单（量大可谈）；超规(三边和≥220cm 或 ≥10kg)+1 元；增值耗材另计",
                "发货仓": "东莞仓：洪梅镇望沙路72号 万×产业园IC栋301（⚠️以货代实际提供为准）｜义乌仓",
                "营业时间": "10:00–22:00，全年不打烊、订单日清、每天多批次送官方仓",
                "赔付": "时效赔付(承诺24h内送仓，超时赔)；贴错单/丢件包赔；损坏丢失按『采购价+运费』赔",
            },
        }
