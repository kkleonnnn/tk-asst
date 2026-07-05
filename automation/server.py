"""控制台 web 服务（纯标准库 http.server，零依赖）。

启动：python3 run.py  （或 python3 server.py）
接口：
  GET  /                 → 控制台页面
  GET  /api/steps        → 所有步骤元信息 + 当前参数值
  GET  /api/config       → 当前配置
  POST /api/config       → 保存参数（按步骤浅合并写回 config.json）
  POST /api/run/<id>     → 跑单步，body {inputs, params}
  POST /api/pipeline     → 跑整条，body {inputs, params_by_step}；遇 blocked/error 暂停
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from steps import PIPELINE, load_config, save_config  # noqa: E402

HOST = "127.0.0.1"
PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))


def _effective_values(cfg):
    """每个步骤每个参数的当前生效值（config 覆盖 default）。"""
    out = {}
    cfg_steps = cfg.get("steps", {}) or {}
    for s in PIPELINE.steps:
        vals = {}
        cs = cfg_steps.get(s.id, {})
        for p in s.params:
            k = p["key"]
            vals[k] = cs[k] if k in cs and cs[k] not in (None, "") else p.get("default")
        out[s.id] = vals
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 安静点
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "web", "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                return self._send(500, {"error": "index.html 缺失"})
        if self.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if self.path == "/api/steps":
            cfg = load_config()
            return self._send(200, {"steps": [s.meta() for s in PIPELINE.steps],
                                    "values": _effective_values(cfg)})
        if self.path == "/api/config":
            return self._send(200, load_config())
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        body = self._body()
        if self.path == "/api/config":
            cfg = load_config()
            incoming = body.get("steps", body) or {}
            cfg.setdefault("steps", {})
            for sid, vals in incoming.items():
                if isinstance(vals, dict):
                    cfg["steps"].setdefault(sid, {}).update(vals)
            save_config(cfg)
            return self._send(200, {"ok": True, "values": _effective_values(cfg)})
        if self.path.startswith("/api/run/"):
            step_id = self.path[len("/api/run/"):]
            cfg = load_config()
            r = PIPELINE.run_step(step_id, body.get("inputs", {}),
                                  body.get("params", {}), cfg)
            return self._send(200, r.to_dict())
        if self.path == "/api/pipeline":
            cfg = load_config()
            res = PIPELINE.run_all(body.get("inputs", {}),
                                   body.get("params_by_step", {}), cfg)
            return self._send(200, {"results": res})
        return self._send(404, {"error": "not found"})


def make_server():
    return ThreadingHTTPServer((HOST, PORT), Handler)


if __name__ == "__main__":
    print(f"运营控制台：http://{HOST}:{PORT}/  (Ctrl+C 退出)")
    make_server().serve_forever()
