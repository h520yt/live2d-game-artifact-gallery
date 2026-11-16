"""安装 NIKKE 四批收藏清单：批量下载 Spine、更新清单、核验本地文件。

仅将脚本/元数据提交 Git。游戏图像保存到 nikke/data/（.gitignore 已忽略）。
使用：
    python nikke/scripts/install_batches.py --all
    python nikke/scripts/install_batches.py 1 2 --dry-run
    python nikke/scripts/install_batches.py 4 --verify-only
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


NIKKE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = NIKKE_DIR / "data"
BATCH_FILE = NIKKE_DIR / "curated_batches.json"
MANIFEST_FILE = NIKKE_DIR / "viewer" / "nikke_manifest.json"
REPORT_FILE = DATA_DIR / "_curated_batches_report.json"


def load_batches():
    """读取四批清单，验证批次格式与资源 ID，避免误请求。"""
    with BATCH_FILE.open(encoding="utf-8") as stream:
        config = json.load(stream)
    batches = config.get("batches", [])
    if not isinstance(batches, list) or not batches:
        raise ValueError("curated_batches.json 中没有有效批次")
    keys = set()
    for batch in batches:
        key = str(batch.get("key", ""))
        if not key or key in keys:
            raise ValueError(f"重复或无效的批次编号: {key}")
        keys.add(key)
        if not isinstance(batch.get("items"), list):
            raise ValueError(f"批次 {key} 缺少资源数组")
        for item in batch["items"]:
            cid = item.get("id") if isinstance(item, dict) else None
            if not isinstance(cid, str) or not cid.startswith("c"):
                raise ValueError(f"批次 {key} 存在不正确的资源 ID: {cid}")
    return batches


def select_items(batches, wanted, select_all):
    """按指定批次保留原始顺序并以资源 ID 去重。"""
    known = {str(batch["key"]) for batch in batches}
    selected = known if select_all else set(wanted)
    unknown = selected - known
    if unknown:
        raise ValueError("不存在的批次：" + ", ".join(sorted(unknown)))
    if not selected:
        raise ValueError("请选择批次编号 1-4，或者使用 --all")
    unique = {}
    for batch in batches:
        if str(batch["key"]) not in selected:
            continue
        for item in batch["items"]:
            cid = item["id"]
            if cid not in unique:
                unique[cid] = {
                    "id": cid,
                    "name": item.get("name", cid),
                    "batches": [],
                }
            if str(batch["key"]) not in unique[cid]["batches"]:
                unique[cid]["batches"].append(str(batch["key"]))
    return list(unique.values())


def validate_pose(cid, info, data_root):
    """校验 skel、atlas 及 atlas 中列出的全部贴图，单纯目录存在不算成功。"""
    folder = data_root / cid / (info.get("sub") or "")
    needed = [info.get("skel"), info.get("atlas"), *(info.get("pages") or [])]
    if not info.get("skel") or not info.get("atlas") or not info.get("pages"):
        return False, ["缺少 skel / atlas / 贴图记录"]
    missing = []
    for filename in needed:
        if not isinstance(filename, str) or Path(filename).name != filename:
            missing.append(str(filename) + "（无效文件名）")
            continue
        path = folder / filename
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(str(path.relative_to(data_root)))
    return not missing, missing


def verify_installations(items, manifest, data_root):
    """区分完整 fb、只有其他姿态、文件不完整以及资源缺失。"""
    indexed = {item["id"]: item for item in manifest.get("characters", [])}
    results = []
    for selected in items:
        cid = selected["id"]
        char = indexed.get(cid)
        if not char:
            results.append({**selected, "status": "missing", "poses": [], "missing_files": []})
            continue
        poses = char.get("poses") or {}
        working, missing = [], []
        for pose, info in poses.items():
            complete, lacking = validate_pose(cid, info, data_root)
            if complete:
                working.append(pose)
            else:
                missing.extend(lacking)
        if "fb" in working:
            status = "ready"
        elif working:
            status = "partial"
        else:
            status = "incomplete"
        results.append({**selected, "status": status, "poses": working, "missing_files": missing})
    return results


def print_report(results, report_path):
    """持久化本机验证结果，输出可用于排障的缺失详情。"""
    counts = Counter(result["status"] for result in results)
    print("\n资源检查：")
    for item in results:
        status = item["status"]
        poses = ",".join(item["poses"]) or "-"
        print(f'  [{status:10}] {item["id"]:9} {item["name"]} ({poses})')
        if item["missing_files"]:
            print("    缺少：" + ", ".join(item["missing_files"][:5]))
    print(
        f'完整 fb {counts["ready"]} / 仅其他姿态 {counts["partial"]} / '
        f'不完整 {counts["incomplete"]} / 缺失 {counts["missing"]}'
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": dict(counts),
            "results": results,
        }, file, ensure_ascii=False, indent=2)
    print(f"报告：{report_path}")
    return counts


def main():
    parser = argparse.ArgumentParser(description="NIKKE 四批资源一键补齐与文件完整性检查")
    parser.add_argument("batches", nargs="*", help="批次编号，如 1 2 3 4")
    parser.add_argument("--all", action="store_true", help="安装全部四批（35 个 ID）")
    parser.add_argument("--dry-run", action="store_true", help="仅查看将处理的资源")
    parser.add_argument("--verify-only", action="store_true", help="不下载，只重建清单并检查本地资源")
    parser.add_argument("--direct", action="store_true", help="网络未使用代理时直连 CDN / GitHub 镜像")
    args = parser.parse_args()

    if args.all and args.batches:
        parser.error("--all 不能与批次编号同时使用")
    if args.dry_run and args.verify_only:
        parser.error("--dry-run 与 --verify-only 不能同时使用")

    groups = load_batches()
    items = select_items(groups, args.batches, args.all)
    ids = [item["id"] for item in items]
    print(f"选中 {len(items)} 个不同资源 ID")
    for batch in groups:
        if args.all or str(batch["key"]) in args.batches:
            print(f'  第{batch["key"]}批：{batch["title"]}，{len(batch["items"])} 个 ID')
    print("  " + " ".join(ids))

    if args.dry_run:
        return 0

    if not args.verify_only:
        # 使用已经支持断点续传的抓取器，始终在本机 nikke/data 下保存资产。
        command = [sys.executable, str(NIKKE_DIR / "scripts" / "fetch_nikke.py")]
        if args.direct:
            command.append("--direct")
        command.extend(ids)
        subprocess.run(command, cwd=NIKKE_DIR, check=True)

    subprocess.run(
        [sys.executable, str(NIKKE_DIR / "scripts" / "gen_nikke_manifest.py")],
        cwd=NIKKE_DIR, check=True,
    )
    with MANIFEST_FILE.open(encoding="utf-8") as file:
        manifest = json.load(file)
    results = verify_installations(items, manifest, DATA_DIR)
    counts = print_report(results, REPORT_FILE)
    # 部分 CDN 资源仅存在 cover 或 aim，明确标记而不是假称 fb 完整。
    return 0 if counts["ready"] == len(items) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"执行失败：{error}", file=sys.stderr)
        sys.exit(1)
