"""步骤注册 + 按环节顺序组装流水线。"""
import json
import os

from engine import Pipeline
from steps.scoring import SelectScoreStep
from steps.source import SourceStep
from steps.pricing import PricingStep
from steps.listing import ListingPrepStep
from steps.gated import CollectStep, FulfillStep

# 流水线顺序：选品 → 找货源 → 采集 → 定价 → 上架 → 发货
PIPELINE = Pipeline([
    SelectScoreStep(),   # ① 真跑
    SourceStep(),        # ② 卡授权
    CollectStep(),       # ③ 卡授权
    PricingStep(),       # ④ 真跑
    ListingPrepStep(),   # ⑤ 真跑
    FulfillStep(),       # ⑥ 卡授权
])

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "config.json")


def load_config():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"steps": {}}


def save_config(cfg):
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg
