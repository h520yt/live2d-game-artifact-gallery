"""只补齐已安装皮肤的背景/前景分层，不重新下载 Live2D。

在仓库根目录：
  python azur_lane/scripts/install_scene_layers.py --plan
  python azur_lane/scripts/install_scene_layers.py
  python azur_lane/scripts/install_scene_layers.py --only baifeng_3 hu_2
  python azur_lane/scripts/install_scene_layers.py --geometry  # 可选：重建人物/背景坐标数据
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import config as C
from gen_manifest import generate, load_skin_map, split_suffixes
from install_batch2 import (
    SCENE_PART_TOKENS, download_selection, painting_output,
    painting_rows, parse_csv, valid_png,
)

SCRIPT_DIR = Path(__file__).resolve().parent


def installed_assets() -> set[str]:
    """只依据磁盘上真实存在的角色 PNG，避免给清单中的过期皮肤制造孤儿背景。"""
    known = load_skin_map()
    result = set()
    for path in Path(C.PAINTINGS_DIR).glob("*.png"):
        base, kind = split_suffixes(path.stem)
        if kind != "part" and base in known:
            result.add(base)
    return result


def is_scene_layer(row, asset: str) -> bool:
    suffix = row.path[len("painting/" + asset):-len("_tex")]
    tokens = suffix.lstrip("_").split("_")
    return any(t.rstrip("0123456789") in SCENE_PART_TOKENS for t in tokens)


def select_rows(rows, assets: set[str], *, geometry: bool = False):
    """仅选同皮肤的 _bj / _front 等分层。可选补齐人物 Mesh 坐标。"""
    selected = {}
    for asset in sorted(assets):
        for row in painting_rows(rows, asset):
            if is_scene_layer(row, asset):
                selected[row.path] = row
            elif geometry:
                # 完整场景校准：已有角色文件但没有 Mesh 坐标时，重新提取元数据。
                image = painting_output(row, Path(C.PAINTINGS_DIR))
                if valid_png(image) and not image.with_suffix(".meta.json").exists():
                    selected[row.path] = row
    return list(selected.values())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="补齐当前展柜已安装皮肤的背景/前景")
    parser.add_argument("--plan", action="store_true", help="仅列出待下载资源")
    parser.add_argument("--only", nargs="+", metavar="ASSET", help="只处理指定皮肤资源名")
    parser.add_argument("--geometry", action="store_true", help="补齐已有角色立绘的 Mesh 坐标数据")
    parser.add_argument("--force", action="store_true", help="重建所选分层 PNG")
    args = parser.parse_args(argv)

    available = installed_assets()
    selected = available
    if args.only:
        unknown = set(args.only) - available
        if unknown:
            parser.error("这些皮肤尚未在本地安装主立绘：" + ", ".join(sorted(unknown)))
        selected = set(args.only)
    if not selected:
        print("未找到已安装角色立绘：先安装皮肤，或检查 azur_lane/data/paintings/。")
        return 0 if args.plan else 1

    rows = parse_csv(Path(C.HASHES_DIR) / "PAINTING.csv")
    targeted = select_rows(rows, selected, geometry=args.geometry)
    output_dir = Path(C.PAINTINGS_DIR)
    pending = [
        row for row in targeted
        if args.force or not valid_png(painting_output(row, output_dir))
    ]
    missing_bg = {
        asset for asset in selected
        if not any(is_scene_layer(row, asset) and
                   any(token in row.path for token in ("_bj", "_bg", "_back"))
                   for row in targeted)
    }
    print(f"已安装皮肤 {len(selected)} 款，匹配分层/坐标包 {len(targeted)} 个，待重建 {len(pending)} 个")
    print(f"待处理下载体积上限 {sum(row.size for row in pending) / 1024 / 1024:.1f} MiB（缓存可复用）")
    if missing_bg:
        print("官方索引中未发现专属背景的皮肤：" + ", ".join(sorted(missing_bg)))
    if args.plan:
        for row in pending:
            print("  " + row.path)
        return 0
    if not pending:
        generate()
        print("场景分层已齐，已刷新画廊清单")
        return 0

    cache = Path(C.CACHE_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    failed_downloads = {row.path for row in download_selection("场景分层 PAINTING", pending, cache)}
    errors = {}
    for row in pending:
        if row.path in failed_downloads:
            errors[row.path] = "download_or_md5_failed"
            continue
        output = painting_output(row, output_dir)
        temporary = output.with_name(f".{output.stem}.scene.tmp.png")
        temporary.unlink(missing_ok=True)
        temporary.with_suffix(".meta.json").unlink(missing_ok=True)
        source = cache.joinpath(*row.path.split("/"))
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "rebuild_painting.py"), str(source), str(temporary)],
            check=False
        )
        if result.returncode or not valid_png(temporary):
            errors[row.path] = f"rebuild_failed_{result.returncode}"
            temporary.unlink(missing_ok=True)
            temporary.with_suffix(".meta.json").unlink(missing_ok=True)
            print(f"  [失败] {row.path}")
            continue
        os.replace(temporary, output)
        temp_meta = temporary.with_suffix(".meta.json")
        if temp_meta.exists():
            os.replace(temp_meta, output.with_suffix(".meta.json"))
        print(f"  [完成] {output.name}")

    generate()
    report = {
        "installed_skins": len(selected),
        "selected_resources": len(targeted),
        "built_resources": len(pending) - len(errors),
        "errors": errors,
        "missing_dedicated_background": sorted(missing_bg),
    }
    report_path = Path(C.DATA_DIR) / "scene-layer-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：失败 {len(errors)} 项，报告 {report_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
