#!/usr/bin/env python3
"""为 BD2 已精选的皮肤下载官方库存立绘缩略图（无需 GitHub API）。"""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
CATALOG = BASE / "thumbnail_catalog.json"
TARGET = BASE / "data" / "_thumbnails"
CDN = ("https://raw.githubusercontent.com/myssal/Brown-Dust-2-Asset/"
       "master/ui/illust/illust_inven_char/")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IMAGE_NAME = re.compile(r"^illust_inven_char\d{6}_\d+\.png$")
SKIN_ID = re.compile(r"^[a-z0-9-]+$")
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def is_valid_png(data):
    """最低限度防止 GitHub 的 403/404 HTML 被误存为图片。"""
    return (len(data) >= 24 and len(data) <= MAX_IMAGE_BYTES
            and data.startswith(PNG_SIGNATURE)
            and int.from_bytes(data[16:20], "big") > 0
            and int.from_bytes(data[20:24], "big") > 0)


def read_catalog(path=CATALOG):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    images = raw.get("images") or {}
    if not images:
        raise ValueError("没有可下载的缩略图映射")
    for skin_id, filename in images.items():
        if not SKIN_ID.fullmatch(skin_id) or not IMAGE_NAME.fullmatch(filename):
            raise ValueError("缩略图目录含有非法名称: " + skin_id)
    return images


def download_one(skin_id, filename, target=TARGET, opener=urlopen, overwrite=False):
    """单文件原子落地：下载完成并验证 PNG 后才替换本地版本。"""
    target = Path(target)
    destination = target / (skin_id + ".png")
    if destination.exists() and not overwrite:
        if is_valid_png(destination.read_bytes()):
            return "cached", destination
    url = CDN + filename
    request = Request(url, headers={"User-Agent": "BD2-Gallery/1.0"})
    response = opener(request, timeout=25)
    with response:
        # 目录中的游戏图一般 60–120 KiB，防止无限/异常响应。
        data = response.read(MAX_IMAGE_BYTES + 1)
    if not is_valid_png(data):
        raise ValueError("缩略图响应不是完整 PNG: " + skin_id)
    target.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".tmp")
    try:
        temp.write_bytes(data)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return "downloaded", destination


def main(argv=None):
    parser = argparse.ArgumentParser(description="为 BD2 皮肤画廊缓存真实角色立绘")
    parser.add_argument("--only", help="只获取指定皮肤 ID")
    parser.add_argument("--force", action="store_true", help="重新下载已有的有效缩略图")
    parser.add_argument("--list", action="store_true", help="仅检查本地缩略图，不联网")
    args = parser.parse_args(argv)
    images = read_catalog()
    if args.only:
        if args.only not in images:
            parser.error("未知精选皮肤 ID：" + args.only)
        images = {args.only: images[args.only]}
    cached = downloaded = failed = 0
    for skin_id, filename in images.items():
        destination = TARGET / (skin_id + ".png")
        if args.list:
            ok = destination.exists() and is_valid_png(destination.read_bytes())
            print(skin_id, filename, "本地已缓存" if ok else "待缓存")
            cached += int(ok)
            continue
        try:
            status, _ = download_one(skin_id, filename, overwrite=args.force)
            cached += int(status == "cached")
            downloaded += int(status == "downloaded")
            print(f"[{status}] {skin_id}")
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            print(f"[失败] {skin_id}: {error}")
            failed += 1
    print(f"缓存 {cached} / 新增 {downloaded} / 失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
