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

from pathlib import Path
import sys

from install_batch2 import Skin, main as install_batch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from gallery_core.collections import load_skin_batch

# 以仓库完整资源索引中的 skin ID / painting 名为准。
# 类型统一使用 live2d：仅表示存在可提取模型，不代替官方档次判断。
BATCH = tuple(
    Skin(**item) for item in load_skin_batch(
        PROJECT_ROOT / "azur_lane/config/curated_collections.json", "batch3"
    )
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
