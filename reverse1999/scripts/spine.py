#!/usr/bin/env python3
"""《重返未来：1999》Spine 资源索引、按需下载及完整性核查。

目录检查基于 GitHub Git Tree；不会把目录存在误判为已验证全部动画可播放。
所有美术资源、缓存和第三方运行时都只保留在本机，不纳入 Git。
"""
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "myssal/Reverse-1999-CN-Asset"
API = f"https://api.github.com/repos/{SOURCE}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPOSITORY_ROOT / "data" / "spine"
CUBISM_DIR = REPOSITORY_ROOT / "data" / "models"
CONFIG_DIR = REPOSITORY_ROOT / "config"
VENDOR_DIR = REPOSITORY_ROOT / "vendor"
CATALOG_PATH = CONFIG_DIR / "catalog_index.json"
AUDIT_PATH = CONFIG_DIR / "audit-report.json"
FOLDER_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
ID_RE = re.compile(r"(?:^|_)(\d{6})(?:_|$)")
VERSION_RE = re.compile(rb"(?:3\.8|4\.[012])\.\d+")

# 官方提供的 Spine Web Player 4.2 运行时；版本固定，保证可复现。
RUNTIME_BASE = "https://unpkg.com/@esotericsoftware/spine-player@4.2.87/dist"
RUNTIME_FILES = (
    ("spine-player4.2.min.js", f"{RUNTIME_BASE}/iife/spine-player.min.js", 150_000),
    ("spine-player4.2.css", f"{RUNTIME_BASE}/spine-player.css", 10_000),
)


def fetch_bytes(url, api=False, timeout=60):
    headers = {"User-Agent": "Reverse1999-local-asset-viewer/1.1"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}：{url}（GitHub API 限流可设置 GITHUB_TOKEN）") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"网络请求失败：{url}：{exc.reason}") from exc


def fetch_json(url, api=True):
    return json.loads(fetch_bytes(url, api=api).decode("utf-8-sig"))


def remote_folder(url, root):
    marker = f"/{root}/"
    text = str(url or "")
    if marker not in text:
        return ""
    folder = text.split(marker, 1)[1].strip("/")
    return folder if FOLDER_RE.fullmatch(folder) else ""


def extract_id(folder):
    match = ID_RE.search(folder)
    return match.group(1) if match else None


def skin_entries(mapping):
    entries = {}
    for character in mapping:
        for skin in character.get("live2d", []):
            skin_id = skin.get("id")
            if skin_id is None:
                continue
            entries[str(skin_id)] = {
                "id": skin_id,
                "name": character.get("name") or skin.get("name") or str(skin_id),
                "en": character.get("nameEng") or "",
                "skin": skin.get("characterSkin") or skin.get("des") or "初始皮肤",
                "skin_en": skin.get("characterSkinNameEng") or "",
                "spine": remote_folder(skin.get("spine"), "roles"),
                "cubism": remote_folder(skin.get("cubism"), "live2d/roles"),
                "alternate_spine": remote_folder(skin.get("alternateSpine"), "roles"),
            }
    return entries


def catalog(refresh=False):
    if CATALOG_PATH.is_file() and not refresh:
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    try:
        root = fetch_json(f"{API}/git/trees/master")["tree"]
        sha = {x["path"]: x["sha"] for x in root if x["type"] == "tree"}
        roles = fetch_json(f"{API}/git/trees/{sha['roles']}")
        live2d = fetch_json(f"{API}/git/trees/{sha['live2d']}")
        cubism_branch = next(x["sha"] for x in live2d["tree"] if x["path"] == "roles")
        cubism = fetch_json(f"{API}/git/trees/{cubism_branch}")
        if roles.get("truncated") or cubism.get("truncated"):
            raise RuntimeError("Git Tree 被截断，拒绝据此判定资源缺失")
        result = {
            "source": SOURCE,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "spine": sorted(x["path"] for x in roles["tree"] if x["type"] == "tree"),
            "cubism": sorted(x["path"] for x in cubism["tree"] if x["type"] == "tree"),
        }
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
    except (RuntimeError, ValueError, KeyError, StopIteration) as exc:
        if CATALOG_PATH.is_file():
            print(f"警告：在线目录拉取失败，使用历史快照：{exc}")
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        raise RuntimeError(f"无法取得上游资源目录：{exc}") from exc


def catalog_matches(entry, resources, kind):
    expected = entry[kind]
    candidates = set(resources[kind])
    if expected in candidates:
        return expected
    sid = str(entry["id"])
    matches = sorted(x for x in candidates if extract_id(x) == sid)
    # 版本前缀可能不同，仅当唯一匹配时自动修正，避免下载错皮肤。
    if len(matches) == 1:
        return matches[0]
    return ""


def audit(mapping, refresh=False, show_missing=False):
    index = catalog(refresh)
    entries = skin_entries(mapping)
    output = []
    for entry in entries.values():
        spine = catalog_matches(entry, index, "spine")
        cubism = catalog_matches(entry, index, "cubism")
        output.append({**entry, "spine_actual": spine, "cubism_actual": cubism,
                       "spine_exists": bool(spine), "cubism_exists": bool(cubism)})
    stats = {
        "characters": len(mapping),
        "mapped_skins": len(entries),
        "spine_directories": len(index["spine"]),
        "cubism_directories": len(index["cubism"]),
        "skin_spine_present": sum(bool(x["spine_actual"]) for x in output),
        "skin_spine_missing": sum(not x["spine_actual"] for x in output),
        "skin_cubism_present": sum(bool(x["cubism_actual"]) for x in output),
        "skin_cubism_missing": sum(not x["cubism_actual"] for x in output),
        "skin_neither_present": sum(not x["spine_actual"] and not x["cubism_actual"] for x in output),
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps({"source": SOURCE, "catalog_checked_at_utc": index["checked_at_utc"],
                                       "note": "仅核查映射目录存在，未逐一验证目录内文件完整性和动画兼容性。",
                                       "stats": stats, "skins": output}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print("资源目录审计：", json.dumps(stats, ensure_ascii=False))
    print(f"明细已写入 {AUDIT_PATH.relative_to(REPOSITORY_ROOT)}")
    if show_missing:
        for x in output:
            if not x["spine_actual"] or not x["cubism_actual"]:
                print(f"{x['id']} {x['name']} {x['skin']}: "
                      f"Spine={'有' if x['spine_actual'] else '无'} / Cubism={'有' if x['cubism_actual'] else '无'}")
    return stats


def list_assets(mapping, query="", refresh=False):
    idx = catalog(refresh)
    q = query.strip().casefold()
    rows = list(skin_entries(mapping).values())
    if q:
        rows = [r for r in rows if q in " ".join(str(r.get(k, "")) for k in
                ("id", "name", "en", "skin", "skin_en", "spine", "cubism")).casefold()]
    for row in sorted(rows, key=lambda x: str(x["id"])):
        kinds = "/".join(k for k in ("spine", "cubism") if catalog_matches(row, idx, k)) or "未找到"
        print(f"{str(row['id']):<9} {row['name']:<12} {row['skin'][:20]:<20} [{kinds}]")
    print(f"共 {len(rows)} 条已映射皮肤（状态按上游资源目录判定）")


def download_file(url, target, expected=0):
    if target.is_file() and target.stat().st_size == expected and expected > 0:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_bytes(url, timeout=90)
    if expected and len(data) != expected:
        raise RuntimeError(f"下载文件大小不符：{target.name}（期待 {expected}，实际 {len(data)}）")
    fd, temp = tempfile.mkstemp(prefix=".download-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print(f"已保存：{target.relative_to(REPOSITORY_ROOT)} ({len(data):,} B)")
    return True


def github_files(path):
    url = f"{API}/contents/{urllib.parse.quote(path, safe='/')}"
    nodes = fetch_json(url)
    if not isinstance(nodes, list):
        raise RuntimeError(f"不是 GitHub 目录：{path}")
    for node in nodes:
        if node["type"] == "dir":
            yield from github_files(node["path"])
        elif node["type"] == "file":
            yield node


def download_asset(kind, folder):
    if not FOLDER_RE.fullmatch(folder):
        raise ValueError(f"非法目录名：{folder!r}")
    source_root, output = ("roles", DATA_DIR) if kind == "spine" else ("live2d/roles", CUBISM_DIR)
    prefix = f"{source_root}/{folder}"
    items = list(github_files(prefix))
    names = [x["name"] for x in items]
    if kind == "spine" and not (any(x.endswith(".skel") for x in names) and
                                any(x.endswith(".atlas") for x in names) and
                                any(x.endswith(".png") for x in names)):
        raise RuntimeError(f"资源不完整：{prefix} 缺少 .skel/.atlas/.png")
    if kind == "cubism" and not any(x.endswith(".model3.json") for x in names):
        raise RuntimeError(f"资源不完整：{prefix} 缺少 .model3.json")
    print(f"准备下载 {kind}：{prefix}，共 {len(items)} 个文件")
    for item in items:
        path = item["path"]
        if not path.startswith(prefix + "/"):
            raise RuntimeError("资源路径越界")
        rel = Path(path[len(prefix) + 1:])
        if rel.is_absolute() or not rel.parts or any(p in ("..", ".") for p in rel.parts):
            raise RuntimeError("不安全的相对路径")
        url = item.get("download_url") or ""
        if not url.startswith(f"https://raw.githubusercontent.com/{SOURCE}/"):
            raise RuntimeError(f"非预期下载来源：{url}")
        download_file(url, output / folder / rel, int(item.get("size") or 0))
    print(f"下载完成：{folder}")


def setup_runtime():
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    for name, url, minimum in RUNTIME_FILES:
        dest = VENDOR_DIR / name
        if dest.exists() and dest.stat().st_size > minimum:
            continue
        print(f"安装官方 Spine Web Player：{name}")
        # 官方 unpkg 运行时按需下载到本地，不把第三方二进制分发进 GitHub 仓库。
        content = fetch_bytes(url, timeout=90)
        if len(content) < minimum:
            raise RuntimeError(f"Spine 运行时文件异常：{name}，实际大小 {len(content)}")
        fd, temp = tempfile.mkstemp(prefix=".runtime-", dir=VENDOR_DIR)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(content)
            os.replace(temp, dest)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        print(f"安装完成：{dest.relative_to(REPOSITORY_ROOT)}")


def download_selected(mapping, target, kind="auto", refresh=False):
    data = skin_entries(mapping)
    index = catalog(refresh)
    row = data.get(str(target))
    if row is None:
        raise ValueError(f"未找到皮肤 ID {target}；先运行 list --search 角色名 查看编号")
    available = {k: catalog_matches(row, index, k) for k in ("spine", "cubism")}
    if kind == "auto":
        chosen = ["cubism"] if available["cubism"] else ["spine"]
    elif kind == "both":
        chosen = [k for k in ("cubism", "spine") if available[k]]
    else:
        chosen = [kind]
    if not chosen or any(not available[k] for k in chosen):
        raise RuntimeError(f"{target} 的 {kind} 资源目录不存在；可用类型：" +
                           ", ".join(k for k, v in available.items() if v))
    for k in chosen:
        download_asset(k, available[k])
    if "spine" in chosen:
        setup_runtime()
    return chosen


def detect_version(path):
    with path.open("rb") as handle:
        head = handle.read(96)
    match = VERSION_RE.search(head)
    return match.group(0).decode("ascii") if match else "unknown"


def collect_spine_models(mapping):
    entries = skin_entries(mapping)
    results = []
    if not DATA_DIR.is_dir():
        return results
    for folder in sorted(DATA_DIR.iterdir()):
        if not folder.is_dir() or not FOLDER_RE.fullmatch(folder.name):
            continue
        atlas_files = sorted(folder.glob("*.atlas"))
        skel_files = sorted(folder.glob("*.skel"))
        if not atlas_files or not skel_files or not list(folder.glob("*.png")):
            continue
        poses = {}
        for skel in skel_files:
            atlas = next((a for a in atlas_files if skel.stem.startswith(a.stem + "_")), atlas_files[0])
            pose = skel.stem[len(atlas.stem):].strip("_") or "default"
            poses[pose] = {
                "skel": skel.name,
                "atlas": atlas.name,
                "version": detect_version(skel),
            }
        ident = extract_id(folder.name)
        meta = entries.get(ident, {})
        results.append({
            "type": "spine",
            "id": meta.get("id") or ident or folder.name,
            "name": meta.get("name") or folder.name,
            "en": meta.get("en") or "",
            "skin": meta.get("skin") or "未匹配皮肤",
            "skin_en": meta.get("skin_en") or "",
            "folder": folder.name,
            "dir": f"../data/spine/{folder.name}",
            "poses": poses,
        })
    return results
