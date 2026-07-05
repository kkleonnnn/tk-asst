"""流水线引擎（纯标准库，零依赖）。

设计目标：把「选品→找货源→采集→定价→上架→发货」建成一串可插拔的 Step。
- 每个 Step 自带：说明(desc)、前置依赖(requires)、可调参数(params)、输入说明。
- 计算型步骤（选品打分/定价/上架预检）真跑；需授权的步骤返回 BLOCKED，流水线在此暂停。
- 引擎不关心 web，可被网页调用，也可将来被定时任务/CLI headless 调用。
"""
from dataclasses import dataclass, field

# 步骤运行状态
OK = "ok"            # 成功
BLOCKED = "blocked"  # 卡在授权/人工/未接入 —— 流水线在此暂停，等人处理
ERROR = "error"      # 参数/运行报错


@dataclass
class StepResult:
    status: str
    message: str = ""
    # data：给网页展示的结果，约定字段（都可选）：
    #   summary(str) / fields(dict 键值对) / checks(list[{label,ok,note}]) / table(list[dict]) / notes(list[str])
    data: dict = field(default_factory=dict)
    # outputs：传给下一步的数据（run_all 会 merge 进上下文）
    outputs: dict = field(default_factory=dict)

    def to_dict(self):
        return {"status": self.status, "message": self.message,
                "data": self.data, "outputs": self.outputs}


class Step:
    """所有步骤的基类。子类实现 run()。"""
    id = ""            # 唯一 id
    name = ""          # 显示名
    stage = ""         # 所属环节：选品/找货源/采集/定价/上架/发货
    desc = ""          # 说明：这一步在干什么、怎么用
    requires = []      # 前置/授权依赖（人类可读，展示用）
    available = True   # False = 默认卡住（需授权/未接入），run() 一般返回 BLOCKED
    params = []        # 可调参数：[{key,label,type(number/text/textarea/select),default,help,options?}]
    inputs_help = ""   # 输入区填什么的说明

    def run(self, inputs: dict, params: dict, config: dict) -> StepResult:
        raise NotImplementedError

    def meta(self):
        return {
            "id": self.id, "name": self.name, "stage": self.stage,
            "desc": self.desc, "requires": list(self.requires),
            "available": self.available, "params": self.params,
            "inputs_help": self.inputs_help,
        }


class Pipeline:
    def __init__(self, steps):
        self.steps = steps
        self.by_id = {s.id: s for s in steps}

    def _merge_params(self, step, params, config):
        """参数优先级：网页传入 > config.json 中该步骤的值 > 参数定义的 default。"""
        merged = {}
        cfg_step = (config.get("steps", {}) or {}).get(step.id, {})
        params = params or {}
        for p in step.params:
            k = p["key"]
            if k in params and params[k] not in (None, ""):
                merged[k] = params[k]
            elif k in cfg_step and cfg_step[k] not in (None, ""):
                merged[k] = cfg_step[k]
            else:
                merged[k] = p.get("default")
        return merged

    def run_step(self, step_id, inputs, params, config):
        step = self.by_id.get(step_id)
        if step is None:
            return StepResult(status=ERROR, message=f"未知步骤：{step_id}")
        merged = self._merge_params(step, params, config)
        try:
            return step.run(inputs or {}, merged, config)
        except Exception as e:  # noqa: BLE001 —— 任何步骤报错都转成 ERROR，不让整个服务崩
            return StepResult(status=ERROR, message=f"{type(e).__name__}: {e}")

    def run_all(self, inputs, params_by_step, config):
        """按顺序跑整条；遇到 BLOCKED/ERROR 就停在那一步（人工处理后可从该步续跑）。"""
        results = []
        carry = dict(inputs or {})
        for step in self.steps:
            r = self.run_step(step.id, carry,
                              (params_by_step or {}).get(step.id, {}), config)
            row = {"step_id": step.id, "name": step.name, "stage": step.stage}
            row.update(r.to_dict())
            results.append(row)
            if r.status == OK:
                carry.update(r.outputs or {})
            else:
                break  # 暂停：不再往下跑
        return results
