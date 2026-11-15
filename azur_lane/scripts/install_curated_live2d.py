"""定向安装 5 款已确认在 Azur Lane 展示柜索引中的 Live2D 换装。

  python azur_lane/scripts/install_curated_live2d.py list
  python azur_lane/scripts/install_curated_live2d.py install
  python azur_lane/scripts/install_curated_live2d.py check
  python azur_lane/scripts/install_curated_live2d.py install --only ougen_8 aijier_4
  python azur_lane/scripts/install_curated_live2d.py install --direct

仅处理目标模型及对应原画变体；绝不写入/重生 viewer/manifest.json。
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import config as C

# 对照项目已有 manifest 和 hash 清单确认的 skin ID。
TARGETS = {
    "jianwu_2": (503011, "建武｜妆点，只为今夜"),
    "aijier_4": (499053, "埃吉尔｜私密闲暇时"),
    "ougen_8": (403037, "欧根亲王｜微醺与试探的距离"),
    "luoen_4": (499012, "罗恩｜苍翠的安眠曲"),
    "shengluyisi_5": (102134, "圣路易斯｜邮轮上的诱人午后"),
}
NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_hashes(label):
    """path -> (path, size, md5)：只用 CSV 中精确资源路径。"""
    file = Path(C.HASHES_DIR) / (label + ".csv")
    if not file.is_file():
        raise FileNotFoundError(f"找不到 {file}，请先运行项目已有清单更新脚本")
    result = {}
    with file.open("r", encoding="utf-8-sig", newline="") as fp:
        for row in csv.reader(fp):
            if len(row) < 3:
                continue
            key, size_s, digest = [s.strip() for s in row[:3]]
            try:
                size = int(size_s)
            except ValueError:
                continue
            digest = digest.lower()
            if size > 0 and re.fullmatch(r"[0-9a-f]{32}", digest):
                if key in result and result[key] != (key, size, digest):
                    raise ValueError(f"hash 清单冲突：{label}/{key}")
                result[key] = (key, size, digest)
    return result


def catalog(selected):
    """从已提交的展示柜索引反查模型与同款所有原画变体。"""
    data = json.loads(Path(C.MANIFEST_PATH).read_text(encoding="utf-8"))
    models, characters = data.get("models", []), data.get("characters", [])
    l2d_hashes, paint_hashes = read_hashes("L2D"), read_hashes("PAINTING")
    entries = []
    for name in selected:
        skin_id, display = TARGETS[name]
        matching_models = [m for m in models if m.get("name") == name and m.get("id") == skin_id]
        matching_skins = [c for c in characters if c.get("skin") == skin_id]
        if len(matching_models) != 1 or len(matching_skins) != 1:
            raise ValueError(f"{name} 模型/皮肤索引不唯一或缺失：model={len(matching_models)}, skin={len(matching_skins)}")
        model, skin = matching_models[0], matching_skins[0]
        if model.get("path") != f"../data/models/{name}/{name}.model3.json":
            raise ValueError(f"{name} 模型路径不匹配：{model.get('path')}")
        l2d_key = f"live2d/{name}"
        if l2d_key not in l2d_hashes:
            raise ValueError(f"L2D.csv 缺少 {l2d_key}")
        paintings = []
        for item in skin.get("items", []):
            painting_name = item.get("name", "")
            if not NAME_PATTERN.fullmatch(painting_name):
                raise ValueError(f"{name} 中存在非法立绘名称：{painting_name!r}")
            key = f"painting/{painting_name}_tex"
            if key not in paint_hashes:
                raise ValueError(f"PAINTING.csv 缺少 {key}")
            if item.get("path") != f"../data/paintings/{painting_name}.png":
                raise ValueError(f"{name} 中立绘路径不匹配：{item.get('path')}")
            paintings.append((painting_name, paint_hashes[key]))
        if not paintings:
            raise ValueError(f"{name} 没有原画变体索引")
        entries.append({"name": name, "id": skin_id, "label": display, "ver": model.get("ver"),
                        "l2d": l2d_hashes[l2d_key], "paintings": paintings})
    return entries


def hash_md5(path):
    d = hashlib.md5()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()


def valid_cache(row):
    key, size, md5 = row
    file = Path(C.CACHE_DIR) / Path(key)
    return file.is_file() and file.stat().st_size == size and hash_md5(file) == md5


def download_rows(label, rows):
    """仅下载缺失/损坏 bundle，并二次强制核对大小及 MD5。"""
    pending = {r[0] for r in rows if not valid_cache(r)}
    if pending:
        print(f"[{label}] 待下载 {len(pending)} 个 bundle")
        from dl_from_csv import download
        download([label], verify=True, only=pending)
    for row in rows:
        if not valid_cache(row):
            raise RuntimeError(f"下载/校验失败：{row[0]}（可重试，已下载的正确文件可复用）")
    print(f"[{label}] {len(rows)} 个 bundle MD5 校验通过")


def safe_relative(base, rel):
    p = (base / rel).resolve()
    if p != base.resolve() and base.resolve() not in p.parents:
        raise ValueError(f"非法资源相对路径：{rel}")
    return p


def check_model(name):
    """返回 (是否通过, 诊断, 动作数量)。检查引用而非仅看 moc3 是否存在。"""
    base = Path(C.MODELS_DIR) / name
    model3 = base / (name + ".model3.json")
    if not model3.is_file():
        return False, "缺少 model3.json", 0
    try:
        data = json.loads(model3.read_text(encoding="utf-8"))
        refs = data.get("FileReferences", {})
        files = [refs.get("Moc"), *(refs.get("Textures") or [])]
        if refs.get("Physics"):
            files.append(refs["Physics"])
        motions = [m.get("File") for group in (refs.get("Motions") or {}).values() for m in group]
        files.extend(motions)
        if not refs.get("Moc") or not refs.get("Textures") or not motions:
            return False, "缺少 moc3 / 贴图 / 动作引用", len(motions)
        for rel in files:
            if not isinstance(rel, str) or not rel:
                return False, "包含空资源文件名", len(motions)
            f = safe_relative(base, rel)
            if not f.is_file() or f.stat().st_size == 0:
                return False, f"缺少文件 {rel}", len(motions)
            if f.suffix == ".moc3":
                with f.open("rb") as fp:
                    if fp.read(4) != b"MOC3":
                        return False, f"损坏的 moc3：{rel}", len(motions)
            if f.suffix == ".png":
                with f.open("rb") as fp:
                    if fp.read(8) != PNG_SIGNATURE:
                        return False, f"损坏的贴图：{rel}", len(motions)
            if f.suffix == ".json":
                json.loads(f.read_text(encoding="utf-8"))
        return True, f"moc3/贴图/动作引用齐全，动作 {len(motions)} 个", len(motions)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return False, str(exc), 0


def valid_painting(name):
    file = Path(C.PAINTINGS_DIR) / (name + ".png")
    if not file.is_file() or file.stat().st_size < 8:
        return False
    with file.open("rb") as fp:
        return fp.read(8) == PNG_SIGNATURE


def install(entries, with_paintings=True):
    all_l2d = [e["l2d"] for e in entries]
    all_paint = [r for e in entries for _, r in e["paintings"]] if with_paintings else []
    print(f"安装目标：{len(entries)} 款 Live2D，{len(all_paint)} 张立绘；不更改 manifest。")
    download_rows("L2D", all_l2d)
    if all_paint:
        download_rows("PAINTING", all_paint)

    to_build = [e["name"] for e in entries if not check_model(e["name"])[0]]
    if to_build:
        print(f"[Live2D] 开始还原：{', '.join(to_build)}")
        from build import build_live2d
        build_live2d(only={f"live2d/{x}" for x in to_build})
    else:
        print("[Live2D] 已有模型完整，跳过重复还原")

    if all_paint:
        pending = [(name, row) for e in entries for name, row in e["paintings"] if not valid_painting(name)]
        if pending:
            import UnityPy
            from rebuild_painting import rebuild
            UnityPy.config.FALLBACK_UNITY_VERSION = C.UNITY_FALLBACK_VERSION
            Path(C.PAINTINGS_DIR).mkdir(parents=True, exist_ok=True)
            for i, (name, row) in enumerate(pending, 1):
                print(f"[立绘 {i}/{len(pending)}] {name}")
                bundle = Path(C.CACHE_DIR) / Path(row[0])
                output = Path(C.PAINTINGS_DIR) / (name + ".png")
                try:
                    rebuild(str(bundle), str(output))
                except Exception as exc:
                    print(f"  还原失败：{exc}")
        else:
            print("[立绘] 已有变体完整，跳过重复还原")
    return check(entries, with_paintings=with_paintings)


def check(entries, with_paintings=True):
    ok = True
    print("\n===== 安装结果（文件级检查）=====")
    for e in entries:
        model_ok, info, _ = check_model(e["name"])
        misses = [name for name, _ in e["paintings"] if not valid_painting(name)] if with_paintings else []
        good = model_ok and not misses
        ok &= good
        print(f"{'通过' if good else '未通过'} | {e['label']} | {e['name']} | {info}"
              + (f" | 缺少立绘：{', '.join(misses)}" if misses else ""))
    if ok:
        print("\n所有目标文件齐全；实际渲染及游戏内高级交互仍需在浏览器验证。")
    else:
        print("\n存在未完成项；修复原因后重新执行 install 可断点续跑。")
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description="定向安装 5 款碧蓝航线 Live2D 换装")
    parser.add_argument("command", choices=["list", "install", "check"], help="列清单、安装或检查")
    parser.add_argument("--only", nargs="+", choices=list(TARGETS), help="只处理指定模型名，默认五款")
    parser.add_argument("--direct", action="store_true", help="不使用项目默认本地代理，直连官方 CDN")
    parser.add_argument("--no-paintings", action="store_true", help="只处理 Live2D，不下载和生成立绘变体")
    args = parser.parse_args(argv)
    if args.direct:
        C.USE_PROXY = False
    chosen = list(dict.fromkeys(args.only or TARGETS))
    try:
        entries = catalog(chosen)
        if args.command == "list":
            for e in entries:
                model_mib = e["l2d"][1] / 1024**2
                paint_mib = sum(r[1] for _, r in e["paintings"]) / 1024**2
                print(f"{e['label']}: {e['name']} | 皮肤ID {e['id']} | Cubism v{e['ver']} | "
                      f"L2D {model_mib:.1f} MiB | 立绘 {len(e['paintings'])} 张，bundle {paint_mib:.1f} MiB")
            print("以上为 Unity bundle 下载体积，解包后空间占用会更大")
            return 0
        if args.command == "check":
            ok = check(entries, with_paintings=not args.no_paintings)
        else:
            ok = install(entries, with_paintings=not args.no_paintings)
        if ok:
            print("\n启动展示柜：在仓库根目录运行 python -m http.server 8000")
            print("浏览器打开 http://127.0.0.1:8000/azur_lane/viewer/ ，搜索模型名或皮肤英文名")
        return 0 if ok else 1
    except Exception as exc:
        print(f"[错误] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("检查 Python 依赖、网络代理、manifest.json、hashes CSV 后重试", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
