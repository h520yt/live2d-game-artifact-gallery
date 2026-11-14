"""仅下载、还原、验证菲莉西娅·鲁梅 Schwarzes Kaninchen 的 Live2D。

在仓库根目录执行：
  python azur_lane/scripts/probe_fulici.py catalog
  python azur_lane/scripts/probe_fulici.py install
  python azur_lane/scripts/probe_fulici.py check
  python azur_lane/scripts/probe_fulici.py install --direct

不会修改仓库跟踪的 manifest，避免把已有数百条模型索引缩减成一条。
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import config as C

MODEL = "fulici_2"
SKIN_ID = 407041
SKIN_EN = "Schwarzes Kaninchen"
L2D_PATH = f"live2d/{MODEL}"
COVER_PATH = f"painting/{MODEL}_rw_tex"
COVER_NAME = f"{MODEL}_rw.png"


def csv_row(csv_file, target):
    """只匹配清单中的精确资源路径，不使用前缀匹配。"""
    with open(csv_file, encoding="utf-8-sig") as fp:
        for line in fp:
            parts = line.strip().split(",")
            if len(parts) >= 3 and parts[0] == target:
                size = int(parts[1])
                digest = parts[2].strip().lower()
                if size <= 0 or len(digest) != 32 or not all(c in "0123456789abcdef" for c in digest):
                    raise ValueError(f"清单记录不合法: {target}")
                return target, size, digest
    raise FileNotFoundError(f"清单中没有 {target}，请先更新对应 hashes CSV")


def file_md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_bundle(label, entry):
    """下载失败不会被静默忽略：下载结束后强制校验大小和 md5。"""
    from dl_from_csv import download
    key, size, digest = entry
    dst = Path(C.CACHE_DIR) / Path(key)
    if dst.is_file() and dst.stat().st_size == size and file_md5(dst) == digest:
        print(f"[缓存命中] {key} ({size / 1024 / 1024:.1f} MB)")
        return dst
    print(f"[下载] {key} ({size / 1024 / 1024:.1f} MB)")
    download([label], verify=True, only={key})
    if not dst.is_file() or dst.stat().st_size != size or file_md5(dst) != digest:
        raise RuntimeError(f"下载资源未通过 MD5/大小校验: {key}；请检查网络、代理与 CDN")
    return dst


def catalog():
    path = Path(C.MANIFEST_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"缺少资源索引: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    models = [m for m in data.get("models", []) if m.get("name") == MODEL and m.get("id") == SKIN_ID]
    if len(models) != 1:
        raise RuntimeError(f"模型索引匹配数量应为1，实际 {len(models)}；请检查 manifest")
    model = models[0]
    print(f"[索引] {MODEL} | 皮肤 {model['id']} | {model.get('en')} | Cubism ver={model.get('ver')}")
    if model.get("en") != SKIN_EN:
        print("[提示] 中/英文换装名称不同步；不影响通过模型编号加载")
    print(f"[封面] {model.get('cover') or '未配置'}")
    print(f"[模型] {model.get('path')}")
    print(f"[L2D] {csv_row(Path(C.HASHES_DIR) / 'L2D.csv', L2D_PATH)}")
    return model


def _safe_file(base, relative):
    """拒绝跨目录引用（仅验证 model3.json 中相对于模型根目录的资源）。"""
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"非法相对路径: {relative}")
    return path


def check():
    catalog()
    model_dir = Path(C.MODELS_DIR) / MODEL
    model_path = model_dir / f"{MODEL}.model3.json"
    errors = []
    if not model_path.is_file():
        print(f"[未落地] {model_path} 不存在；请先执行 install")
        return False
    try:
        data = json.loads(model_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"[失败] model3.json 无法读取: {exc}")
        return False
    refs = data.get("FileReferences", {})
    required = [refs.get("Moc"), *(refs.get("Textures") or [])]
    required += [refs.get("Physics")] if refs.get("Physics") else []
    motions = refs.get("Motions") or {}
    total_motions = 0
    for group, entries in motions.items():
        for entry in entries:
            total_motions += 1
            required.append(entry.get("File"))
    if not refs.get("Moc") or not refs.get("Textures"):
        errors.append("model3 缺少 moc3 或贴图引用")
    for relative in required:
        if not relative:
            errors.append("model3 含空资源引用")
            continue
        try:
            file = _safe_file(model_dir, relative)
            if not file.is_file() or file.stat().st_size <= 0:
                errors.append(f"缺少/空文件 {relative}")
                continue
            if relative.endswith((".moc3", ".png")):
                with file.open("rb") as fp:
                    header = fp.read(8)
                if relative.endswith(".moc3") and header[:4] != b"MOC3":
                    errors.append(f"MOC3 文件头不匹配: {relative}")
                if relative.endswith(".png") and header != b"\x89PNG\r\n\x1a\n":
                    errors.append(f"PNG 文件头不匹配: {relative}")
            if relative.endswith(".json"):
                json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(f"{relative}: {exc}")
    cover = Path(C.PAINTINGS_DIR) / COVER_NAME
    print(f"[结果] moc3={'有' if refs.get('Moc') else '无'} | 贴图={len(refs.get('Textures') or [])} | 动作组={len(motions)} | 动作文件={total_motions}")
    print(f"[封面] {'已落地' if cover.is_file() else '缺少（不影响模型播放，但画廊卡片可能无图）'}")
    if total_motions == 0:
        errors.append("没有有效动作：只能检查模型静态加载，无法验证动画交互")
    if errors:
        for err in errors:
            print(f"[失败] {err}")
        return False
    print("[通过] 模型引用文件齐全；浏览器动态渲染和游戏内隐藏互动仍需人工检查")
    return True


def install(with_cover=True):
    catalog()
    entry = csv_row(Path(C.HASHES_DIR) / "L2D.csv", L2D_PATH)
    ensure_bundle("L2D", entry)

    # 只重建本模型；不要使用 build.py live2d 的无参全量模式。
    from build import build_live2d
    build_live2d(only={L2D_PATH})

    if with_cover:
        entry = csv_row(Path(C.HASHES_DIR) / "PAINTING.csv", COVER_PATH)
        bundle = ensure_bundle("PAINTING", entry)
        from rebuild_painting import rebuild
        import UnityPy
        UnityPy.config.FALLBACK_UNITY_VERSION = C.UNITY_FALLBACK_VERSION
        cover = Path(C.PAINTINGS_DIR) / COVER_NAME
        cover.parent.mkdir(parents=True, exist_ok=True)
        rebuild(str(bundle), str(cover))
        if not cover.is_file() or cover.stat().st_size == 0:
            print("[提示] 封面生成失败，不影响模型本身的验证")
    return check()


def main():
    parser = argparse.ArgumentParser(description="单独接入/验证 Schwarzes Kaninchen (fulici_2)")
    parser.add_argument("command", choices=["catalog", "install", "check"])
    parser.add_argument("--direct", action="store_true", help="关闭项目内 127.0.0.1:7897 代理，直接连接官方 CDN")
    parser.add_argument("--no-cover", action="store_true", help="仅拉 Live2D 不拉封面立绘")
    args = parser.parse_args()
    if args.direct:
        C.USE_PROXY = False
    try:
        if args.command == "catalog":
            catalog()
            ok = True
        elif args.command == "install":
            ok = install(with_cover=not args.no_cover)
        else:
            ok = check()
    except Exception as exc:
        print(f"[错误] {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.command == "install":
            print("[建议] 检查 pip install -r requirements.txt；检查网络/代理；重试不会重下已校验的包", file=sys.stderr)
        ok = False
    if ok and args.command == "install":
        print("\n启动：python -m http.server 8000")
        print("访问：http://127.0.0.1:8000/azur_lane/viewer/fulici_probe.html")
        print("原画廊： http://127.0.0.1:8000/azur_lane/viewer/  搜索 fulici_2")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
