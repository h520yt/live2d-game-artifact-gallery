"""安装 NIKKE 游戏背景素材（本地图片目录/ZIP 或明文 UnityFS 客户端缓存）。

来源参考 Nikke-db 的 backgroundImages.json（只作为文件名白名单，不分发游戏图片）。
场景素材放到 nikke/data/backgrounds/；不会把非背景贴图或图集碎片误入库。
"""
import argparse
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

import config as C


NIKKE_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = NIKKE_ROOT / "background_catalog.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_BYTES = 64 * 1024 * 1024
MIN_DIMENSION = 240


def load_catalog(path=CATALOG_PATH):
    """返回按文件名小写索引的标准名称；不接受模糊匹配以避免场景错配。"""
    with Path(path).open(encoding="utf-8") as stream:
        names = json.load(stream)
    if not isinstance(names, list) or not names:
        raise ValueError("背景白名单为空或格式错误")
    result = {}
    for name in names:
        if not isinstance(name, str) or Path(name).name != name or Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"背景文件名非法: {name!r}")
        result[name.casefold()] = name
    return result


def canonical_filename(name, catalog):
    """容忍 ZIP 子目录及文件名大小写差异，但绝不推断皮肤专属关系。"""
    simple = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    return catalog.get(simple.casefold())


def valid_image(payload):
    """拒绝 HTML 伪图片、损坏文件及明显不是场景图的小图标。"""
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        return False
    try:
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            if min(width, height) < MIN_DIMENSION:
                return False
            image.verify()
        return True
    except (OSError, ValueError, UnidentifiedImageError):
        return False


def install_one(name, payload, catalog, output_dir, *, plan=False, force=False, report=None):
    """校验后以原子替换方式写入；已有文件默认不覆盖。"""
    report = report if report is not None else {}
    canonical = canonical_filename(name, catalog)
    if not canonical:
        report["unmatched"] = report.get("unmatched", 0) + 1
        return "unmatched"
    report["matched"] = report.get("matched", 0) + 1
    target = Path(output_dir) / canonical
    if target.is_symlink():
        report["rejected"] = report.get("rejected", 0) + 1
        return "rejected"
    if target.is_file() and target.stat().st_size > 0 and not force:
        report["existing"] = report.get("existing", 0) + 1
        return "existing"
    if not valid_image(payload):
        report["rejected"] = report.get("rejected", 0) + 1
        return "rejected"
    if plan:
        report["planned"] = report.get("planned", 0) + 1
        return "planned"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=str(output_dir), prefix=".scene-", suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(payload)
        os.replace(temp_path, target)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    report["installed"] = report.get("installed", 0) + 1
    print(f"  [入库] {canonical}")
    return "installed"


def scan_source(source, catalog, output_dir, *, plan=False, force=False, report=None):
    """从本地解压目录或 ZIP 导入；ZIP 不直接解压，防路径穿越和超大条目。"""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"找不到背景包: {source}")
    report = report if report is not None else {}
    if source.is_dir():
        files = sorted(path for path in source.rglob("*") if path.is_file())
        for path in files:
            if not canonical_filename(path.name, catalog):
                continue
            if path.stat().st_size > MAX_IMAGE_BYTES:
                report["oversized"] = report.get("oversized", 0) + 1
                continue
            install_one(path.name, path.read_bytes(), catalog, output_dir, plan=plan, force=force, report=report)
        return
    if not zipfile.is_zipfile(source):
        raise ValueError("仅支持背景目录或 ZIP 压缩包")
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not canonical_filename(entry.filename, catalog):
                continue
            if entry.file_size > MAX_IMAGE_BYTES or entry.compress_size > MAX_IMAGE_BYTES:
                report["oversized"] = report.get("oversized", 0) + 1
                continue
            with archive.open(entry) as stream:
                payload = stream.read(MAX_IMAGE_BYTES + 1)
            install_one(entry.filename, payload, catalog, output_dir, plan=plan, force=force, report=report)


def scan_local_cache(catalog, output_dir, *, cache_root=None, buckets=None, max_bundles=0, plan=False, force=False, report=None):
    """仅处理 UnityFS 明文包中名称明确匹配背景索引的 Texture2D。

    NKAB 加密包跳过。可能需要处理大量本地缓存，故必须显式 --scan-cache 开启。
    """
    try:
        import UnityPy
    except ImportError as exc:
        raise RuntimeError("扫描本地缓存需要先安装 UnityPy") from exc

    base = Path(cache_root or C.LOCAL_ASSETS)
    naps = base if base.name.lower() == "naps" else base / "naps"
    if not naps.is_dir():
        raise FileNotFoundError(f"未找到 NIKKE 客户端缓存: {naps}")
    report = report if report is not None else {}
    folders = [naps / b for b in buckets] if buckets else sorted(path for path in naps.iterdir() if path.is_dir())
    processed = 0
    for folder in folders:
        if not folder.is_dir():
            print(f"  [跳过] 找不到桶: {folder.name}")
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            with path.open("rb") as stream:
                head = stream.read(7)
            if head == b"NKAB":
                report["encrypted"] = report.get("encrypted", 0) + 1
                continue
            if head != b"UnityFS":
                continue
            if max_bundles and processed >= max_bundles:
                return
            processed += 1
            report["bundles"] = processed
            try:
                env = UnityPy.load(str(path))
                for obj in env.objects:
                    if obj.type.name != "Texture2D":
                        continue
                    data = obj.read()
                    canonical = canonical_filename(data.m_Name + ".png", catalog)
                    if not canonical:
                        canonical = canonical_filename(data.m_Name, catalog)
                    if not canonical:
                        continue
                    target = Path(output_dir) / canonical
                    if target.is_file() and target.stat().st_size > 0 and not force:
                        report["existing"] = report.get("existing", 0) + 1
                        continue
                    with io.BytesIO() as stream:
                        data.image.save(stream, format="PNG")
                        payload = stream.getvalue()
                    install_one(canonical, payload, catalog, output_dir, plan=plan, force=force, report=report)
            except Exception:
                report["bundle_errors"] = report.get("bundle_errors", 0) + 1
        print(f"  [缓存扫描] {folder.name}；已检查明文包 {processed}；匹配 {report.get('matched', 0)}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="导入 NIKKE 人物场景背景素材")
    parser.add_argument("--source", action="append", default=[], help="背景图片目录或 ZIP 路径，可多次指定")
    parser.add_argument("--scan-cache", action="store_true", help="额外扫描本机 UnityFS 明文客户端缓存")
    parser.add_argument("--cache-root", help="本地客户端资源根目录（默认使用 NIKKE_LOCAL_ASSETS）")
    parser.add_argument("--buckets", nargs="+", help="只扫指定的 naps 缓存桶，例如 00 01")
    parser.add_argument("--max-bundles", type=int, default=0, help="最多扫描多少个明文资源包，0 为全部")
    parser.add_argument("--plan", action="store_true", help="只分析命中素材，不写入文件")
    parser.add_argument("--force", action="store_true", help="覆盖已经存在的同名背景")
    args = parser.parse_args(argv)

    if not args.source and not args.scan_cache:
        parser.error("至少指定 --source <背景包目录/ZIP> 或 --scan-cache")
    if args.max_bundles < 0:
        parser.error("--max-bundles 必须大于等于零")
    catalog = load_catalog()
    target = Path(C.DATA_DIR) / "backgrounds"
    report = {"catalog": len(catalog), "matched": 0, "installed": 0, "existing": 0,
              "planned": 0, "rejected": 0, "oversized": 0}

    for source in args.source:
        print(f"正在核对背景素材: {source}")
        scan_source(source, catalog, target, plan=args.plan, force=args.force, report=report)
    if args.scan_cache:
        scan_local_cache(catalog, target, cache_root=args.cache_root,
                         buckets=args.buckets, max_bundles=args.max_bundles,
                         plan=args.plan, force=args.force, report=report)

    print("背景导入统计:", json.dumps(report, ensure_ascii=False))
    if args.plan:
        return 0
    from gen_nikke_manifest import main as rebuild_manifest
    rebuild_manifest()
    report_file = Path(C.DATA_DIR) / "_background_install_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
