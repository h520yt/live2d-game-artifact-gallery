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

from install_batch2 import Skin, main as install_batch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "batch5-install-report.json"

# 角色、英文换装名、精确 L2D 资源路径名、鞋履风格、人工审核优先级。
# 鞋履款式仅是筛选标签；待复核项需在本地预览确认，赤脚应移出本批。
CANDIDATES = (
    ("欧根亲王", "Final Lap", "ougen_5", "长靴", "优先"),
    ("企业", "Wind Catcher", "qiye_7", "长靴", "优先"),
    ("乌尔里希·冯·胡滕", "Ignition Matrician", "wuerlixi_2", "长靴", "优先"),
    ("巴尔的摩", "Finish Line Flagbearer", "baerdimo_5", "长靴", "优先"),
    ("圣路易斯", "Luxurious Wheels", "shengluyisi_2", "长靴", "优先"),
    ("维托里奥·维内托", "The Flower of La Spezia", "weineituo_2", "高跟鞋", "优先"),
    ("乌尔里希·冯·胡滕", "Mayhem Maid", "wuerlixi_3", "女仆鞋", "优先"),
    ("埃吉尔", "Iron Blood's Dragon Maid", "aijier_2", "女仆鞋", "优先"),
    ("兴登堡", "Delirious Duel", "xingdengbao_2", "高跟鞋", "优先"),
    ("基尔萨治", "All-Night Charge", "jialisuoniye_3", "高跟鞋", "优先"),
    ("武藏", "The Purple Rabbit's Marksmanship", "wuzang_3", "高跟鞋", "优先"),
    ("大凤", "Fun on the Baize", "dafeng_7", "高跟鞋", "优先"),
    ("欧根亲王", "Kindred Evening Spirits", "ougen_6", "高跟鞋", "候选"),
    ("企业", "Diving Under Blue Skies", "qiye_9", "高跟鞋", "候选"),
    ("圣路易斯", "Holiness to Haziness", "shengluyisi_4", "鞋履待复核", "候选"),
    ("柴郡", "Cheshire Cat's Fairytale Maze", "chaijun_4", "鞋履待复核", "候选"),
    ("贝尔法斯特", "Iridescent Rosa", "beierfasite_2", "高跟鞋", "候选"),
    ("罗马", "White Heron of Darkest Night", "luoma_2", "高跟鞋", "候选"),
    ("纳希莫夫海军上将", "First Time in the Limelight", "naximofu_2", "鞋履待复核", "候选"),
    ("匹兹堡", "The Bartender's Gambit", "pizibao_2", "靴子", "候选"),
)


def catalog() -> tuple[Skin, ...]:
    """用社区元数据确定皮肤 ID，避免手写猜测造成错配。"""
    from config import CFG_JSON_DIR
    metadata_path = Path(CFG_JSON_DIR) / "ship_skin_template.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"缺少 {metadata_path}，先运行 fetch_metadata.py")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    by_asset: dict[str, list[int]] = {}
    for item in metadata.values():
        if not isinstance(item, dict):
            continue
        asset = item.get("painting")
        skin_id = item.get("id")
        if isinstance(asset, str) and isinstance(skin_id, int) and skin_id > 0:
            by_asset.setdefault(asset.lower(), []).append(skin_id)
    result = []
    for character, title, asset, _, _ in CANDIDATES:
        ids = sorted(set(by_asset.get(asset, [])))
        if len(ids) != 1:
            raise ValueError(f"{asset} 对应皮肤 ID 不唯一或不存在: {ids}，请更新元数据")
        result.append(Skin(character, title, asset, ids[0], "live2d"))
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
