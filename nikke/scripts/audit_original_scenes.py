"""核查 NIKKE 原版 Lobby / Burst / EventScene 候选资源，不自动绑定背景。

仅报告疑似相关原始素材名与来源文件，不把普通背景与角色按名称强行配对。
读取明文 UnityFS（需要 UnityPy），NKAB 加密包跳过；还可扫描已解包 data 目录。
"""
import argparse
import json
import re
import sys
from pathlib import Path

import config as C


PATTERNS = [
    ("lobby", re.compile(r"lobby|wallpaper|livewallpaper", re.I)),
    ("burst", re.compile(r"skillcut|burst|skill_cut", re.I)),
    ("event", re.compile(r"eventscene", re.I)),
]
# 此字段仅提示从资源名解析出的可能角色 ID；不是经过核实的皮肤关联。
CHARACTER_ID = re.compile(r"(?:^|[^a-z0-9])(c\d{3}(?:_\d{2})?)(?:[^a-z0-9]|$)", re.I)
VALID_EXTRACTED = {".skel", ".atlas", ".json", ".png"}


def classify_candidate_name(name):
    """只识别含特征词的原始对象名，不猜测具体人物或皮肤。"""
    for label, pattern in PATTERNS:
        if pattern.search(name or ""):
            return label
    return None


def hinted_character_id(name):
    """ID 只作为人工复核线索，禁止直接作为皮肤→场景映射。"""
    match = CHARACTER_ID.search(name or "")
    return match.group(1).lower() if match else None


def record_asset(results, name, asset_type, source):
    category = classify_candidate_name(name)
    if not category:
        return
    results[(source, name, asset_type)] = {
        "name": name,
        "asset_type": asset_type,
        "scene_type_candidate": category,
        "character_id_hint": hinted_character_id(name),
        "source": source,
        "verified": False,
    }


def scan_extracted_directory(root, results, max_files=0):
    """对已经提取的 Spine / 场景目录建立候选索引。"""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"找不到提取目录: {root}")
    checked = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VALID_EXTRACTED:
            continue
        # 本工具只作资源名索引，不直接读取或复制任何图片。
        checked += 1
        record_asset(results, path.stem, path.suffix[1:], str(path.relative_to(root)))
        if max_files and checked >= max_files:
            break
    return {"files": checked}


def scan_cache(root, results, buckets=None, max_bundles=0):
    """只读取本地客户端明文 UnityFS 的资源对象名称，跳过加密 NKAB。"""
    try:
        import UnityPy
    except ImportError as error:
        raise RuntimeError("扫描客户端缓存需要 UnityPy；请先安装相应依赖") from error

    base = Path(root)
    naps = base if base.name.lower() == "naps" else base / "naps"
    if not naps.is_dir():
        raise FileNotFoundError(f"找不到客户端缓存 naps 目录: {naps}")
    folders = ([naps / part for part in buckets]
               if buckets else sorted(p for p in naps.iterdir() if p.is_dir()))
    counts = {"unityfs": 0, "nkab": 0, "errors": 0}
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            try:
                with path.open("rb") as stream:
                    header = stream.read(7)
            except OSError:
                counts["errors"] += 1
                continue
            if header.startswith(b"NKAB"):
                counts["nkab"] += 1
                continue
            if header != b"UnityFS":
                continue
            if max_bundles and counts["unityfs"] >= max_bundles:
                return counts
            counts["unityfs"] += 1
            try:
                env = UnityPy.load(str(path))
                for obj in env.objects:
                    # name 必须来自原始资源对象，不依赖下载的随机位置。
                    try:
                        data = obj.read()
                        name = getattr(data, "m_Name", "")
                        if isinstance(name, str) and name:
                            record_asset(results, name, obj.type.name,
                                         str(path.relative_to(naps)))
                    except Exception:
                        counts["errors"] += 1
            except Exception:
                counts["errors"] += 1
        print(f"  [核查] {folder.name}: 明文 {counts['unityfs']}，加密 {counts['nkab']}，候选 {len(results)}",
              flush=True)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="只核查真正的 NIKKE Lobby/Burst 原版场景候选")
    parser.add_argument("--from-data", action="store_true", help="扫描已提取 nikke/data 中的场景文件名")
    parser.add_argument("--scan-cache", action="store_true", help="扫描原始客户端明文 UnityFS 包")
    parser.add_argument("--cache-root", default=C.LOCAL_ASSETS, help="客户端缓存根目录")
    parser.add_argument("--buckets", nargs="+", help="只核查指定缓存桶（00-ff）")
    parser.add_argument("--max-bundles", type=int, default=200, help="缓存明文包扫描上限，0 为全部")
    parser.add_argument("--max-files", type=int, default=0, help="已提取文件扫描上限，0 为全部")
    args = parser.parse_args(argv)
    if not args.from_data and not args.scan_cache:
        parser.error("至少指定 --from-data 或 --scan-cache")
    if args.max_bundles < 0 or args.max_files < 0:
        parser.error("扫描上限不能为负数")

    results = {}
    stats = {}
    if args.from_data:
        stats["extracted"] = scan_extracted_directory(C.DATA_DIR, results, args.max_files)
    if args.scan_cache:
        stats["cache"] = scan_cache(args.cache_root, results, args.buckets, args.max_bundles)

    destination = Path(C.DATA_DIR) / "_original_scene_candidates.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "notice": "候选资源，不代表任何皮肤/背景已经核实配对；不得自动写入 scene_bindings.json。",
        "stats": stats,
        "candidates": sorted(results.values(), key=lambda x: (x["scene_type_candidate"], x["name"], x["source"]))
    }
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"发现候选 {len(results)} 条 -> {destination}")
    print("候选只用于人工核实游戏原始资源中的实际场景，不会修改现有展示柜绑定。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
