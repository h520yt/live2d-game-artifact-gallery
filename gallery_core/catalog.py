"""多游戏展示柜统一只读索引（v1）。

仅规范化已有四套 manifest；不改写游戏原始 manifest，不移动素材目录，
也不在生成索引时把「资源条目存在」误判成「渲染/互动已验证」。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .plugins import load_plugins

GAME_MANIFESTS = {
    "azur_lane": "azur_lane/viewer/manifest.json",
    "nikke": "nikke/viewer/nikke_manifest.json",
    "reverse1999": "reverse1999/viewer/manifest.json",
    "brown_dust2": "brown_dust2/viewer/manifest.json",
}
SCHEMA_VERSION = 1

GAME_INFO = {
    "azur_lane": {"title": "碧蓝航线", "viewer": "azur_lane/viewer/index.html"},
    "nikke": {"title": "NIKKE", "viewer": "nikke/viewer/index.html"},
    "reverse1999": {"title": "重返未来：1999", "viewer": "reverse1999/viewer/index.html"},
    "brown_dust2": {"title": "棕色尘埃2", "viewer": "brown_dust2/viewer/index.html"},
}


def _read(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"资源清单格式无效：{path}")
    return data


def _local_path(root: Path, manifest: Path, value: Any) -> str | None:
    """清单路径转为仓库相对路径；拒绝绝对路径、URL 和目录穿越。"""
    if not isinstance(value, str) or not value.strip():
        return None
    value = unquote(value.replace("\\", "/").strip())
    if "://" in value or value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        raise ValueError(f"不允许的外部/绝对路径：{value}")
    target = (manifest.parent / value).resolve()
    repo_root = root.resolve()
    if target != repo_root and repo_root not in target.parents:
        raise ValueError(f"资源路径超出仓库：{value}")
    return target.relative_to(repo_root).as_posix()


def _paths(root: Path, manifest: Path, values: list[Any]) -> list[str]:
    return list(dict.fromkeys(
        p for v in values if (p := _local_path(root, manifest, v)) is not None
    ))


def _record(
    game: str,
    source_id: str,
    title: str,
    renderer: str,
    roles: dict[str, list[str]],
    *,
    required: list[str],
    optional: list[str] | None = None,
    preview: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not source_id:
        raise ValueError(f"{game}: 资源 ID 不能为空")
    return {
        "id": f"{game}:{source_id}",
        "game": game,
        "source_id": source_id,
        "title": title or source_id,
        "renderer": renderer,
        "roles": roles,
        "preview": preview,
        "tags": tags or [],
        "required_files": list(dict.fromkeys(required)),
        "optional_files": list(dict.fromkeys(optional or [])),
        "metadata": metadata or {},
        "verification": "not_checked",
    }


def _azur_collection_info(root: Path) -> dict[str, dict[str, Any]]:
    """为统一浏览补齐批次/鞋履候选信息，不将初筛直接标注为人工验收。"""
    config = root / "azur_lane" / "config" / "curated_collections.json"
    if not config.is_file():
        return {}
    batches = _read(config).get("batches")
    if not isinstance(batches, dict):
        raise ValueError("碧蓝航线精选批次配置无效")

    result: dict[str, dict[str, Any]] = {}
    for batch, group in batches.items():
        if not isinstance(group, dict):
            continue
        for item in group.get("items", []):
            if not isinstance(item, dict) or not isinstance(item.get("asset"), str):
                continue
            asset = item["asset"].lower()
            info = result.setdefault(asset, {"batches": [], "tags": [], "reviews": []})
            info["batches"].append(batch)
            footwear = item.get("footwear")
            if isinstance(footwear, str) and footwear:
                # "候选"是关键限定词，不能暗示整套动作/场景均符合鞋履要求。
                for tag in ("鞋履候选", "候选：" + footwear):
                    if tag not in info["tags"]:
                        info["tags"].append(tag)
            status = item.get("review_status") or item.get("review_priority")
            if status:
                info["reviews"].append({"batch": batch, "status": status})
    return result


def _azur_lane(root: Path, manifest: Path, data: dict) -> list[dict]:
    models = data.get("models", [])
    artworks = data.get("characters", [])
    if not isinstance(models, list) or not isinstance(artworks, list):
        raise ValueError("Azur Lane manifest models/characters 不是数组")
    result = []
    grouped_models: set[str] = set()
    collections = _azur_collection_info(root)

    for art in artworks:
        if not isinstance(art, dict) or not art.get("asset"):
            continue
        asset = str(art["asset"])
        matches = [m for m in models if isinstance(m, dict)
                   and (m.get("name") == asset or str(m.get("name", "")).startswith(asset + "_hx"))]
        names = {str(m["name"]) for m in matches}
        grouped_models.update(names)
        model_paths = _paths(root, manifest, [m.get("path") for m in matches])
        paintings = _paths(root, manifest, [
            item.get("path") for item in art.get("items", []) if isinstance(item, dict)
        ])
        preview = _local_path(root, manifest, art.get("rep_path"))
        roles = {"model": model_paths, "artwork": paintings}
        collection = collections.get(asset.lower(), {})
        # 多模型形态均为必要入口；立绘变体属于可选资源。
        required = model_paths or ([preview] if preview else paintings[:1])
        result.append(_record(
            "azur_lane", asset, str(art.get("en") or asset),
            "cubism" if model_paths else "static", roles,
            required=required, optional=paintings, preview=preview,
            tags=collection.get("tags", []),
            metadata={"skin_id": art.get("skin"), "release": art.get("rel"),
                      "batches": collection.get("batches", []),
                      "reviews": collection.get("reviews", [])},
        ))

    for model in models:
        if not isinstance(model, dict) or not model.get("name"):
            continue
        name = str(model["name"])
        if name in grouped_models:
            continue
        model_paths = _paths(root, manifest, [model.get("path")])
        preview = _local_path(root, manifest, model.get("cover"))
        collection = collections.get(name.lower(), {})
        result.append(_record(
            "azur_lane", name, str(model.get("en") or name), "cubism",
            {"model": model_paths}, required=model_paths,
            optional=[preview] if preview else [], preview=preview,
            tags=collection.get("tags", []),
            metadata={"skin_id": model.get("id"), "model_version": model.get("ver"),
                      "batches": collection.get("batches", []),
                      "reviews": collection.get("reviews", [])},
        ))
    return result


def _nikke(root: Path, manifest: Path, data: dict) -> list[dict]:
    result = []
    for char in data.get("characters", []):
        if not isinstance(char, dict) or not char.get("id"):
            continue
        roles, required = {}, []
        for pose, info in (char.get("poses") or {}).items():
            if not isinstance(info, dict):
                continue
            base = str(char.get("dir") or "").rstrip("/")
            sub = str(info.get("sub") or "").strip("/")
            folder = "/".join(part for part in (base, sub) if part)
            paths = _paths(root, manifest, [
                f"{folder}/{name}" for name in (
                    [info.get("skel"), info.get("atlas")] + list(info.get("pages") or [])
                ) if isinstance(name, str) and name
            ])
            roles[str(pose)] = paths
            required.extend(paths)
        preview = _local_path(root, manifest, char.get("cover"))
        art = _local_path(root, manifest, char.get("art"))
        result.append(_record(
            "nikke", str(char["id"]), str(char.get("name") or char["id"]), "spine",
            roles, required=required, optional=[art] if art else [],
            preview=preview, tags=list(char.get("tags") or []),
            metadata={"spine_version": char.get("version"), "batches": char.get("batches") or []},
        ))
    return result


def _reverse1999(root: Path, manifest: Path, data: dict) -> list[dict]:
    result = []
    # unique/jukebox 是额外的筛选视图，非另一份已安装模型，避免重复计数。
    for model in data.get("models", []):
        if not isinstance(model, dict) or model.get("id") is None:
            continue
        raw_id = str(model["id"])
        variant = str(model.get("folder") or model.get("channel") or model.get("skin") or "")
        source_id = f"{raw_id}:{variant}" if variant else raw_id
        model_paths = _paths(root, manifest, [model.get("path")])
        artwork = _paths(root, manifest, [model.get("artwork")])
        background = _paths(root, manifest, [model.get("background")])
        raw_type = str(model.get("type") or "").lower()
        renderer = "spine" if "spine" in raw_type else "cubism" if (
            "cubism" in raw_type or "live2d" in raw_type
        ) else "static"
        result.append(_record(
            "reverse1999", source_id,
            str(model.get("skin") or model.get("name") or raw_id), renderer,
            {"model": model_paths, "artwork": artwork, "background": background},
            required=model_paths or artwork[:1],
            optional=artwork + background,
            preview=(artwork or background or [None])[0],
            tags=[str(model["tier"])] if model.get("tier") else [],
            metadata={"character": model.get("name"), "skin_id": model.get("id"),
                      "channel": model.get("channel"), "tier": model.get("tier")},
        ))
    return result


def _brown_dust2(root: Path, manifest: Path, data: dict) -> list[dict]:
    # 角色/皮肤名称与风格标签分别来自原始目录和审核清单，安装 manifest 只管文件。
    meta = {}
    for name, key in (("costume_catalog.json", "skins"),
                      ("curated_prestige.json", "skins")):
        catalog_file = root / "brown_dust2" / name
        if catalog_file.is_file():
            meta.update({str(x["id"]): x for x in _read(catalog_file).get(key, [])
                         if isinstance(x, dict) and x.get("id")})
    tags_file = root / "brown_dust2" / "curated_style.json"
    tags = {}
    if tags_file.is_file():
        tags = {str(x["id"]): x.get("tags", [])
                for x in _read(tags_file).get("styles", [])
                if isinstance(x, dict) and x.get("id")}

    result = []
    for skin in data.get("installed", []):
        if not isinstance(skin, dict) or not skin.get("id"):
            continue
        source_id = str(skin["id"])
        roles, required = {}, []
        for role, info in (skin.get("roles") or {}).items():
            if not isinstance(info, dict):
                continue
            folder = str(info.get("dir") or "").rstrip("/")
            paths = _paths(root, manifest, [
                f"{folder}/{name}" for name in (
                    [info.get("skel"), info.get("atlas")] + list(info.get("pages") or [])
                ) if isinstance(name, str) and name
            ])
            roles[str(role)] = paths
            required.extend(paths)
        details = meta.get(source_id, {})
        title = details.get("skin") or details.get("skin_en") or source_id
        result.append(_record(
            "brown_dust2", source_id, str(title), "spine", roles,
            required=required, tags=list(tags.get(source_id) or []),
            metadata={"character": details.get("character") or details.get("character_en"),
                      "tier": details.get("tier"), "role_names": list(roles)},
        ))
    return result


ADAPTERS = {
    "azur_lane": _azur_lane,
    "nikke": _nikke,
    "reverse1999": _reverse1999,
    "brown_dust2": _brown_dust2,
}


def _generic_game(root: Path, manifest: Path, data: dict, game: str) -> list[dict]:
    """通用插件清单适配，特殊引擎行为由对应游戏自己的 viewer 实现。"""
    if data.get("schema_version") != 1 or not isinstance(data.get("assets"), list):
        raise ValueError(f"{game}: 插件 manifest 须使用 generic-assets-v1 格式")
    entries = []
    for item in data["assets"]:
        if not isinstance(item, dict):
            raise ValueError(f"{game}: asset 必须是对象")
        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id or len(source_id) > 180:
            raise ValueError(f"{game}: asset id 无效")
        if not all(char.isascii() and (char.isalnum() or char in "_:.-") for char in source_id):
            raise ValueError(f"{game}: asset id 含不支持的字符：{source_id}")
        renderer = item.get("renderer", "static")
        if renderer not in ("static", "spine", "cubism"):
            raise ValueError(f"{game}: 不支持的资源渲染类型：{renderer}")
        roles_data = item.get("roles", {})
        if not isinstance(roles_data, dict):
            raise ValueError(f"{game}: roles 应为路径数组的对象")
        roles: dict[str, list[str]] = {}
        for role, paths in roles_data.items():
            if not isinstance(role, str) or not role or not isinstance(paths, list):
                raise ValueError(f"{game}: roles 无效：{role}")
            if any(not isinstance(path, str) or not path for path in paths):
                raise ValueError(f"{game}: {role} 必须为非空字符串路径数组")
            roles[role] = _paths(root, manifest, paths)
        required_data = item.get("required_files", [])
        optional_data = item.get("optional_files", [])
        tags = item.get("tags", [])
        metadata = item.get("metadata", {})
        if (not isinstance(required_data, list) or not isinstance(optional_data, list)
                or not isinstance(tags, list) or not isinstance(metadata, dict)):
            raise ValueError(f"{game}: 资源校验、标签或扩展信息类型错误")
        if any(not isinstance(value, str) for value in tags):
            raise ValueError(f"{game}: tags 只允许字符串")
        required = _paths(root, manifest, required_data)
        optional = _paths(root, manifest, optional_data)
        preview = _local_path(root, manifest, item.get("preview"))
        entries.append(_record(
            game, source_id, str(item.get("title") or source_id), renderer, roles,
            required=required, optional=optional, preview=preview,
            tags=tags, metadata=metadata,
        ))
    return entries


def build_catalog(root: Path) -> dict[str, Any]:
    """从四个原始清单生成统一索引，无需网络或游戏素材文件。"""
    root = root.resolve()
    records = []
    for game, relative in GAME_MANIFESTS.items():
        manifest = root / relative
        if not manifest.is_file():
            raise FileNotFoundError(f"缺少 {game} 的资源清单：{manifest}")
        records.extend(ADAPTERS[game](root, manifest, _read(manifest)))

    game_info = {key: dict(value) for key, value in GAME_INFO.items()}
    plugins = load_plugins(root, reserved=set(GAME_MANIFESTS))
    for spec in plugins:
        manifest = root / spec["manifest"]
        records.extend(_generic_game(root, manifest, _read(manifest), spec["id"]))
        game_info[spec["id"]] = {"title": spec["title"], "viewer": spec["viewer"]}

    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        duplicates = sorted({rid for rid in ids if ids.count(rid) > 1})
        raise ValueError(f"统一索引中存在重复 ID：{duplicates[:10]}")

    # 摘要只反映可见资源元数据，不依赖生成时间，供浏览器识别过期核验报告。
    stable_content = {"games": list(game_info), "game_info": game_info, "assets": records}
    encoded = json.dumps(stable_content, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return {"schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "catalog_digest": digest,
            **stable_content}


def verify_catalog(root: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    """核查必要入口文件是否存在；不冒充 Cubism/Spine 可渲染验收。"""
    root = root.resolve()
    results = []
    for row in catalog.get("assets", []):
        required = row.get("required_files") or []
        missing = []
        for relative in required:
            target = (root / relative).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"索引包含越界路径：{relative}")
            if not target.is_file() or target.stat().st_size == 0:
                missing.append(relative)
        status = ("no_entrypoints" if not required else "missing" if len(missing) == len(required)
                  else "partial" if missing else "entrypoints_present")
        results.append({"id": row["id"], "status": status, "missing": missing,
                        "checked": len(required)})
    counts = {status: sum(x["status"] == status for x in results)
              for status in ("entrypoints_present", "partial", "missing", "no_entrypoints")}
    return {"checked_at": datetime.now(timezone.utc).isoformat(),
            "catalog_digest": catalog.get("catalog_digest"),
            "status_definition": "entrypoints_present 不代表贴图/动作/互动已完整验证",
            "counts": counts, "items": results}
