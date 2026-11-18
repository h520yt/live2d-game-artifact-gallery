"""碧蓝航线第六批：闭合鞋头/遮住脚背主题 20 个 Live2D 候选。

注意：两款赛车皮肤仅完成外部立绘初筛，其余候选需要本地预览才能确认鞋履。
不能把模型文件齐全等同于已确认鞋履合格。
运行（项目根目录）：
  python azur_lane/scripts/install_batch6.py --plan
  python azur_lane/scripts/install_batch6.py
  python azur_lane/scripts/install_batch6.py --only xinnong_3 dafeng_2
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from gallery_core.azur_metadata import load_skin_metadata, resolve_skin_entry

from install_batch2 import Skin, main as install_batch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "batch6-install-report.json"

# 资源名称均已在当前 L2D.csv 与 PAINTING.csv 找到；18 款鞋履仍需人工审核。
# 中文名称仅用于候选导航，不推断为真实皮肤 ID；ID 从元数据读取。
CANDIDATES = (
    ("信浓", "xinnong_3", "赛车长靴", "Moonlit Chrome", "初筛符合"),
    ("大凤", "dafeng_2", "赛车长靴", "Enraptured Companion", "初筛符合"),
    ("布雷默顿", "bulaimodun_4", "休闲/运动鞋候选", "", "待复核"),
    ("布雷默顿", "bulaimodun_5", "休闲/运动鞋候选", "", "待复核"),
    ("埃吉尔", "aijier_3", "冬装鞋候选", "One-on-One Leisure Time", "待复核"),
    ("七省", "qisheng_2", "制服/礼装候选", "", "待复核"),
    ("安妮女王复仇号", "anninvwang_2", "海盗风鞋候选", "Call of the Creeping Embrace", "待复核"),
    ("皇家方舟", "huangjiafangzhou_3", "制服鞋候选", "", "待复核"),
    ("金鹿号", "jinluhao_2", "礼装鞋候选", "Forlorn Femme Fatale", "待复核"),
    ("德意志", "deyizhi_3", "制服鞋候选", "", "待复核"),
    ("格奈森瑙", "genaisennao_2", "制服鞋候选", "", "待复核"),
    ("列克星敦II", "liekexingdunii_2", "女仆鞋候选", "The Fluffiest of Maids", "待复核"),
    ("光辉", "guanghui_7", "礼装鞋候选", "", "待复核"),
    ("威悉", "weixi_2", "礼装鞋候选", "", "待复核"),
    ("圣路易斯", "shengluyisi_3", "礼装鞋候选", "", "待复核"),
    ("路易九世", "luyijiushi_4", "礼装鞋候选", "", "待复核"),
    ("克利夫兰", "kelifulan_8", "制服鞋候选", "", "待复核"),
    ("北卡罗来纳", "beikaluolaina_2", "礼装鞋候选", "", "待复核"),
    ("埃米尔·贝尔汀", "aimierbeierding_3", "礼装鞋候选", "", "待复核"),
    ("俾斯麦", "bisimai_4", "节庆鞋候选", "Unpacked Surprise", "待复核"),
)


def load_catalog() -> tuple[Skin, ...]:
    """复用共享消歧规则；无法确定 ID 时仍可按资源名下载。"""
    from config import CFG_JSON_DIR
    source = Path(CFG_JSON_DIR) / "ship_skin_template.json"
    index = load_skin_metadata(source)

    result = []
    for character, asset, _, title_hint, _ in CANDIDATES:
        chosen_id, chosen_entry = resolve_skin_entry(index, asset, allow_unknown=True)
        if chosen_id == -1:
            candidates = sorted({e["id"] for e in index.get(asset.lower(), [])})
            print(f"[警告] {asset}: 元数据皮肤 ID 不明确 {candidates}；"
                  "保留未知 ID，不影响资源下载")
        title = chosen_entry.get("name") if chosen_entry else None
        if not isinstance(title, str) or not title.strip():
            title = title_hint or asset
        result.append(Skin(character, title, asset, chosen_id, "live2d"))

    if len(result) != 20 or len({skin.asset for skin in result}) != 20:
        raise ValueError("第六批要求20个不同的资源名称")
    return tuple(result)


def main(argv: list[str] | None = None) -> int:
    """继承已有 download/MD5/UnityPy/manifest 逻辑，并生成严格报告。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--refresh" in args:
        if "--plan" in args:
            print("--plan 不能和 --refresh 同时使用", file=sys.stderr)
            return 2
        from fetch_metadata import fetch as fetch_metadata
        from fetch_manifests import fetch as fetch_manifests
        fetch_metadata()
        fetch_manifests()
        # 已刷新过元数据与资源 hash，不再让公共安装器重复刷新。
        args = [arg for arg in args if arg != "--refresh"]
    try:
        batch = load_catalog()
    except (OSError, TypeError, ValueError) as exc:
        print(f"第六批元数据校验失败：{exc}", file=sys.stderr)
        return 2
    result = install_batch(
        args, batch=batch, batch_key="batch6",
        batch_label="第六批·包脚鞋履候选", gallery_page="batch6.html",
    )
    if "--plan" in args:
        return result
    if not REPORT.is_file():
        print("安装报告未生成", file=sys.stderr)
        return 1
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        # 支持 --only：只验证本次生成的项目，避免部分安装无端报错。
        incomplete = []
        if data.get("batch") != "azur_lane_batch6":
            raise ValueError("报告批次号不匹配")
        for item in data.get("skins", []):
            p_need = int(item.get("paintings_expected", 0))
            m_need = int(item.get("models_expected", 0))
            complete = (p_need > 0 and m_need > 0 and
                        int(item.get("paintings_built", 0)) == p_need and
                        int(item.get("models_built", 0)) == m_need)
            if not complete:
                item["status"] = "incomplete"
                incomplete.append(item.get("asset", "?"))
            item["footwear_verified"] = False
            item["all_motions_verified"] = False
        REPORT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        print(f"第六批报告检查失败：{exc}", file=sys.stderr)
        return 1
    if incomplete:
        print("本次以下皮肤未提取完整：" + ", ".join(incomplete), file=sys.stderr)
        return 1
    print("模型和立绘文件已检查；包脚鞋履条件及动作仍须浏览器核验。")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
