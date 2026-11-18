#!/usr/bin/env python3
"""新游戏插件脚手架：生成标准 manifest、最小查看器及注册表记录。"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gallery_core.catalog import GAME_MANIFESTS  # noqa: E402
from gallery_core.plugins import PLUGIN_CONFIG, SLUG_PATTERN, load_plugins  # noqa: E402


def viewer_html(title: str) -> str:
    safe = html.escape(title, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe} · 游戏资源</title>
<style>
body{{background:#111b27;color:#eff4fa;font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif}}
main{{max-width:1000px;margin:30px auto;padding:15px}}a{{color:#f2c68d}}
button{{cursor:pointer;color:inherit;background:#26394b;border:1px solid #54677e;border-radius:8px;padding:10px;margin:5px}}
#preview{{display:block;max-height:65vh;max-width:100%;object-fit:contain;margin:16px auto}}[hidden]{{display:none!important}}
.note{{color:#b1c3d4}}
</style></head><body><main>
<a href="../../../gallery/">← 统一资源目录</a><h1>{safe}</h1>
<p class="note">插件模板仅提供静态预览；动态 Spine/Cubism 播放须接入此游戏专属引擎适配器。</p>
<h2 id="selected">选择资源</h2><p id="detail" class="note"></p><img id="preview" hidden alt="">
<div id="items"></div></main>
<script src="../../../shared/gallery_bridge.js"></script><script src="viewer.js"></script>
</body></html>
"""


def viewer_js(game: str) -> str:
    source = r'''"use strict";
(async () => {
  const game = __GAME__;
  const items = document.getElementById("items");
  const selected = document.getElementById("selected");
  const detail = document.getElementById("detail");
  const image = document.getElementById("preview");
  let assets = [];
  let current = null;

  function open(id) {
    current = assets.find((asset) => asset.id === id) || null;
    if (!current) return false;
    selected.textContent = current.title || current.id;
    detail.textContent = "格式：" + current.renderer + "。动态资源需在此游戏的 viewer 实现播放器。";
    image.hidden = true;
    image.removeAttribute("src");
    const cover = current.preview;
    if (typeof cover === "string" && cover.startsWith("../data/")) {
      const parts = cover.slice("../data/".length).split("/");
      const valid = parts.length > 0 && parts.every((part) =>
        part !== "" && part !== "." && part !== ".." &&
        !part.includes("\\") && !part.includes("?") && !part.includes("#"));
      if (valid) {
        image.src = cover;
        image.hidden = false;
      }
    }
    return true;
  }

  try {
    const response = await fetch("manifest.json", {cache: "no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const payload = await response.json();
    if (payload.schema_version !== 1 || !Array.isArray(payload.assets)) throw new Error("manifest 结构错误");
    assets = payload.assets;
    for (const item of assets) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = item.title || item.id;
      button.onclick = () => open(item.id);
      items.append(button);
    }
    window.GalleryViewerBridge?.register({
      game,
      open,
      listRoles: () => Object.keys(current?.roles || {}),
      selectRole: (role) => {
        if (!Array.isArray(current?.roles?.[role])) return false;
        detail.textContent = role + "：已索引 " + current.roles[role].length +
          " 个文件。播放功能需要专属游戏适配器实现。";
        return true;
      },
      listActions: () => [],
      playAction: () => false,
    });
  } catch (error) {
    detail.textContent = "无法读取插件资源索引：" + error.message;
  }
})();
'''
    return source.replace("__GAME__", json.dumps(game))


def readme(game: str, title: str) -> str:
    return f"""# {title} 游戏插件

ID: {game}

1. 在 viewer/manifest.json 中添加真实资源项。每个 asset 具有 id、title、renderer、
   roles（资源角色到路径数组）、preview、tags、required_files、optional_files、metadata。
2. 相对路径均以 viewer/manifest.json 位置为基准，例如 ../data/example.png。
3. 在此游戏目录内实现自己的下载、解包、Cubism / Spine 渲染与互动编排代码。
4. 替换 viewer/viewer.js 中的占位静态预览实现，保留 GalleryViewerBridge 协议。
5. 运行 python scripts/gallery.py serve 重新生成全局索引并查看。

脚手架不会下载任何版权素材。当前静态查看器不支持骨骼动画播放。
本地素材放到 data/，该目录默认由 Git 忽略。
"""


def atomic_registry(path: Path, data: dict) -> None:
    """先完成插件文件创建，最后一次性更新注册表。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".registry-", suffix=".tmp", delete=False
        ) as output:
            temp = Path(output.name)
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def create_game(game: str, title: str, dry_run: bool = False) -> list[str]:
    if not SLUG_PATTERN.fullmatch(game) or game in GAME_MANIFESTS:
        raise ValueError("游戏 ID 须为小写 ASCII 字母开头的 2~40 位字母、数字、下划线，且不能重复")
    if not title.strip() or len(title) > 120:
        raise ValueError("游戏名称必须为 1~120 个字符")
    folder = ROOT / "games" / game
    if folder.exists():
        raise FileExistsError(f"游戏目录已存在：{folder}")
    existing = load_plugins(ROOT, reserved=set(GAME_MANIFESTS))
    if game in {plugin["id"] for plugin in existing}:
        raise ValueError("游戏已存在注册")
    registry = ROOT / PLUGIN_CONFIG
    config = json.loads(registry.read_text(encoding="utf-8")) if registry.is_file() else {
        "schema_version": 1, "plugins": []
    }
    if config.get("schema_version") != 1 or not isinstance(config.get("plugins"), list):
        raise ValueError("插件注册表格式错误")
    files = {
        folder / "viewer/manifest.json":
            json.dumps({"schema_version": 1, "assets": []}, ensure_ascii=False, indent=2) + "\n",
        folder / "viewer/index.html": viewer_html(title),
        folder / "viewer/viewer.js": viewer_js(game),
        folder / "README.md": readme(game, title),
    }
    planned = [p.relative_to(ROOT).as_posix() for p in files] + [PLUGIN_CONFIG]
    if dry_run:
        return planned
    (folder / "viewer").mkdir(parents=True, exist_ok=False)
    for path, value in files.items():
        path.write_text(value, encoding="utf-8")
    config["plugins"].append({"id": game, "title": title.strip()})
    atomic_registry(registry, config)
    return planned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成新游戏插件及查看器模板")
    parser.add_argument("--id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        files = create_game(args.id, args.title, args.dry_run)
    except (OSError, ValueError) as exc:
        print(f"插件生成失败：{exc}", file=sys.stderr)
        return 1
    print("仅预览将创建的文件：" if args.dry_run else "游戏插件已创建：")
    for path in files:
        print("  " + path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
