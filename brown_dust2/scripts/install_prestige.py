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
ALL_COSTUMES = BASE / "costume_catalog.json"
CURATED_STYLE = BASE / "curated_style.json"
INTERACTION_BATCH = BASE / "curated_interactions.json"
NEXT_BATCH = BASE / "curated_batch_20.json"
MANIFEST = BASE / "viewer" / "manifest.json"
REPORT = DATA / "install-report.json"
REPO = "myssal/Brown-Dust-2-Asset"
BRANCH = "master"
ALLOWED_EXT = {".skel", ".json", ".atlas", ".png", ".jpg", ".jpeg", ".webp"}
VALID_ROLE = {"character", "cutscene", "interaction", "interaction2"}
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
        r"spine/illust/illust_dating/illust_dating[0-9]+(?:_[12])?",
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


def read_catalog():
    """只暴露尊爵、特殊皮肤及经过外观筛选的服装，保留完整索引作资料。"""
    prestige = json.loads(CATALOG.read_text(encoding="utf-8"))["skins"]
    all_costumes = json.loads(ALL_COSTUMES.read_text(encoding="utf-8"))["skins"]
    style_entries = json.loads(CURATED_STYLE.read_text(encoding="utf-8"))["styles"]
    style_ids = [entry["id"] for entry in style_entries]
    if len(style_ids) != len(set(style_ids)):
        raise ValueError("风格精选存在重复 ID")
    style_map = {entry["id"]: entry for entry in style_entries}
    missing = set(style_ids) - {entry["id"] for entry in all_costumes}
    if missing:
        raise ValueError("风格精选映射不存在: " + ", ".join(sorted(missing)))

    selected = []
    for costume in all_costumes:
        preference = style_map.get(costume["id"])
        if costume.get("tier") != "Special Skin" and preference is None:
            continue
        item = dict(costume)
        if preference is not None:
            item["preference_tags"] = preference["tags"]
            item["preference_reason"] = preference["reason"]
        selected.append(item)
    selected.sort(key=lambda item: (
        0 if item["tier"] == "Special Skin" else 1,
        item["character_en"].casefold(),
        item["skin_en"].casefold(),
    ))
    # 独立互动第 2 批：只登记交互骨骼，不要求人物、技能演出同时存在。
    batch = json.loads(INTERACTION_BATCH.read_text(encoding="utf-8"))["skins"]
    known = {item["id"]: item for item in all_costumes}
    existing = {item["id"] for item in prestige + selected}
    batch_ids = set()
    for item in batch:
        identifier = item["id"]
        if identifier in existing or identifier in batch_ids:
            raise ValueError("独立互动精选与现有条目重复: " + identifier)
        source = known.get(identifier)
        if not source:
            raise ValueError("互动条目不在原始服装索引中: " + identifier)
        if set(item.get("roles", {})) != {"interaction"}:
            raise ValueError("互动专辑只能包含 interaction 资源: " + identifier)
        if item["roles"]["interaction"] != source["roles"].get("interaction"):
            raise ValueError("互动模型关联与来源索引不一致: " + identifier)
        if not item.get("interaction_only") or not item.get("interaction_batch"):
            raise ValueError("互动专辑缺少独立模型标记: " + identifier)
        batch_ids.add(identifier)
    newest = json.loads(NEXT_BATCH.read_text(encoding="utf-8"))["skins"]
    newest_ids = set()
    for item in newest:
        identifier = item["id"]
        if identifier in existing or identifier in batch_ids or identifier in newest_ids:
            raise ValueError("第三批与已收录资源重复: " + identifier)
        source = known.get(identifier)
        if not source:
            raise ValueError("第三批服装不在来源目录中: " + identifier)
        expected_roles = dict(source["roles"])
        if identifier == "costume-067902":
            expected_roles["interaction"] = (
                "spine/illust/illust_dating/illust_dating22_1"
            )
            expected_roles["interaction2"] = (
                "spine/illust/illust_dating/illust_dating22_2"
            )
        if item["roles"] != expected_roles:
            raise ValueError("第三批资源映射不一致: " + identifier)
        newest_ids.add(identifier)
    selected = newest + batch + selected
    ids = [item["id"] for item in prestige + selected]
    if len(ids) != len(set(ids)):
        raise ValueError("精选目录存在重复 ID")
    return prestige, selected


def select_skins(prestige, costumes, collection, only=None, character=None, limit=None,
                 offset=0):
    """所有命令只允许下载精选资源，不能误把原始 200 套全部下载。"""
    all_selected = prestige + costumes
    if only:
        selected = [skin for skin in all_selected if skin["id"] == only]
        if not selected:
            raise ValueError("不在当前精选范围的服装 ID: " + only)
    elif collection == "batch-20":
        selected = [skin for skin in costumes if skin.get("interaction_batch") == "interaction-03"]
    elif collection == "interaction-batch":
        selected = [skin for skin in costumes if skin.get("interaction_batch") == "interaction-02"]
    elif collection == "prestige":
        selected = prestige
    elif collection == "special":
        selected = prestige + [skin for skin in costumes
                               if skin["tier"] == "Special Skin"]
    elif collection in ("style", "other"):
        selected = [skin for skin in costumes if skin.get("preference_tags")]
    elif collection == "guest":
        selected = [skin for skin in costumes if skin["tier"] == "Fated Guest"]
    elif collection == "interactive":
        selected = [skin for skin in all_selected if "interaction" in skin["roles"]]
    else:
        selected = all_selected
    if character:
        query = character.casefold().strip()
        selected = [skin for skin in selected if query in
                    (skin["character"] + " " + skin["character_en"]).casefold()]
    if offset < 0:
        raise ValueError("--offset 不能是负数")
    selected = selected[offset:]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit 必须大于零")
        selected = selected[:limit]
    return selected


def interaction_state(skin):
    """来源目录和本地安装状态分别报告；不冒充真正的互动场景。"""
    path = skin.get("roles", {}).get("interaction")
    if path:
        model = inspect_model(DATA / skin["id"] / "interaction")
        return "已安装独立互动" if model else "有独立互动，待本地下载"
    if skin.get("tier") == "Special Skin":
        return "官方 Special Skin 不含独立互动"
    return "尚未发现该服装的独立互动资源"


def main(argv=None):
    prestige, costumes = read_catalog()
    parser = argparse.ArgumentParser(description="BD2 独立互动优先资源安装器")
    parser.add_argument("--plan", action="store_true", help="列举上游文件，不下载模型")
    parser.add_argument("--list", action="store_true", help="离线列出服装、模型数量与安装状态")
    parser.add_argument("--audit-interactions", action="store_true",
                        help="离线核对所有精选服装的真实独立互动情况")
    parser.add_argument("--role", choices=("character", "cutscene", "interaction", "interaction2"),
                        help="仅下载指定模型类别")
    parser.add_argument("--interaction-only", action="store_true",
                        help="只下载互动资源；同时包含 Aquila 的 interaction 与 interaction2")
    parser.add_argument("--collection",
                        choices=("batch-20", "interaction-batch", "interactive", "all", "special", "prestige", "style", "guest", "other"),
                        default="batch-20",
                        help="默认第3批20套；interaction-batch=上批8套；interactive=全部互动"))
    parser.add_argument("--character", help="按角色名筛选，例如 Eclipse / Teresse")
    parser.add_argument("--limit", type=int, help="本次最多处理的套数，建议批量安装时设置")
    parser.add_argument("--offset", type=int, default=0,
                        help="从集合第几套开始安装（0 起），与 --limit 配合分批下载")
    parser.add_argument("--source", choices=("raw", "api"), default="raw",
                        help="默认 raw 避开 GitHub API 限流")
    parser.add_argument("--verify", action="store_true", help="离线检查全部模型并重建已安装清单")
    parser.add_argument("--only", choices=[skin["id"] for skin in prestige + costumes],
                        help="仅安装指定套装，也支持 costume-xxxxxx")
    args = parser.parse_args(argv)
    if args.role and args.interaction_only:
        parser.error("--role 与 --interaction-only 不可同时使用")
    skins = prestige + costumes
    try:
        selected = select_skins(prestige, costumes, args.collection,
                                args.only, args.character, args.limit, args.offset)
    except ValueError as error:
        parser.error(str(error))
    if args.audit_interactions:
        for skin in selected:
            print(f"{skin['id']:34} {skin['character_en'][:14]:14} "
                  f"{skin['skin_en'][:24]:24} {interaction_state(skin)}")
        print("独立互动索引:", sum("interaction" in x["roles"] for x in selected),
              "/", len(selected), "套")
        return 0
    if args.list:
        for skin in selected:
            complete = [role for role in skin["roles"]
                        if inspect_model(DATA / skin["id"] / role)]
            print(f"{skin['id']:32} {skin['character_en'][:18]:18} "
                  f"{skin['skin_en'][:33]:33} "
                  f"本地 {len(complete)}/{len(skin['roles'])}")
        print("本次列表:", len(selected), "套；尊爵:", len(prestige),
              "其它:", len(costumes))
        return 0
    if args.verify:
        manifest = build_manifest(skins)
        write_json(MANIFEST, manifest)
        for skin in selected:
            roles = next((x["roles"] for x in manifest["installed"]
                          if x["id"] == skin["id"]), {})
            print(skin["id"], "有效模型:", ", ".join(roles) or "无")
        print("本地已安装至少一类资源:", len(manifest["installed"]),
              "/", len(skins))
        return 0
    failures = []
    summary = []
    for skin in selected:
        print(f"\n[{skin['id']}] {skin['character']} · {skin['skin']}")
        for role, folder in skin["roles"].items():
            if args.role is not None and role != args.role:
                continue
            if args.interaction_only and not role.startswith("interaction"):
                continue
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
