"""新游戏声明式注册。仅支持仓库本地可信插件，禁止任意 Python 动态导入。

约定：games/<slug>/viewer/manifest.json 和 games/<slug>/viewer/index.html，
manifest 使用 gallery generic-assets-v1 格式。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PLUGIN_CONFIG = "gallery/plugins.json"
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,39}$")


def load_plugins(root: Path, reserved: set[str] | None = None) -> list[dict[str, Any]]:
    """读取并验证插件注册表，不扫描或执行任意路径上的代码。"""
    path = root / PLUGIN_CONFIG
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("新游戏注册表版本无效")
    entries = data.get("plugins")
    if not isinstance(entries, list):
        raise ValueError("新游戏注册表 plugins 必须是数组")
    names = set(reserved or set())
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("游戏注册项必须为对象")
        game = entry.get("id")
        title = entry.get("title")
        if not isinstance(game, str) or not SLUG_PATTERN.fullmatch(game):
            raise ValueError(f"无效游戏标识：{game}")
        if not isinstance(title, str) or not title.strip() or len(title) > 120:
            raise ValueError(f"{game}: 游戏名称不能为空或过长")
        if game in names:
            raise ValueError(f"游戏标识重复或与已有游戏冲突：{game}")
        names.add(game)
        manifest = f"games/{game}/viewer/manifest.json"
        viewer = f"games/{game}/viewer/index.html"
        if not (root / manifest).is_file() or not (root / viewer).is_file():
            raise FileNotFoundError(f"{game}: 缺少插件 manifest 或查看器文件")
        result.append({"id": game, "title": title.strip(),
                       "manifest": manifest, "viewer": viewer})
    return result
