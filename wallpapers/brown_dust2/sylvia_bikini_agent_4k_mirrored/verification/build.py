"""Reproduce the standalone file:// wallpaper from the existing local gallery assets."""
import base64
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored"
SOURCE = ROOT / "brown_dust2/data/costume-001006/interaction"


def build():
    catalog = json.loads((ROOT / 'brown_dust2/costume_catalog.json').read_text(encoding='utf-8'))
    costume = next(x for x in catalog['skins'] if x['id'] == 'costume-001006')
    assert (costume['character_en'], costume['skin_en'], costume['tier']) == ('Sylvia', 'Bikini Agent', 'Fated Guest')
    installed = json.loads((ROOT / 'brown_dust2/viewer/manifest.json').read_text(encoding='utf-8'))
    model = next(x for x in installed['installed'] if x['id'] == costume['id'])['roles']['interaction']
    assert model['skel'] == 'illust_dating8.skel' and model['atlas'] == 'illust_dating8.atlas'
    assert (ROOT / 'brown_dust2/viewer' / model['dir']).resolve() == SOURCE.resolve()
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "js").mkdir(exist_ok=True)
    atlas = SOURCE / "illust_dating8.atlas"
    pages = [line.strip() for line in atlas.read_text(encoding="utf-8").splitlines()
             if line.strip().endswith(".png")]
    files = [SOURCE / "illust_dating8.skel", atlas, *[SOURCE / p for p in pages]]
    assert pages == model['pages'] and len(pages) == 6
    assert all(f.is_file() and f.stat().st_size > 0 for f in files)
    uris = {}
    manifest = []
    for file in files:
        content = file.read_bytes()
        shutil.copy2(file, OUT / "assets" / file.name)
        mime = "image/png" if file.suffix == ".png" else "application/octet-stream"
        uris["assets/" + file.name] = "data:" + mime + ";base64," + base64.b64encode(content).decode("ascii")
        manifest.append({"file": "assets/" + file.name, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()})
    # Script loading works on file:// without fetch/XHR or browser security flags.
    # Originals are retained for audit; only this bundle is read during playback.
    (OUT / "js/assets.bundle.js").write_text("window.BD2_ASSETS=" + json.dumps(uris, separators=(",", ":")) + ";\n", encoding="utf-8")
    shutil.copy2(ROOT / "shared/vendor/spine-player4.1.js", OUT / "js/spine-player4.1.js")
    (OUT / "assets-manifest.json").write_text(json.dumps({
        "costume": "costume-001006", "source": "spine/illust/illust_dating/illust_dating8",
        "spine": "4.1.11", "skin": "default", "animation": "idle1", "track": 0,
        "character": costume['character_en'], "costumeName": costume['skin_en'], "tier": costume['tier'],
        "localSource": str(SOURCE.relative_to(ROOT)).replace('\\', '/'),
        "mirrored": True, "resolution": [3840, 2160],
        "runtimeSha256": hashlib.sha256((OUT / 'js/spine-player4.1.js').read_bytes()).hexdigest(),
        "files": manifest
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {OUT}: {len(files)} original assets, {sum(x['bytes'] for x in manifest):,} bytes")


if __name__ == "__main__":
    build()
