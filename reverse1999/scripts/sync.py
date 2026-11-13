#!/usr/bin/env python3
"""按需下载《重返未来：1999》Live2D 模型并生成本地查看器索引。

源：myssal/Reverse-1999-CN-Asset；不依赖游戏客户端。
只下载使用者指定的模型，不批量克隆整个大型仓库。
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SOURCE = "myssal/Reverse-1999-CN-Asset"
SOURCE_ROOT = "live2d/roles"
API_ROOT = f"https://api.github.com/repos/{SOURCE}/contents"
MAP_URL = f"https://raw.githubusercontent.com/{SOURCE}/master/mappings/ArcanistMap.json"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "models"
CONFIG_DIR = ROOT / "config"
MANIFEST = ROOT / "viewer" / "manifest.json"
CACHE = CONFIG_DIR / "ArcanistMap.json"
FOLDER_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def request_bytes(url, api=False):
    headers = {"User-Agent": "Reverse1999-local-viewer/1.0"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and api:
            raise RuntimeError("GitHub API 可能触发了访问频率限制；稍后重试，或设置 GITHUB_TOKEN") from exc
        raise RuntimeError(f"下载失败 HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接资源服务器：{exc.reason}") from exc


def get_json(url, api=False):
    return json.loads(request_bytes(url, api=api).decode("utf-8-sig"))


def load_mapping(refresh=False):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    try:
        data = get_json(MAP_URL)
        if not isinstance(data, list):
            raise RuntimeError("角色映射格式不正确")
        temp = CACHE.with_suffix(".json.tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(CACHE)
        return data
    except (RuntimeError, ValueError) as exc:
        if CACHE.exists():
            print(f"警告：在线映射获取失败，使用本地缓存：{exc}", file=sys.stderr)
            return json.loads(CACHE.read_text(encoding="utf-8"))
        raise


def mapped_entries(mapping):
    """只收录映射明确关联到 live2d/roles/<folder> 的模型。"""
    results = {}
    marker = f"/{SOURCE_ROOT}/"
    for person in mapping:
        for skin in person.get("live2d", []):
            url = skin.get("cubism", "")
            # GitHub 上可能存在空目录链接，须过滤。
            if marker not in url:
                continue
            folder = url.split(marker, 1)[1].strip("/")
            if not FOLDER_RE.fullmatch(folder):
                continue
            key = str(skin.get("id", ""))
            results[key] = {
                "id": skin.get("id"),
                "name": person.get("name") or skin.get("name") or folder,
                "en": person.get("nameEng") or "",
                "skin": skin.get("characterSkin") or skin.get("des") or "默认皮肤",
                "skin_en": skin.get("characterSkinNameEng") or "",
                "folder": folder,
            }
    return results


def list_remote(mapping, query=""):
    rows = mapped_entries(mapping).values()
    search = query.strip().lower()
    if search:
        rows = [x for x in rows if search in " ".join(str(x[k]) for k in ("id", "name", "en", "skin", "skin_en", "folder")).lower()]
    rows = sorted(rows, key=lambda x: str(x["id"]))
    for row in rows:
        print(f"{row['id']:<9} {row['name']:<12} {row['skin']:<18} {row['folder']}")
    print(f"共找到 {len(rows)} 条映射（不代表全部都有可下载文件）")


def safe_model_dir(folder):
    if not FOLDER_RE.fullmatch(folder):
        raise ValueError(f"非法资源目录名：{folder!r}")
    return DATA_DIR / folder


def walk_github(path):
    """列出当前模型子目录（通常为 textures/motions/expressions）。"""
    safe_path = urllib.parse.quote(path, safe="/")
    items = get_json(f"{API_ROOT}/{safe_path}", api=True)
    if not isinstance(items, list):
        raise RuntimeError(f"GitHub 路径不是目录：{path}")
    for item in items:
        kind = item.get("type")
        if kind == "dir":
            yield from walk_github(item["path"])
        elif kind == "file":
            yield item


def download_one(item, folder):
    rel = item["path"].split(f"{SOURCE_ROOT}/{folder}/", 1)
    if len(rel) != 2:
        raise RuntimeError(f"资源路径不在目标文件夹内：{item['path']}")
    relative = Path(rel[1])
    if relative.is_absolute() or any(part in ("..", ".") for part in relative.parts):
        raise RuntimeError(f"非法资源文件路径：{relative}")
    target = safe_model_dir(folder) / relative
    expected = int(item.get("size") or 0)
    if target.is_file() and (expected == 0 or target.stat().st_size == expected):
        print(f"已存在：{target.relative_to(ROOT)}")
        return False
    url = item.get("download_url")
    # 仅允许来自已知上游仓库的下载地址，避免清单污染导致请求第三方服务器。
    allowed = f"https://raw.githubusercontent.com/{SOURCE}/"
    if not isinstance(url, str) or not url.startswith(allowed):
        raise RuntimeError(f"不可信的资源地址：{url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".downloading-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            req = urllib.request.Request(url, headers={"User-Agent": "Reverse1999-local-viewer/1.0"})
            with urllib.request.urlopen(req, timeout=75) as stream:
                shutil.copyfileobj(stream, out)
        if expected and os.stat(tmp_name).st_size != expected:
            raise RuntimeError(f"下载体积不匹配：{relative}")
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    print(f"下载完成：{target.relative_to(ROOT)} ({target.stat().st_size:,} 字节)")
    return True


def download_model(folder):
    target = safe_model_dir(folder)
    files = list(walk_github(f"{SOURCE_ROOT}/{folder}"))
    if not any(f["name"].endswith(".model3.json") for f in files):
        raise RuntimeError(f"{folder} 缺少 .model3.json，无法作为 Live2D 模型加载")
    print(f"找到模型 {folder}，共 {len(files)} 个文件")
    new = sum(download_one(item, folder) for item in files)
    print(f"本次下载/更新 {new} 个文件，目录：{target}")


def generate_manifest(mapping):
    meta = mapped_entries(mapping)
    by_folder = {}
    for m in meta.values():
        by_folder[m["folder"]] = m
    models = []
    if DATA_DIR.is_dir():
        for folder in sorted(DATA_DIR.iterdir()):
            if not folder.is_dir() or not FOLDER_RE.fullmatch(folder.name):
                continue
            configs = sorted(folder.glob("*.model3.json"))
            for config in configs:
                try:
                    info = json.loads(config.read_text(encoding="utf-8-sig"))
                    refs = info.get("FileReferences", {})
                    assets = [refs.get("Moc")] + list(refs.get("Textures", []))
                    if not all(x and (folder / x).is_file() for x in assets):
                        print(f"跳过缺少核心文件的模型：{config.name}", file=sys.stderr)
                        continue
                except (ValueError, OSError, TypeError):
                    print(f"跳过配置错误的模型：{config.name}", file=sys.stderr)
                    continue
                record = by_folder.get(folder.name, {})
                models.append({
                    "id": record.get("id") or folder.name,
                    "name": record.get("name") or folder.name,
                    "en": record.get("en") or "",
                    "skin": record.get("skin") or "未匹配皮肤",
                    "skin_en": record.get("skin_en") or "",
                    "folder": folder.name,
                    "path": f"../data/models/{folder.name}/{config.name}",
                })
    models.sort(key=lambda x: (str(x["name"]), str(x["skin"]), str(x["folder"])))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    output = {"source": SOURCE, "models": models}
    MANIFEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成索引：{MANIFEST}，包含 {len(models)} 套模型")


def main(argv=None):
    parser = argparse.ArgumentParser(description="重返未来：1999 Live2D 本地按需下载")
    parser.add_argument("action", choices=["list", "download", "manifest"], help="列出角色、下载指定模型、重建本地索引")
    parser.add_argument("target", nargs="?", help="download 使用角色皮肤 ID（例如 300301），也可使用资源目录名")
    parser.add_argument("--search", default="", help="list 时按角色名或皮肤名搜索")
    parser.add_argument("--refresh", action="store_true", help="刷新远程角色映射")
    args = parser.parse_args(argv)
    if args.action == "download" and not args.target:
        parser.error("download 必须指定皮肤 ID 或资源目录名")
    try:
        mapping = load_mapping(args.refresh)
        if args.action == "list":
            list_remote(mapping, args.search)
        elif args.action == "manifest":
            generate_manifest(mapping)
        else:
            entries = mapped_entries(mapping)
            folder = entries[args.target]["folder"] if args.target in entries else args.target
            # 不允许任意服务器 URL，只允许上游安全目录名。
            safe_model_dir(folder)
            download_model(folder)
            generate_manifest(mapping)
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
