"""Bundle the locally installed kewei_6 Live2D model for file:// playback."""

import base64
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "azur_lane/data/models/kewei_6"
OUTPUT = ROOT / "wallpapers/azur_lane/kewei_anniversary_memories"
RUNTIMES = ("live2dcubismcore.min.js", "pixi.min.js", "live2d.min.js")
MOTION = "idle5"


def build():
    settings = json.loads((SOURCE / "kewei_6.model3.json").read_text(encoding="utf-8-sig"))
    refs = settings["FileReferences"]
    motion, = refs["Motions"][MOTION]
    motion.pop("Sound", None)
    refs["Motions"] = {MOTION: [motion]}

    files = {
        refs["Moc"]: "application/octet-stream",
        refs["Physics"]: "application/json",
        motion["File"]: "application/json",
    }
    files.update(dict.fromkeys(refs["Textures"], "image/png"))

    (OUTPUT / "vendor").mkdir(parents=True, exist_ok=True)
    for filename in RUNTIMES:
        shutil.copyfile(ROOT / "shared/vendor" / filename, OUTPUT / "vendor" / filename)

    # The browser reads this as a local script, so bare file:// playback needs no server.
    bundle = OUTPUT / "model.bundle.js"
    temporary = bundle.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as out:
        out.write("window.live2dBundle = {\n  settings: ")
        json.dump(settings, out)
        out.write(",\n  assets: {\n")
        for filename, mime in files.items():
            encoded = base64.b64encode((SOURCE / filename).read_bytes()).decode("ascii")
            out.write(f"    {json.dumps(filename)}: [\"{mime}\", \"{encoded}\"],\n")
        out.write("  }\n};\n")
    temporary.replace(bundle)


if __name__ == "__main__":
    build()
