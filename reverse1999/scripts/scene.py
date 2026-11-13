"""《重返未来：1999》商城皮肤场景素材下载与本地组合清单。

仅把已验证的同 ID 商城展示骨骼和专属背景组合预览；
不是游戏 Unity 的场景复刻，无法假定所有粒子/遮挡/交互完整。
"""
import json
import re
from pathlib import Path

import spine

ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / "data" / "scenes"
BUST_ROOT = "roles_bust"
BG_ROOT = "singlebg/skin2dbg"
BUST_PRIORITY = ("skinstorecardface", "skinstore", "skinsuit")
PNG_PATTERN = re.compile(r"(?m)^([a-zA-Z0-9_.-]+\.png)[ \t]*$")


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


def locate_scene(skin_id):
    """确认背景文件和商城动画资源分别真实存在。"""
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
    return result
