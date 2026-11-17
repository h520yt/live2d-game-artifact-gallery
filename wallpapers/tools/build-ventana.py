"""Reproduce the standalone file:// wallpaper from the existing local gallery assets."""
import base64
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "wallpapers/brown_dust2/ventana_onsen_practitioner"
SOURCE = ROOT / "brown_dust2/data/costume-067004/interaction"


def build():
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "vendor").mkdir(exist_ok=True)
    atlas = SOURCE / "illust_dating15.atlas"
    pages = [line.strip() for line in atlas.read_text(encoding="utf-8").splitlines()
             if line.strip().endswith(".png")]
    files = [SOURCE / "illust_dating15.skel", atlas, *[SOURCE / p for p in pages]]
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
    (OUT / "assets.bundle.js").write_text("window.BD2_ASSETS=" + json.dumps(uris, separators=(",", ":")) + ";\n", encoding="utf-8")
    shutil.copy2(ROOT / "shared/vendor/spine-player4.1.js", OUT / "vendor/spine-player4.1.js")
    (OUT / "assets-manifest.json").write_text(json.dumps({
        "costume": "costume-067004", "source": "spine/illust/illust_dating/illust_dating15",
        "spine": "4.1.11", "skin": "default", "animation": "idle2", "track": 0,
        "files": manifest
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {OUT}: {len(files)} original assets, {sum(x['bytes'] for x in manifest):,} bytes")


if __name__ == "__main__":
    build()
