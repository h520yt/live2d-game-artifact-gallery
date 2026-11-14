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
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
AZL_ROOT = SCRIPT_DIR.parent


@dataclass(frozen=True)
class Skin:
    character: str
    title: str
    asset: str
    skin_id: int
    category: str  # live2d_plus | special_dynamic | dynamic


BATCH = (
    Skin("光辉", "幽影徘徊之夜", "guanghui_9", 237031, "live2d_plus"),
    Skin("白凤", "晴雨狐嫁", "baifeng_3", 307162, "live2d_plus"),
    Skin("本宁顿", "全速！盛夏逐光企划", "benningdun_2", 107201, "live2d_plus"),
    Skin("水星号", "天使降临之日", "shuixinghao_2", 9600171, "live2d_plus"),
    Skin("伊冯娜（约克DE）", "幻夜绮舞", "yueke_ger_4", 403113, "special_dynamic"),
    Skin("虎", "临水的辰星", "hu_2", 202381, "dynamic"),
    Skin("七省", "秽翼天使", "qisheng_3", 1102012, "dynamic"),
    Skin("安妮女王复仇号", "堕翼之诱", "anninvwang_3", 9600122, "dynamic"),
    Skin("菲莉西娅·鲁梅", "暮色邀约", "fulici_3", 407042, "dynamic"),
    Skin("埃塞克斯", "泳池里的默契训练", "aisaikesi_10", 137090, "dynamic"),
)

# 绘画贴图中 *_bj_tex / *_bg_tex 等只是背景、特效分层，不是完整人物。
# 排除它们，防止被 gen_manifest 当成另一款皮肤。
PAINT_VARIANTS = frozenset({
    "", "_n", "_rw", "_n_rw", "_hx", "_n_hx", "_rw_hx", "_n_rw_hx",
    "_g", "_n_g", "_rw_g", "_n_rw_g",
})


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
        if variant in PAINT_VARIANTS:
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
    filename = cache_root.joinpath(*row.path.split("/"))
    if not filename.is_file() or filename.stat().st_size != row.size:
        return False
    digest = hashlib.md5()
    with filename.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == row.md5


def pick_skins(only: list[str] | None) -> list[Skin]:
    if not only:
        return list(BATCH)
    wanted = set(only)
    selected = [s for s in BATCH if s.asset in wanted or str(s.skin_id) in wanted or s.character in wanted]
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="碧蓝航线第二批 10 款皮肤按需安装")
    parser.add_argument("--plan", action="store_true", help="只核对目录、资源类型、下载规模，不修改文件")
    parser.add_argument("--refresh", action="store_true", help="更新皮肤元数据和官方资源清单")
    parser.add_argument("--only", nargs="+", metavar="NAME", help="只安装指定资源名/skin ID/角色名")
    parser.add_argument("--force-paintings", action="store_true", help="已有 PNG 也重新还原")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPT_DIR))
    import config as C

    try:
        selected = pick_skins(args.only)
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
        if skin.category == "live2d_plus" and not models:
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
        if output.is_file() and output.stat().st_size > 0 and not args.force_paintings:
            print(f"  [跳过] {output.name}")
            continue
        bundle = cache_dir.joinpath(*row.path.split("/"))
        print(f"  [重建] {output.name}", flush=True)
        # 原脚本在部分资源出错时返回码可能仍为 0，故还需验证输出存在且非空。
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "rebuild_painting.py"), str(bundle), str(output)], check=False)
        if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            paint_errors[row.path] = f"rebuild_failed_{result.returncode}"
            print(f"  [失败] {row.path}", flush=True)

    print("\n[3/4] 下载并还原 Live2D 模型")
    bad_models = {r.path for r in download_selection("L2D", all_models, cache_dir)}
    ok_model_paths = {r.path for r in all_models if r.path not in bad_models}
    if ok_model_paths:
        from build import build_live2d
        build_live2d(only=ok_model_paths)

    print("\n[4/4] 检查结果，更新查看器")
    report = []
    failed = False
    for skin, paints, models in plans:
        passed_paints = [r for r in paints if r.path not in paint_errors and painting_output(r, painting_dir).is_file()]
        passed_models = [r for r in models if r.path in ok_model_paths and (model_dir / Path(r.path).name / (Path(r.path).name + ".model3.json")).is_file()]
        painting_ok = bool(passed_paints)
        model_ok = bool(passed_models)
        # 动态/特殊动态不等于拥有可播放的完整特效，即使提取出模型也需验证交互/特效。
        status = "live2d_files_ready" if model_ok else "painting_only" if painting_ok else "failed"
        if status == "failed" or (skin.category == "live2d_plus" and not model_ok):
            failed = True
        record = {
            **asdict(skin),
            "status": status,
            "paintings_built": len(passed_paints),
            "paintings_expected": len(paints),
            "models_built": len(passed_models),
            "models_expected": len(models),
            "animated_effect_verified": False,
            "notes": "静态立绘可浏览；动态/特殊动态效果尚未被当前查看器验证" if skin.category != "live2d_plus" else "模型已提取，需在查看器实测动作/交互",
        }
        report.append(record)
        print(f"  {skin.character}《{skin.title}》 => {status} (PNG {len(passed_paints)}/{len(paints)}, L2D {len(passed_models)}/{len(models)})")

    # 避免没有任何可用资源时刷新为空白清单。
    if any(x["status"] != "failed" for x in report):
        from gen_manifest import generate
        generate()

    report_path = Path(C.DATA_DIR) / "batch2-install-report.json"  # data/ 已被 .gitignore 排除
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump({"batch": "azur_lane_batch2", "generated_at": datetime.now(timezone.utc).isoformat(), "skins": report}, f, ensure_ascii=False, indent=2)
    print(f"安装检查记录：{report_path}")
    print("可在仓库根执行 python -m http.server 8000 并打开 /azur_lane/viewer/")
    return 1 if failed or paint_errors or bad_models else 0


if __name__ == "__main__":
    raise SystemExit(main())
