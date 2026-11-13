"""《重返未来：1999》商城皮肤场景素材下载与本地组合清单。

仅把已验证的同 ID 商城展示骨骼和专属背景组合预览；
不是游戏 Unity 的场景复刻，无法假定所有粒子/遮挡/交互完整。
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

import spine

ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / "data" / "scenes"
BUST_ROOT = "roles_bust"
BG_ROOT = "singlebg/skin2dbg"
BUST_PRIORITY = ("skinstorecardface", "skinstore", "skinsuit")
PNG_PATTERN = re.compile(r"(?m)^([a-zA-Z0-9_.-]+\.png)[ \t]*$")


# 313403 是已通过真实下载验证的样板。记录经过确认的原始文件路径和大小，
# 使这套场景不必向 api.github.com 请求目录树（匿名 GitHub API 容易触发 403）。
# 新资源若未人工核实，仍按原有目录扫描流程处理，不猜测角色资产关系。
VERIFIED_SCENES = {
    "313403": {
        "folder": "v4a0_313403_ble_skinstorecardface",
        "background_size": 9438795,
        "files": {
            "313403_ble_skinstorecardface.atlas": 8017,
            "313403_ble_skinstorecardface.png": 4154336,
            "313403_ble_skinstorecardface.skel": 282811,
        },
        "skeleton": "313403_ble_skinstorecardface.skel",
        "atlas": "313403_ble_skinstorecardface.atlas",
        "pages": ["313403_ble_skinstorecardface.png"],
    },
}


def verified_scene(skin_id):
    """针对核对过的商城素材构造下载清单：只访问原始文件，不调用 GitHub API。"""
    sid = str(skin_id)
    record = VERIFIED_SCENES.get(sid)
    if record is None:
        return None
    root = f"https://raw.githubusercontent.com/{spine.SOURCE}/master"
    folder = record["folder"]
    bg_name = sid + ".png"
    bg_path = f"{BG_ROOT}/{bg_name}"
    background = {
        "type": "file",
        "name": bg_name,
        "size": record["background_size"],
        "download_url": f"{root}/{bg_path}",
    }
    items = [{
        "type": "file",
        "name": name,
        "size": size,
        "path": f"{BUST_ROOT}/{folder}/{name}",
        "download_url": f"{root}/{BUST_ROOT}/{folder}/{name}",
    } for name, size in record["files"].items()]
    return {
        "id": sid,
        "folder": folder,
        "background": background,
        "items": items,
        "skeleton": record["skeleton"],
        "atlas": record["atlas"],
        "pages": list(record["pages"]),
    }


# 313403 的模型目录由上游真实文件验证，model3.json 可以列出完整的动作和贴图依赖。
# 采用同一个源库的固定目录路径，不需要 GitHub API 查询目录。
VERIFIED_LIVE2D = {
    "313403": "v4a0_313403_ble",
}


def safe_cubism_reference(value):
    """验证 model3.json 文件引用，仅允许当前 Live2D 根目录内的资源。"""
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("Live2D 引用包含非法路径")
    path = PurePosixPath(value)
    if (path.is_absolute() or len(path.parts) not in (1, 2)
            or any(not re.fullmatch(r"[a-zA-Z0-9_.-]+", part) or part in (".", "..")
                   for part in path.parts)):
        raise ValueError(f"Live2D 引用路径非法：{value!r}")
    return path.as_posix()


def cubism_references(model_json):
    """解析 Cubism 的模型、贴图、动作、表情、物理文件等完整引用。"""
    refs = model_json.get("FileReferences", {})
    files = [refs.get("Moc")]
    files.extend(refs.get("Textures") or [])
    files.extend(refs.get(key) for key in ("Physics", "Pose", "DisplayInfo", "UserData"))
    for motions in (refs.get("Motions") or {}).values():
        for entry in motions:
            files.append(entry.get("File"))
            files.append(entry.get("Sound"))
    for entry in refs.get("Expressions") or []:
        files.append(entry.get("File"))
    return sorted({safe_cubism_reference(p) for p in files if p})


def download_verified_live2d(skin_id, root):
    """从同皮肤 ID 的 Cubism 原始目录下载 model3.json 所需文件，不调用 GitHub API。"""
    folder = VERIFIED_LIVE2D.get(str(skin_id))
    if not folder:
        return None
    root_url = f"https://raw.githubusercontent.com/{spine.SOURCE}/master/live2d/roles/{folder}"
    model_filename = f"{folder}.model3.json"
    cubism_dir = root / "cubism"
    config_path = cubism_dir / model_filename
    spine.download_file(f"{root_url}/{model_filename}", config_path)
    try:
        model_json = json.loads(config_path.read_text(encoding="utf-8-sig"))
        files = cubism_references(model_json)
    except (ValueError, OSError, TypeError) as exc:
        raise RuntimeError(f"Live2D 模型配置解析失败：{exc}") from exc
    if not files or not any(f.endswith(".moc3") for f in files):
        raise RuntimeError("Live2D 模型配置缺少 moc3")
    print(f"已找到 {skin_id} 的 Cubism 动态立绘：{len(files)} 个依赖文件，含动作及表情")
    # 每个文件独立原子写入；限制并发，不影响已有 Spine 资源。
    def download_asset(path):
        return spine.download_file(f"{root_url}/{path}", cubism_dir / path)
    with ThreadPoolExecutor(max_workers=5) as pool:
        jobs = {pool.submit(download_asset, path): path for path in files}
        for job in as_completed(jobs):
            job.result()
    return f"cubism/{model_filename}"


def cubism_ready(skin_id, root, metadata):
    """只有所有 model3.json 引用完整存在，才在浏览器提供 Live2D 模式。"""
    model_path = metadata.get("cubism")
    if str(skin_id) not in VERIFIED_LIVE2D or not model_path:
        return None
    try:
        relative = safe_cubism_reference(model_path)
        if not relative.startswith("cubism/") or not relative.endswith(".model3.json"):
            return None
        config = root / relative
        model_json = json.loads(config.read_text(encoding="utf-8-sig"))
        if not all((config.parent / p).is_file() for p in cubism_references(model_json)):
            return None
        return f"../data/scenes/{skin_id}/{relative}"
    except (OSError, ValueError, TypeError):
        return None


def choose_bust_directory(tree, skin_id):
    """仅从存在商城标识的目录里选。未出现专属展示骨骼时不假定普通人物骨骼等价。"""
    sid = str(skin_id)
    if not sid.isdigit() or len(sid) != 6:
        raise ValueError("场景素材需要六位数字皮肤 ID")
    candidates = [x["path"] for x in tree if x.get("type") == "tree"
                  and spine.extract_id(x.get("path", "")) == sid]
    for suffix in BUST_PRIORITY:
        found = sorted(x for x in candidates if x.endswith("_" + suffix))
        if found:
            return found[0]
    return ""


def locate_scene_remote(skin_id):
    """对尚未核实过的皮肤，仍通过 API 检索原始商城目录。"""
    sid = str(skin_id)
    if not sid.isdigit() or len(sid) != 6:
        raise ValueError("请输入六位数字皮肤 ID")
    root = spine.fetch_json(f"{spine.API}/git/trees/master")["tree"]
    bust = next(x for x in root if x["path"] == BUST_ROOT and x["type"] == "tree")
    nodes = spine.fetch_json(f"{spine.API}/git/trees/{bust['sha']}")
    if nodes.get("truncated"):
        raise RuntimeError("商城骨骼目录列表不完整，不能自动选取")
    folder = choose_bust_directory(nodes["tree"], sid)
    if not folder:
        raise RuntimeError(f"{sid} 没找到自包含的 skinstorecardface / skinstore / skinsuit 商城骨骼目录")
    bg_files = spine.fetch_json(f"{spine.API}/contents/{BG_ROOT}")
    bg = next((x for x in bg_files if x["type"] == "file" and x["name"] == sid + ".png"), None)
    if not bg:
        raise RuntimeError(f"{sid} 没找到独立商城背景 {BG_ROOT}/{sid}.png")
    items = list(spine.github_files(f"{BUST_ROOT}/{folder}"))
    names = {x["name"] for x in items}
    skeletons = sorted(x for x in names if x.endswith(".skel"))
    atlases = sorted(x for x in names if x.endswith(".atlas"))
    if not skeletons or not atlases:
        raise RuntimeError(f"商城资源目录缺少 skel/atlas：{folder}")
    compatible = [(skel, atlas) for skel in skeletons for atlas in atlases
                  if Path(skel).stem == Path(atlas).stem]
    if not compatible:
        raise RuntimeError(f"商城资源缺少骨骼图集同名配对：{folder}")
    skeleton, atlas = compatible[0]
    atlas_info = next(x for x in items if x["name"] == atlas)
    atlas_url = atlas_info.get("download_url", "")
    if not atlas_url.startswith(f"https://raw.githubusercontent.com/{spine.SOURCE}/"):
        raise RuntimeError("非预期图集来源")
    atlas_text = spine.fetch_bytes(atlas_url).decode("utf-8-sig")
    pages = sorted(set(PNG_PATTERN.findall(atlas_text)))
    if not pages or not all(page in names for page in pages):
        raise RuntimeError("商城骨骼图集引用的贴图未全部包含在资源目录内")
    return {"id": sid, "folder": folder, "background": bg, "items": items,
            "skeleton": skeleton, "atlas": atlas, "pages": pages}



def locate_scene(skin_id):
    sid = str(skin_id)
    if not sid.isdigit() or len(sid) != 6:
        raise ValueError("请输入六位数字皮肤 ID")
    verified = verified_scene(sid)
    if verified is not None:
        print(f"使用已核实的 {sid} 商城资源清单，无需 GitHub API。")
        return verified
    return locate_scene_remote(sid)


def download_scene(mapping, skin_id):
    sid = str(skin_id)
    if sid not in spine.skin_entries(mapping):
        raise ValueError(f"皮肤 {sid} 不在角色映射中")
    found = locate_scene(sid)
    root = SCENES / sid
    root.mkdir(parents=True, exist_ok=True)
    bg = found["background"]
    url = bg.get("download_url", "")
    if not url.startswith(f"https://raw.githubusercontent.com/{spine.SOURCE}/"):
        raise RuntimeError("商城背景来源不可信")
    # bg 命名和下载路径都固定，不接受清单中的任意路径。
    spine.download_file(url, root / "background.png", int(bg.get("size") or 0))
    for item in found["items"]:
        name = item["name"]
        if not spine.FOLDER_RE.fullmatch(name) and not re.fullmatch(r"[a-zA-Z0-9_.-]+", name):
            raise RuntimeError("不安全的商城素材文件名")
        remote = item.get("download_url", "")
        if not remote.startswith(f"https://raw.githubusercontent.com/{spine.SOURCE}/"):
            raise RuntimeError("商城素材来源不可信")
        spine.download_file(remote, root / "spine" / name, int(item.get("size") or 0))
    spine.setup_runtime()
    cubism_path = download_verified_live2d(sid, root)
    # 单独保存场景来源；索引由 manifest 命令统一扫描本地数据。
    metadata = {
        "id": sid,
        "source": spine.SOURCE,
        "background_source": f"{BG_ROOT}/{sid}.png",
        "actor_source": f"{BUST_ROOT}/{found['folder']}",
        "skeleton": found["skeleton"],
        "atlas": found["atlas"],
        "pages": found["pages"],
        "composition": "local-preview",
        "cubism": cubism_path,
        "notice": "同皮肤ID背景+商城骨骼组合预览；未验证Unity全部前景、特效及交互。",
    }
    (root / "scene.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    print(f"场景素材下载完成：{sid} / {found['folder']}")
    return metadata


def collect_scenes(mapping):
    result = []
    if not SCENES.exists():
        return result
    meta = spine.skin_entries(mapping)
    for folder in sorted(SCENES.iterdir()):
        if not folder.is_dir() or not folder.name.isdigit():
            continue
        path = folder / "scene.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            skeleton = folder / "spine" / record["skeleton"]
            atlas = folder / "spine" / record["atlas"]
            background = folder / "background.png"
            pages = record["pages"]
            if not skeleton.is_file() or not atlas.is_file() or not background.is_file():
                continue
            if not all((folder / "spine" / p).is_file() for p in pages):
                continue
            version = spine.detect_version(skeleton)
            if not version.startswith("4.2."):
                print(f"场景 {folder.name} 骨骼版本 {version} 暂不兼容 4.2 播放器")
                continue
        except (OSError, ValueError, KeyError, TypeError):
            continue
        skin = meta.get(folder.name, {})
        result.append({
            "type": "scene",
            "id": skin.get("id") or folder.name,
            "name": skin.get("name") or folder.name,
            "skin": skin.get("skin") or "未知衣着",
            "en": skin.get("en") or "",
            "skin_en": skin.get("skin_en") or "",
            "folder": record.get("actor_source") or folder.name,
            "scene": {
                "background": f"../data/scenes/{folder.name}/background.png",
                "dir": f"../data/scenes/{folder.name}/spine",
                "skel": record["skeleton"],
                "atlas": record["atlas"],
                "version": version,
                "label": "商城素材组合预览（非游戏内完整复刻）",
            },
        })
        cubism_path = cubism_ready(folder.name, folder, record)
        if cubism_path:
            result.append({
                "type": "scene-live2d",
                "id": skin.get("id") or folder.name,
                "name": skin.get("name") or folder.name,
                "skin": skin.get("skin") or "未知衣着",
                "en": skin.get("en") or "",
                "skin_en": skin.get("skin_en") or "",
                "folder": VERIFIED_LIVE2D[folder.name],
                "path": cubism_path,
                "background": f"../data/scenes/{folder.name}/background.png",
                "description": "原始专属背景 + Cubism Live2D 角色动画（非全特效复刻）",
            })
    return result
