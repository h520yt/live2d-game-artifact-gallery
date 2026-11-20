"""为 NIKKE 展柜生成静态人物＋背景卡片预览（不是官方原始配套海报）。

运行前先准备已安装的背景及透明人物图（art.png 或 art_render.png）。
不修改骨骼，不上传美术素材，输出位于 git 忽略的 nikke/data/。
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

import config as C


ROOT = Path(C.DATA_DIR)
MANIFEST = Path(C.MANIFEST_PATH)
IMAGE_FILES = ("art.png", "art.webp", "art.jpg", "art_render.png")
DEFAULT_BACKGROUNDS = ("CommanderRoom.png", "Ark.png", "Office.png")
SIZE = (720, 1080)


def select_background(character, backgrounds):
    """经验证配置优先，其次通用场景。不给没有证据的皮肤伪造官方背景。"""
    if not backgrounds:
        return None
    verified = (character.get("scene") or {}).get("filename")
    if verified and verified in backgrounds:
        return backgrounds[verified]
    for filename in DEFAULT_BACKGROUNDS:
        if filename in backgrounds:
            return backgrounds[filename]
    return next(iter(backgrounds.values()))


def find_art(character_id):
    """优先真实透明的 Spine 导出帧；不要把不透明原画再叠到背景上。"""
    directory = ROOT / character_id
    for filename in ("art_render.png", "art.png", "art.webp", "art.jpg"):
        candidate = directory / filename
        if not candidate.is_file() or candidate.stat().st_size == 0:
            continue
        try:
            with Image.open(candidate) as image:
                if image.mode not in ("RGBA", "LA", "P"):
                    continue
                alpha = image.convert("RGBA").getchannel("A")
                if alpha.getextrema()[0] == 255:
                    continue
            return candidate
        except OSError:
            continue
    return None


def compose_preview(background_path, character_path, destination, *, size=SIZE):
    """背景按 cover 裁切；透明角色自适应缩放到 92% 高度并靠近画面下部。"""
    with Image.open(background_path) as source:
        bg = ImageOps.fit(source.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    with Image.open(character_path) as source:
        portrait = ImageOps.exif_transpose(source.convert("RGBA"))
    bbox = portrait.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("角色图片透明，没有可渲染人物")
    portrait = portrait.crop(bbox)
    max_width, max_height = int(size[0] * .94), int(size[1] * .92)
    scale = min(max_width / portrait.width, max_height / portrait.height)
    dimensions = (max(1, round(portrait.width * scale)), max(1, round(portrait.height * scale)))
    portrait = portrait.resize(dimensions, Image.Resampling.LANCZOS)
    x = (size[0] - portrait.width) // 2
    y = max(0, int(size[1] * .96) - portrait.height)
    bg.paste(portrait, (x, y), portrait)
    destination.parent.mkdir(parents=True, exist_ok=True)
    bg.save(destination, "WEBP", quality=88, method=4)


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成 NIKKE 角色+背景合成预览")
    parser.add_argument("--all", action="store_true", help="对全部已安装角色生成预览")
    parser.add_argument("--only", nargs="+", default=[], help="只处理指定资源 ID")
    parser.add_argument("--force", action="store_true", help="覆盖既有场景预览")
    parser.add_argument("--plan", action="store_true", help="仅输出预览计划")
    args = parser.parse_args(argv)
    if args.all and args.only:
        parser.error("--all 与 --only 不能同时使用")

    if not MANIFEST.is_file():
        print("清单不存在，请先执行 python nikke/scripts/gen_nikke_manifest.py")
        return 1
    with MANIFEST.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    installed = {x["filename"]: ROOT / "backgrounds" / x["filename"]
                 for x in manifest.get("backgrounds", [])
                 if x.get("filename") and (ROOT / "backgrounds" / x["filename"]).is_file()}
    if not installed:
        print("没有背景图片，请先运行 install_backgrounds.py")
        return 1

    wanted = set(args.only)
    characters = [c for c in manifest.get("characters", []) if c.get("category") == "character"]
    if not args.all:
        if not wanted:
            parser.error("需要 --all 或 --only <资源ID ...>")
        missing = wanted - {c["id"] for c in characters}
        if missing:
            print("清单缺少角色:", ", ".join(sorted(missing)))
            return 1
        characters = [c for c in characters if c["id"] in wanted]

    stats = {"ready": 0, "skipped": 0, "missing_art": 0, "failed": 0}
    for character in characters:
        cid = character["id"]
        art = find_art(cid)
        if not art:
            print(f"[缺少透明角色图] {cid}，先用 render_art.mjs 导出")
            stats["missing_art"] += 1
            continue
        bg = select_background(character, installed)
        dest = ROOT / cid / "scene_preview.webp"
        if dest.exists() and not args.force:
            stats["skipped"] += 1
            continue
        if args.plan:
            print(f"[计划] {cid}: {art.name} + {bg.name}")
            stats["ready"] += 1
            continue
        try:
            compose_preview(bg, art, dest)
            stats["ready"] += 1
            print(f"[完成] {cid}: {art.name} + {bg.name}")
        except (OSError, ValueError) as error:
            stats["failed"] += 1
            print(f"[失败] {cid}: {error}")

    print("生成统计:", json.dumps(stats, ensure_ascii=False))
    if not args.plan:
        from gen_nikke_manifest import main as rebuild
        rebuild()
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
