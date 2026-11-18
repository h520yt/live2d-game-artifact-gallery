"""碧蓝航线皮肤资源名与皮肤 ID 的唯一映射入口。

资源名可能同时被可玩皮肤和 900xxx 剧情记录引用。不能按元数据出现顺序选择。
此模块不读取网络或下载资源，供各批次安装脚本和将来的游戏适配器调用。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 确认过的歧义项。配置失效时主动报错，避免静默安装错误皮肤。
PREFERRED_SKIN_IDS: dict[str, int] = {
    "wuzang_3": 305102,
}


def load_skin_metadata(path: Path) -> dict[str, list[dict[str, Any]]]:
    """索引官方/社区元数据；同一 painting 可以映射到多个记录。"""
    if not path.is_file():
        raise FileNotFoundError(f"缺少皮肤元数据：{path}；先运行 fetch_metadata.py")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("皮肤元数据必须是对象")
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in data.values():
        if not isinstance(entry, dict):
            continue
        asset = entry.get("painting")
        sid = entry.get("id")
        if isinstance(asset, str) and asset.strip() and type(sid) is int and sid > 0:
            index.setdefault(asset.strip().lower(), []).append(entry)
    return index


def resolve_skin_entry(
    index: dict[str, list[dict[str, Any]]],
    asset: str,
    *,
    allow_unknown: bool = False,
    overrides: dict[str, int] | None = None,
) -> tuple[int, dict[str, Any]]:
    """返回明确的皮肤 ID 及其元数据；不能判定时严格模式报错。

    allow_unknown 仅供「仍可按资源名下载」的批次使用，此时返回 (-1, {})。
    显式 override 若与当前元数据冲突，即使 allow_unknown 也必须报错。
    """
    key = asset.strip().lower()
    if not key:
        raise ValueError("资源名不能为空")
    matches = index.get(key, [])
    ids = sorted({item["id"] for item in matches})
    preferred = (overrides if overrides is not None else PREFERRED_SKIN_IDS).get(key)

    if preferred is not None:
        if preferred not in ids:
            raise ValueError(f"{key}: 指定皮肤 ID {preferred} 不在元数据候选 {ids} 中")
        chosen = preferred
    elif len(ids) == 1:
        chosen = ids[0]
    else:
        # 900000~999999 为剧情/NPC 常见复用区间，不能错误排除 960xxxx。
        playable = [sid for sid in ids if not 900000 <= sid <= 999999]
        if len(playable) == 1:
            chosen = playable[0]
        elif allow_unknown:
            return -1, {}
        elif not ids:
            raise ValueError(f"{key}: 元数据缺失皮肤 ID")
        else:
            raise ValueError(f"{key}: 多个无法消歧的皮肤 ID {ids}，请添加显式映射")

    entry = next(item for item in matches if item["id"] == chosen)
    return chosen, entry
