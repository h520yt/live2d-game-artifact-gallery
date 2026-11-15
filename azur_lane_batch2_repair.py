"""修复碧蓝航线第二批：UnityPy 回退版本、输出验证、缺失缩略图提示。

把此文件放在 live2d-game-artifact-gallery 仓库根目录：
  python azur_lane_batch2_repair.py --check
  python azur_lane_batch2_repair.py
  python azur_lane/scripts/install_batch2.py --force-paintings

本脚本不会下载游戏资源，也不会 git commit / push；可重复执行。
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

FALLBACK_SETTING = '''import config as C

# 子进程单独加载 Unity 资源时也必须配置版本回退（与 build.py 保持一致）。
UnityPy.config.FALLBACK_UNITY_VERSION = C.UNITY_FALLBACK_VERSION
'''

PNG_VALIDATOR = '''def valid_png(path: Path) -> bool:
    """先验证 PNG 文件头，避免将旧的空文件误认作成功立绘。"""
    try:
        with path.open("rb") as fp:
            return fp.read(8) == b"\\x89PNG\\r\\n\\x1a\\n"
    except OSError:
        return False


def valid_live2d_model(model_dir: Path, name: str) -> bool:
    """有效模型至少需要 settings、MOC3 以及全部贴图。"""
    try:
        model3 = model_dir / f"{name}.model3.json"
        refs = json.loads(model3.read_text(encoding="utf-8"))["FileReferences"]
        moc = refs.get("Moc")
        textures = refs.get("Textures")
        if not isinstance(moc, str) or not moc or not isinstance(textures, list) or not textures:
            return False
        with (model_dir / moc).open("rb") as fp:
            if fp.read(4) != b"MOC3":
                return False
        return all(isinstance(t, str) and t and (model_dir / t).is_file()
                   and (model_dir / t).stat().st_size > 0 for t in textures)
    except (OSError, ValueError, KeyError, TypeError):
        return False


'''

GEN_MODEL_VALIDATOR = '''def valid_model_files(model_dir, name):
    """不把缺失 moc3 / 贴图的残缺模型放进展示柜清单。"""
    try:
        path = os.path.join(model_dir, f"{name}.model3.json")
        with open(path, encoding="utf-8") as fp:
            refs = json.load(fp)["FileReferences"]
        moc = refs.get("Moc")
        textures = refs.get("Textures")
        if not isinstance(moc, str) or not moc or not isinstance(textures, list) or not textures:
            return False
        with open(os.path.join(model_dir, moc), "rb") as fp:
            if fp.read(4) != b"MOC3":
                return False
        return all(isinstance(t, str) and t and os.path.isfile(os.path.join(model_dir, t))
                   and os.path.getsize(os.path.join(model_dir, t)) > 0 for t in textures)
    except (OSError, ValueError, TypeError, KeyError):
        return False


'''


def replace_once(text: str, before: str, after: str, path: str) -> str:
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f"{path}：预期唯一匹配片段，实际匹配 {count} 处；停止，避免误改现有代码")
    return text.replace(before, after, 1)


def patch_rebuild(src: str) -> str:
    if 'UnityPy.config.FALLBACK_UNITY_VERSION = C.UNITY_FALLBACK_VERSION' in src:
        return src
    return replace_once(src, 'import sys\n', 'import sys\n' + FALLBACK_SETTING, 'rebuild_painting.py')


def patch_installer(src: str) -> str:
    if 'def valid_live2d_model(' not in src:
        src = replace_once(src, 'def pick_skins(', PNG_VALIDATOR + 'def pick_skins(', 'install_batch2.py')
    if 'if valid_png(output) and not args.force_paintings:' not in src:
        old = '''        if output.is_file() and output.stat().st_size > 0 and not args.force_paintings:
            print(f"  [跳过] {output.name}")
            continue
        bundle = cache_dir.joinpath(*row.path.split("/"))
        print(f"  [重建] {output.name}", flush=True)
        # 原脚本在部分资源出错时返回码可能仍为 0，故还需验证输出存在且非空。
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "rebuild_painting.py"), str(bundle), str(output)], check=False)
        if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            paint_errors[row.path] = f"rebuild_failed_{result.returncode}"
            print(f"  [失败] {row.path}", flush=True)
'''
        new = '''        if valid_png(output) and not args.force_paintings:
            print(f"  [跳过] {output.name}")
            continue
        bundle = cache_dir.joinpath(*row.path.split("/"))
        # 使用临时输出，重建失败不覆盖既有的正常立绘文件。
        temporary = output.with_name(f".{output.stem}.batch2.tmp.png")
        if temporary.exists():
            temporary.unlink()
        print(f"  [重建] {output.name}", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "rebuild_painting.py"), str(bundle), str(temporary)], check=False)
        if result.returncode != 0 or not valid_png(temporary):
            paint_errors[row.path] = f"rebuild_failed_{result.returncode}"
            temporary.unlink(missing_ok=True)
            print(f"  [失败] {row.path}", flush=True)
        else:
            os.replace(temporary, output)
'''
        src=replace_once(src, old, new, 'install_batch2.py output')
    if 'valid_png(painting_output(r, painting_dir))' not in src:
        src=replace_once(src, 'painting_output(r, painting_dir).is_file()', 'valid_png(painting_output(r, painting_dir))', 'install_batch2.py painting check')
    if 'valid_live2d_model(model_dir / Path(r.path).name, Path(r.path).name)' not in src:
        src=replace_once(src, '(model_dir / Path(r.path).name / (Path(r.path).name + ".model3.json")).is_file()', 'valid_live2d_model(model_dir / Path(r.path).name, Path(r.path).name)', 'install_batch2.py model check')
    return src


def patch_manifest(src: str) -> str:
    if 'def valid_model_files(' not in src:
        src=replace_once(src,'def moc3_version(', GEN_MODEL_VALIDATOR+'def moc3_version(', 'gen_manifest.py validator')
    if 'if valid_model_files(os.path.join(C.MODELS_DIR, d), d):' not in src:
        src=replace_once(src, '        if os.path.exists(m3):\n', '        if valid_model_files(os.path.join(C.MODELS_DIR, d), d):\n', 'gen_manifest.py filtering')
    return src


def patch_viewer(src: str) -> str:
    if '暂无预览 · 请检查立绘安装' in src:
        return src
    old = '''  card.innerHTML = `<div class="thumb">${badge}${leftBadge}<img loading="lazy" src="${escapeHtml(img)}" alt="${escapeHtml(alt)}"></div>${info}`;
  card.onclick = onClick;'''
    new = '''  card.innerHTML = `<div class="thumb">${badge}${leftBadge}<img loading="lazy" src="${escapeHtml(img)}" alt="${escapeHtml(alt)}"></div>${info}`;
  const preview = card.querySelector('img');
  const showMissing = () => {
    if (!preview.isConnected) return;
    preview.remove();
    const message = document.createElement('span');
    message.textContent = '暂无预览 · 请检查立绘安装';
    message.style.cssText = 'display:flex;align-items:center;justify-content:center;width:100%;height:100%;padding:18px;text-align:center;font-size:12px;color:#a5b9cc';
    card.querySelector('.thumb').appendChild(message);
  };
  if (!img) showMissing();
  else preview.addEventListener('error', showMissing, { once: true });
  card.onclick = onClick;'''
    return replace_once(src, old, new, 'viewer/index.html')


PATCHES = {
    'azur_lane/scripts/rebuild_painting.py': patch_rebuild,
    'azur_lane/scripts/install_batch2.py': patch_installer,
    'azur_lane/scripts/gen_manifest.py': patch_manifest,
    'azur_lane/viewer/index.html': patch_viewer,
}


def patch_all(root: Path, check_only: bool = False) -> list[str]:
    changes = {}
    # 预检全部文件，任何一处不符合已知仓库版本就不写入。
    for filename, fn in PATCHES.items():
        path=root / filename
        if not path.is_file():
            raise FileNotFoundError(f'找不到 {path}，请从仓库根目录运行')
        raw=path.read_bytes()
        newline=b'\r\n' if b'\r\n' in raw else b'\n'
        before=raw.decode('utf-8-sig').replace('\r\n','\n')
        after=fn(before)
        compile(after, filename, 'exec') if filename.endswith('.py') else None
        if after!=before:
            changes[path]=after.replace('\n', newline.decode('ascii')).encode('utf-8')
    if not check_only:
        for path,data in changes.items():
            path.write_bytes(data)
    return [str(path.relative_to(root)) for path in changes]


def main(argv=None):
    parser=argparse.ArgumentParser(description='修复碧蓝航线第二批 UnityPy/缩略图安装问题')
    parser.add_argument('--check', action='store_true', help='只检查需要修改的文件，不写入')
    args=parser.parse_args(argv)
    root=Path.cwd()
    try:
        changes=patch_all(root,args.check)
    except Exception as exc:
        print(f'修复中止：{exc}',file=sys.stderr)
        return 1
    if changes:
        print(('需要修复' if args.check else '已修复')+f' {len(changes)} 个文件：')
        for p in changes:print('  '+p)
    else:print('已是修复后的代码，无需重复修改')
    if not args.check:
        print('下一步：python azur_lane/scripts/install_batch2.py --force-paintings')
        print('然后启动 python -m http.server 8000，重新打开碧蓝航线展厅')
        print('未执行 git 提交或资源下载。')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
