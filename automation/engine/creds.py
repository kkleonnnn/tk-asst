"""接口凭证管理。

⚠️ 安全：本仓库 PUBLIC。真实凭证写入 automation/credentials.json —— 该文件已被 .gitignore 忽略，
   绝不入库。只提交 credentials.example.json 模板。
   secret 类字段（app_secret/token 等）不会回传给浏览器展示，避免截图/共享泄露。
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(_ROOT, "credentials.json")

# 凭证结构：按服务分组；secret=True 的字段视为敏感（不回显、留空=不改）
CRED_SCHEMA = [
    {"group": "tiktok_shop", "label": "TikTok Shop Open API",
     "help": "partner.tiktokshop.com 注册开发者 → 提交企业资料审核(约2-3天) → 建App拿 Key/Secret/ServiceID → 店铺 OAuth 授权拿 token。用于②真·上架等。",
     "fields": [
        {"key": "app_key", "label": "App Key", "secret": False},
        {"key": "app_secret", "label": "App Secret", "secret": True},
        {"key": "service_id", "label": "Service ID", "secret": False},
        {"key": "shop_cipher", "label": "Shop Cipher", "secret": False},
        {"key": "access_token", "label": "Access Token", "secret": True},
        {"key": "refresh_token", "label": "Refresh Token", "secret": True},
     ]},
    {"group": "ali_1688", "label": "1688 开放平台",
     "help": "open.1688.com 企业资质认证 → 创建应用拿 App Key/Secret。用于②找货源/③采集。",
     "fields": [
        {"key": "app_key", "label": "App Key", "secret": False},
        {"key": "app_secret", "label": "App Secret", "secret": True},
        {"key": "access_token", "label": "Access Token", "secret": True},
     ]},
    {"group": "freight", "label": "货代系统（达意 / 货叮咚 ERP）",
     "help": "达意货代系统 dyhd.huoyuanjiawms.com，与货叮咚 ERP 无缝对接；打包费 2 元/单。用于⑥发货对接。",
     "fields": [
        {"key": "system_url", "label": "系统网址", "secret": False},
        {"key": "account", "label": "登录账号", "secret": False},
        {"key": "api_token", "label": "API Token（如有）", "secret": True},
        {"key": "note", "label": "备注", "secret": False},
     ]},
]

_SECRET_KEYS = {(g["group"], f["key"]) for g in CRED_SCHEMA for f in g["fields"] if f["secret"]}


def load_credentials():
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_credentials(creds):
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(_PATH, 0o600)  # 仅本人可读写
    except OSError:
        pass
    return creds


def public_view(creds=None):
    """回给浏览器：secret 字段一律不回显（只给 filled 标记），非 secret 明文回显。"""
    creds = creds if creds is not None else load_credentials()
    values, filled = {}, {}
    for g in CRED_SCHEMA:
        stored = creds.get(g["group"], {}) or {}
        gv, gf = {}, {}
        for fld in g["fields"]:
            k = fld["key"]
            v = stored.get(k, "")
            gf[k] = bool(v)
            gv[k] = "" if fld["secret"] else v
        values[g["group"]] = gv
        filled[g["group"]] = gf
    return {"schema": CRED_SCHEMA, "values": values, "filled": filled}


def merge_save(incoming):
    """合并保存：secret 字段留空=保留原值（不清空）；其余覆盖。"""
    creds = load_credentials()
    incoming = incoming or {}
    for g in CRED_SCHEMA:
        gid = g["group"]
        inc = incoming.get(gid, {}) or {}
        cur = creds.setdefault(gid, {})
        for fld in g["fields"]:
            k = fld["key"]
            if k not in inc:
                continue
            val = inc[k]
            if (gid, k) in _SECRET_KEYS and (val is None or val == ""):
                continue  # 留空不改，保住已存密钥
            cur[k] = val
    save_credentials(creds)
    return creds
