"""碧蓝航线第四批：12 款成熟御姐 / 长腿构图换装按需安装。

仅下载第四批涉及的资源，复用第二/三批的 MD5、UnityPy 回退与模型验收。
斯特拉斯堡同时匹配 sitelasibao_2 与 sitelasibao_2_hx 两个模型包；
必须两个都通过验证才把整款标记为完整。
用法（仓库根目录）：
  python azur_lane/scripts/install_batch4.py --plan
  python azur_lane/scripts/install_batch4.py
  python azur_lane/scripts/install_batch4.py --only feiteliedadi_4 jinluhao_3
  python azur_lane/scripts/install_batch4.py --refresh

注意：提取 Live2D 文件不意味着双形态/场景交互已完整复现。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from install_batch2 import Skin, main as install_batch

# skin ID / 英文标题与项目历史 manifest 及官方资源 hash 清单对应。
# category=live2d 仅说明 CDN 存在模型包，不代表游戏内特殊动态效果全部支持。
BATCH = (
    Skin("腓特烈大帝", "Boudoir's Lingering Flame", "feiteliedadi_4", 499023, "live2d"),
    Skin("金鹿号", "The Pale Phantom's Smile", "jinluhao_3", 9600032, "live2d"),
    Skin("珍珠号", "Fallen Angel in the Dark Castle", "zhenzhuhao_2", 9600141, "live2d"),
    Skin("信浓", "Dreamy White Sands", "xinnong_4", 307083, "live2d"),
    Skin("斯特拉斯堡", "Faerie of the Race Circuit", "sitelasibao_2", 904021, "live2d"),
    Skin("天狼星", "Rabbit of Paradise", "tianlangxing_5", 202204, "live2d"),
    Skin("雷根斯堡", "Dark Dragon, Brilliant Beach", "leigensibao_2", 402101, "live2d"),
    Skin("新泽西", "Midsummer Leisure", "xinzexi_3", 105172, "live2d"),
    Skin("腓特烈大帝", "One Summer Night's Intimacy", "feiteliedadi_3", 499022, "live2d"),
    Skin("君主", "Sovereign of the Beach", "junzhu_5", 299024, "live2d"),
    Skin("大凤", "Seaside Daydreams", "dafeng_6", 307075, "live2d"),
    Skin("企业", "Bathing Under Sunny Skies", "qiye_10", 137061, "live2d"),
)

REPORT = Path(__file__).resolve().parents[1] / "data" / "batch4-install-report.json"


def review_report(report: dict) -> list[str]:
    """校验每款应有的所有图片与模型（包括 _hx），未齐全不能报告安装完成。

    原公共安装器的状态是：只要一个模型有效就记作 live2d_files_ready。
    第四批增加严格汇总检查，不改动已经稳定使用的第二/三批逻辑。
    """
    incomplete = []
    for skin in report.get("skins", []):
        paints = int(skin.get("paintings_built", 0))
        expected_paints = int(skin.get("paintings_expected", 0))
        models = int(skin.get("models_built", 0))
        expected_models = int(skin.get("models_expected", 0))
        # 数量来自本地 hash 清单；为 0 视作缺项，不能借空集合得到成功。
        complete = (expected_paints > 0 and expected_models > 0
                    and paints == expected_paints and models == expected_models)
        if not complete:
            skin["status"] = "incomplete"
            skin["notes"] = "资源包未全部提取，需检查下载/还原日志并重跑；缺少的双模型变体不能视作完整"
            incomplete.append(skin.get("asset", "unknown"))
        skin["animated_effect_verified"] = False
    return incomplete


def main(argv: list[str] | None = None) -> int:
    """共享下载重建链路，完成后对本批做严格完整性汇总。"""
    args = list(sys.argv[1:] if argv is None else argv)
    code = install_batch(
        args,
        batch=BATCH,
        batch_key="batch4",
        batch_label="第四批",
        gallery_page="batch4.html",
    )
    if "--plan" in args:
        return code
    if not REPORT.is_file():
        print("第四批安装报告未生成，请检查安装器运行日志", file=sys.stderr)
        return 1 if code == 0 else code
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        if report.get("batch") != "azur_lane_batch4":
            raise ValueError("安装报告批次不匹配")
        incomplete = review_report(report)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        print(f"第四批安装结果校验失败：{exc}", file=sys.stderr)
        return 1
    if incomplete:
        print(f"第四批未完整安装：{', '.join(incomplete)}，可直接重跑同一命令", file=sys.stderr)
        return 1
    print("第四批文件完整性检查通过；双形态及特殊互动仍需浏览器验证。")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
