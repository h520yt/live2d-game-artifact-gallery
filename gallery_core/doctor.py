"""展示柜静态集成诊断。

不下载素材、不运行浏览器，也不使用动画引擎；
验证统一索引、游戏查看器与桥接协议的基本连通性。
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import GAME_MANIFESTS


def diagnose_gallery(root: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    """审计当前资源清单与实际页面入口，输出可归档的失败/警告原因。"""
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    counts = Counter(asset.get("game") for asset in catalog.get("assets", []))
    game_info = catalog.get("game_info", {})
    assets = catalog.get("assets", [])

    if not isinstance(game_info, dict) or not isinstance(assets, list):
        raise ValueError("统一资源目录缺少 game_info / assets")
    if not isinstance(catalog.get("catalog_digest"), str):
        errors.append("目录缺少固定内容摘要，无法校验报告是否对应当前索引")

    required_pages = ("index.html", "gallery/index.html", "gallery/app.js",
                      "shared/gallery_bridge.js")
    for relative in required_pages:
        if not (root / relative).is_file():
            errors.append(f"缺少统一展示柜文件：{relative}")

    for game, info in game_info.items():
        if not isinstance(info, dict):
            errors.append(f"{game}: 游戏注册信息格式错误")
            continue
        relative = info.get("viewer")
        if not isinstance(relative, str) or not relative:
            errors.append(f"{game}: 缺少专属查看器地址")
            continue
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            errors.append(f"{game}: 查看器不存在或路径越界：{relative}")
            continue
        source = target.read_text(encoding="utf-8")
        bridge_ref = "../../shared/gallery_bridge.js" if game in GAME_MANIFESTS \
            else "../../../shared/gallery_bridge.js"
        if bridge_ref not in source:
            errors.append(f"{game}: 未在查看器中加载共享桥接脚本")
        # 动作桥接可以位于插件独立 JS 文件中，不要求写在 HTML 内。
        scripts = [source]
        plugin_script = target.parent / "viewer.js"
        if plugin_script.is_file():
            scripts.append(plugin_script.read_text(encoding="utf-8"))
        if not any("GalleryViewerBridge" in text and "register" in text for text in scripts):
            errors.append(f"{game}: 未实现注册接口，统一皮肤直达不可用")
        if not counts.get(game):
            warnings.append(f"{game}: 当前 manifest 没有安装资源，可能是尚未提取或未生成清单")

    seen = set()
    for asset in assets:
        if not isinstance(asset, dict):
            errors.append("目录中存在非对象资源条目")
            continue
        key = asset.get("id")
        game = asset.get("game")
        source = asset.get("source_id")
        if not isinstance(key, str) or not key:
            errors.append(f"{game}: 资源 ID 无效")
            continue
        if key in seen:
            errors.append(f"重复的统一资源 ID：{key}")
        seen.add(key)
        if game not in game_info or key != f"{game}:{source}":
            errors.append(f"{key}: 资源归属或 ID 格式不一致")
        paths = asset.get("required_files")
        if not isinstance(paths, list):
            errors.append(f"{key}: required_files 必须是数组")
        elif not paths:
            # 仅提示，不代表不能播放。常见于没有独立文件的静态目录项。
            warnings.append(f"{key}: 未声明可核查的必要入口文件")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "catalog_digest": catalog.get("catalog_digest"),
        "games": len(game_info),
        "resources": len(assets),
        "per_game": {game: counts.get(game, 0) for game in game_info},
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "scope": "静态资源入口与桥接检查，不等于真实浏览器及动作验收",
    }
