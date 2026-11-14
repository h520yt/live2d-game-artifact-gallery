#!/usr/bin/env python3
"""《重返未来：1999》截至国服 4.1 的女性角色 UNIQUE 最高档衣着。

按已经核实的 12 套同皮肤 ID 背景 + Cubism 目录下载，不请求 GitHub API；
不提交游戏模型和贴图至 Git，只保存索引/下载器。浏览器可选动作、表情。
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import scene
import spine

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "unique"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# skin2dbg 恰有 12 张与 UNIQUE 衣着 ID 对应的独立商城背景。
# 模型目录从上游 live2d/roles Git Tree 核对；不要直接使用映射中可能缺版本前缀的链接。
# tuple: (skin_id, 角色, 衣着, 资源目录, 背景 PNG 字节数, 实装版本)
UNIQUE_SKINS = (
    ("302504", "星锑", "启航！向明日", "v1a9_302504_xingti", 1829348, "1.9"),
    ("306604", "37", "泉眼深处", "v2a2_306604_37", 5267932, "2.2"),
    ("308303", "曲娘", "壁上桃源", "v2a5_308303_quniang", 5772724, "2.5"),
    ("308603", "露西", "生如行棋", "v2a8_308603_lx", 4303396, "2.8"),
    ("310003", "天使娜娜", "恶之果", "v3a2_310003_tsnn", 2268008, "3.2"),
    ("311003", "梁月", "照雪明", "v3a4_311003_ly", 3333978, "3.4"),
    ("305305", "牙仙", "彩衣曲", "v3a4_305305_yx", 2448460, "3.4"),
    ("314403", "珐琅眼", "醒时声", "v3a7_314403_fly", 4013636, "3.7"),
    ("312003", "诺谛卡", "名以光辉", "v3a7_312003_ndk", 2353588, "3.7"),
    ("310504", "纸信圈儿", "原子时报晓", "s02_310504_zxqe", 2751807, "S02"),
    ("315503", "狩勋女巫红弩箭", "虹色冠冕", "v4a0_315503_tlzchnj", 8152920, "4.0"),
    ("313403", "贝丽尔", "释命运以弦音", "v4a0_313403_ble", 9438795, "4.0"),
)
SKINS = {row[0]: row for row in UNIQUE_SKINS}
BASE = f"https://raw.githubusercontent.com/{spine.SOURCE}/master"


def require_skin(skin_id):
    sid = str(skin_id)
    if not re.fullmatch(r"\d{6}", sid) or sid not in SKINS:
        raise ValueError(f"UNIQUE 未收录皮肤 {sid!r}；可用 skin ID：{', '.join(SKINS)}")
    return SKINS[sid]


def resource_url(relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("资源路径非法")
    # 文件名和子目录均使用上游确认的安全相对路径，不接受 URL、绝对路径或 ..。
    parts = relative.split("/")
    if any(p in (".", "..", "") or not re.fullmatch(r"[a-zA-Z0-9_.-]+", p) for p in parts):
        raise ValueError(f"非法资源路径：{relative}")
    return f"{BASE}/{relative}"


def download_once(url, target, size=0):
    # 本下载器采用原子写入；没有中途产生的半文件。
    # 已完成的文件复用并校验固定背景体积，重新执行失败的批次无需重复下载全部内容。
    if target.is_file() and target.stat().st_size > 0:
        if not size or target.stat().st_size == size:
            return False
    return spine.download_file(url, target, size)


def inspect_local(skin_id):
    """仅当背景、模型与全部 model3.json 声明的依赖齐全时才报告已下载。"""
    sid, name, garment, folder, bg_size, version = require_skin(skin_id)
    root = DATA_DIR / sid
    bg = root / "background.png"
    cfg = root / "cubism" / (folder + ".model3.json")
    if not bg.is_file() or bg.stat().st_size != bg_size or not cfg.is_file():
        return None
    try:
        with bg.open("rb") as stream:
            if stream.read(8) != PNG_SIGNATURE:
                return None
        model = json.loads(cfg.read_text(encoding="utf-8-sig"))
        files = scene.cubism_references(model)
        if not files or not any(x.endswith(".moc3") for x in files):
            return None
        for relative in files:
            asset = cfg.parent / relative
            if not asset.is_file() or asset.stat().st_size == 0:
                return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {"id": int(sid), "name": name, "skin": garment, "version": version,
            "folder": folder, "config": cfg, "background": bg,
            "motion_groups": len(model.get("FileReferences", {}).get("Motions") or {}),
            "expressions": len(model.get("FileReferences", {}).get("Expressions") or []),
            "files": len(files)}


def catalog():
    return [{
        "id": int(sid), "name": name, "skin": garment, "tier": "UNIQUE", "version": version,
        "downloaded": inspect_local(sid) is not None,
    } for sid, name, garment, folder, _, version in UNIQUE_SKINS]


def download_one(mapping, skin_id):
    sid, name, garment, folder, bg_size, version = require_skin(skin_id)
    record = spine.skin_entries(mapping).get(sid)
    if not record or record["name"] != name or record["skin"] != garment:
        raise RuntimeError(f"{sid} 的角色/衣着映射与已核实的 UNIQUE 清单不一致，不下载")
    dest = DATA_DIR / sid
    bg_path = dest / "background.png"
    download_once(resource_url(f"singlebg/skin2dbg/{sid}.png"), bg_path, bg_size)

    config_name = folder + ".model3.json"
    root = f"live2d/roles/{folder}"
    config_path = dest / "cubism" / config_name
    # JSON 文件很小，读取更新后的依赖列表；已存在时不重复下载。
    download_once(resource_url(f"{root}/{config_name}"), config_path)
    try:
        model_json = json.loads(config_path.read_text(encoding="utf-8-sig"))
        dependencies = scene.cubism_references(model_json)
    except (ValueError, OSError, TypeError) as exc:
        raise RuntimeError(f"{sid} 的 Live2D 配置错误：{exc}") from exc
    if not any(x.endswith(".moc3") for x in dependencies):
        raise RuntimeError(f"{sid} 的模型配置中找不到 .moc3")

    def worker(relative):
        url = resource_url(f"{root}/{relative}")
        target = config_path.parent / relative
        download_once(url, target)
        return relative

    print(f"\n[{sid}] {name} · {garment}：下载 {len(dependencies)} 个 Live2D 依赖文件")
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(worker, rel): rel for rel in dependencies}
        try:
            for future in as_completed(futures):
                future.result()
        except Exception:
            for future in futures:
                future.cancel()
            raise
    info = inspect_local(sid)
    if info is None:
        raise RuntimeError(f"{sid} 的资源仍不完整，不会加入展示柜")
    print(f"[{sid}] 完成：{info['motion_groups']} 组动作、{info['expressions']} 条表情配置")
    return info


def download(mapping, target):
    keys = list(SKINS) if str(target).lower() == "all" else [require_skin(target)[0]]
    success, failures = [], []
    for i, sid in enumerate(keys, 1):
        print(f"\nUNIQUE 衣着资源 [{i}/{len(keys)}] {SKINS[sid][1]} · {SKINS[sid][2]}")
        try:
            success.append(download_one(mapping, sid))
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"下载失败：{sid} {exc}（下次可重新执行，会复用已完成的文件）")
            failures.append(f"{sid}: {exc}")
    print(f"\nUNIQUE 批量结果：成功 {len(success)}/{len(keys)}，失败 {len(failures)}")
    if failures:
        raise RuntimeError("未完成衣着：" + "；".join(failures))
    return success


def collect_models(mapping):
    results = []
    lookup = spine.skin_entries(mapping)
    for sid, name, garment, folder, _, version in UNIQUE_SKINS:
        info = inspect_local(sid)
        if not info or sid not in lookup:
            continue
        record = lookup[sid]
        results.append({
            "type": "scene-live2d",
            "tier": "UNIQUE",
            "id": int(sid),
            "name": name,
            "en": record.get("en") or "",
            "skin": garment,
            "skin_en": record.get("skin_en") or "",
            "folder": folder,
            "path": f"../data/unique/{sid}/cubism/{folder}.model3.json",
            "background": f"../data/unique/{sid}/background.png",
            "version": version,
            "description": "Unique 最高档：官方同 ID 背景 + Cubism 原生动态衣着；不包含 Unity 全特效与编排",
            "motion_groups": info["motion_groups"],
        })
    return results
