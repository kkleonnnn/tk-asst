"""需授权/未接入的步骤（框架占位）。

这些步骤 available=False，run() 直接返回 BLOCKED —— 流水线跑到这里会「暂停并报错说明」，
正是需求里的「遇到阻塞可以报错暂停」。等 kk 拿到对应授权/接口后，把 run() 换成真实现即可。
每个 how_to_unblock 写清楚「缺什么、去哪办、接哪个 API」。
"""
from engine import Step, StepResult, BLOCKED


class _Gated(Step):
    available = False
    how_to_unblock = ""

    def run(self, inputs, params, config):
        return StepResult(
            status=BLOCKED,
            message="⏸ 未接入，流水线在此暂停。" + self.how_to_unblock,
            data={"summary": "需授权/接口，暂由人工完成",
                  "notes": [self.how_to_unblock,
                            "人工做完后，可跳过本步、从下一步继续跑。"]},
        )


class SourceStep(_Gated):
    id = "source"
    name = "② 找货源(1688)"
    stage = "找货源"
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
    desc = ("把 1688 货源采集成 TikTok 草稿商品（标题/图/SKU 标准化）。"
            "货叮咚 ERP 的插件已经在做这件事；自建采集需 1688 商详 API（爬虫违规且易坏，不建议）。")
    requires = ["1688 商品详情 API（同②的 App Key）；或继续用货叮咚插件手动采集/认领"]
    how_to_unblock = ("推荐继续用货叮咚插件完成采集+认领（它已成熟）；"
                      "若要自动化，接 1688 商详 API 拉字段后在此生成草稿。"
                      "无论哪种，采集图务必去中文/logo/水印。")


class FulfillStep(_Gated):
    id = "fulfill"
    name = "⑥ 发货"
    stage = "发货"
    desc = ("出单后：货叮咚采购派单到1688 → 货代打包贴单送东莞官仓 → 守72h入仓 → 平台物流到马来。"
            "自动化需订单/采购/物流接口。")
    requires = ["TikTok Shop 订单 API + 1688 采购/一件代发 API + 货代对接（或继续用货叮咚采购派单）"]
    how_to_unblock = ("当前用货叮咚『采购派单(官方API/插件)』+ 达意货代送官仓，人工闭环；"
                      "全自动需打通 订单→采购→物流 三段接口。发货 SLA 见 reference/04。")
