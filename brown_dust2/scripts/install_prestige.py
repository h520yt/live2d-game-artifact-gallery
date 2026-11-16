#!/usr/bin/env python3
"""棕色尘埃2 Prestige Skin 首批资源本地安装器（不提交素材）。"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
CATALOG = BASE / "curated_prestige.json"
MANIFEST = BASE / "viewer" / "manifest.json"
REPORT = DATA / "install-report.json"
REPO = "myssal/Brown-Dust-2-Asset"
BRANCH = "master"
ALLOWED_EXT = {".skel", ".json", ".atlas", ".png", ".jpg", ".jpeg", ".webp"}
VALID_ROLE = {"character", "cutscene", "interaction"}
VERSION = re.compile(rb"([34]\.\d+\.\d+)")
AGENT = "Personal-RD-Lab-BD2-Installer/1.0"


def request(url, binary=False):
    """GitHub 域名白名单下载；支持令牌与瞬时网络错误重试。"""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in (
        "api.github.com", "raw.githubusercontent.com"
    ):
        raise ValueError("禁止从未知资源域名下载: " + url)
    headers = {"User-Agent": AGENT, "Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token and parsed.netloc == "api.github.com":
        headers["Authorization"] = "Bearer " + token
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=45) as response:
                return response.read() if binary else json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as err:
            last_error = err
            if isinstance(err, HTTPError) and err.code in (403, 404):
                break
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"{url}: {last_error}")


def remote_files(folder, root=None):
    """递归取得上游目录文件，包含 cutscene/bg，且不能越过指定根目录。"""
    root = folder if root is None else root
    if not root.startswith(("spine/char/", "spine/cutscenes/",
                            "spine/illust/illust_dating/")):
        raise ValueError("目录不在白名单: " + root)
    if folder != root and not folder.startswith(root.rstrip("/") + "/"):
        raise ValueError("超出下载目录: " + folder)
    url = ("https://api.github.com/repos/" + REPO +
           "/contents/" + quote(folder, safe="/") +
           "?" + urlencode({"ref": BRANCH}))
    result = request(url)
    if not isinstance(result, list):
        raise ValueError("上游目录响应不是文件列表: " + folder)
    found = []
    for item in result:
        path = item.get("path", "")
        if not path.startswith(folder.rstrip("/") + "/"):
            continue
        if item.get("type") == "dir":
            found.extend(remote_files(path, root))
        elif item.get("type") == "file":
            if Path(path).suffix.lower() not in ALLOWED_EXT:
                continue
            raw_url = item.get("download_url") or ""
            if urlparse(raw_url).netloc != "raw.githubusercontent.com":
                continue
            found.append({"path": path, "size": int(item.get("size") or 0),
                          "url": raw_url})
    return found


def atlas_pages(text):
    """从 atlas 中读取 PNG 等贴图页面（区域行不会以图片扩展名结尾）。"""
    pages = []
    for line in text.splitlines():
        name = line.strip().lstrip("\ufeff")
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            if name != Path(name).name or name in (".", ".."):
                raise ValueError("不安全的图片页名称: " + name)
            if name not in pages:
                pages.append(name)
    return pages


def inspect_model(folder):
    """模型必须拥有非空 skel / atlas / 完整 atlas 贴图页才算安装。"""
    if not folder.is_dir():
        return None
    for skeleton in sorted(folder.glob("*.skel")):
        atlas = skeleton.with_suffix(".atlas")
        if not atlas.is_file() or skeleton.stat().st_size == 0:
            continue
        if atlas.stat().st_size == 0:
            continue
        try:
            pages = atlas_pages(atlas.read_text(encoding="utf-8-sig"))
            if not pages:
                continue
            if any(not (folder / page).is_file() or
                   (folder / page).stat().st_size == 0 for page in pages):
                continue
            with skeleton.open("rb") as handle:
                head = handle.read(100)
            version = VERSION.search(head)
            detected = ".".join(version.group(1).decode().split(".")[:2]) if version else "4.1"
            return {"skel": skeleton.name, "atlas": atlas.name,
                    "pages": pages, "version": detected}
        except (OSError, UnicodeError, ValueError):
            continue
    return None


def target_path(skin_id, role, remote_path):
    """上游文件名映射到隔离的本地目录。"""
    if role not in VALID_ROLE:
        raise ValueError("非法资源类型: " + role)
    filename = Path(remote_path).name
    if filename in ("", ".", ".."):
        raise ValueError("非法文件名")
    return DATA / skin_id / role / filename


def download_one(record, dest):
    """相同大小文件直接缓存命中；临时文件写入后原子替换。"""
    expected = record["size"]
    if expected > 0 and dest.is_file() and dest.stat().st_size == expected:
        return "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = request(record["url"], binary=True)
    if expected <= 0 or len(payload) != expected:
        raise RuntimeError("资源大小不匹配: " + record["path"])
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as handle:
            tmp_name = handle.name
            handle.write(payload)
        os.replace(tmp_name, dest)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return "downloaded"


def build_manifest(skins):
    """清单只记录已存在且通过完整性检测的真实模型。"""
    installed = []
    for skin in skins:
        roles = {}
        for role in skin["roles"]:
            model = inspect_model(DATA / skin["id"] / role)
            if model:
                model["dir"] = "../data/" + quote(skin["id"]) + "/" + quote(role)
                roles[role] = model
        if roles:
            installed.append({"id": skin["id"], "roles": roles})
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "installed": installed}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def main(argv=None):
    skins = json.loads(CATALOG.read_text(encoding="utf-8"))["skins"]
    parser = argparse.ArgumentParser(description="BD2 Prestige Skin 六款首批本地安装")
    parser.add_argument("--plan", action="store_true", help="列举文件与大小，不下载")
    parser.add_argument("--verify", action="store_true", help="离线核验并重建清单")
    parser.add_argument("--only", choices=[skin["id"] for skin in skins],
                        help="仅安装指定皮肤")
    args = parser.parse_args(argv)
    selected = [skin for skin in skins if not args.only or skin["id"] == args.only]
    if args.verify:
        manifest = build_manifest(skins)
        write_json(MANIFEST, manifest)
        for skin in selected:
            roles = next((x["roles"] for x in manifest["installed"]
                          if x["id"] == skin["id"]), {})
            print(skin["id"], "有效模型:", ", ".join(roles) or "无")
        return 0
    failures = []
    summary = []
    for skin in selected:
        print(f"\n[{skin['id']}] {skin['character']} · {skin['skin']}")
        for role, folder in skin["roles"].items():
            try:
                files = remote_files(folder)
                if not files or not any(record["path"].endswith(".skel") for record in files):
                    raise RuntimeError("上游未找到可用的 Spine 骨骼")
                total = sum(record["size"] for record in files)
                print(f"  {role}: {len(files)} 个文件, {total / 1024 / 1024:.1f} MiB")
                if not args.plan:
                    for record in files:
                        dest = target_path(skin["id"], role, record["path"])
                        print("    ", download_one(record, dest), dest.name)
                    if not inspect_model(DATA / skin["id"] / role):
                        raise RuntimeError("atlas 引用贴图不完整，模型未通过核验")
                summary.append({"id": skin["id"], "role": role,
                                "files": len(files), "bytes": total,
                                "status": "planned" if args.plan else "installed"})
            except Exception as err:
                print("  [失败]", role, err, file=sys.stderr)
                failures.append({"id": skin["id"], "role": role, "error": str(err)})
    if args.plan:
        print("\n预计总量: %.1f MiB" % (
            sum(item["bytes"] for item in summary) / 1024 / 1024))
    else:
        write_json(MANIFEST, build_manifest(skins))
        write_json(REPORT, {"summary": summary, "failures": failures})
        print("\n已更新:", MANIFEST)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
