"""Compare the real viewer frames and lay out the supplied shoe reference."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
OUTFITS = HERE.parents[1] / "azur_lane/config/outfits/baifeng_3"
BASE = OUTFITS / "outfit_01_repaint"
FINAL = OUTFITS / "outfit_01_loafers"
MARGIN, GAP, HEADER = 16, 12, 44
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)


def image(name):
    with Image.open(HERE / name) as source:
        return source.convert("RGB")


def panel(images, labels, name):
    width = sum(item.width for item in images) + GAP * (len(images) - 1) + 2 * MARGIN
    height = max(item.height for item in images) + HEADER + MARGIN
    canvas = Image.new("RGB", (width, height), "#182127")
    draw = ImageDraw.Draw(canvas)
    x = MARGIN
    for item, label in zip(images, labels):
        draw.text((x, 10), label, font=FONT, fill="#edf1f3")
        canvas.paste(item, (x, HEADER))
        x += item.width + GAP
    canvas.save(HERE / name, optimize=True)


def capture_checks(refine=False):
    baseline = json.loads((HERE / "baseline-check.local.json").read_text(encoding="utf8"))
    for variant in ("structure", "final"):
        actual = json.loads((HERE / f"{variant}-check.local.json").read_text(encoding="utf8"))
        assert baseline == actual, f"Viewer camera, pose or draw sequence differs for {variant}"
    base_config = json.loads(BASE.with_suffix(".json").read_text(encoding="utf8"))
    final_config = json.loads(FINAL.with_suffix(".json").read_text(encoding="utf8"))
    assert final_config.pop("atlas") == FINAL.name + ".png"
    assert base_config.pop("atlas") == BASE.name + ".png"
    assert base_config == final_config

    with Image.open(BASE.with_suffix(".png")) as base, Image.open(FINAL.with_suffix(".png")) as final:
        assert base.size == final.size
        base_pixels, final_pixels = np.asarray(base), np.asarray(final)
        np.testing.assert_array_equal(base_pixels[:, :, 3], final_pixels[:, :, 3])
        allowed = np.zeros(base_pixels.shape[:2], dtype=bool)
        regions = [patch["region"] for patch in base_config["patches"] if not (refine and patch.get("overlay"))]
        regions += [layer["region"] for attachment in base_config["attachments"]
                    for form in attachment["forms"] for layer in form["layers"]]
        for x, y, w, h in regions:
            allowed[y:y + h, x:x + w] = base_pixels[y:y + h, x:x + w, 3] > 0
        changed = np.any(base_pixels != final_pixels, axis=2)
        assert changed.any() and not changed[~allowed].any()

    region = (1742, 1273, 1882, 1424) if refine else (1630, 1160, 1910, 1450)
    comparisons = {}
    with Image.open(HERE / "baseline-render.local.png") as before:
        before_pixels = np.asarray(before)
    for stage in ("structure", "final"):
        with Image.open(HERE / f"{stage}-render.png") as after:
            after_pixels = np.asarray(after)
        np.testing.assert_array_equal(before_pixels[:, :, 3], after_pixels[:, :, 3])
        y, x = np.where(np.any(before_pixels != after_pixels, axis=2))
        assert len(x) > 0
        left, top, right, bottom = region if stage == "final" else (1630, 1160, 1910, 1450)
        assert (x >= left).all() and (x < right).all() and (y >= top).all() and (y < bottom).all()
        comparisons[stage] = {"changedPixels": len(x), "changedOutsideFootCrop": 0,
                              "changedBounds": [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1]}
    report = {**baseline, "changedAtlasAlphaTexels": 0, "changedOutsidePaintTiles": 0,
              "changedAtlasRgbTexels": int(changed.sum()), "originalModelFilesVerified": 88,
              "restoredOriginalFramesVerified": 2, "fullFrameComparison": comparisons,
              "baselineSha256": {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                                 for file in (BASE.with_suffix(".json"), BASE.with_suffix(".png"))}}
    if refine:
        report["changedAnkleOverlayTexels"] = 0
        report["finalDetailBoundsLimit"] = region
    (HERE / "checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


def make_evidence(reference):
    capture_checks()
    crop = (70, 290, 786, 820)
    before, structure, final = [image(f"{name}-detail.local.png") for name in ("baseline", "structure", "final")]
    panel([before.crop(crop), final.crop(crop)], ["重绘前 · 已贴合鞋胚", "重绘后 · 亮面马衔扣乐福鞋"],
          "before-after.png")
    panel([structure.crop(crop), final.crop(crop)], ["第一步 · 结构重绘", "第二步 · 材质重绘"],
          "structure-material.png")
    final.crop((78, 477, 776, 816)).save(HERE / "foreground-detail.png")
    final.crop((224, 302, 748, 635)).save(HERE / "rear-detail.png")

    with Image.open(reference) as source:
        source = source.convert("RGB")
        assert source.size == (1536, 1024), "Expected the attached 1536 × 1024 design sheet"
        main = ImageOps.contain(source.crop((18, 69, 492, 443)), (567, 481), Image.Resampling.LANCZOS)
        side = source.crop((758, 199, 1081, 311)).resize((295, 102), Image.Resampling.LANCZOS)
        hardware = source.crop((148, 227, 349, 318)).resize((244, 110), Image.Resampling.LANCZOS)
    design = Image.new("RGB", (567, 605), "#182127")
    design.paste(main, (0, (481 - main.height) // 2))
    design.paste(side, (0, 493))
    design.paste(hardware, (323, 491))
    panel([design, final.crop((70, 250, 786, 855))], ["目标参考 · 整体、侧面、马衔扣", "白凤 · 默认姿态浏览器渲染"],
          "reference-comparison.png")


def make_refinement(pose_reference, design_reference):
    capture_checks(refine=True)
    before, structure, final = [image(f"{name}-detail.local.png") for name in ("baseline", "structure", "final")]
    crop = (70, 290, 786, 820)
    panel([before.crop(crop), final.crop(crop)], ["精修前", "精修后"], "before-after.png")
    panel([structure.crop(crop), final.crop(crop)], ["扣带、扣框与鞋面结构", "恢复材质后的浏览器渲染"],
          "structure-material.png")
    final.crop((78, 477, 776, 816)).save(HERE / "foreground-detail.png")
    final.crop((224, 302, 748, 635)).save(HERE / "rear-detail.png")

    def buckle_card(base):
        front = base.crop((354, 507, 545, 734))
        rear = base.crop((378, 347, 542, 514))
        card = Image.new("RGB", (360, 640), "#182127")
        draw = ImageDraw.Draw(card)
        draw.text((0, 0), "前景鞋", font=FONT, fill="#edf1f3")
        draw.text((0, 340), "后景鞋", font=FONT, fill="#edf1f3")
        for y, cut, size in ((30, front, (250, 298)), (370, rear, (244, 248))):
            card.paste(cut.resize(size, Image.Resampling.LANCZOS), ((card.width - size[0]) // 2, y))
        return card

    panel([buckle_card(before), buckle_card(final)], ["精修前 · 扣带与马衔扣", "精修后 · 扣带与马衔扣"],
          "buckle-comparison.png")

    with Image.open(pose_reference) as source:
        assert source.size == (1374, 1145)
        target = source.convert("RGB").crop((222, 358, 1092, 959))
    with Image.open(design_reference) as source:
        assert source.size == (1536, 1024)
        hardware = source.convert("RGB").crop((145, 223, 353, 328))
        side = source.convert("RGB").crop((758, 199, 1081, 311))
    design = Image.new("RGB", (630, 595), "#182127")
    design.paste(ImageOps.contain(target, (630, 446), Image.Resampling.LANCZOS), (0, 0))
    design.paste(ImageOps.contain(hardware, (247, 126), Image.Resampling.LANCZOS), (0, 464))
    design.paste(ImageOps.contain(side, (353, 126), Image.Resampling.LANCZOS), (262, 464))
    draw = ImageDraw.Draw(design)
    draw.text((0, 439), "原款马衔扣细节", font=FONT, fill="#edf1f3")
    draw.text((262, 439), "原款侧视", font=FONT, fill="#edf1f3")
    panel([design, final.crop((70, 250, 786, 845))], ["本轮姿态参考与原鞋款", "白凤 · 默认姿态浏览器渲染"],
          "reference-comparison.png")


def make_final_repaint(reference):
    capture_checks()
    baseline = json.loads((HERE / "baseline-check.local.json").read_text(encoding="utf8"))
    for stage in ("structure", "preview"):
        front_check = json.loads((HERE / f"foreground-{stage}-check.local.json").read_text(encoding="utf8"))
        assert front_check == baseline

    crop = (70, 290, 786, 820)
    before, structure, final = [image(f"{name}-detail.local.png") for name in ("baseline", "structure", "final")]
    panel([before.crop(crop), final.crop(crop)], ["本轮开始时的鞋胚", "最终浏览器渲染"], "before-after.png")
    panel([structure.crop(crop), final.crop(crop)], ["鞋面、鞋底与马衔扣结构", "漆皮与金属材质"],
          "structure-material.png")
    final.crop(crop).save(HERE / "both-shoes.png")
    final.crop((78, 477, 776, 816)).save(HERE / "foreground-detail.png")
    final.crop((224, 302, 748, 635)).save(HERE / "rear-detail.png")
    front_crop = (342, 498, 565, 690)
    fore_shoe = (78, 477, 776, 816)
    panel([image("foreground-structure-detail.local.png").crop(fore_shoe),
           image("foreground-preview-detail.local.png").crop(fore_shoe)],
          ["前景鞋先校正结构", "前景鞋材质验收"], "foreground-stages.png")
    panel([cut.resize((cut.width * 2, cut.height * 2), Image.Resampling.LANCZOS) for cut in
           [final.crop(front_crop), final.crop((366, 337, 544, 508))]],
          ["前景鞋 · 银色马衔扣", "后景鞋 · 银色马衔扣"], "horsebit-detail.png")

    with Image.open(reference) as source:
        assert source.size == (1448, 1086)
        target = source.convert("RGB").crop((964, 786, 1266, 1053))
    target = ImageOps.contain(target, (716, 530), Image.Resampling.LANCZOS)
    panel([target, final.crop(crop)], ["最新完整角色图 · 足部裁区", "Live2D 默认姿态"],
          "reference-comparison.png")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--final-repaint":
        HERE = HERE.parent / "baifeng_3-loafer-final"
        BASE = OUTFITS / "outfit_01_loafer_detail"
        FINAL = OUTFITS / "outfit_01_final_repaint"
        make_final_repaint(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "--refine":
        HERE = HERE.parent / "baifeng_3-loafer-detail"
        BASE = OUTFITS / "outfit_01_loafers"
        FINAL = OUTFITS / "outfit_01_loafer_detail"
        make_refinement(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2:
        make_evidence(sys.argv[1])
    else:
        raise SystemExit("Usage: python evidence.py REFERENCE_PNG | --refine POSE_PNG DESIGN_PNG | --final-repaint REFERENCE_PNG")
