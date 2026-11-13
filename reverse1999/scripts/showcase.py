#!/usr/bin/env python3
"""《重返未来：1999》商城衣着分层预览资源。

仅对已核实存在的同皮肤资源建立组合关系；不使用任意活动背景冒充商城场景。
本地下载数据不纳入 Git，配方可以逐个验证后再扩展。
"""
import json
import re
from pathlib import Path, PurePosixPath

import spine

SCENE_DIR = Path(__file__).resolve().parents[1] / "data" / "showcase"
SCENES = {
    # 露西「生如行棋」：两处来源均直接以衣着 ID 308603 命名。
    # 这是网页分层预览，不保证 Unity 场景脚本/粒子、机位参数 1:1 还原。
    "308603": {
        "background": "singlebg/skin2dbg/308603.png",
        "foreground": "roles_bust/v2a8_308603_lxxx_skinstore",
        "description": "衣着关联背景 + 商城 Spine 展示动作（非游戏客户端逐帧复刻）",
        "pose": "商城展示",
        "display": {"fit": "cover", "scale": 1.8},
    },
}
ID_RE = re.compile(r"^\d{6}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def safe_scene_id(value):
    sid = str(value)
    if not ID_RE.fullmatch(sid):
        raise ValueError("衣着 ID 必须是六位数字")
    if sid not in SCENES:
        raise ValueError(f"尚未核实 {sid} 的完整展示资源，目前支持：{', '.join(sorted(SCENES))}")
    return sid


def validate_recipe(sid, recipe):
    """检查配置只能访问本项目指定的上游资源路径。"""
    bg = recipe["background"]
    fg = recipe["foreground"]
    if bg != f"singlebg/skin2dbg/{sid}.png":
        raise ValueError("背景必须由同一皮肤 ID 对应，禁止跨皮肤配图")
    parts = PurePosixPath(fg).parts
    if len(parts) != 2 or parts[0] != "roles_bust" or sid not in parts[1] or not spine.FOLDER_RE.fullmatch(parts[1]):
        raise ValueError("商城展示 Spine 目录不合法或与皮肤 ID 不匹配")
    return bg, fg


def validate_resource_pair(directory):
    skels = sorted(directory.glob("*.skel"))
    atlases = sorted(directory.glob("*.atlas"))
    pngs = list(directory.glob("*.png"))
    if not skels or not atlases or not pngs:
        raise RuntimeError("展示动画缺少 .skel/.atlas/.png")
    # 同名 .skel 和 .atlas，避免误用不同皮肤的图集。
    pairs = [(s, directory / (s.stem + ".atlas")) for s in skels if (directory / (s.stem + ".atlas")).is_file()]
    if not pairs:
        raise RuntimeError("展示动画骨骼与图集不匹配")
    return pairs[0]


def download_showcase(mapping, skin_id):
    sid = safe_scene_id(skin_id)
    record = spine.skin_entries(mapping).get(sid)
    if not record:
        raise RuntimeError(f"角色映射中不存在衣着 {sid}")
    bg, fg = validate_recipe(sid, SCENES[sid])
    folder = SCENE_DIR / sid
    foreground = folder / "foreground"

    # 核查精确文件路径，再下载；API 只用于取得 GitHub 文件元信息。
    background = spine.fetch_json(f"{spine.API}/contents/{bg}")
    if not isinstance(background, dict) or background.get("type") != "file":
        raise RuntimeError(f"没有找到衣着专属背景：{bg}")
    url = background.get("download_url") or ""
    if not url.startswith(f"https://raw.githubusercontent.com/{spine.SOURCE}/"):
        raise RuntimeError("背景下载地址不可信")

    files = list(spine.github_files(fg))
    if not files:
        raise RuntimeError(f"找不到衣着商城动画目录：{fg}")
    names = [file["name"] for file in files]
    if not any(n.endswith(".skel") for n in names) or not any(n.endswith(".atlas") for n in names) or not any(n.endswith(".png") for n in names):
        raise RuntimeError("上游商城动画目录缺少核心文件")

    # 原子下载：单个文件只有经过长度检查才会替换已有文件。
    spine.download_file(url, folder / "background.png", int(background.get("size") or 0))
    prefix = fg + "/"
    for file in files:
        name = file["path"]
        if not name.startswith(prefix):
            raise RuntimeError("衣着资源路径越界")
        relative = PurePosixPath(name[len(prefix):])
        if relative.is_absolute() or len(relative.parts) != 1 or not spine.FOLDER_RE.fullmatch(relative.stem):
            # 对这套样板只允许单层的安全文件名。
            raise RuntimeError(f"不安全的衣着资源文件：{name}")
        asset_url = file.get("download_url") or ""
        if not asset_url.startswith(f"https://raw.githubusercontent.com/{spine.SOURCE}/"):
            raise RuntimeError(f"非预期的资源服务器：{asset_url}")
        spine.download_file(asset_url, foreground / relative.name, int(file.get("size") or 0))

    skel, atlas = validate_resource_pair(foreground)
    with (folder / "background.png").open("rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise RuntimeError("商城背景不是有效的 PNG 文件")
    version = spine.detect_version(skel)
    if not version.startswith("4.2."):
        raise RuntimeError(f"商城展示骨骼版本是 Spine {version}，目前仅支持 4.2")
    spine.setup_runtime()
    print(f"皮肤展示资源准备完成：{record['name']} · {record['skin']} (ID {sid})")
    print(f"背景：{bg}；人物：{fg}；动画版本：{version}")
    return sid


def collect_showcases(mapping):
    lookup = spine.skin_entries(mapping)
    results = []
    for sid, spec in sorted(SCENES.items()):
        if sid not in lookup:
            continue
        validate_recipe(sid, spec)
        folder = SCENE_DIR / sid
        foreground = folder / "foreground"
        background = folder / "background.png"
        if not foreground.is_dir() or not background.is_file():
            continue
        with background.open("rb") as handle:
            if handle.read(8) != PNG_SIGNATURE:
                continue
        try:
            skel, atlas = validate_resource_pair(foreground)
        except RuntimeError:
            continue
        version = spine.detect_version(skel)
        if not version.startswith("4.2."):
            continue
        entry = lookup[sid]
        results.append({
            "type": "showcase",
            "id": entry["id"],
            "name": entry["name"],
            "en": entry["en"],
            "skin": entry["skin"],
            "skin_en": entry["skin_en"],
            "folder": sid,
            "dir": f"../data/showcase/{sid}/foreground",
            "background": f"../data/showcase/{sid}/background.png",
            "description": spec["description"],
            "display": spec["display"],
            "poses": {spec["pose"]: {
                "skel": skel.name,
                "atlas": atlas.name,
                "version": version,
            }},
        })
    return results
