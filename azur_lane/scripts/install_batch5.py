"""碧蓝航线第五批：鞋履主题 20 款 Live2D 定向安装。

在仓库根目录执行：
  python azur_lane/scripts/install_batch5.py --plan
  python azur_lane/scripts/install_batch5.py
  python azur_lane/scripts/install_batch5.py --only ougen_5 qiye_7
  python azur_lane/scripts/install_batch5.py --refresh

名单与展示页对应；皮肤 ID 从本地 ship_skin_template.json 精确读取，
不根据拼音猜 ID。安装只在本地下载版权素材，不提交资源文件。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from gallery_core.azur_metadata import load_skin_metadata, resolve_skin_entry
from gallery_core.collections import load_batch_candidates

from install_batch2 import Skin, main as install_batch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "batch5-install-report.json"

# 角色、英文换装名、精确 L2D 资源路径名、鞋履风格、人工审核优先级。
# 鞋履款式仅是筛选标签；待复核项需在本地预览确认，赤脚应移出本批。
CANDIDATES = load_batch_candidates(
    ROOT / "config" / "curated_collections.json", "batch5",
    ("character", "title", "asset", "footwear", "review_priority"),
)


def catalog() -> tuple[Skin, ...]:
    """按共享元数据解析器映射皮肤 ID，不重复实现消歧逻辑。"""
    from config import CFG_JSON_DIR
    metadata_path = Path(CFG_JSON_DIR) / "ship_skin_template.json"
    index = load_skin_metadata(metadata_path)
    result = []
    errors = []
    for character, title, asset, _, _ in CANDIDATES:
        try:
            skin_id, _ = resolve_skin_entry(index, asset)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        result.append(Skin(character, title, asset, skin_id, "live2d"))
    if errors:
        raise ValueError("第五批存在以下元数据映射问题：\n" + "\n".join(errors))
    if len(result) != 20 or len({s.asset for s in result}) != 20:
        raise ValueError("第五批应当包含 20 个不同模型名称")
    return tuple(result)


def validate_report(report: dict) -> list[str]:
    """模型变体与立绘包必须全部齐全，单一变体就绪不可冒充整套完整。"""
    if report.get("batch") != "azur_lane_batch5":
        raise ValueError("安装报告的批次号不匹配")
    incomplete = []
    for skin in report.get("skins", []):
        expected_paints = int(skin.get("paintings_expected", 0))
        expected_models = int(skin.get("models_expected", 0))
        painted = int(skin.get("paintings_built", 0))
        modeled = int(skin.get("models_built", 0))
        complete = (expected_paints > 0 and expected_models > 0
                    and painted == expected_paints and modeled == expected_models)
        if not complete:
            skin["status"] = "incomplete"
            skin["notes"] = "资源不完整；请检查 CDN、UnityPy 回退版本与本地提取日志后重跑"
            incomplete.append(skin.get("asset", "unknown"))
        skin["animated_effect_verified"] = False
        skin["footwear_visually_verified"] = False
    return incomplete


def main(argv: list[str] | None = None) -> int:
    """复用已有下载/重建工具链，仅新增第五批清单与严格验收。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--refresh" in args:
        from fetch_metadata import fetch
        fetch()
    try:
        batch = catalog()
    except (OSError, ValueError, TypeError) as exc:
        print(f"第五批元数据校验失败：{exc}", file=sys.stderr)
        return 2
    result = install_batch(
        args, batch=batch, batch_key="batch5",
        batch_label="第五批·鞋履 Live2D", gallery_page="batch5.html",
    )
    if "--plan" in args:
        return result
    if not REPORT.is_file():
        print("第五批安装报告未生成", file=sys.stderr)
        return 1
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        incomplete = validate_report(report)
        REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"第五批报告校验失败：{exc}", file=sys.stderr)
        return 1
    if incomplete:
        print("未完整安装：" + ", ".join(incomplete), file=sys.stderr)
        return 1
    print("第五批资源文件已通过完整性检查；动作与鞋履外观仍需浏览器人工验收。")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
