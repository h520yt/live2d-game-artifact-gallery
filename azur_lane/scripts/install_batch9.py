"""碧蓝航线第九批：成熟制服、礼装、靴与丝袜方向的 Live2D 候选，直接进入原统一查看器。

不再生成新的批次专题网页。20 个候选在公开 L2D/PAINTING 哈希清单中
核对过名称；偏幼态及待复核造型自动跳过，鞋履及动作仍需人工检查。

项目根目录执行：
  python azur_lane/scripts/install_batch9.py --plan
  python azur_lane/scripts/install_batch9.py
  python azur_lane/scripts/install_batch9.py --only suweiaitongmeng_3 rangbaer_4
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gallery_core.azur_metadata import load_skin_metadata, resolve_skin_entry
from gallery_core.collections import load_batch_candidates
from install_batch2 import Skin, main as install_batch

AZUR_ROOT = PROJECT_ROOT / "azur_lane"
COLLECTIONS = AZUR_ROOT / "config" / "curated_collections.json"
REPORT = AZUR_ROOT / "data" / "batch9-install-report.json"

# 来源及审核描述只放在配置中，避免 Python 与网页分别维护同一份候选名单。
FIELDS = ("character", "title_hint", "asset", "style", "footwear", "review_status")
CANDIDATES = load_batch_candidates(COLLECTIONS, "batch9", FIELDS)


def validate_batch_uniqueness() -> None:
    """防止第九批加入已在前六批内安装的换装资源。"""
    document = json.loads(COLLECTIONS.read_text(encoding="utf-8"))
    batches = document["batches"]
    historical = {
        item["asset"].lower()
        for key, group in batches.items()
        if key != "batch9"
        for item in group.get("items", [])
    }
    assets = {row[2].lower() for row in CANDIDATES}
    overlap = assets & historical
    if overlap:
        raise ValueError("第九批与已有批次重复：" + "、".join(sorted(overlap)))
    # 原始 20 条候选保留历史记录，暂缓项不会进入安装流程。
    if len(batches["batch9"]["items"]) != 20 or not CANDIDATES or len(assets) != len(CANDIDATES):
        raise ValueError("第九批候选数据数量、筛选结果或资源去重异常")


def load_catalog() -> tuple[Skin, ...]:
    """皮肤 ID 由实际下载环境中的元数据解析，不能直接套用外部候选 ID。"""
    from config import CFG_JSON_DIR

    validate_batch_uniqueness()
    index = load_skin_metadata(Path(CFG_JSON_DIR) / "ship_skin_template.json")
    source_data = json.loads(COLLECTIONS.read_text(encoding="utf-8"))
    hints = {
        row["asset"].lower(): row.get("source_skin_id")
        for row in source_data["batches"]["batch9"]["items"]
    }

    skins = []
    for character, title_hint, asset, _, _, _ in CANDIDATES:
        skin_id, skin_entry = resolve_skin_entry(index, asset, allow_unknown=True)
        if skin_id == -1:
            print(f"[提示] {asset}：本地皮肤 ID 未确定，仍按准确资源名尝试安装")
        elif hints.get(asset.lower()) not in (None, skin_id):
            print(f"[提示] {asset}：本地皮肤 ID {skin_id} 与外部参考 "
                  f"{hints[asset.lower()]} 不同，请注意核查所用服务器版本")
        name = skin_entry.get("name") if skin_entry else None
        if not isinstance(name, str) or not name.strip():
            name = title_hint or asset
        skins.append(Skin(character, name, asset, skin_id, "live2d"))
    return tuple(skins)


def validate_report(data: dict) -> list[str]:
    """明确区分模型/立绘完整、视觉符合与全部动作已审核三种状态。"""
    if data.get("batch") != "azur_lane_batch9":
        raise ValueError("第九批安装报告编号不匹配")

    info = {item[2]: item for item in CANDIDATES}
    incomplete = []
    for row in data.get("skins", []):
        asset = row.get("asset")
        if asset not in info:
            raise ValueError(f"报告出现非第九批资源：{asset}")
        character, _, _, style, footwear, _ = info[asset]
        expected_models = int(row.get("models_expected", 0))
        expected_paints = int(row.get("paintings_expected", 0))
        complete = (
            expected_models > 0 and expected_paints > 0 and
            int(row.get("models_built", 0)) == expected_models and
            int(row.get("paintings_built", 0)) == expected_paints
        )
        if not complete:
            row["status"] = "incomplete"
            incomplete.append(asset)
        row["style_candidate"] = style
        row["footwear_candidate"] = footwear
        row["review_status"] = "pending_visual_and_motion_review"
        row["footwear_verified"] = False
        row["all_motions_verified"] = False
    return incomplete


def main(argv: list[str] | None = None) -> int:
    """保留既有批次安装器全部能力；安装后直接返回统一模型工作台。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--refresh" in args:
        if "--plan" in args:
            print("--refresh 和 --plan 不能同时使用", file=sys.stderr)
            return 2
        from fetch_metadata import fetch as fetch_metadata
        from fetch_manifests import fetch as fetch_manifests
        fetch_metadata()
        fetch_manifests()
        args = [arg for arg in args if arg != "--refresh"]

    try:
        skins = load_catalog()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"第九批配置或元数据错误：{exc}", file=sys.stderr)
        return 2

    result = install_batch(
        args,
        batch=skins,
        batch_key="batch9",
        batch_label="第九批·成熟风格 Live2D 候选",
        gallery_page="index.html",
    )
    if "--plan" in args:
        return result

    if not REPORT.is_file():
        print("未找到第九批安装报告", file=sys.stderr)
        return 1

    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        incomplete = validate_report(data)
        REPORT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        print(f"第九批安装报告校验失败：{exc}", file=sys.stderr)
        return 1

    if incomplete:
        print("第九批以下皮肤未安装完整：" + "、".join(incomplete), file=sys.stderr)
        return 1
    print("第九批立绘与模型入口已检查，需在原 Live2D 查看器逐个审核鞋履及动作。")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
