"""Generate a small Cubism runtime test from a single public-domain photo."""

import base64
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
WHEEL = ROOT / 'py_moc3-0.1.0-py3-none-any.whl'
assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == (
    'a955c2c0d62b998de2289a3efac2f0a7c02dffe8489fa0f9bcd03470967f70e2'
)
sys.path.insert(0, str(WHEEL))
from moc3 import Moc3
from moc3._core import ElemType, SECTION_LAYOUT


# Correct the section ordering for the pinned serializer release.
# https://github.com/fifteen42/live2d-from-art/blob/main/references/direct-moc3.md
SECTION_LAYOUT[41], SECTION_LAYOUT[44] = SECTION_LAYOUT[44], SECTION_LAYOUT[41]
SECTION_LAYOUT[82], SECTION_LAYOUT[83] = SECTION_LAYOUT[83], SECTION_LAYOUT[82]

SIZE = 512
ATLAS_SIZE = (1024, 512)
PHOTO = Image.open(ROOT / 'source.png').convert('RGBA')
assert PHOTO.size == (SIZE, SIZE)
ATLAS = Image.new('RGBA', ATLAS_SIZE)
ATLAS.paste(PHOTO, (0, 0))


def closed_eye(box, contour):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    image = PHOTO.crop(box)
    for x in range(width):
        for y in range(height):
            blend = min(1.0, max(0.0, (y - 3) / (height - 6)))
            upper = PHOTO.getpixel((left + x, top + int(y * 0.17)))
            lower = PHOTO.getpixel((left + x, bottom - 3 + int(y * 0.12)))
            color = tuple(round(a + (b - a) * blend) for a, b in zip(upper, lower))
            image.putpixel((x, y), color)

    scale = 4
    image = image.resize((width * scale, height * scale), Image.Resampling.BICUBIC)
    points = [((x - left) * scale, (y - top) * scale) for x, y in contour]
    ImageDraw.Draw(image).line(points, fill=(107, 76, 55, 255), width=4, joint='curve')
    image = image.filter(ImageFilter.GaussianBlur(1.25)).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    mask = Image.new('L', (width, height))
    ImageDraw.Draw(mask).rounded_rectangle((3, 3, width - 4, height - 4), radius=5, fill=255)
    image.putalpha(mask.filter(ImageFilter.GaussianBlur(1.4)))
    return image


LEFT_BOX = (232, 95, 264, 113)
RIGHT_BOX = (188, 93, 216, 110)
ATLAS.paste(closed_eye(LEFT_BOX, [(236, 103), (241, 105), (247, 106), (253, 106), (258, 104)]), (520, 8))
ATLAS.paste(closed_eye(RIGHT_BOX, [(192, 100), (197, 103), (203, 104), (209, 103), (212, 101)]), (520, 40))


def tilt_point(x, y, angle):
    # Keep the mesh stationary outside the head and blend towards the neckline.
    radius = math.hypot((x - 226) / 118, (y - 106) / 148)
    influence = min(1.0, max(0.0, (1 - radius) / 0.36))
    top_edge = min(1.0, y / 24)
    angle = math.radians(angle) * influence**2 * (3 - 2 * influence) * top_edge
    dx, dy = x - 225, y - 180
    return (
        225 + dx * math.cos(angle) - dy * math.sin(angle),
        180 + dx * math.sin(angle) + dy * math.cos(angle),
    )


parameters = [
    ('ParamAngleZ', [-6.0, 0.0, 6.0], 0.0),
    ('ParamEyeLOpen', [0.0, 1.0], 1.0),
    ('ParamEyeROpen', [0.0, 1.0], 1.0),
]
meshes = [
    ('Portrait', (0, 0, SIZE, SIZE), (0, 0), 65, 65, [0]),
    ('ClosedLeft', LEFT_BOX, (520, 8), 5, 5, [1, 0]),
    ('ClosedRight', RIGHT_BOX, (520, 40), 5, 5, [2, 0]),
]

model = Moc3()
model.canvas.pixels_per_unit = SIZE
model.canvas.origin_x = model.canvas.origin_y = SIZE / 2
model.canvas.canvas_width = model.canvas.canvas_height = SIZE
sections = {}


def add(group, **fields):
    for field, value in fields.items():
        sections.setdefault(f'{group}.{field}', []).extend(value)


for index, (name, box, texture_origin, columns, rows, axes) in enumerate(meshes):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    points = [(left + width * col / (columns - 1), top + height * row / (rows - 1))
              for row in range(rows) for col in range(columns)]
    triangles = []
    for row in range(rows - 1):
        for col in range(columns - 1):
            corner = row * columns + col
            triangles.extend([corner, corner + columns, corner + 1,
                              corner + 1, corner + columns, corner + columns + 1])

    add('art_mesh', ids=[name], keyform_binding_band_indices=[index],
        keyform_begin_indices=[len(sections.get('art_mesh_keyform.opacities', []))],
        keyform_counts=[math.prod(len(parameters[axis][1]) for axis in axes)],
        visibles=[True], enables=[True], parent_part_indices=[-1], parent_deformer_indices=[-1],
        texture_indices=[0], drawable_flags=[4], vertex_counts=[len(points)],
        position_index_counts=[len(triangles)], uv_begin_indices=[len(sections.get('uv.xys', []))],
        position_index_begin_indices=[len(sections.get('position_index.indices', []))])
    add('keyform_binding_band', begin_indices=[len(sections.get('keyform_binding_index.indices', []))],
        counts=[len(axes)])
    add('keyform_binding_index', indices=axes)

    tx, ty = texture_origin
    for x, y in points:
        add('uv', xys=[(tx + x - left) / ATLAS_SIZE[0], (ty + y - top) / ATLAS_SIZE[1]])
    add('position_index', indices=triangles)

    for tilt in parameters[0][1]:
        for eye_open in ([0.0] if index == 0 else [0.0, 1.0]):
            add('art_mesh_keyform', opacities=[1.0 - eye_open], draw_orders=[float(index)],
                keyform_position_begin_indices=[len(sections.get('keyform_position.xys', []))])
            for x, y in points:
                px, py = tilt_point(x, y, tilt)
                add('keyform_position', xys=[px / SIZE - 0.5, py / SIZE - 0.5])
            add('keyform_position', xys=[0.0] * (-(2 * len(points)) % 16))

for index, (name, keys, default) in enumerate(parameters):
    add('parameter', ids=[name], min_values=[keys[0]], max_values=[keys[-1]],
        default_values=[default], decimal_places=[3], keyform_binding_begin_indices=[index],
        keyform_binding_counts=[1])
    add('keyform_binding', keys_begin_indices=[len(sections.get('keys.values', []))], keys_counts=[len(keys)])
    add('keys', values=keys)

count = len(meshes)
add('draw_order_group', object_begin_indices=[0], object_counts=[count],
    object_total_counts=[count], min_draw_orders=[0], max_draw_orders=[count - 1])
add('draw_order_group_object', types=[0] * count, indices=list(range(count)), group_indices=[-1] * count)

for entry in SECTION_LAYOUT:
    if entry.name in sections:
        model.counts[entry.count_idx] = len(sections[entry.name])
for entry in SECTION_LAYOUT:
    if entry.elem_type != ElemType.RUNTIME:
        default = '' if entry.elem_type == ElemType.STR64 else 0
        values = sections.get(entry.name, [default] * model.counts[entry.count_idx])
        assert len(values) == model.counts[entry.count_idx], entry.name
        model[entry.name] = values

moc_path = ROOT / 'portrait.moc3'
atlas_path = ROOT / 'portrait-texture.png'
model.to_file(moc_path)
ATLAS.save(atlas_path)
(ROOT / 'portrait.model3.json').write_text(json.dumps({
    'Version': 3,
    'FileReferences': {'Moc': moc_path.name, 'Textures': [atlas_path.name]},
    'Groups': [{'Target': 'Parameter', 'Name': 'EyeBlink', 'Ids': ['ParamEyeLOpen', 'ParamEyeROpen']}],
}, indent=2) + '\n', encoding='utf-8')

# A classic script can load these same assets when the HTML is opened as file://.
preview_assets = {
    'moc': base64.b64encode(moc_path.read_bytes()).decode('ascii'),
    'atlas': 'data:image/png;base64,' + base64.b64encode(atlas_path.read_bytes()).decode('ascii'),
}
(ROOT / 'preview-data.js').write_text(
    '// Generated by build.py.\nwindow.portraitPreviewData = ' + json.dumps(preview_assets) + ';\n',
    encoding='utf-8',
)
