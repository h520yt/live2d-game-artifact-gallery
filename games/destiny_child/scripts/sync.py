#!/usr/bin/env python3
"""下载《天命之子》 Cubism 2 Live2D 模型及已配对场景到本地。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image

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
    model = safe_file(settings["model"])
    textures = settings["textures"]
    if not model.endswith(".moc") or not isinstance(textures, list) or not textures:
        raise ValueError("模型未声明 Cubism 2 MOC 或纹理")
    textures = [safe_file(value) for value in textures]
    if any(not name.endswith(".png") or name == "icon.png" for name in textures):
        raise ValueError("模型声明了无效纹理")
    names = {"icon.png", model, *textures}
    for actions in settings.get("motions", {}).values():
        for action in actions:
            motion = safe_file(action["file"])
            if not motion.endswith(".mtn"):
                raise ValueError(f"不是 Cubism 2 动作：{motion}")
            names.add(motion)
            if action.get("sound"):
                names.add(safe_file(action["sound"]))
    names.update(safe_file(item["file"]) for item in settings.get("expressions", []))
    for key in ("physics", "pose"):
        if settings.get(key):
            names.add(safe_file(settings[key]))
    if "model.json" in names:
        raise ValueError("配置不能引用自身")
    return sorted(names)


def download(url: str, name: str | None = None, digest: str | None = None) -> bytes:
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "live2d-game-artifact-gallery"})
            with urlopen(request, timeout=35) as response:
                content = response.read()
            if len(content) < 8 or (name is not None and not valid(name, content, digest)):
                raise ValueError(f"资源数据不完整或格式无效：{url}")
            return content
        except HTTPError as error:
            if error.code in (404, 410) or attempt == 2:
                raise
        except (OSError, IncompleteRead, ValueError):
            if attempt == 2:
                raise
        time.sleep(attempt * 2 + 1)
    raise RuntimeError("下载失败")


def valid(name: str, data: bytes, digest: str | None = None) -> bool:
    if len(data) < 8 or data[:64].lstrip().lower().startswith(b"<!doctype html"):
        return False
    if digest is not None and hashlib.sha256(data).hexdigest() != digest:
        return False
    if name.endswith(".png"):
        if not data.endswith(b"\x00\x00\x00\x00IEND\xaeB\x60\x82"):
            return False
        try:
            with Image.open(BytesIO(data), formats=["PNG"]) as image:
                image.verify()
            return True
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
            return False
    if name.endswith(".moc"):
        return data.startswith(b"moc")
    if name.endswith(".mtn"):
        return data.startswith(b"# Live2D Animator Motion Data") and b"=" in data
    if name.endswith(".json"):
        try:
            payload = json.loads(data.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                return False
            if name == "model.json":
                dependencies(payload)
            return True
        except (ValueError, KeyError, TypeError, AttributeError):
            return False
    return True


def installed(path: Path, digest: str | None = None) -> bytes | None:
    if path.is_file():
        data = path.read_bytes()
        if valid(path.name, data, digest):
            return data
    return None


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
    digests = row.get("metadata", {}).get("file_sha256", {})
    model_path = folder / "model.json"
    model_digest = digests.get("model.json")
    saved_model = None if force else installed(model_path, model_digest)
    model_bytes = saved_model
    if saved_model is None:
        model_bytes = download(url + model_path.name, model_path.name, model_digest)
    settings = json.loads(model_bytes.decode("utf-8-sig"))
    names = dependencies(settings)
    if digests and set(digests) != {*names, model_path.name}:
        raise ValueError(f"{asset_id} 的校验清单与模型依赖不一致")
    copied = 0
    for name in names:
        path = folder / name
        digest = digests.get(name)
        if not force and installed(path, digest) is not None:
            continue
        atomic_write_bytes(path, download(url + name, name, digest))
        copied += 1
        print(f"    写入：{name}（{path.stat().st_size} 字节）")
    if saved_model is None:
        atomic_write_bytes(model_path, model_bytes)
        copied += 1
    print(f"  完成：{asset_id}，本次更新 {copied}/{len(names) + 1} 个文件")


def install_background(row: dict, force: bool, completed: set[str]) -> None:
    paths = row.get("roles", {}).get("background")
    if not paths:
        return
    path, = paths
    name = safe_file(path.removeprefix("../data/backgrounds/"))
    if path != f"../data/backgrounds/{name}" or not re.fullmatch(r"[\w-]+\.png", name):
        raise ValueError(f"背景路径无效：{path}")
    if name in completed:
        return
    info = row["metadata"]["background"]
    url = info["url"]
    source = urlsplit(url)
    if source.scheme != "https" or not source.hostname or not re.fullmatch(r"[0-9a-f]{64}", info["sha256"]):
        raise ValueError(f"背景来源或校验码无效：{name}")
    destination = GAME / "data" / "backgrounds" / name
    digest = info["sha256"]
    if force or installed(destination, digest) is None:
        atomic_write_bytes(destination, download(url, name, digest))
        print(f"  [背景已安装] {name}")
    completed.add(name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Destiny Child Live2D 下载器")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--id", action="append", metavar="c001_14", help="指定模型，可重复")
    group.add_argument("--all", action="store_true", help="安装清单全部（默认）")
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
        backgrounds = set()
        for row in todo:
            print(f"\n[安装] {row['id']} · {row['title']}")
            try:
                install(row, args.force)
                install_background(row, args.force, backgrounds)
            except (OSError, ValueError, KeyError, TypeError, IncompleteRead) as error:
                failures += 1
                print(f"[失败] {row['id']}: {error}", file=sys.stderr)
        print(f"安装结束：成功 {len(todo) - failures}，失败 {failures}")
        return int(failures > 0)
    except (OSError, ValueError, KeyError, TypeError, IncompleteRead) as error:
        print("执行失败：" + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
