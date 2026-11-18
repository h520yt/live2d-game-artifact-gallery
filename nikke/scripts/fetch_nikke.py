"""从 Nikke-db CDN 拉取 NIKKE 立绘/模型（Spine）资源。

流程：
  1. 拉取 l2d.json 索引（name/id/version）。
  2. 对每个角色，尝试三种姿态 fb / cover / aim：
       fb   : {id}/{id}_00.skel|.atlas + atlas 引用的所有 .png
       cover: {id}/cover/{id}_cover_00.skel|.atlas + .png
       aim  : {id}/aim/{id}_aim_00.skel|.atlas + .png
  3. 解析 atlas 拿到全部贴图页文件名，逐个下载。
  4. 已存在且大小 >0 的文件跳过（可断点续传）。

用法：
    python fetch_nikke.py             # 拉全部
    python fetch_nikke.py c010 c470   # 只拉指定 id
    python fetch_nikke.py --limit 20  # 只拉前 20 个（快速验证）
"""
import os
import sys
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

import config as C

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from gallery_core.storage import atomic_write_bytes, file_ready


def make_session():
    s = requests.Session()
    if C.PROXY:
        s.proxies.update({"http": C.PROXY, "https": C.PROXY})
    # Cloudflare Pages（nikke-db-legacy.pages.dev）会对缺少 UA/Referer 的请求返回 403，
    # 需伪装为浏览器并带上 Referer 才能正常拿到资源。
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0 Safari/537.36"),
        "Referer": "https://nikke-db-legacy.pages.dev/",
    })
    return s


def fetch_index(session):
    urls = [
        getattr(C, "INDEX_URL", None),
        getattr(C, "INDEX_URL_MIRROR", None),
        getattr(C, "INDEX_URL_LEGACY", None),
    ]
    for url in urls:
        if not url:
            continue
        for attempt in range(3):
            try:
                r = session.get(url, timeout=30)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and len(data) > 50:
                    cached = os.path.join(C.DATA_DIR, "_l2d_index.json")
                    os.makedirs(C.DATA_DIR, exist_ok=True)
                    try:
                        with open(cached, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    return data
            except Exception:
                time.sleep(1)
                continue
    # 兜底：若网络拉取失败，尝试使用本地已有缓存
    cached = os.path.join(C.DATA_DIR, "_l2d_index.json")
    if os.path.exists(cached):
        print("  [提示] 使用本地缓存的 l2d.json 索引")
        return json.load(open(cached, encoding="utf-8"))
    raise RuntimeError("无法获取 l2d.json 索引")


def asset_base_urls(cid, sub):
    """主 CDN 与 GitHub 镜像按顺序回退；两个地址指向同一套已解包文件。"""
    configured = [C.CDN_BASE, getattr(C, "CDN_MIRROR", "")]
    bases = []
    for base in configured:
        if not base:
            continue
        url = f"{base.rstrip('/')}/{cid}/{sub}"
        if url not in bases:
            bases.append(url)
    return bases


def download(session, urls, dest):
    """下载文件，主源失败自动尝试镜像；已有非空文件不重复请求。

    返回 (ok, size, skipped)。仅 HTTP 200 且非 HTML、实际非空才视为成功。
    """
    if file_ready(dest):
        return True, os.path.getsize(dest), True

    if isinstance(urls, str):
        urls = [urls]
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for url in urls:
        for attempt in range(2):
            try:
                with session.get(url, timeout=60, stream=True) as response:
                    if response.status_code != 200:
                        break
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" in content_type:
                        break
                    size = 0
                    with open(tmp, "wb") as file:
                        for chunk in response.iter_content(65536):
                            if chunk:
                                file.write(chunk)
                                size += len(chunk)
                    if size == 0:
                        continue
                    # 某些镜像把不存在的文件返回为 HTML 页面，不能作为资源写入。
                    with open(tmp, "rb") as file:
                        header = file.read(96).lstrip().lower()
                    if header.startswith((b"<!doctype html", b"<html")):
                        continue
                    os.replace(tmp, dest)
                    return True, size, False
            except requests.RequestException:
                if attempt == 0:
                    time.sleep(0.3)
            except OSError as error:
                print(f"  [写入错误] {dest}: {error}")
                break
            finally:
                if os.path.isfile(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
    return False, 0, False


def download_atlas(session, urls, dest):
    """读取已有 atlas 或下载主源/镜像；校验贴图页列表，拒绝 HTML 与空文件。"""
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        try:
            with open(dest, encoding="utf-8", errors="ignore") as file:
                pages = parse_atlas_pages(file.read())
            if pages:
                return pages
        except OSError:
            pass

    for url in urls:
        for attempt in range(2):
            try:
                with session.get(url, timeout=30) as response:
                    if response.status_code != 200:
                        break
                    if "text/html" in response.headers.get("content-type", "").lower():
                        break
                    payload = response.content
                    pages = parse_atlas_pages(payload.decode("utf-8", "ignore"))
                    if not pages:
                        break
                    atomic_write_bytes(dest, payload)
                    return pages
            except (requests.RequestException, OSError) as error:
                if attempt == 0:
                    time.sleep(0.3)
                else:
                    print(f"  [atlas 源失败] {url}: {error}")
    return []

def parse_atlas_pages(atlas_text):
    """解析 atlas，返回引用的所有 .png 文件名（按出现顺序）。"""
    pages = []
    for line in atlas_text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if line.endswith(".png") and line not in pages:
            pages.append(line)
    return pages


_INDEX_CACHE = None


def get_index_entry(cid):
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        idx_path = os.path.join(C.DATA_DIR, "_l2d_index.json")
        if os.path.exists(idx_path):
            try:
                data = json.load(open(idx_path, encoding="utf-8"))
                _INDEX_CACHE = {e["id"]: e for e in data}
            except Exception:
                _INDEX_CACHE = {}
        else:
            _INDEX_CACHE = {}
    return _INDEX_CACHE.get(cid, {})


def pose_paths(cid, pose, f_name=None):
    """返回 (远端子路径前缀, skel名, atlas名) 用于该姿态。"""
    if not f_name:
        f_name = get_index_entry(cid).get("f")
    if pose == "fb":
        stem = f_name if f_name else f"{cid}_00"
        sub = ""
    else:
        stem = f"{cid}_{pose}_00"
        sub = f"{pose}/"
    return sub, f"{stem}.skel", f"{stem}.atlas"


def get_local_pose(cid, pose, f_name=None):
    """检查本地是否已完整拥有该姿态（skel + atlas + 所有贴图 png）。如果是，直接返回描述字典。"""
    sub, skel_name, atlas_name = pose_paths(cid, pose, f_name)
    local_dir = os.path.join(C.DATA_DIR, cid, sub.rstrip("/")) if sub else os.path.join(C.DATA_DIR, cid)
    skel_path = os.path.join(local_dir, skel_name)
    atlas_path = os.path.join(local_dir, atlas_name)
    if not (os.path.exists(skel_path) and os.path.getsize(skel_path) > 0 and
            os.path.exists(atlas_path) and os.path.getsize(atlas_path) > 0):
        # 兼容已有以 f_name(小写) 为目录名的情况（例如 eventscene_terminusticket_01）
        if f_name and pose == "fb":
            alt_dir = os.path.join(C.DATA_DIR, f_name.lower())
            alt_skel = os.path.join(alt_dir, skel_name)
            alt_atlas = os.path.join(alt_dir, atlas_name)
            if (os.path.isfile(alt_skel) and os.path.getsize(alt_skel) > 0
                    and os.path.isfile(alt_atlas) and os.path.getsize(alt_atlas) > 0):
                pages = parse_atlas_pages(open(alt_atlas, encoding="utf-8", errors="ignore").read())
                if pages and all(
                        os.path.basename(page) == page and
                        os.path.isfile(os.path.join(alt_dir, page)) and
                        os.path.getsize(os.path.join(alt_dir, page)) > 0
                        for page in pages):
                    return {
                        "pose": pose,
                        "sub": "",
                        "skel": skel_name,
                        "atlas": atlas_name,
                        "pages": pages,
                    }
        return None
    try:
        with open(atlas_path, "r", encoding="utf-8", errors="ignore") as f:
            pages = parse_atlas_pages(f.read())
    except Exception:
        return None
    if not pages:
        return None
    for p in pages:
        png_path = os.path.join(local_dir, p)
        if not (os.path.exists(png_path) and os.path.getsize(png_path) > 0):
            return None
    return {
        "pose": pose,
        "sub": sub,
        "skel": skel_name,
        "atlas": atlas_name,
        "pages": pages,
    }


def fetch_pose(session, cid, pose, f_name=None):
    """下载完整姿态：骨骼+图集+全部贴图，网络失败自动回退镜像。"""
    local_info = get_local_pose(cid, pose, f_name)
    if local_info:
        return local_info

    sub, skel_name, atlas_name = pose_paths(cid, pose, f_name)
    bases = asset_base_urls(cid, sub)
    local_dir = os.path.join(C.DATA_DIR, cid, sub.rstrip("/")) if sub else os.path.join(C.DATA_DIR, cid)

    atlas_path = os.path.join(local_dir, atlas_name)
    pages = download_atlas(session, [base + atlas_name for base in bases], atlas_path)
    if not pages:
        print(f"  [未找到图集] {cid}/{sub}{atlas_name} (主源和镜像均失败)")
        return None

    ok_skel, _, _ = download(
        session, [base + skel_name for base in bases],
        os.path.join(local_dir, skel_name),
    )
    if not ok_skel:
        print(f"  [未找到骨骼] {cid}/{sub}{skel_name} (主源和镜像均失败)")
        return None

    missing = []
    for png in pages:
        if os.path.basename(png) != png:
            print(f"  [图集路径异常] {cid}: {png}")
            missing.append(png)
            continue
        ok, _, _ = download(session, [base + png for base in bases], os.path.join(local_dir, png))
        if not ok:
            missing.append(png)
    if missing:
        print(f"  [贴图不完整] {cid}/{sub}: 缺少 {len(missing)} 张：{', '.join(missing[:4])}")
        return None

    return {
        "pose": pose,
        "sub": sub,
        "skel": skel_name,
        "atlas": atlas_name,
        "pages": pages,
    }

def fetch_character(session, entry):
    cid = entry["id"]
    f_val = entry.get("f")
    if not f_val:
        f_val = get_index_entry(cid).get("f")
    name = entry.get("name")
    if not name or name == cid:
        name = get_index_entry(cid).get("name", cid)

    result = {"id": cid, "name": name, "poses": {}}
    if "version" in entry:
        result["version"] = entry["version"]
    if f_val:
        result["f"] = f_val

    # only_missing=True 时只补抓本地尚不存在的姿态（用于扫描补漏，不重复下载）
    only_missing = entry.get("only_missing", False)
    for pose in C.POSES:
        if only_missing and _pose_exists_local(cid, pose, f_val):
            continue
        info = fetch_pose(session, cid, pose, f_val)
        if info:
            result["poses"][pose] = info
    if not result["poses"]:
        return None
    # 头像图标（渲染好的 128x128，用作列表封面）
    icon = fetch_icon(session, cid)
    if icon:
        result["icon"] = icon
    return result


def _pose_exists_local(cid, pose, f_name=None):
    """检查整个姿态是否完整；不能只凭 skel 存在跳过缺失的贴图。"""
    return get_local_pose(cid, pose, f_name) is not None


def fetch_icon(session, cid):
    """下载 si_{id}_00_s.png 头像图标；返回本地文件名或 None。
    Cloudflare Pages 对缺失文件返回 200 + HTML，需按 content-type 甄别。"""
    dest = os.path.join(C.DATA_DIR, cid, "_icon.png")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "_icon.png"
    url = f"{C.SPRITE_BASE}/si_{cid}_00_s.png"
    try:
        r = session.get(url, timeout=30)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    if not r.headers.get("content-type", "").startswith("image"):
        return None
    dest = os.path.join(C.DATA_DIR, cid, "_icon.png")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(r.content)
    return "_icon.png"


def scan_existing_ids():
    """扫描 data/ 下已有的角色目录，返回符合 cNNN[_skin] 命名的 id 列表。

    用于补漏：Nikke-db 的 l2d.json 索引并不完整（例如 c515 及大量角色未收录），
    但 CDN 上其 fb/cover/aim 资源实际存在。这些角色往往只由 extract_local.py
    从本地客户端缓存提取到 skillcut，缺少常规立绘/半身/瞄准。
    """
    import re
    ids = []
    for name in sorted(os.listdir(C.DATA_DIR)):
        p = os.path.join(C.DATA_DIR, name)
        if not os.path.isdir(p):
            continue
        # 仅处理标准角色 id（c + 3位数字，可带 _NN 皮肤后缀）
        if re.match(r"^c\d{3}(_\d{2})?$", name):
            ids.append(name)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="只拉取指定角色 id")
    ap.add_argument("--limit", type=int, default=0, help="只拉前 N 个角色")
    ap.add_argument("--direct", action="store_true", help="不使用默认代理，直接访问资源源站")
    ap.add_argument("--new-only", action="store_true",
                    help="仅拉取本地 manifest 尚未收录的新角色/新条目")
    ap.add_argument("--scan-existing", action="store_true",
                    help="不依赖索引，扫描 data/ 已有角色目录逐个补抓 CDN 上的 fb/cover/aim")
    ap.add_argument("--only-missing", action="store_true",
                    help="仅补抓本地尚不存在的姿态（配合 --scan-existing 使用，避免重复下载）")
    args = ap.parse_args()

    if args.direct:
        C.PROXY = None
    session = make_session()

    if args.scan_existing:
        ids = scan_existing_ids()
        if args.ids:
            wanted = set(args.ids)
            ids = [i for i in ids if i in wanted]
        if args.limit:
            ids = ids[: args.limit]
        # 扫描模式下无索引名字，用 id 占位
        index = [{"id": i, "name": i, "only_missing": args.only_missing}
                 for i in ids]
        print(f"扫描到 {len(index)} 个已有角色目录，逐个探测 CDN 补抓姿态")
    else:
        print("拉取索引 ...")
        index = fetch_index(session)
        print(f"索引共 {len(index)} 个条目")

        if args.new_only and os.path.exists(C.MANIFEST_PATH):
            try:
                m = json.load(open(C.MANIFEST_PATH, encoding="utf-8"))
                have_ids = set(c["id"] for c in m.get("characters", []))
                index = [e for e in index if e["id"] not in have_ids and (not e.get("f") or e["f"].lower() not in have_ids)]
                print(f"过滤后剩余 {len(index)} 个未收录新条目")
            except Exception:
                pass

        if args.ids:
            wanted = set(args.ids)
            index = [e for e in index if e["id"] in wanted]
        if args.limit:
            index = index[: args.limit]
        print(f"本次处理 {len(index)} 个角色")

    os.makedirs(C.DATA_DIR, exist_ok=True)
    results = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        futs = {ex.submit(fetch_character, make_session(), e): e for e in index}
        done = 0
        for fut in as_completed(futs):
            e = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as ex_err:
                print(f"  [{done}/{len(index)}] {e['id']:14s} 失败: {ex_err}")
                continue
            if r:
                poses = ",".join(r["poses"].keys())
                results.append(r)
                print(f"  [{done}/{len(index)}] {e['id']:14s} OK ({poses})")
            else:
                print(f"  [{done}/{len(index)}] {e['id']:14s} 无资源，跳过")

    # 保存本次抓取到的角色元数据，并与已有历史合并，供 manifest 生成使用
    meta_path = os.path.join(C.DATA_DIR, "_fetched.json")
    all_meta = {}
    if os.path.exists(meta_path):
        try:
            for item in json.load(open(meta_path, encoding="utf-8")):
                all_meta[item["id"]] = item
        except Exception:
            pass
    for item in results:
        all_meta[item["id"]] = item

    json.dump(list(all_meta.values()), open(meta_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n完成 {len(results)}/{len(index)} 个角色，用时 {time.time()-t0:.1f}s")
    print(f"元数据已合并 ({len(all_meta)} 条) -> {meta_path}")


if __name__ == "__main__":
    main()
