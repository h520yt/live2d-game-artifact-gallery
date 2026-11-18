#!/usr/bin/env python3
"""跨游戏资源统一入口。

当前仅实现索引、查询和本地入口文件核查；仍使用现有游戏脚本下载/还原。
在仓库根目录运行：
    python scripts/gallery.py sync-index
    python scripts/gallery.py list --game nikke --tag 运动系
    python scripts/gallery.py verify
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gallery_core import GAME_MANIFESTS, build_catalog, verify_catalog  # noqa: E402

CATALOG_FILE = ROOT / "gallery" / "catalog.json"
REPORT_FILE = ROOT / "gallery" / "verification-report.json"


def write_json(path: Path, data: dict) -> None:
    """原子写入本地生成产物，避免中断留下半份索引。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """提供稳定命令行入口；默认绝不触发下载或覆盖素材。"""
    parser = argparse.ArgumentParser(description="多游戏资源统一索引与核验")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync-index", help="从现有游戏 manifest 生成统一索引")
    serve = sub.add_parser("serve", help="生成索引及核验报告，启动本地统一展柜")
    serve.add_argument("--port", type=int, default=8000, help="监听端口，默认 8000")
    listing = sub.add_parser("list", help="筛选跨游戏资源（直接读取当前原始清单）")
    listing.add_argument("--game", choices=tuple(GAME_MANIFESTS), help="指定游戏")
    listing.add_argument("--tag", help="按已标注的风格标签筛选")
    listing.add_argument("--limit", type=int, default=40, help="显示条目数")
    verify = sub.add_parser("verify", help="核查本地入口文件，不执行渲染")
    verify.add_argument("--strict", action="store_true",
                        help="若必要文件缺失或没有入口文件，返回失败码")
    args = parser.parse_args(argv)
    if args.command == "list" and args.limit < 0:
        parser.error("--limit 不能为负数")
    if args.command == "serve" and not 1 <= args.port <= 65535:
        parser.error("--port 必须在 1-65535 范围内")

    try:
        catalog = build_catalog(ROOT)
        if args.command == "serve":
            write_json(CATALOG_FILE, catalog)
            report = verify_catalog(ROOT, catalog)
            write_json(REPORT_FILE, report)
            handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                print(f"已生成 {len(catalog['assets'])} 项资源索引及核验报告")
                print(f"展柜首页：http://127.0.0.1:{args.port}/")
                print(f"统一目录：http://127.0.0.1:{args.port}/gallery/")
                print("仅监听本机，按 Ctrl+C 停止服务；新增素材后重启可刷新索引。")
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    print("服务已停止")
            return 0

        if args.command == "sync-index":
            write_json(CATALOG_FILE, catalog)
            counts = {game: sum(row["game"] == game for row in catalog["assets"])
                      for game in GAME_MANIFESTS}
            print(f"已写入 {CATALOG_FILE.relative_to(ROOT)}（仅生成索引，不下载）")
            for game, count in counts.items():
                print(f"  {game}: {count} 个条目")
            return 0

        if args.command == "list":
            selected = [row for row in catalog["assets"]
                        if (not args.game or row["game"] == args.game)
                        and (not args.tag or args.tag in row["tags"])]
            for row in selected[:args.limit]:
                print(f'{row["id"]}\t{row["title"]}\t{row["renderer"]}')
            print(f"符合条件 {len(selected)} 条，已显示 {min(len(selected), args.limit)} 条")
            return 0

        report = verify_catalog(ROOT, catalog)
        write_json(REPORT_FILE, report)
        print(f"已核查 {len(report['items'])} 项；报告：{REPORT_FILE.relative_to(ROOT)}")
        for status, count in report["counts"].items():
            print(f"  {status}: {count}")
        print("注意：这里只核查入口文件，不代表动画和交互已验收。")
        return int(args.strict and any(
            report["counts"][key] for key in ("missing", "partial", "no_entrypoints")
        ))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"资源索引处理失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
