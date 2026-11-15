"""按外观风格批量安装 NIKKE Spine 资源，支持从项目根目录执行。

用法：
    python nikke/scripts/install_style.py 运动系
    python nikke/scripts/install_style.py 运动系 --dry-run
    python nikke/scripts/install_style.py 腿部重点
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

NIKKE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = NIKKE_DIR / "scripts"
TAGS_PATH = NIKKE_DIR / "style_tags.json"


def load_tags():
    with TAGS_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("style_tags.json 必须是 ID -> 标签数组 的对象")
    return data


def main():
    parser = argparse.ArgumentParser(description="按照外观风格批量抓取并刷新 NIKKE 清单")
    parser.add_argument("style", help="风格，如 运动系 / 御姐 / 腿部重点")
    parser.add_argument("--dry-run", action="store_true", help="只打印资源 ID，不下载")
    args = parser.parse_args()

    tags = load_tags()
    ids = sorted(cid for cid, styles in tags.items()
                 if isinstance(styles, list) and args.style in styles)
    if not ids:
        print(f"未找到风格：{args.style}")
        return 2

    print(f"风格 {args.style}：共 {len(ids)} 套角色/皮肤")
    print("资源 ID：" + " ".join(ids))
    if args.dry_run:
        return 0

    # 直接复用现有断点续传脚本和 manifest 构建器，避免引入第二套下载规则。
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "fetch_nikke.py"), *ids],
                   cwd=NIKKE_DIR, check=True)
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "gen_nikke_manifest.py")],
                   cwd=NIKKE_DIR, check=True)
    manifest_path = NIKKE_DIR / "viewer" / "nikke_manifest.json"
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)
    installed = [char["id"] for char in manifest.get("characters", [])
                 if args.style in char.get("tags", [])]
    print(f"已安装 {len(installed)} / {len(ids)} 套（CDN 缺失或下载失败的不会凭空入库）")
    return 0 if installed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"安装失败：{error}", file=sys.stderr)
        sys.exit(1)
