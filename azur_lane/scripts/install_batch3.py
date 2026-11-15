"""碧蓝航线第三批：12 款御姐 / 腿部构图优先的 Live2D 换装按需安装。

沿用第二批修复过的 MD5 校验、UnityPy 立绘重建与完整模型验收逻辑。
使用：
  python azur_lane/scripts/install_batch3.py --plan
  python azur_lane/scripts/install_batch3.py
  python azur_lane/scripts/install_batch3.py --only gaoxiong_7 mojiaduoer_4
  python azur_lane/scripts/install_batch3.py --refresh

特别说明：获取到 Live2D 资源包不代表双形态的全部互动与特效都已还原。
"""
from __future__ import annotations

from install_batch2 import Skin, main as install_batch

# 以仓库完整资源索引中的 skin ID / painting 名为准。
# 类型统一使用 live2d：仅表示存在可提取模型，不代替官方档次判断。
BATCH = (
    Skin("高雄", "Inner Cultivation", "gaoxiong_7", 303117, "live2d"),
    Skin("奥古斯特·冯·帕塞瓦尔", "Night Rendezvous with the Unhulde", "aogusite_4", 499063, "live2d"),
    Skin("兴登堡", "Dancer of the Deep Chamber", "xingdengbao_3", 499092, "live2d"),
    Skin("戈茨·冯·贝利欣根", "Rapture Beneath the Blood Moon", "gezi_2", 405071, "live2d"),
    Skin("莫加多尔", "Diving for Desire", "mojiaduoer_4", 901073, "live2d"),
    Skin("信浓", "Embrace Upon A Melted Dream", "xinnong_6", 307085, "live2d"),
    Skin("新泽西", "Black Blur Prelude", "xinzexi_5", 105174, "live2d"),
    Skin("马塞纳", "Sweetly Intoxicating Spring", "masaina_2", 804011, "live2d"),
    Skin("布雷斯特", "Moonlit Night's Spring Vista", "buleisite_3", 899032, "live2d"),
    Skin("怨仇", "Her Beauty Runneth Over", "yuanchou_3", 207072, "live2d"),
    Skin("梅克伦堡", "Branding Witchcraft", "meikelunbao_2", 499101, "live2d"),
    Skin("阿尔萨斯", "Tipsy Oni on a Sacred Night", "aersasi_3", 805032, "live2d"),
)


def main(argv: list[str] | None = None) -> int:
    return install_batch(
        argv,
        batch=BATCH,
        batch_key="batch3",
        batch_label="第三批",
        gallery_page="batch3.html",
    )


if __name__ == "__main__":
    raise SystemExit(main())
