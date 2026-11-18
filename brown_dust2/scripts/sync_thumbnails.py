#!/usr/bin/env python3
"""缓存棕色尘埃2库存立绘缩略图，供统一展示柜离线显示。

仅下载已在 thumbnail_catalog.json 登记的真实 256x256 皮肤库存图。
不处理 Spine 骨骼/atlas；不会将版权素材提交到 Git。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gallery_core.storage import atomic_write_bytes  # noqa: E402

BASE = PROJECT_ROOT / "brown_dust2"
CATALOG = BASE / "thumbnail_catalog.json"
OUTPUT = BASE / "data" / "_thumbnails"
SOURCE = (
    "https://raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/"
    "master/ui/illust/illust_inven_char/"
)
FILE_NAME = re.compile(r"illust_inven_char\d{6}_\d+\.png")
COSTUME_ID = re.compile(r"[a-zA-Z0-9_-]{1,128}")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 10 * 1024 * 1024


def load_mappings(path: Path = CATALOG) -> dict[str, str]:
    """只接受已核对的皮肤 ID 和库存 PNG 文件名，阻止路径穿越。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    images = payload.get("images")
    if not isinstance(images, dict) or not images:
        raise ValueError("缩略图索引 images 不存在或无条目")
    for skin_id, name in images.items():
        if not COSTUME_ID.fullmatch(skin_id):
            raise ValueError(f"非法皮肤 ID：{skin_id}")
        if not isinstance(name, str) or not FILE_NAME.fullmatch(name):
            raise ValueError(f"非法库存立绘文件名：{skin_id}")
    return images


def is_valid_png(path: Path) -> bool:
    """检查本地 PNG 基本签名与大小，不把 HTML 错误页当缓存。"""
    try:
        if not path.is_file() or not 8 < path.stat().st_size <= MAX_PNG_BYTES:
            return False
        with path.open("rb") as stream:
            return stream.read(8) == PNG_SIGNATURE
    except OSError:
        return False


def fetch_image(url: str, attempts: int = 3) -> bytes:
    """受信任的固定 CDN URL，短时错误重试，拒绝空内容及异常大文件。"""
    error = None
    for index in range(attempts):
        try:
            request = Request(url, headers={
                "User-Agent": "Personal-RD-Lab-BD2-Thumbnails/1.0",
                "Accept": "image/png",
            })
            with urlopen(request, timeout=30) as response:
                payload = response.read(MAX_PNG_BYTES + 1)
            if not (8 < len(payload) <= MAX_PNG_BYTES) or not payload.startswith(PNG_SIGNATURE):
                raise ValueError("远端返回非 PNG 或超出大小限制")
            return payload
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            error = exc
            if index + 1 < attempts:
                time.sleep(0.4 * (index + 1))
    raise RuntimeError(f"获取缩略图失败：{url}：{error}")


def install_one(skin_id: str, filename: str, refresh: bool = False) -> str:
    """缓存单张立绘；写入为原子替换，失败不会损坏已有文件。"""
    path = OUTPUT / (skin_id + ".png")
    if is_valid_png(path) and not refresh:
        return "cached"
    image = fetch_image(SOURCE + filename)
    atomic_write_bytes(path, image)
    return "downloaded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="缓存棕色尘埃2的真实库存立绘缩略图")
    parser.add_argument("--only", nargs="+", help="仅缓存指定皮肤 ID")
    parser.add_argument("--plan", action="store_true", help="仅列出本地缓存状态，不下载")
    parser.add_argument("--refresh", action="store_true", help="重新拉取并更新已有缓存")
    parser.add_argument("--workers", type=int, default=6, help="并发下载数量，1-12，默认 6")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 12:
        parser.error("--workers 必须在 1 到 12 之间")
    try:
        mappings = load_mappings()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"缩略图索引错误：{exc}", file=sys.stderr)
        return 1

    if args.only:
        unknown = set(args.only) - set(mappings)
        if unknown:
            print("未知皮肤 ID：" + ", ".join(sorted(unknown)), file=sys.stderr)
            return 1
        selected = [(name, mappings[name]) for name in dict.fromkeys(args.only)]
    else:
        selected = list(mappings.items())

    ready = [(skin_id, filename) for skin_id, filename in selected
             if is_valid_png(OUTPUT / (skin_id + ".png"))]
    print(f"缩略图：总计 {len(selected)} 张；本地有效缓存 {len(ready)} 张")
    if args.plan:
        for skin_id, filename in selected:
            result = "已缓存" if (skin_id, filename) in ready else "待下载"
            print(f"  [{result}] {skin_id} -> {filename}")
        return 0

    downloaded = cached = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(install_one, skin_id, filename, args.refresh): skin_id
                   for skin_id, filename in selected}
        for future in as_completed(pending):
            skin_id = pending[future]
            try:
                result = future.result()
                if result == "cached":
                    cached += 1
                else:
                    downloaded += 1
            except (OSError, RuntimeError, ValueError) as exc:
                failed += 1
                print(f"  [失败] {skin_id}：{exc}", file=sys.stderr)
    print(f"处理完成：下载 {downloaded}，跳过缓存 {cached}，失败 {failed}")
    if not failed:
        print("请运行 python scripts/gallery.py sync-index 后刷新统一目录，优先使用本地封面。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
