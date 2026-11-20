"""生成 NIKKE Spine 资源的 manifest。

扫描 data/<id>/ 目录，识别三种姿态：
    fb   : {id}_00.skel|.atlas          （立绘全身，默认）
    cover: cover/{id}_cover_00.skel|.atlas
    aim  : aim/{id}_aim_00.skel|.atlas

同时兼容旧的 EventScene 目录（无姿态子目录，直接放 .skel/.atlas/.png）。
每条记录读取 skel 头部 16 字节，识别 Spine 版本（4.0 / 4.1）供前端选择 runtime。
封面优先用 fb 的首张贴图。
输出 viewer/nikke_manifest.json。
"""
import os
import re
import json
import glob
from urllib.parse import quote

import config as C

VERSION_RE = re.compile(rb"([34]\.[0-9]+\.[0-9]+)")


def detect_version(skel_path):
    """读 skel 头部识别 Spine 版本，返回 '4.0' / '4.1' / '3.8' 等（主次版本）。"""
    try:
        with open(skel_path, "rb") as f:
            head = f.read(64)
        m = VERSION_RE.search(head)
        if m:
            full = m.group(1).decode()
            return ".".join(full.split(".")[:2])
    except Exception:
        pass
    return "4.1"


def atlas_pages(atlas_path):
    pages = []
    try:
        with open(atlas_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if line.endswith(".png") and line not in pages:
                    pages.append(line)
    except Exception:
        pass
    return pages


def find_pose(rdir, cid, pose):
    """选择 skel/atlas 匹配且 PNG 图集页完整的姿态。

    不能把只存在 skel、atlas 但缺图的目录写进 manifest，
    否则浏览器看起来收录了该皮肤，实际无法渲染。
    """
    pdir = rdir if pose == "fb" else os.path.join(rdir, pose)
    if not os.path.isdir(pdir):
        return None
    skels = sorted(glob.glob(os.path.join(pdir, "*.skel")))
    for skel in skels:
        stem = os.path.splitext(os.path.basename(skel))[0]
        atlas = os.path.join(pdir, stem + ".atlas")
        if not os.path.isfile(atlas) or os.path.getsize(atlas) == 0:
            continue
        if os.path.getsize(skel) == 0:
            continue
        pages = atlas_pages(atlas)
        if not pages:
            continue
        if any(os.path.basename(page) != page or
               not os.path.isfile(os.path.join(pdir, page)) or
               os.path.getsize(os.path.join(pdir, page)) == 0 for page in pages):
            continue
        return {
            "sub": "" if pose == "fb" else pose,
            "skel": os.path.basename(skel),
            "atlas": os.path.basename(atlas),
            "pages": pages,
            "version": detect_version(skel),
        }
    return None

def scan_legacy(rdir, cid):
    """兼容旧 EventScene，但仍需要骨骼、atlas、贴图页齐全。"""
    return find_pose(rdir, cid, "fb")

def load_name_map():
    """构建 id->显示名 映射，多来源合并（优先级低->高）：
      1. 现有 manifest（保留此前已解析出的真实名字，避免被覆盖）
      2. CDN 索引 l2d.json（若能读到）
      3. _fetched.json（本次抓取；扫描补漏时 name 可能是 id 占位）

    注意：_fetched.json 在 --scan-existing 补漏后其 name 多为 id 占位，
    不能让它覆盖来源 1/2 里已有的真实名字，因此占位名（name==id）不参与覆盖。
    """
    names = {}

    # 1. 现有 manifest 的名字（最先加载，作为基础，后续来源仅补充/覆盖为“非占位”名）
    if os.path.exists(C.MANIFEST_PATH):
        try:
            m = json.load(open(C.MANIFEST_PATH, encoding="utf-8"))
            for c in m.get("characters", []):
                if c.get("name") and c["name"] != c["id"]:
                    names[c["id"]] = c["name"]
        except Exception:
            pass

    # 2. CDN 索引 l2d.json（本地缓存或运行时不一定可用，容错处理）
    idx_path = os.path.join(C.DATA_DIR, "_l2d_index.json")
    if os.path.exists(idx_path):
        try:
            for e in json.load(open(idx_path, encoding="utf-8")):
                if e.get("name"):
                    names[e["id"]] = e["name"]
                    if e.get("f"):
                        names[e["f"].lower()] = e["name"]
        except Exception:
            pass

    # 3. _fetched.json —— 仅采用“非占位”名字（name != id），避免覆盖真实名
    meta_path = os.path.join(C.DATA_DIR, "_fetched.json")
    if os.path.exists(meta_path):
        try:
            for e in json.load(open(meta_path, encoding="utf-8")):
                nm = e.get("name", e["id"])
                if nm and nm != e["id"]:
                    names[e["id"]] = nm
        except Exception:
            pass

    return names


def load_style_tags():
    """读取人工审核的外观风格标签，不影响 character / event / story 的资源分类。"""
    tag_path = os.path.join(C.BASE, "style_tags.json")
    if not os.path.isfile(tag_path):
        return {}
    try:
        with open(tag_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as err:
        print(f"风格标签读取失败: {err}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        cid: list(dict.fromkeys(tag for tag in tags if isinstance(tag, str) and tag.strip()))
        for cid, tags in data.items()
        if isinstance(cid, str) and isinstance(tags, list)
    }


def load_curated_batches():
    """建立角色 ID 到收藏批次的映射；不创建不存在的角色资源。"""
    config_path = os.path.join(C.BASE, "curated_batches.json")
    if not os.path.isfile(config_path):
        return {}

    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
    except (ValueError, OSError) as err:
        print(f"收藏批次读取失败: {err}")
        return {}

    mapping = {}
    for batch in config.get("batches", []):
        key = str(batch.get("key", ""))
        if not key:
            continue
        for item in batch.get("items", []):
            cid = item.get("id") if isinstance(item, dict) else None
            if cid:
                batches = mapping.setdefault(cid, [])
                if key not in batches:
                    batches.append(key)
    return mapping


def categorize(cid):
    """给条目打分类标签，用于前端导航/筛选。

    character : 角色（c### / c###_皮肤）
    event     : 活动剧情立绘（eventscene*）
    story     : 主线过场/剧情（chapter*/mvg*/*glass*/*chap*/liberation*/timeline*）
    misc      : 其它（BB / 道具 / 未归类）
    """
    i = cid.lower()
    if re.match(r"^c\d{3}(_\d+)?$", i):
        return "character"
    if i.startswith("eventscene"):
        return "event"
    if (i.startswith("chapter") or i.startswith("mvg") or i.startswith("liberation")
            or i.startswith("timeline") or "glass" in i or "chap" in i or "anarchyorr" in i):
        return "story"
    return "misc"


def static_art_url(cid):
    """独立静态图优先；没有时使用本地 Spine 帧渲染图。两者均非强制官方原画。"""
    for filename in ("art.png", "art.webp", "art.jpg", "art_render.png"):
        path = os.path.join(C.DATA_DIR, cid, filename)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return f"../data/{quote(cid)}/{quote(filename)}"
    return None


SCENE_VARIANT_LABELS = {
    "d": "白天",
    "n": "夜晚",
    "s": "黄昏",
    "e": "活动",
    "i": "特殊",
    "r": "替代",
}


def load_background_locations():
    """读取 Nikke-db 地点/背景关系；不是角色皮肤的专属场景映射。"""
    path = os.path.join(C.BASE, "background_locations.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as stream:
            locations = json.load(stream)
    except (OSError, ValueError) as error:
        print(f"背景地点索引读取失败: {error}")
        return {}
    if not isinstance(locations, dict):
        return {}
    return {
        filename.casefold(): str(location)
        for location, filenames in locations.items()
        if isinstance(filenames, list)
        for filename in filenames
        if isinstance(filename, str)
    }


def scene_variant(filename):
    """识别背景图后缀标注的昼夜/黄昏，不把变体当成另一个地点。"""
    stem = os.path.splitext(filename)[0]
    match = re.search(r"_([dnseir])$", stem, re.I)
    return SCENE_VARIANT_LABELS.get(match.group(1).lower(), "") if match else ""


def load_scene_bindings(backgrounds):
    """只有人工明确记录证据且图片已存在时，才给角色建立背景关联。"""
    path = os.path.join(C.BASE, "scene_bindings.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as stream:
            bindings = json.load(stream)
    except (OSError, ValueError) as error:
        print(f"皮肤场景绑定读取失败: {error}")
        return {}
    if not isinstance(bindings, dict):
        return {}

    available = {entry["filename"]: entry for entry in backgrounds}
    results = {}
    for cid, entry in bindings.items():
        if not isinstance(cid, str) or not isinstance(entry, dict):
            continue
        filename = entry.get("background")
        evidence = entry.get("evidence")
        source_asset = entry.get("source_asset")
        # 单有随手写的备注不算证据；必须提供可追踪的原始资源标识并明确复核。
        if (not isinstance(filename, str)
                or not isinstance(evidence, str) or not evidence.strip()
                or not isinstance(source_asset, str) or not source_asset.strip()
                or entry.get("confirmed") is not True):
            continue
        if filename not in available:
            print(f"  [场景未安装] {cid}: {filename}")
            continue
        results[cid] = {"background": available[filename]["file"], "filename": filename,
                        "source_asset": source_asset.strip(), "evidence": evidence.strip(),
                        "kind": "verified"}
    return results


def static_scene_preview_url(cid, rdir, scene):
    """防止旧版本错误组合的残留 WebP 被误认为已核实的专属场景。

    只有经过复核的绑定，且预览附带相同背景和源资源标识时，才允许出现在卡片。
    """
    if not scene or scene.get("kind") != "verified":
        return None
    image = os.path.join(rdir, "scene_preview.webp")
    metadata = os.path.join(rdir, "scene_preview.meta.json")
    if not os.path.isfile(image) or os.path.getsize(image) == 0 or not os.path.isfile(metadata):
        return None
    try:
        with open(metadata, encoding="utf-8") as stream:
            record = json.load(stream)
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    if (record.get("filename") != scene["filename"]
            or record.get("source_asset") != scene["source_asset"]):
        return None
    return f"../data/{quote(cid)}/scene_preview.webp"


def load_backgrounds():
    """从本地背景目录建索引：只有真实存在的文件才会进入查看器。"""
    folder = os.path.join(C.DATA_DIR, "backgrounds")
    if not os.path.isdir(folder):
        return []

    # 可选元数据文件（随仓库追踪）；不把场景与特定皮肤错误绑定。
    metadata_file = os.path.join(C.BASE, "backgrounds.json")
    metadata = {}
    if os.path.isfile(metadata_file):
        try:
            with open(metadata_file, encoding="utf-8") as fp:
                metadata = json.load(fp)
        except (ValueError, OSError) as err:
            print(f"背景元数据读取失败: {err}")
    locations = load_background_locations()
    backgrounds = []
    for filename in sorted(os.listdir(folder)):
        base, ext = os.path.splitext(filename)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        path = os.path.join(folder, filename)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            continue
        info = metadata.get(filename, {})
        if not isinstance(info, dict):
            info = {}
        variant = scene_variant(filename)
        display_name = info.get("name") or base
        backgrounds.append({
            "id": base,
            "filename": filename,
            "name": display_name,
            "category": info.get("category") or locations.get(filename.casefold(), "其他场景"),
            "variant": variant,
            "file": "../data/backgrounds/" + quote(filename),
        })
    return backgrounds


def cover_url(cid, pose_info):
    """封面优先用渲染好的头像图标 _icon.png；否则退回姿态首张贴图（可能是碎片 atlas）。"""
    art = static_art_url(cid)
    if art:
        return art
    icon = os.path.join(C.DATA_DIR, cid, "_icon.png")
    if os.path.exists(icon) and os.path.getsize(icon) > 0:
        return f"../data/{cid}/_icon.png"
    if pose_info and pose_info.get("pages"):
        sub = pose_info["sub"]
        prefix = f"../data/{cid}/{sub}/" if sub else f"../data/{cid}/"
        return prefix + pose_info["pages"][0]
    return None


def main():
    names = load_name_map()
    style_tags = load_style_tags()
    curated_batches = load_curated_batches()
    backgrounds = load_backgrounds()
    scene_bindings = load_scene_bindings(backgrounds)
    chars = []
    # 即使 data/ 暂时不存在，也生成空清单，避免展示柜误读仓库跟踪的旧数据。
    os.makedirs(C.DATA_DIR, exist_ok=True)

    for cid in sorted(os.listdir(C.DATA_DIR)):
        rdir = os.path.join(C.DATA_DIR, cid)
        if not os.path.isdir(rdir):
            continue

        poses = {}
        for pose in ("fb", "cover", "aim", "skillcut"):
            info = find_pose(rdir, cid, pose)
            if info:
                poses[pose] = info

        # 若标准命名没找到，尝试旧 EventScene 结构
        if not poses:
            legacy = scan_legacy(rdir, cid)
            if legacy:
                poses["fb"] = legacy

        if not poses:
            continue

        fb = poses.get("fb") or next(iter(poses.values()))
        chars.append({
            "id": cid,
            "name": names.get(cid, cid),
            "dir": f"../data/{cid}",
            "category": categorize(cid),
            "tags": style_tags.get(cid, []),
            "batches": curated_batches.get(cid, []),
            "poses": poses,
            "version": fb["version"],
            "cover": cover_url(cid, fb),
            "art": static_art_url(cid),
            "scene": scene_bindings.get(cid),
            "scene_preview": static_scene_preview_url(cid, rdir, scene_bindings.get(cid)),
        })

    os.makedirs(C.VIEWER_DIR, exist_ok=True)
    json.dump({"characters": chars, "backgrounds": backgrounds}, open(C.MANIFEST_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"NIKKE 角色 {len(chars)} / 背景 {len(backgrounds)} -> {C.MANIFEST_PATH}")
    # 版本 + 分类统计
    from collections import Counter
    vc = Counter(c["version"] for c in chars)
    cc = Counter(c["category"] for c in chars)
    print("版本分布:", dict(vc))
    print("分类分布:", dict(cc))
    _sync_counts(len(chars), cc.get("character", 0))


def _sync_counts(n_total, n_chars):
    """把 manifest 的实际数量回写到 index.html 与 README.md，避免手动改漏。"""
    repo = os.path.dirname(C.BASE)
    idx_path = os.path.join(repo, "index.html")
    readme_path = os.path.join(repo, "README.md")
    if os.path.exists(idx_path):
        try:
            src = open(idx_path, encoding="utf-8").read()
            out = re.sub(r'(<span class="tag">Spine · )\d+(</span>)', rf'\g<1>{n_total}\g<2>', src)
            out = re.sub(r'(<span class="tag">角色 · )\d+(</span>)', rf'\g<1>{n_chars}\g<2>', out)
            if out != src:
                open(idx_path, "w", encoding="utf-8", newline="").write(out)
                print("  计数已同步: index.html")
        except Exception as e:
            print(f"  计数同步失败 (index.html): {e}")

    if os.path.exists(readme_path):
        try:
            src = open(readme_path, encoding="utf-8").read()
            out = re.sub(r'(- \*\*立绘 / 模型\*\*：)\d+( 套 Spine 骨骼动画（其中角色 )\d+( 套）)',
                         rf'\g<1>{n_total}\g<2>{n_chars}\g<3>', src)
            if out != src:
                open(readme_path, "w", encoding="utf-8", newline="").write(out)
                print("  计数已同步: README.md")
        except Exception as e:
            print(f"  计数同步失败 (README.md): {e}")


if __name__ == "__main__":
    main()
