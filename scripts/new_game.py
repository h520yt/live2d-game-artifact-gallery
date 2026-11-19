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
    """未来新游戏默认使用「卡片网格 → 全屏大舞台 → 原位返回」公共结构。"""
    safe = html.escape(title, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe} · 游戏皮肤展示柜</title>
<link rel="stylesheet" href="../../../shared/skin_gallery.css">
<style>
#preview{{width:100%;height:100%;object-fit:contain;background:#0b1827}}
#preview[hidden]{{display:none!important}}
#preview-empty{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  color:#9fb2c3;text-align:center;max-width:80%;pointer-events:none}}
</style>
</head><body class="sg-host">
<header class="sg-header"><a href="../../../gallery/">← 总目录</a>
<div><strong>{safe}</strong><small>资源卡片 · 完整画面 · 独立动态舞台</small></div></header>
<section id="catalog-view" class="sg-catalog">
  <div class="sg-toolbar"><h2>皮肤画廊</h2><span id="count" class="sg-count">读取中…</span>
    <div class="sg-tools">
      <input id="search" type="search" placeholder="搜索角色 / 皮肤 / 编号" aria-label="搜索皮肤">
      <select id="sort" aria-label="排序">
        <option value="recent">默认顺序</option>
        <option value="installed">已安装优先</option>
        <option value="name">名称</option>
      </select>
    </div>
  </div>
  <div class="sg-grid" id="items"></div>
  <p class="sg-list-note" id="catalog-status">本页面为标准静态查看器。动态资源由游戏专属适配器加载，不会假装模型已可播放。</p>
</section>
<main id="detail-view" class="sg-detail-overlay" hidden>
  <div class="sg-detail-head">
    <button id="back-to-catalog" type="button">← 返回列表</button>
    <div class="sg-detail-identity"><strong id="selected">皮肤</strong><small id="detail">资源预览</small></div>
    <div class="sg-detail-nav"><button id="prev" type="button">〈 上一个</button><button id="next" type="button">下一个 〉</button></div>
  </div>
  <div class="sg-workspace">
    <img id="preview" hidden alt="本地角色与场景预览">
    <div id="preview-empty">暂无完整场景预览。动态 Spine / Cubism 需要为该游戏实现专属播放器。</div>
  </div>
</main>
<script src="../../../shared/gallery_bridge.js"></script>
<script src="../../../shared/skin_gallery.js"></script>
<script src="viewer.js"></script>
</body></html>
"""


def viewer_js(game: str) -> str:
    source = r'''"use strict";
(async () => {
  const game = __GAME__;
  const $ = id => document.getElementById(id);
  let assets = [];
  let current = null;
  let gallery = null;

  function safeCover(value) {
    if (typeof value !== "string" || !value.startsWith("../data/")) return null;
    const parts = value.slice("../data/".length).split("/");
    return parts.length > 0 && parts.every(part =>
      part && part !== "." && part !== ".." &&
      !part.includes("\\") && !part.includes("?") && !part.includes("#")
    ) ? value : null;
  }

  function selectAsset(row) {
    current = row.asset;
    $("selected").textContent = current.title || current.id;
    $("detail").textContent = "资源格式：" + current.renderer +
      " · 静态预览 / 动态模型需接入专属播放器";
    const cover = safeCover(current.preview);
    $("preview").hidden = !cover;
    $("preview-empty").hidden = !!cover;
    if (cover) $("preview").src = cover;
    else $("preview").removeAttribute("src");
    return true;
  }

  try {
    const response = await fetch("manifest.json", {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const payload = await response.json();
    if (payload.schema_version !== 1 || !Array.isArray(payload.assets)) throw new Error("manifest 结构错误");
    assets = payload.assets;
    gallery = SkinGallery.create({
      grid:$("items"),search:$("search"),sort:$("sort"),count:$("count"),detail:$("detail-view"),
      onOpen:selectAsset,
      onClose:() => {
        $("preview").hidden = true;
        $("preview").removeAttribute("src");
      },
    });
    gallery.setItems(assets.map(asset => ({
      key:asset.id,title:asset.title||asset.id,subtitle:asset.metadata?.character||asset.renderer,
      ready:!!safeCover(asset.preview),preview:safeCover(asset.preview),
      status:asset.renderer==="static"?"静态资源":"专属播放器待接入",
      asset,
    })));
    $("back-to-catalog").onclick = () => gallery.close();
    $("prev").onclick = () => gallery.navigate(-1);
    $("next").onclick = () => gallery.navigate(1);
    $("preview").onerror = () => {
      $("preview").hidden = true;
      $("preview-empty").hidden = false;
    };
    window.GalleryViewerBridge?.register({
      game,
      open: id => gallery.open(id),
      listRoles: () => Object.keys(current?.roles || {}),
      selectRole: role => {
        if (!Array.isArray(current?.roles?.[role])) return false;
        $("detail").textContent = "已索引 " + current.roles[role].length +
          " 个文件。动态播放须实现游戏专属适配器。";
        return true;
      },
      listActions: () => [],
      playAction: () => false,
    });
  } catch (error) {
    $("catalog-status").textContent = "无法读取资源索引：" + error.message;
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
4. 标准布局由 shared/skin_gallery.css 与 shared/skin_gallery.js 提供，
   所有游戏统一「封面卡片 -> 独立大舞台 -> 返回原位」；不要新增价格/批次独立页面。
5. 在 viewer/viewer.js 中补充游戏专属 Spine/Cubism 播放器，
   保留 SkinGallery 和 GalleryViewerBridge 协议。
6. 运行 python scripts/gallery.py serve 重新生成全局索引并查看。

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
