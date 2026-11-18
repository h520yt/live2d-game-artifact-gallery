"""按需安装碧蓝航线第二批指定换装（不下载整个资源库）。

仅使用项目现有工具：dl_from_csv / rebuild_painting / build / gen_manifest。
官方标记“动态立绘/特殊动态”的换装，若本地 L2D.csv 无对应包，
当前只还原可查看的静态立绘，不假定动效已还原。

在仓库根目录执行：
    python azur_lane/scripts/install_batch2.py --plan
    python azur_lane/scripts/install_batch2.py
    python azur_lane/scripts/install_batch2.py --refresh
    python azur_lane/scripts/install_batch2.py --only guanghui_9 baifeng_3
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
AZL_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = AZL_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from gallery_core.collections import load_skin_batch
from gallery_core.storage import file_ready


@dataclass(frozen=True)
class Skin:
    character: str
    title: str
    asset: str
    skin_id: int
    category: str  # live2d_plus | special_dynamic | dynamic


BATCH = tuple(
    Skin(**item) for item in load_skin_batch(
        PROJECT_ROOT / "azur_lane/config/curated_collections.json", "batch2"
    )
)

# 主立绘和换装变体；背景/前景属于同一皮肤的场景分层，也需要安装。
PAINT_VARIANTS = frozenset({
    "", "_n", "_rw", "_n_rw", "_hx", "_n_hx", "_rw_hx", "_n_rw_hx",
    "_g", "_n_g", "_rw_g", "_n_rw_g",
})

# 支持官方分层资源命名：hu_2_bj / hu_2_n_bj_hx / xxx_front。
# 不含任意未知后缀，也不会把 hu_20 误匹配为 hu_2。
SCENE_PART_TOKENS = frozenset({
    "bj", "bg", "front", "back", "middle", "mid",
    "shadow", "dark", "effect", "light", "wjz", "jz", "pt",
})
VARIANT_TOKENS = frozenset({"n", "rw", "hx", "g", "ex", "hd", "bh", "h", "p", "d"})


@dataclass(frozen=True)
class AssetRow:
    path: str
    size: int
    md5: str


def parse_csv(path: Path) -> list[AssetRow]:
    if not path.exists():
        raise FileNotFoundError(f"找不到资源清单：{path}，请先执行 python azur_lane/scripts/fetch_manifests.py")
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 3:
                name, size, md5 = parts[:3]
                if size.isdecimal() and len(md5) == 32:
                    rows.append(AssetRow(name.replace("\\", "/"), int(size), md5.lower()))
    return rows


def painting_rows(rows: list[AssetRow], asset: str) -> list[AssetRow]:
    prefix = f"painting/{asset}"
    result = []
    for row in rows:
        if not row.path.startswith(prefix) or not row.path.endswith("_tex"):
            continue
        variant = row.path[len(prefix):-len("_tex")]
        tokens = variant.lstrip("_").split("_") if variant.startswith("_") else []
        # 无后缀 / 正常角色变体，或包含明确场景层且其它字段都是已知变体。
        is_scene_part = (bool(tokens) and any(t.rstrip("0123456789") in SCENE_PART_TOKENS for t in tokens)
                         and all(t in VARIANT_TOKENS or t.rstrip("0123456789") in SCENE_PART_TOKENS for t in tokens))
        if variant in PAINT_VARIANTS or is_scene_part:
            result.append(row)
    return sorted(result, key=lambda x: x.path)


def live2d_rows(rows: list[AssetRow], asset: str) -> list[AssetRow]:
    prefix = f"live2d/{asset}"
    return sorted((r for r in rows if r.path == prefix or r.path.startswith(prefix + "_")), key=lambda x: x.path)


def painting_output(row: AssetRow, dest_dir: Path) -> Path:
    filename = Path(row.path).name
    if not filename.endswith("_tex"):
        raise ValueError(f"不是绘画资源包：{row.path}")
    return dest_dir / (filename[:-4] + ".png")


def check_hash(row: AssetRow, cache_root: Path) -> bool:
    """使用公共流式 MD5 校验缓存文件，官方清单仍是唯一哈希来源。"""
    file = cache_root.joinpath(*row.path.split("/"))
    return file_ready(file, expected_size=row.size, expected_md5=row.md5)


def valid_png(path: Path) -> bool:
    """先验证 PNG 文件头，避免将旧的空文件误认作成功立绘。"""
    try:
        with path.open("rb") as fp:
            return fp.read(8) == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def valid_live2d_model(model_dir: Path, name: str) -> bool:
    """有效模型至少需要 settings、MOC3 以及全部贴图。"""
    try:
        model3 = model_dir / f"{name}.model3.json"
        refs = json.loads(model3.read_text(encoding="utf-8"))["FileReferences"]
        moc = refs.get("Moc")
        textures = refs.get("Textures")
        if not isinstance(moc, str) or not moc or not isinstance(textures, list) or not textures:
            return False
        with (model_dir / moc).open("rb") as fp:
            if fp.read(4) != b"MOC3":
                return False
        return all(isinstance(t, str) and t and (model_dir / t).is_file()
                   and (model_dir / t).stat().st_size > 0 for t in textures)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def pick_skins(only: list[str] | None, batch: tuple[Skin, ...] | None = None) -> list[Skin]:
    skins = BATCH if batch is None else batch
    if not only:
        return list(skins)
    wanted = set(only)
    selected = [s for s in skins if s.asset in wanted or str(s.skin_id) in wanted or s.character in wanted]
    found = {key for s in selected for key in (s.asset, str(s.skin_id), s.character)}
    unknown = wanted - found
    if unknown:
        raise ValueError(f"未识别的皮肤：{', '.join(sorted(unknown))}")
    return selected


def download_selection(label: str, rows: list[AssetRow], cache_dir: Path) -> list[AssetRow]:
    if not rows:
        return []
    from dl_from_csv import download
    download([label], verify=True, only={r.path for r in rows})
    missing = [row for row in rows if not check_hash(row, cache_dir)]
    if missing:
        print(f"  [错误] {label} 有 {len(missing)} 个资源未通过文件/md5 校验", flush=True)
        for row in missing[:15]:
            print(f"    - {row.path}", flush=True)
    return missing


def main(argv: list[str] | None = None, *, batch: tuple[Skin, ...] | None = None,
         batch_key: str = "batch2", batch_label: str = "第二批",
         gallery_page: str = "batch2.html") -> int:
    """公共批次安装入口：batch2 默认行为保持不变，其他批次传入独立目录与报告名。"""
    skins = BATCH if batch is None else batch
    parser = argparse.ArgumentParser(description=f"碧蓝航线{batch_label} {len(skins)} 款皮肤按需安装")
    parser.add_argument("--plan", action="store_true", help="只核对目录、资源类型、下载规模，不修改文件")
    parser.add_argument("--refresh", action="store_true", help="更新皮肤元数据和官方资源清单")
    parser.add_argument("--only", nargs="+", metavar="NAME", help="只安装指定资源名/skin ID/角色名")
    parser.add_argument("--force-paintings", action="store_true", help="已有 PNG 也重新还原")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPT_DIR))
    import config as C

    try:
        selected = pick_skins(args.only, batch=skins)
    except ValueError as exc:
        parser.error(str(exc))

    if args.plan and args.refresh:
        parser.error("--plan 为纯只读检查，不能与 --refresh 同时使用")

    if args.refresh:
        from fetch_metadata import fetch as fetch_metadata
        from fetch_manifests import fetch as fetch_manifests
        fetch_metadata()
        fetch_manifests()

    csv_dir = Path(C.HASHES_DIR)
    try:
        paint_csv = parse_csv(csv_dir / "PAINTING.csv")
        live_csv = parse_csv(csv_dir / "L2D.csv")
    except (FileNotFoundError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    plans = []
    paint_all: dict[str, AssetRow] = {}
    model_all: dict[str, AssetRow] = {}
    for skin in selected:
        paints = painting_rows(paint_csv, skin.asset)
        models = live2d_rows(live_csv, skin.asset)
        plans.append((skin, paints, models))
        paint_all.update({row.path: row for row in paints})
        model_all.update({row.path: row for row in models})
        print(f"{skin.character}《{skin.title}》 | skin={skin.skin_id} | {skin.category} | 立绘包={len(paints)} | 模型包={len(models)}")
        if not paints:
            print("  [警告] 清单中缺少绘画资源；可能需要 --refresh 或切换资源服")
        if skin.category in ("live2d_plus", "live2d") and not models:
            print("  [警告] 官方标注 Live2D+，但 L2D 清单中没有匹配模型，请检查版本")
        elif skin.category != "live2d_plus" and not models:
            print("  [提示] 非 Live2D 换装，现有工具链只能还原静态立绘；动效未接入")

    all_paints = list(paint_all.values())
    all_models = list(model_all.values())
    total = sum(r.size for r in all_paints + all_models)
    print(f"\n合计：{len(selected)} 款 / {len(all_paints)} 个绘画包 / {len(all_models)} 个模型包 / 约 {total / 1024 / 1024:.1f} MiB（未计算已有缓存）")
    if args.plan:
        return 0

    cache_dir = Path(C.CACHE_DIR)
    painting_dir = Path(C.PAINTINGS_DIR)
    model_dir = Path(C.MODELS_DIR)
    painting_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] 下载并校验立绘包")
    bad_paints = {r.path for r in download_selection("PAINTING", all_paints, cache_dir)}
    print("\n[2/4] 按需重建立绘")
    paint_errors: dict[str, str] = {}
    for row in all_paints:
        if row.path in bad_paints:
            paint_errors[row.path] = "download_or_md5_failed"
            continue
        output = painting_output(row, painting_dir)
        if valid_png(output) and not args.force_paintings:
            print(f"  [跳过] {output.name}")
            continue
        bundle = cache_dir.joinpath(*row.path.split("/"))
        # 使用临时输出，重建失败不覆盖既有的正常立绘文件。
        temporary = output.with_name(f".{output.stem}.{batch_key}.tmp.png")
        if temporary.exists():
            temporary.unlink()
        print(f"  [重建] {output.name}", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "rebuild_painting.py"), str(bundle), str(temporary)], check=False)
        if result.returncode != 0 or not valid_png(temporary):
            paint_errors[row.path] = f"rebuild_failed_{result.returncode}"
            temporary.unlink(missing_ok=True)
            print(f"  [失败] {row.path}", flush=True)
        else:
            os.replace(temporary, output)
            # 保留重建时导出的 Mesh 坐标，供前端准确对齐分层；失败时保留原图。
            temp_meta = temporary.with_suffix(".meta.json")
            if temp_meta.exists():
                os.replace(temp_meta, output.with_suffix(".meta.json"))

    print("\n[3/4] 下载并还原 Live2D 模型")
    bad_models = {r.path for r in download_selection("L2D", all_models, cache_dir)}
    ok_model_paths = {r.path for r in all_models if r.path not in bad_models}
    needs_build = {r.path for r in all_models if r.path in ok_model_paths
                   and not valid_live2d_model(model_dir / Path(r.path).name, Path(r.path).name)}
    if needs_build:
        from build import build_live2d
        build_live2d(only=needs_build)
    else:
        print("  已有模型文件通过检查，无需重复提取", flush=True)

    print("\n[4/4] 检查结果，更新查看器")
    report = []
    failed = False
    for skin, paints, models in plans:
        passed_paints = [r for r in paints if r.path not in paint_errors and valid_png(painting_output(r, painting_dir))]
        passed_models = [r for r in models if r.path in ok_model_paths and valid_live2d_model(model_dir / Path(r.path).name, Path(r.path).name)]
        painting_ok = bool(passed_paints)
        model_ok = bool(passed_models)
        # 动态/特殊动态不等于拥有可播放的完整特效，即使提取出模型也需验证交互/特效。
        status = "live2d_files_ready" if model_ok else "painting_only" if painting_ok else "failed"
        if not painting_ok or (skin.category in ("live2d_plus", "live2d") and not model_ok):
            failed = True
        record = {
            **asdict(skin),
            "status": status,
            "paintings_built": len(passed_paints),
            "paintings_expected": len(paints),
            "models_built": len(passed_models),
            "models_expected": len(models),
            "animated_effect_verified": False,
            "notes": "静态立绘可浏览；动态/特殊动态效果尚未被当前查看器验证" if skin.category not in ("live2d_plus", "live2d") else "模型文件已提取，需在查看器实测动作/交互",
        }
        report.append(record)
        print(f"  {skin.character}《{skin.title}》 => {status} (PNG {len(passed_paints)}/{len(paints)}, L2D {len(passed_models)}/{len(models)})")

    # 避免没有任何可用资源时刷新为空白清单。
    if any(x["status"] != "failed" for x in report):
        from gen_manifest import generate
        generate()

    report_path = Path(C.DATA_DIR) / f"{batch_key}-install-report.json"  # data/ 已被 .gitignore 排除
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump({"batch": f"azur_lane_{batch_key}", "generated_at": datetime.now(timezone.utc).isoformat(), "skins": report}, f, ensure_ascii=False, indent=2)
    print(f"安装检查记录：{report_path}")
    print(f"可在仓库根执行 python -m http.server 8000 并打开 /azur_lane/viewer/{gallery_page}")
    return 1 if failed or paint_errors or bad_models else 0


if __name__ == "__main__":
    raise SystemExit(main())
