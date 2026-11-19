#!/usr/bin/env python3
"""下载《天命之子》 Cubism 2 Live2D 模型到本地，不提交游戏资源。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from gallery_core.storage import atomic_write_bytes  # noqa: E402

GAME = ROOT / "games" / "destiny_child"
SOURCE_COMMIT = "63e43d034512946c5eb308754f18a1865382bdf6"
BASE = "https://raw.githubusercontent.com/Pelom777/DestinyChildLive2D/" + SOURCE_COMMIT + "/assets/live2d/"
MANIFEST = GAME / "viewer" / "manifest.json"
# 采用已验证的 Cubism 2 SDK + pixi-live2d-display Cubism 2 插件；
# 第三方运行时仅下载到本地 vendor，不入库分发（遵循上游许可）。
RUNTIME_REVISION = "4a2a6ce32185563fe48a8debd533780dfb9b392d"
RUNTIME_BASE = (
    "https://raw.githubusercontent.com/Live2D-DCG/Live2D-DCG.github.io/"
    + RUNTIME_REVISION + "/vendor/"
)
RUNTIME_FILES = {
    "live2d.min.js": ("Live2D", "Live2DModelWebGL"),
    "pixi-live2d-display-cubism2.min.js": ("Live2DModel", "Cubism 2"),
}
ID_RE = re.compile(r"^c\d{3}_\d{2}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def safe_file(value: object) -> str:
    if not isinstance(value, str) or value in (".", "..") or not NAME_RE.fullmatch(value):
        raise ValueError(f"不安全的资源名：{value!r}")
    return value


def dependencies(settings: dict) -> list[str]:
    """从真实 Cubism 2 配置提取模型、纹理、动作、表情文件。"""
    names = {"model.json", "icon.png", safe_file(settings["model"])}
    names.update(safe_file(value) for value in settings.get("textures", []))
    for actions in settings.get("motions", {}).values():
        names.update(safe_file(action["file"]) for action in actions)
    names.update(safe_file(item["file"]) for item in settings.get("expressions", []))
    for key in ("physics", "pose"):
        if settings.get(key):
            names.add(safe_file(settings[key]))
    if not any(name.endswith(".png") and name != "icon.png" for name in names):
        raise ValueError("模型未声明纹理")
    return sorted(names)


def download(url: str) -> bytes:
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "live2d-game-artifact-gallery"})
            with urlopen(request, timeout=35) as response:
                content = response.read()
            if len(content) < 8:
                raise ValueError("资源数据太短")
            return content
        except HTTPError as error:
            if error.code in (404, 410) or attempt == 2:
                raise
        except (URLError, TimeoutError, ValueError):
            if attempt == 2:
                raise
        time.sleep(attempt * 2 + 1)
    raise RuntimeError("下载失败")


def valid(name: str, data: bytes) -> bool:
    if len(data) < 8 or data[:64].lstrip().lower().startswith(b"<!doctype html"):
        return False
    if name.endswith(".png"):
        return data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24
    if name.endswith(".json"):
        try:
            json.loads(data.decode("utf-8-sig"))
            return True
        except (ValueError, UnicodeDecodeError):
            return False
    return True


def install_runtime(force: bool = False) -> None:
    """补齐本地 Cubism 2 播放器。运行时有独立许可，不提交 Git 仓库。"""
    vendor = GAME / "vendor"
    for filename, markers in RUNTIME_FILES.items():
        destination = vendor / filename
        if destination.is_file() and not force:
            try:
                saved = destination.read_bytes()
                if len(saved) > 10000 and all(
                    marker.encode("ascii") in saved for marker in markers
                ):
                    print(f"  [运行时已有] {filename}")
                    continue
            except OSError:
                pass
        data = download(RUNTIME_BASE + filename)
        if len(data) <= 10000 or not all(
            marker.encode("ascii") in data for marker in markers
        ):
            raise ValueError(f"Cubism 2 运行时文件不完整：{filename}")
        atomic_write_bytes(destination, data)
        print(f"  [运行时已安装] {filename} ({len(data)} bytes)")


def entries() -> list[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("assets"), list):
        raise ValueError("资源清单格式不正确")
    rows = manifest["assets"]
    ids = [row["id"] for row in rows]
    if any(not ID_RE.fullmatch(asset_id) for asset_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("资源编号无效或重复")
    return rows


def install(row: dict, force: bool) -> None:
    asset_id = row["id"]
    folder = GAME / "data" / asset_id
    url = BASE + asset_id + "/"
    model_bytes = download(url + "model.json")
    settings = json.loads(model_bytes.decode("utf-8-sig"))
    names = dependencies(settings)
    copied = 0
    for name in names:
        path = folder / name
        if name != "model.json" and not force and path.is_file() and valid(name, path.read_bytes()):
            print(f"    已有：{name}")
            continue
        content = model_bytes if name == "model.json" else download(url + name)
        if not valid(name, content):
            raise ValueError(f"{asset_id}: {name} 文件无效")
        atomic_write_bytes(path, content)
        copied += 1
        print(f"    写入：{name}（{len(content)} 字节）")
    if any(not (folder / name).is_file() or not valid(name, (folder / name).read_bytes()) for name in names):
        raise ValueError("安装后文件校验失败")
    print(f"  完成：{asset_id}，本次更新 {copied}/{len(names)} 个文件")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Destiny Child Live2D 下载器")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--id", action="append", metavar="c001_14", help="指定模型，可重复")
    group.add_argument("--all", action="store_true", help="安装首批全部（默认）")
    group.add_argument("--runtime-only", action="store_true", help="仅修复 Cubism 2 播放运行时")
    parser.add_argument("--plan", action="store_true", help="离线查看安装计划")
    parser.add_argument("--force", action="store_true", help="修复并覆盖已有文件")
    args = parser.parse_args(argv)
    try:
        if args.runtime_only:
            if args.plan:
                print("运行时安装计划：" + ", ".join(RUNTIME_FILES))
                return 0
            install_runtime(args.force)
            print("Cubism 2 播放运行时安装完成；请刷新浏览器。")
            return 0
        rows = entries()
        requested = set(args.id) if args.id else {row["id"] for row in rows}
        absent = requested - {row["id"] for row in rows}
        if absent:
            raise ValueError("清单未收录：" + ", ".join(sorted(absent)))
        todo = [row for row in rows if row["id"] in requested]
        print(f"天命之子：{len(todo)} 套；来源固定于 {SOURCE_COMMIT[:12]}")
        for row in todo:
            print(f"  {row['id']}  {row['title']}")
        if args.plan:
            print("同时准备运行时：" + ", ".join(RUNTIME_FILES))
            return 0
        install_runtime(args.force)
        failures = 0
        for row in todo:
            print(f"\n[安装] {row['id']} · {row['title']}")
            try:
                install(row, args.force)
            except (OSError, ValueError, KeyError, TypeError, HTTPError, URLError) as error:
                failures += 1
                print(f"[失败] {row['id']}: {error}", file=sys.stderr)
        print(f"安装结束：成功 {len(todo) - failures}，失败 {failures}")
        return int(failures > 0)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("执行失败：" + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
