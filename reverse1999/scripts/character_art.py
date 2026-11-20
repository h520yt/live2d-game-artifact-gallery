#!/usr/bin/env python3
"""重返未来：1999 · 佩施塔（玩家常称“白雪”）真实角色原画接入。

角色原画和 skin2dbg 独立场景背景不是同一类素材。
先尝试维基原尺寸 Portrait，已验证的 315901 角色插画地址作为后备；
不使用模型截图、头像小图、其他角色或其他皮肤的背景冒充原画。
图片只下载到用户本机 reverse1999/data/character_art/，不提交至 Git。
"""
from pathlib import Path

import artwork
import spine

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "character_art"

# 来自 ArcanistMap 的已核实角色及衣着 ID。
SKINS = {
    "315901": ("佩施塔", "初始皮肤"),
    "315902": ("佩施塔", "童话出逃日"),
}

# 经资源图鉴核对：315902 的这张原始 WebP 本身包含角色和该套衣着的
# 室内楼梯场景。先取它，避免误用人物透明底或任意拼接背景。
VERIFIED_SCENE_ART = {
    "315902": "https://assets.merui.net/headicon_img/315902.webp",
}

# 315901 素材已在 Merui 角色图鉴核实为佩施塔真实人物立绘
# （1024px 级透明背景）。原尺寸维基 Portrait 优先；仅在不可用时回退。
VERIFIED_FALLBACKS = {
    "315901": ("https://assets.merui.net/headicon_img/315901.webp",),
}


def require_skin(skin_id):
    sid = str(skin_id)
    if sid not in SKINS:
        raise ValueError("仅支持已核实佩施塔衣着 ID：" + "、".join(SKINS))
    return sid


def image_file(skin_id):
    return DATA_DIR / require_skin(skin_id) / "artwork.webp"


def is_ready(skin_id):
    return artwork.exists(image_file(skin_id))


def catalog():
    return [
        {"id": int(sid), "name": name, "skin": garment,
         "artwork_downloaded": is_ready(sid)}
        for sid, (name, garment) in SKINS.items()
    ]


def download_one(skin_id):
    """从真实原始立绘图源下载并验证 WebP，失败时不登记任何新图。"""
    sid = require_skin(skin_id)
    sources = artwork.urls(sid) + VERIFIED_FALLBACKS.get(sid, ())
    candidates = ((VERIFIED_SCENE_ART[sid],) + sources
                  if sid in VERIFIED_SCENE_ART else sources)
    dest = image_file(sid)
    artwork.download(sid, dest, sources=candidates)
    if not is_ready(sid):
        raise RuntimeError(f"{sid} 原画下载后校验未通过")
    print(f"[{sid}] {SKINS[sid][0]} · {SKINS[sid][1]} 角色原画已就绪")
    return dest


def download(target):
    ids = list(SKINS) if str(target).lower() == "all" else [require_skin(target)]
    failed = []
    for sid in ids:
        try:
            download_one(sid)
        except (RuntimeError, OSError, ValueError) as error:
            print(f"[{sid}] 未安装原画：{error}")
            failed.append(f"{sid}：{error}")
    print(f"佩施塔角色原画下载：{len(ids)-len(failed)}/{len(ids)} 套")
    if failed:
        raise RuntimeError("以下原画未能核实或下载：" + "；".join(failed))


def attach_artwork(models, mapping):
    """已有模型直接附加原画，不创建第二张卡片；仅有原画也能正常入柜。"""
    lookup = spine.skin_entries(mapping)
    seen = set()
    for model in models:
        sid = str(model.get("id"))
        if sid not in SKINS or not is_ready(sid):
            continue
        model["artwork"] = f"../data/character_art/{sid}/artwork.webp"
        model["artwork_kind"] = ("character-scene-portrait"
                                 if sid in VERIFIED_SCENE_ART else "character-portrait")
        seen.add(sid)

    # 本地只有真实原画而模型还没装时，也能使用同一个衣着 ID 查看静态原画。
    for sid, (name, garment) in SKINS.items():
        if sid in seen or not is_ready(sid):
            continue
        entry = lookup.get(sid, {})
        models.append({
            "type": "artwork", "id": int(sid),
            "name": entry.get("name") or name,
            "skin": entry.get("skin") or garment,
            "en": entry.get("en") or "Perchta",
            "skin_en": entry.get("skin_en") or "",
            "folder": f"character_art_{sid}",
            "artwork": f"../data/character_art/{sid}/artwork.webp",
            "artwork_kind": ("character-scene-portrait"
                             if sid in VERIFIED_SCENE_ART else "character-portrait"),
        })
    return models
