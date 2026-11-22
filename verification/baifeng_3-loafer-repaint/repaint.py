"""Transfer the two new paint plates through the existing pose-to-UV map."""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "baifeng_3-foot-repaint"
OUTFITS = HERE.parents[1] / "azur_lane/config/outfits/baifeng_3"
sys.path.insert(0, str(BASE))
from build import FOOT_IDS, LEG_IDS, mesh_pixels, sample, uv_pixels, uv_projection


def apply_rgb(atlas, region, rgb):
    x, y, width, height = region
    tile = atlas[y:y + height, x:x + width]
    assert tile.shape[:2] == rgb.shape[:2]
    visible = tile[:, :, 3] > 0
    tile[visible, :3] = rgb[visible, :3]


def repaint(stage, refine=False, final_repaint=False, foreground=False):
    if final_repaint:
        evidence = HERE.parent / "baifeng_3-loafer-final"
        source, name = "outfit_01_loafer_detail", "outfit_01_final_repaint"
    elif refine:
        evidence = HERE.parent / "baifeng_3-loafer-detail"
        source, name = "outfit_01_loafers", "outfit_01_loafer_detail"
    else:
        evidence = HERE
        source, name = "outfit_01_repaint", "outfit_01_loafers"
    original_config = (OUTFITS / f"{source}.json").read_text(encoding="utf8")
    config = json.loads(original_config)
    analysis = json.loads((BASE / "analysis.json").read_text(encoding="utf8"))
    geometry = json.loads((BASE / "foot-meshes.json").read_text(encoding="utf8"))
    geometry["textures"] = geometry["textureSizes"]
    with Image.open(OUTFITS / config["atlas"]) as image:
        baseline = np.asarray(image.convert("RGBA"))
    atlas = baseline.copy()
    plate_paths = {foot: evidence / f"{foot}-{stage}-art.local.png" for foot in (["fore"] if foreground else FOOT_IDS)}
    plates = {foot: Image.open(path).convert("RGBA") for foot, path in plate_paths.items()}
    foot_for_mesh = {mesh: foot for foot, ids in FOOT_IDS.items() for mesh in ids + LEG_IDS[foot]}

    for patch in config["patches"]:
        if refine and patch.get("overlay"):
            continue  # Preserve the existing ankle overlay texels exactly.
        [id] = patch["drawables"]
        foot = foot_for_mesh[id]
        if foot not in plates:
            continue
        x, y = patch["source"]
        left, top, width, height = patch["region"]
        mesh = geometry["drawables"][id]
        coords, valid, _ = uv_projection(uv_pixels(mesh, geometry), mesh_pixels(mesh, geometry),
                                         np.asarray(mesh["triangles"]).reshape(-1, 3),
                                         (x, y, x + width, y + height))
        rgba = sample(plates[foot], coords, [0, 0, 0, 0])
        active = baseline[top:top + height, left:left + width, 3] > 0
        assert (valid & (rgba[:, :, 3] > 0))[active].all(), f"Paint missed shell texels on {id}"
        apply_rgb(atlas, patch["region"], np.rint(rgba * 255).astype(np.uint8))

    for attachment in config["attachments"]:
        [form] = attachment["forms"]
        [layer] = form["layers"]
        foot = foot_for_mesh[form["anchor"]]
        if foot not in plates:
            continue
        assert layer["id"] == "outline-extension"
        crop = tuple(analysis["extensions"][foot]["crop"])
        apply_rgb(atlas, layer["region"], np.asarray(plates[foot].crop(crop)))

    assert np.array_equal(atlas[:, :, 3], baseline[:, :, 3])
    for patch in config["patches"]:
        if "coverage" in patch:
            x, y = patch["coverage"]
            _, _, width, height = patch["region"]
            np.testing.assert_array_equal(atlas[y:y + height, x:x + width], baseline[y:y + height, x:x + width])

    if stage == "structure" or foreground:
        variant = "structure" if stage == "structure" else "preview"
        Image.fromarray(atlas).save(evidence / f"{variant}-atlas.local.png", optimize=True)
        return

    Image.fromarray(atlas).save(OUTFITS / f"{name}.png", optimize=True)
    destination = original_config.replace(config["atlas"], f"{name}.png")
    (OUTFITS / f"{name}.json").write_text(destination, encoding="utf8")


if __name__ == "__main__":
    profiles = ([], ["--refine"], ["--final-repaint"], ["--final-repaint", "--foreground"])
    if len(sys.argv) < 2 or sys.argv[1] not in ("structure", "final") or sys.argv[2:] not in profiles:
        raise SystemExit("Usage: python repaint.py {structure,final} [--refine | --final-repaint [--foreground]]")
    repaint(sys.argv[1], refine="--refine" in sys.argv, final_repaint="--final-repaint" in sys.argv,
            foreground="--foreground" in sys.argv)
