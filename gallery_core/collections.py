"""声明式批次配置读取与校验。

游戏安装器继续管理下载/重建；收藏集 JSON 只负责候选条目和审核信息。
"""
from __future__ import annotations

import json
from pathlib import Path


def load_batch_candidates(path: Path, batch: str, fields: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """读取配置并按安装器原字段顺序输出 tuple，保持旧脚本调用契约。"""
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema_version") != 1:
        raise ValueError(f"不支持的批次配置版本：{path}")
    batches = source.get("batches")
    if not isinstance(batches, dict) or batch not in batches:
        raise ValueError(f"批次配置不存在：{batch}")
    items = batches[batch].get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"批次 {batch} 没有候选数据")
    if "asset" not in fields:
        raise ValueError("批次字段必须包含 asset")

    results = []
    seen_assets = set()
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{batch} 第 {i} 项格式不正确")
        row = []
        for field in fields:
            value = item.get(field)
            if not isinstance(value, str):
                raise ValueError(f"{batch} 第 {i} 项的 {field} 必须为字符串")
            if field == "asset" and not value.strip():
                raise ValueError(f"{batch} 第 {i} 项资源名称不能为空")
            row.append(value)
        asset = item["asset"].lower()
        if asset in seen_assets:
            raise ValueError(f"{batch} 存在重复资源名：{asset}")
        seen_assets.add(asset)
        results.append(tuple(row))
    return tuple(results)


def load_skin_batch(path: Path, batch: str) -> tuple[dict, ...]:
    """读取已确认的静态皮肤元数据（第2~4批），不依赖游戏运行时。

    这些批次的历史 ID 是明确绑定，严禁默默换成其他 ID。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"不支持的批次配置版本：{path}")
    groups = data.get("batches")
    group = groups.get(batch) if isinstance(groups, dict) else None
    entries = group.get("items") if isinstance(group, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"批次 {batch} 缺少有效条目")
    keys = ("character", "title", "asset", "skin_id", "category")
    result = []
    seen = set()
    for i, item in enumerate(entries, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{batch} 第 {i} 项必须为对象")
        row = {}
        for field in keys:
            value = item.get(field)
            if field == "skin_id":
                if type(value) is not int or value <= 0:
                    raise ValueError(f"{batch} 第 {i} 项 skin_id 必须为正整数")
            elif not isinstance(value, str) or not value.strip():
                raise ValueError(f"{batch} 第 {i} 项 {field} 必须为非空字符串")
            row[field] = value
        asset = row["asset"].lower()
        if asset in seen:
            raise ValueError(f"{batch} 资源名重复：{asset}")
        seen.add(asset)
        result.append(row)
    return tuple(result)
