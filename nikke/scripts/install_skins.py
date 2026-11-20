"""为已收藏的 NIKKE 角色补齐 Nikke-db 索引中的换装 Spine 模型。

默认只扩充现有四批精选角色的同角色外观，避免把所有角色盲目加入展柜。
--all-indexed 可扩大到索引中全部皮肤（不进行外观审核）。
资源文件仅下载到被 Git 忽略的 nikke/data/，不会提交游戏素材。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import config as C
from fetch_nikke import fetch_index, make_session


NIKKE_DIR = Path(__file__).resolve().parents[1]
MANIFEST = NIKKE_DIR / "viewer" / "nikke_manifest.json"
CURATED = NIKKE_DIR / "curated_batches.json"
SKIN_ID = re.compile(r"^(c\d{3})_\d{2}$", re.IGNORECASE)
CHARACTER_ID = re.compile(r"^(c\d{3})(?:_\d{2})?$", re.IGNORECASE)


def family(cid):
    """把标准皮肤资源归入同一原角色；不猜测 eventscene 等剧情资源的关系。"""
    match = CHARACTER_ID.fullmatch(cid or "")
    return match.group(1).lower() if match else None


def curated_families():
    """从已有收藏配置提取目标家族，不通过画风标签盲猜角色。"""
    with CURATED.open(encoding="utf-8") as stream:
        batches = json.load(stream).get("batches", [])
    return {
        family(item.get("id"))
        for batch in batches
        for item in batch.get("items", [])
        if family(item.get("id"))
    }


def select_skins(index, bases, all_indexed=False):
    """只选择上游明确列出的换装 ID，按 ID 去重并按自然编号排序。"""
    selected = {}
    for entry in index:
        cid = entry.get("id") if isinstance(entry, dict) else None
        match = SKIN_ID.fullmatch(cid or "")
        if not match:
            continue
        if not all_indexed and match.group(1).lower() not in bases:
            continue
        selected[cid] = {"id": cid, "name": entry.get("name") or cid}
    return [selected[cid] for cid in sorted(selected)]


def installed_ids():
    if not MANIFEST.exists():
        return set()
    with MANIFEST.open(encoding="utf-8") as stream:
        data = json.load(stream)
    return {c["id"] for c in data.get("characters", [])}


def main():
    parser = argparse.ArgumentParser(description="补齐 NIKKE 皮肤 Spine 资源")
    parser.add_argument("--plan", "--dry-run", action="store_true", help="只列出待下载皮肤，不修改任何文件")
    parser.add_argument("--direct", action="store_true", help="直连 Nikke-db，不使用默认代理")
    parser.add_argument("--base", nargs="+", metavar="cNNN",
                        help="只查指定角色及其皮肤（例如 --base c090 c810）")
    parser.add_argument("--all-indexed", action="store_true",
                        help="包含上游索引中的全部换装，未经御姐/鞋履等风格筛选")
    args = parser.parse_args()

    if args.base and args.all_indexed:
        parser.error("--base 与 --all-indexed 不能同时使用")
    if args.direct:
        C.PROXY = None

    bases = {family(cid) for cid in args.base} if args.base else curated_families()
    if None in bases:
        parser.error("--base 应为 cNNN 或 cNNN_XX")
    print("查询 Nikke-db 资源索引…")
    index = fetch_index(make_session())
    candidates = select_skins(index, bases, args.all_indexed)
    existing = installed_ids()
    missing = [skin for skin in candidates if skin["id"] not in existing]

    print(f"索引中的目标换装: {len(candidates)}；已在本机清单: {len(candidates) - len(missing)}；待补: {len(missing)}")
    for skin in candidates:
        status = "已收录" if skin["id"] in existing else "待下载"
        print(f'  [{status}] {skin["id"]:<10} {skin["name"]}')
    if args.plan or not missing:
        return 0

    # 下载器逐一检查 atlas 引用的全部 png，脚本本身不虚报资源完整性。
    command = [sys.executable, str(NIKKE_DIR / "scripts" / "fetch_nikke.py")]
    if args.direct:
        command.append("--direct")
    command.extend(skin["id"] for skin in missing)
    if subprocess.call(command) != 0:
        return 1
    if subprocess.call([sys.executable, str(NIKKE_DIR / "scripts" / "gen_nikke_manifest.py")]) != 0:
        return 1

    after = installed_ids()
    failed = [skin["id"] for skin in missing if skin["id"] not in after]
    print(f"新收录: {len(missing) - len(failed)}/{len(missing)}")
    if failed:
        print("仍缺少完整 Spine 文件:", ", ".join(failed))
        return 1
    print("可在 NIKKE 查看器内通过角色皮肤下拉切换已安装外观。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
