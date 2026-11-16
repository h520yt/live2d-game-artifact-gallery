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
from pathlib import Path, PurePosixPath
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


def validate_folder(folder):
    """只允许首批配置中的三类模型根目录，不接受任意路径或路径穿越。"""
    allowed = (
        r"spine/char/char[0-9]+",
        r"spine/cutscenes/cutscene_char[0-9]+",
        r"spine/illust/illust_dating/illust_dating[0-9]+",
    )
    if not any(re.fullmatch(pattern, folder) for pattern in allowed):
        raise ValueError("目录不在白名单: " + folder)


def raw_files(folder, extras=None):
    """不调用 GitHub API：解析 atlas，并下载配置明确指定的附加背景。"""
    validate_folder(folder)
    stem = folder.rsplit("/", 1)[-1]
    atlas_name = stem + ".atlas"
    atlas_path = folder + "/" + atlas_name
    atlas_url = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/" + atlas_path
    atlas_data = request(atlas_url, binary=True)
    if not atlas_data:
        raise RuntimeError("上游 atlas 文件为空: " + atlas_path)
    pages = atlas_pages(atlas_data.decode("utf-8-sig"))
    if not pages:
        raise RuntimeError("无法从 atlas 中获取贴图页: " + atlas_path)

    filenames = [stem + ".skel", atlas_name, *pages]
    for extra in extras or []:
        # 仅允许当前资源目录下的相对背景图，禁止回退和跨目录下载。
        relative = PurePosixPath(extra)
        if (relative.is_absolute() or not relative.parts or
                any(part in (".", "..", "") for part in relative.parts) or
                relative.parts[0] != "bg" or
                relative.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}):
            raise ValueError("无效的额外背景资源路径: " + str(extra))
        filenames.append(relative.as_posix())
    records = []
    for filename in dict.fromkeys(filenames):
        path = folder + "/" + filename
        url = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/" + quote(path, safe="/")
        record = {"path": path, "size": None, "url": url}
        if filename == atlas_name:
            record["payload"] = atlas_data
            record["size"] = len(atlas_data)
        records.append(record)
    return records


def api_files(folder, root=None):
    """可选 API 模式：需要 GitHub Token，可额外取得子目录中的附加文件。"""
    root = folder if root is None else root
    validate_folder(root)
    if folder != root and not folder.startswith(root + "/"):
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
        if not path.startswith(folder + "/"):
            continue
        if item.get("type") == "dir":
            found.extend(api_files(path, root))
        elif item.get("type") == "file":
            if Path(path).suffix.lower() not in ALLOWED_EXT:
                continue
            raw_url = item.get("download_url") or ""
            if urlparse(raw_url).netloc != "raw.githubusercontent.com":
                continue
            found.append({"path": path, "size": int(item.get("size") or 0),
                          "url": raw_url})
    return found


def remote_files(folder, source="raw", extras=None):
    """默认 raw 模式不占用 API 配额，附加背景文件由收藏配置声明。"""
    validate_folder(folder)
    if source == "raw":
        return raw_files(folder, extras)
    if source == "api":
        return api_files(folder)
    raise ValueError("未知资源来源: " + str(source))


def atlas_pages(text):
    """从 atlas 中读取 PNG 等贴图页面（区域行不会以图片扩展名结尾）。"""
    pages = []
    for line in text.splitlines():
        name = line.strip().lstrip("\ufeff")
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            if (name != Path(name).name or name in (".", "..") or
                    "/" in name or "\\" in name or ":" in name):
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


def target_path(skin_id, role, remote_path, source_folder=None):
    """保留上游相对子目录，拒绝越权路径和跨角色覆盖。"""
    if role not in VALID_ROLE:
        raise ValueError("非法资源类型: " + role)
    source_folder = source_folder or str(PurePosixPath(remote_path).parent)
    validate_folder(source_folder)
    relative = PurePosixPath(remote_path).relative_to(PurePosixPath(source_folder))
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError("非法文件路径: " + remote_path)
    return DATA / skin_id / role / Path(*relative.parts)


def download_one(record, dest):
    """下载原子落盘，raw 模式不依赖上游 Content-Length 或 GitHub API。"""
    expected = record.get("size")
    if dest.is_file() and dest.stat().st_size > 0:
        if expected is None or dest.stat().st_size == expected:
            return "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = record.get("payload")
    if payload is None:
        payload = request(record["url"], binary=True)
    if not payload or (expected is not None and len(payload) != expected):
        raise RuntimeError("资源内容为空或大小不匹配: " + record["path"])
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
    parser.add_argument("--plan", action="store_true", help="列举资源文件，不下载图片或骨骼")
    parser.add_argument("--source", choices=("raw", "api"), default="raw",
                        help="默认 raw 不占用 GitHub API 配额；api 模式需有效 Token")
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
                extras = skin.get("extra_files", {}).get(role, [])
                files = remote_files(folder, args.source, extras)
                if not files or not any(record["path"].endswith(".skel") for record in files):
                    raise RuntimeError("上游未找到可用的 Spine 骨骼")
                known_bytes = sum(record["size"] or 0 for record in files)
                size_complete = all(record["size"] is not None for record in files)
                size_note = f"{known_bytes / 1024 / 1024:.1f} MiB" if size_complete else "大小未预估（raw 模式）"
                print(f"  {role}: {len(files)} 个文件, {size_note}")
                if not args.plan:
                    for record in files:
                        dest = target_path(skin["id"], role, record["path"], folder)
                        print("    ", download_one(record, dest), dest.name)
                    if not inspect_model(DATA / skin["id"] / role):
                        raise RuntimeError("atlas 引用贴图不完整，模型未通过核验")
                summary.append({"id": skin["id"], "role": role,
                                "files": len(files), "bytes": known_bytes if size_complete else None,
                                "status": "planned" if args.plan else "installed"})
            except Exception as err:
                print("  [失败]", role, err, file=sys.stderr)
                failures.append({"id": skin["id"], "role": role, "error": str(err)})
    if args.plan:
        if all(item["bytes"] is not None for item in summary):
            print("\n预计总量: %.1f MiB" % (
                sum(item["bytes"] for item in summary) / 1024 / 1024))
        else:
            print("\nraw 模式不依赖 API 文件大小信息；实际下载量请以安装结果为准。")
    else:
        write_json(MANIFEST, build_manifest(skins))
        write_json(REPORT, {"summary": summary, "failures": failures})
        print("\n已更新:", MANIFEST)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
