"""驾驶舱 web 服务（纯标准库 http.server，零依赖）——薄层：只做路由与 IO 粘合。

M0 骨架：静态文件 + 健康检查 + 工作台汇总。看板/导入等 API 在 M1 落地。
启动：python3 run.py
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store import Store  # noqa: E402

HOST = "127.0.0.1"
PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")

STATIC = {  # 白名单静态文件 → content-type
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}

store = Store()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 安静
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

    def do_GET(self):
        if self.path in STATIC:
            fname, ctype = STATIC[self.path]
            try:
                with open(os.path.join(WEB, fname), "rb") as f:
                    return self._send(200, f.read(), ctype)
            except FileNotFoundError:
                return self._send(500, {"error": f"{fname} 缺失"})
        if self.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if self.path == "/api/health":
            return self._send(200, {"ok": True, "version": "v2-m0"})
        if self.path == "/api/workspace":
            try:
                return self._send(200, store.summary())
            except ValueError as e:  # schema 版本不符等
                return self._send(500, {"error": str(e)})
        return self._send(404, {"error": "not found"})


def make_server():
    return ThreadingHTTPServer((HOST, PORT), Handler)


if __name__ == "__main__":
    print(f"驾驶舱：http://{HOST}:{PORT}/  (Ctrl+C 退出)")
    make_server().serve_forever()
