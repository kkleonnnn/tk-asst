"""驾驶舱 web 服务（纯标准库 http.server，零依赖）——薄层：只做路由与 IO 粘合。

业务动作全在 flows.py；workspace 读写全在 store.py；本文件不写业务逻辑。
启动：python3 run.py
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flows  # noqa: E402
from core import scoring  # noqa: E402
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

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

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
        try:
            if self.path == "/api/health":
                return self._send(200, {"ok": True, "version": "v2-m1"})
            if self.path == "/api/workspace":
                return self._send(200, store.summary())
            if self.path == "/api/products":
                return self._send(200, store.load_products())
            if self.path == "/api/tasks":
                return self._send(200, store.load_tasks())
            if self.path == "/api/scoring-params":
                return self._send(200, scoring.DEFAULTS)
        except ValueError as e:  # schema 版本不符等
            return self._send(500, {"error": str(e)})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        body = self._body()
        try:
            if self.path == "/api/import":
                return self._send(200, flows.import_products(
                    store,
                    file_b64=body.get("file_b64"),
                    file_name=body.get("file_name", ""),
                    csv_text=body.get("csv_text", ""),
                    params=body.get("params")))
            if self.path == "/api/status":
                return self._send(200, flows.set_status_bulk(
                    store, body.get("ids") or [], body.get("status", ""),
                    event=body.get("event")))
            if self.path == "/api/dispatch":
                return self._send(200, flows.dispatch_task(
                    store, body.get("type", ""), body.get("ids") or [],
                    body.get("params")))
            if self.path == "/api/compare":
                return self._send(200, flows.compare_sources(
                    store, body.get("id", ""), body.get("params")))
            if self.path == "/api/sources/add":
                return self._send(200, flows.add_source(
                    store, body.get("id", ""), body.get("source") or {}))
            if self.path == "/api/sources/update":
                return self._send(200, flows.update_source(
                    store, body.get("id", ""), body.get("source_id", ""),
                    body.get("patch") or {}))
            if self.path == "/api/choose":
                return self._send(200, flows.choose_source(
                    store, body.get("id", ""), body.get("source_id", ""),
                    body.get("params")))
            if self.path == "/api/listing/set":
                return self._send(200, flows.set_listing(
                    store, body.get("id", ""), body.get("listing") or {}))
            if self.path == "/api/export":
                return self._send(200, flows.export_product(store, body.get("id", "")))
        except (ValueError, KeyError) as e:
            return self._send(400, {"error": str(e)})
        return self._send(404, {"error": "not found"})


def make_server():
    return ThreadingHTTPServer((HOST, PORT), Handler)


if __name__ == "__main__":
    print(f"驾驶舱：http://{HOST}:{PORT}/  (Ctrl+C 退出)")
    make_server().serve_forever()
