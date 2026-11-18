#!/usr/bin/env python3
"""真实浏览器静态资源目录烟测（可选，需本机已安装 Chrome/Chromium）。

使用本地 Python HTTP 服务与已生成的 gallery/catalog.json。
不依赖版权素材，验证首页 JS 执行后能展示真实资源卡片和直达链接。
此测试不证明游戏模型、动作或互动渲染正确。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


class QuietHandler(SimpleHTTPRequestHandler):
    """减少大量缺失缩略图导致的 HTTP 404 日志。"""
    def log_message(self, format, *args):
        return


def find_browser() -> str | None:
    for candidate in BROWSERS:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def main() -> int:
    browser = find_browser()
    if browser is None:
        print("跳过浏览器冒烟：系统没有安装 Chrome/Chromium")
        return 0
    if not (ROOT / "gallery/catalog.json").is_file():
        print("缺少 gallery/catalog.json：请先运行 python scripts/gallery.py sync-index",
              file=sys.stderr)
        return 2

    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        command = [
            browser, "--headless=new", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
            "--virtual-time-budget=7000", "--dump-dom",
            f"http://127.0.0.1:{port}/gallery/",
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=50)
        if result.returncode != 0:
            print("Chrome 启动失败：", result.stderr[-1500:], file=sys.stderr)
            return 1
        page = result.stdout
        count = re.search(r'id="total-count">([\d,]+)</span>', page)
        rendered = bool(count and int(count.group(1).replace(",", "")) > 0)
        links = 'gallery_asset=' in page and 'class="open-link"' in page
        cards = '<article class="card">' in page
        if not (rendered and links and cards):
            print(f"统一目录浏览器烟测失败：统计={rendered}、卡片={cards}、直达链接={links}",
                  file=sys.stderr)
            print("可能是前端脚本异常、生成索引格式错误或 HTTP 加载失败。",
                  file=sys.stderr)
            return 1
        print("Chrome 浏览器烟测通过：已运行前端 JS，生成资源卡片和皮肤直达链接。")
        print("注意：未加载版权模型，不等于动画或独立互动验收通过。")
        return 0
    except subprocess.TimeoutExpired:
        print("Chrome 浏览器烟测超时（本地页面加载不应无限阻塞）", file=sys.stderr)
        return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
