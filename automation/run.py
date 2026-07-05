#!/usr/bin/env python3
"""一键启动运营控制台。

用法（校长）：在 automation/ 目录下双击或运行：
    python3 run.py
浏览器会自动打开 http://127.0.0.1:8765/ 。关闭：回终端按 Ctrl+C。
零依赖，只要装了 Python 3 就能跑。
"""
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from server import make_server, HOST, PORT  # noqa: E402


def main():
    url = f"http://{HOST}:{PORT}/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"✅ 运营控制台已启动：{url}")
    print("   浏览器没自动打开就手动复制上面地址。退出按 Ctrl+C。")
    try:
        make_server().serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")


if __name__ == "__main__":
    main()
