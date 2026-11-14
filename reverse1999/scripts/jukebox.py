#!/usr/bin/env python3
"""吼吼点唱机（典藏光碟 / 玩家俗称「手册」）历期衣着资源。

截至国服 4.1 / 2026-11-14：32 套，27 个原生 Cubism + 5 个 Spine。
仅存资源下载器和目录；游戏图片、动态模型放本地 .gitignore 中。
独立于 UNIQUE/ADVANCED/GARMENT 衣着品质。点唱机衣着不伪造商城背景。
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import scene
import spine

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "jukebox"
SOURCE = spine.SOURCE
RAW = f"https://raw.githubusercontent.com/{SOURCE}/master"

# 角色名称、衣着、实际资产目录来自 ArcanistMap 与上游仓库的 live2d/roles、
# roles Git Tree 交叉核验。前16款也可在灰机「吼吼自选衣箱」核对。
# 源码不以年份或顺序推断皮肤的获取渠道；此表由点唱机获取资料单独核实。
# (皮肤 ID, 角色名, 衣着名, 资源类型, 已验证的源文件夹)
SKINS = (
    ("301703", "夏利", "镜中幕间", "spine", "301703_xiali"),
    ("302003", "柏林以东", "铅红的真相", "spine", "302003_bolinyidong"),
    ("304103", "玛蒂尔达", "天才假日", "cubism", "304103_madierda"),
    ("301103", "玛丽莲", "维纳斯的传道", "spine", "v1a4_301103_malilian"),
    ("302203", "帕米埃", "枪尖向上", "cubism", "v1a5_302203_pamiai"),
    ("302403", "气球派对", "银翅谣", "spine", "v1a6_302403_qqpd"),
    ("303803", "五色月", "银玫瑰", "cubism", "v1a7_303803_wuseyue"),
    ("301603", "婴儿蓝", "于麻雀山上", "spine", "v1a8_301603_yingerlan"),
    ("307503", "沙丝绒", "野性的倾洒", "cubism", "v1a9_307503_shasirong"),
    ("307103", "坎吉拉", "午夜来客", "cubism", "v2a0_307103_kjl"),
    ("306003", "金蜜儿", "铅黄色磨坊", "cubism", "v2a1_306003_jinmier"),
    ("308203", "小叶尼塞", "蓝河湾", "cubism", "v2a2_308203_xyns"),
    ("304304", "坦南特", "鉴赏家之战", "cubism", "v2a3_304304_tnt"),
    ("309503", "环状水星", "午夜曼波", "cubism", "v2a4_309503_hzsx"),
    ("300306", "槲寄生", "荆棘环绕处", "cubism", "v2a5_300306_hjs"),
    ("306204", "梅兰妮", "红与白", "cubism", "v2a6_306204_meilanni"),
    ("304804", "远旅", "群星齐唱时", "cubism", "v2a7_304804_yl"),
    ("305604", "洁西卡", "乐园之声", "cubism", "v2a8_305604_jxk"),
    ("308804", "塞梅尔维斯", "心之盈亏", "cubism", "v3a0_308804_smews"),
    ("305104", "温妮弗雷德", "以黄金哺育", "cubism", "s01_305104_wnfld"),
    ("300731", "未锈铠", "魂灵长青", "cubism", "v3a1_300731_wxk"),
    ("308004", "卡卡尼亚", "时代病陪护", "cubism", "v3a2_308004_kkny"),
    ("304704", "兔毛手袋", "永生苦短", "cubism", "v3a3_304704_tmsd"),
    ("310404", "笃笃骨", "裁春衫", "cubism", "v3a4_310404_ddg"),
    ("309804", "蓝手帕", "冷襁褓", "cubism", "v3a5_309804_lsp"),
    ("311404", "虚构集", "文字，自始至终", "cubism", "v3a6_311404_xgj"),
    ("306605", "37", "完美的流体", "cubism", "v3a7_306605_37"),
    ("311604", "冷周六", "巫阳抚彗歌", "cubism", "v3a8_311604_lzl"),
    ("307705", "北方哨歌", "银色等高线", "cubism", "s02_307705_bfsg"),
    ("312104", "莫莉德尔", "玫瑰午睡时", "cubism", "v3a9_312104_mlde"),
    ("311705", "库珀花环", "牧于晚星", "cubism", "v4a0_311705_kphh"),
    ("312704", "玛尔纱", "告慰尘与惘", "cubism", "v4a1_312704_mes"),
)
BY_ID = {row[0]: row for row in SKINS}

# 对没有 Cubism 的5套，原始 Spine 目录已逐一查验：
# 一个 atlas / 贴图、fight/room/ui 三种姿态和 bloom 辅助贴图。
SPINE_BASE = {
    "301703": "301703_xiali",
    "302003": "302003_bolinyidong",
    "301103": "301103_malilian",
    "302403": "302403_qqpd",
    "301603": "301603_yingerlan",
}


def require_skin(ident):
    sid = str(ident)
    if not re.fullmatch(r"\d{6}", sid) or sid not in BY_ID:
        raise ValueError(f"未收录的点唱机衣着 {sid!r}")
    return BY_ID[sid]


def safe_ref(ref):
    return scene.safe_cubism_reference(ref)


def remote(relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", x) or x in (".", "..")
                   for x in relative.split("/"))):
        raise ValueError("非法资源文件路径")
    return f"{RAW}/{relative}"


def download_file(url, target):
    """下载采用目标文件原子更新，复用完整已存在的内容。"""
    if target.is_file() and target.stat().st_size > 0:
        return False
    return spine.download_file(url, target)


def known_models(sid):
    sid, name, garment, kind, folder = require_skin(sid)
    root = DATA_DIR / sid
    if kind == "cubism":
        config = root / "cubism" / (folder + ".model3.json")
        if not config.is_file():
            return None
        try:
            model = json.loads(config.read_text(encoding="utf-8-sig"))
            dependencies = scene.cubism_references(model)
            if not dependencies or not any(f.endswith(".moc3") for f in dependencies):
                return None
            if not all((config.parent / p).is_file() and (config.parent / p).stat().st_size > 0 for p in dependencies):
                return None
        except (OSError, ValueError, TypeError, KeyError):
            return None
        return {"type": "cubism", "config": config,
                "motions": len(model.get("FileReferences", {}).get("Motions") or {}),
                "files": len(dependencies)}
    # Spine 必须有对应 atlas、三种 skel 和图集贴图。
    base = SPINE_BASE[sid]
    folder_path = root / "spine"
    needed = [base + ".atlas", base + ".png", base + "_fight.skel",
              base + "_room.skel", base + "_ui.skel"]
    if not all((folder_path / p).is_file() and (folder_path / p).stat().st_size > 0 for p in needed):
        return None
    try:
        version = spine.detect_version(folder_path / (base + "_ui.skel"))
    except (OSError, ValueError):
        return None
    return {"type": "spine", "version": version, "files": len(needed)}


def catalog():
    return [{"id": int(sid), "name": name, "skin": garment, "type": kind,
             "channel": "JUKEBOX", "downloaded": known_models(sid) is not None}
            for sid, name, garment, kind, folder in SKINS]


def verify_mapping(mapping, sid, name, garment):
    entries = spine.skin_entries(mapping)
    row = entries.get(sid)
    if not row or row.get("name") != name or row.get("skin") != garment:
        raise RuntimeError(f"点唱机皮肤 ID {sid} 与上游人物/衣着映射不一致")


def download_one(mapping, ident):
    sid, name, garment, kind, folder = require_skin(ident)
    verify_mapping(mapping, sid, name, garment)
    root = DATA_DIR / sid
    if kind == "cubism":
        base = f"live2d/roles/{folder}"
        config = root / "cubism" / (folder + ".model3.json")
        download_file(remote(f"{base}/{config.name}"), config)
        try:
            data = json.loads(config.read_text(encoding="utf-8-sig"))
            deps = scene.cubism_references(data)
            if not any(x.endswith(".moc3") for x in deps):
                raise ValueError("模型不含 moc3")
        except (ValueError, TypeError, OSError) as exc:
            raise RuntimeError(f"{sid} Cubism 配置错误：{exc}") from exc

        print(f"[{sid}] {name} · {garment}（Cubism）：{len(deps)} 个依赖")
        def worker(rel):
            rel = safe_ref(rel)
            return download_file(remote(f"{base}/{rel}"), config.parent / rel)
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker, x) for x in deps]
            try:
                for future in as_completed(futures):
                    future.result()
            except Exception:
                for future in futures:
                    future.cancel()
                raise
    else:
        base = SPINE_BASE[sid]
        path = f"roles/{folder}"
        print(f"[{sid}] {name} · {garment}（Spine，ui/room/fight）")
        names = [base + ".atlas", base + ".png", base + "_bloom.png",
                 base + "_fight.skel", base + "_room.skel", base + "_ui.skel"]
        for filename in names:
            download_file(remote(f"{path}/{filename}"), root / "spine" / filename)
        spine.setup_runtime()
    info = known_models(sid)
    if not info:
        raise RuntimeError(f"{sid} 部分文件仍缺失，不加入展示柜；重新运行即可续传")
    print(f"[{sid}] 完成 ({info['type']})")
    return info


def download(mapping, target):
    ids = list(BY_ID) if str(target).lower() == "all" else [require_skin(target)[0]]
    failed, done = [], 0
    for i, sid in enumerate(ids, 1):
        print(f"\n点唱机衣着 [{i}/{len(ids)}] {sid} {BY_ID[sid][1]} · {BY_ID[sid][2]}")
        try:
            download_one(mapping, sid)
            done += 1
        except (RuntimeError, ValueError, OSError) as exc:
            failed.append((sid, str(exc)))
            print(f"失败 {sid}：{exc}")
    print(f"\n点唱机下载完成 {done}/{len(ids)}；失败 {len(failed)}")
    if failed:
        raise RuntimeError("尚未完成：" + "；".join(f"{x}: {reason}" for x, reason in failed))


def collect_models(mapping):
    rows = spine.skin_entries(mapping)
    out = []
    for sid, name, garment, kind, folder in SKINS:
        info = known_models(sid)
        if not info or sid not in rows:
            continue
        standard = {"id": int(sid), "name": name, "skin": garment,
                    "en": rows[sid].get("en") or "",
                    "skin_en": rows[sid].get("skin_en") or "",
                    "folder": folder, "channel": "JUKEBOX"}
        if kind == "cubism":
            standard.update({"type": "cubism",
                             "path": f"../data/jukebox/{sid}/cubism/{folder}.model3.json"})
        else:
            base = SPINE_BASE[sid]
            standard.update({"type": "spine",
                             "dir": f"../data/jukebox/{sid}/spine",
                             "poses": {pose: {"skel": f"{base}_{pose}.skel",
                                              "atlas": f"{base}.atlas",
                                              "version": info["version"]}
                                       for pose in ("ui", "room", "fight")}})
        out.append(standard)
    return out
