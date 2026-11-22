"""Compile the default-pose paintings into per-ArtMesh Cubism outfit tiles.

Run capture.cjs and capture.cjs --art first. Requires Pillow and NumPy.
All painting coordinates refer to the recorded viewer framebuffer crop.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'azur_lane/data/models/baifeng_3'
OUTPUT = ROOT / 'azur_lane/config/outfits/baifeng_3'
FRAME = (1630, 1160, 1910, 1450)
WIDTH = FRAME[2] - FRAME[0]
HEIGHT = FRAME[3] - FRAME[1]
ART_SCALE = 3
GUTTER = 4
FOOT_IDS = {
    'fore': ['ArtMesh13', 'ArtMesh214', *(f'ArtMesh{i}' for i in range(230, 236))],
    'rear': ['ArtMesh18', 'ArtMesh156'],
}
LEG_IDS = {'fore': ['ArtMesh12', 'ArtMesh100'], 'rear': ['ArtMesh17', 'ArtMesh216', 'ArtMesh217']}
COLORS = ['#52e2d1', '#f6a0d0', '#e0b476', '#b8c8ff', '#f3e27b', '#98e2ab', '#ffaa97', '#b1adf1']


def load_local(name):
    with Image.open(HERE / f'{name}.local.png') as image:
        return image.convert('RGBA')


def mesh_pixels(mesh, geometry):
    vertices = np.array(mesh['vertices']).reshape(-1, 2)
    width, height = geometry['canvas']
    scale = np.array([width / 2, -height / 2])
    matrix = np.array(geometry['matrix']).reshape(4, 4)
    projected = (vertices @ matrix[:2, :2] + matrix[3, :2]) * scale + [width / 2, height / 2]
    return projected - FRAME[:2]


def uv_pixels(mesh, geometry):
    uv = np.array(mesh['uv']).reshape(-1, 2)
    return (uv * [1, -1] + [0, 1]) * geometry['textures'][mesh['texture']]


def uv_bounds(uv, image):
    x, y = np.maximum(np.floor(uv.min(axis=0)).astype(int) - GUTTER, 0)
    right, bottom = np.minimum(np.ceil(uv.max(axis=0)).astype(int) + GUTTER, image.size)
    return int(x), int(y), int(right), int(bottom)


def uv_projection(uv, projected, triangles, bounds):
    """Map atlas texel centers into the pose by barycentric interpolation.

    Favor a triangle interior over the small edge bleed used for bilinear
    filtering. Report interior overlaps that project to different positions.
    """
    x, y, right, bottom = bounds
    shape = (bottom - y, right - x)
    priority = np.full(shape, -np.inf)
    xy = np.zeros((*shape, 2))
    overlaps = np.zeros(shape, dtype=bool)
    for triangle in triangles:
        a, b, c = uv[triangle] - [x, y]
        basis = np.array([b - a, c - a]).T
        if abs(np.linalg.det(basis)) < 1e-6:
            continue
        left, top = np.maximum(np.floor(np.minimum(np.minimum(a, b), c)).astype(int) - 2, 0)
        end_x, end_y = np.minimum(np.ceil(np.maximum(np.maximum(a, b), c)).astype(int) + 2, shape[::-1])
        row, col = np.mgrid[top:end_y, left:end_x] + .5
        inverse = np.linalg.inv(basis)
        ab = (np.stack((col, row), axis=-1) - a) @ inverse.T
        weights = np.dstack((1 - ab.sum(axis=-1), ab))
        gradients = np.vstack((-inverse.sum(axis=0), inverse))
        distance = (weights / np.linalg.norm(gradients, axis=1)).min(axis=-1)
        target = np.s_[top:end_y, left:end_x]
        old = priority[target]
        pose = weights @ projected[triangle]
        overlaps[target] |= (old > .05) & (distance > .05) & (np.linalg.norm(xy[target] - pose, axis=-1) > .5)
        replace = (distance > old) & (distance > -1.8)
        xy[target][replace] = pose[replace]
        old[replace] = distance[replace]
    return xy, np.isfinite(priority), overlaps


def sample(image, xy, outside):
    """Bilinear interpolation, with transparent RGB weighted by alpha."""
    pixels = np.array(image, dtype=np.float32) / 255
    pixels[:, :, :3] *= pixels[:, :, 3:]
    points = xy * ART_SCALE - .5
    inside = (points >= 0).all(axis=-1) & (points < [image.width - 1, image.height - 1]).all(axis=-1)
    x, y = points[inside].T
    i, j = np.floor(x).astype(int), np.floor(y).astype(int)
    u, v = (x - i)[:, None], (y - j)[:, None]
    output = np.empty((*xy.shape[:2], 4), dtype=np.float32)
    output[:] = outside
    output[inside] = (pixels[j, i] * (1 - u) + pixels[j, i + 1] * u) * (1 - v) + (
        pixels[j + 1, i] * (1 - u) + pixels[j + 1, i + 1] * u) * v
    alpha = output[:, :, 3:]
    np.divide(output[:, :, :3], alpha, out=output[:, :, :3], where=alpha > 0)
    return output


def to_image(pixels):
    return Image.fromarray(np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8))


class Atlas:
    def __init__(self):
        self.image = Image.new('RGBA', (2048, 2048))
        self.x = GUTTER
        self.y = GUTTER
        self.height = 0

    def add(self, tile):
        width, height = tile.size
        if self.x + width + GUTTER > self.image.width:
            self.x, self.y = GUTTER, self.y + self.height + GUTTER
            self.height = 0
        assert self.y + height + GUTTER <= self.image.height
        region = [self.x, self.y, width, height]
        self.image.paste(tile, (self.x, self.y))
        self.x += width + GUTTER
        self.height = max(self.height, height)
        return region

    def save(self, path):
        self.image.crop((0, 0, self.image.width, self.y + self.height + GUTTER)).save(path, optimize=True)


def plot_uv(entries, originals):
    cards = Image.new('RGB', (1200, 820), '#1b222a')
    draw = ImageDraw.Draw(cards)
    font = ImageFont.load_default(size=16)
    draw.text((20, 14), 'Original texture_00.png  /  Cubism UV triangles', fill='white', font=font)
    preview = originals[0].resize((540, 540), Image.Resampling.LANCZOS)
    cards.paste(preview, (20, 46), preview)
    for index, (id, mesh) in enumerate(entries.items()):
        uv, triangles, bounds = mesh['uv'], mesh['triangles'], mesh['bounds']
        tint = COLORS[index % len(COLORS)]
        x, y, right, bottom = bounds
        box = 20 + x * 540 / 4096, 46 + y * 540 / 4096, 20 + right * 540 / 4096, 46 + bottom * 540 / 4096
        draw.rectangle(box, outline=tint, width=2)
        column, row = index % 3, index // 3
        ox, oy = 580 + column * 202, 47 + row * 153
        draw.rectangle((ox, oy, ox + 193, oy + 143), outline='#3b4853')
        draw.text((ox + 7, oy + 6), id, fill=tint, font=font)
        draw.text((ox + 7, oy + 121), f'{x}, {y}   {right-x} × {bottom-y}', fill='#d6d9dc')
        crop = originals[0].crop(bounds)
        ratio = min(178 / crop.width, 92 / crop.height)
        crop = crop.resize((max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio))))
        ox, oy = ox + 8, oy + 27
        cards.paste(crop, (ox, oy), crop)
        points = (uv - [x, y]) * ratio + [ox, oy]
        for a, b, c in points[triangles]:
            draw.line([tuple(a), tuple(b), tuple(c), tuple(a)], fill=tint, width=1)
    cards.save(HERE / 'original-uv.png')


def plot_meshes(entries):
    original = Image.open(HERE / 'original.png').crop(FRAME)
    zoom = 3
    figure = Image.new('RGB', (WIDTH * zoom * 2, HEIGHT * zoom), '#202830')
    for index, foot in enumerate(FOOT_IDS):
        ids = [id for id, mesh in entries.items() if mesh['foot'] == foot]
        offset = WIDTH * zoom * index
        figure.paste(original.resize((WIDTH * zoom, HEIGHT * zoom)), (offset, 0))
        draw = ImageDraw.Draw(figure)
        for id in ids:
            mesh = entries[id]
            color = COLORS[list(entries).index(id) % len(COLORS)]
            points = mesh['projected'] * zoom + [offset, 0]
            for a, b, c in points[mesh['triangles']]:
                draw.line([tuple(a), tuple(b), tuple(c), tuple(a)], fill=color, width=1)
            y = 16 + ids.index(id) * 22
            draw.text((offset + 14, y), id, fill=color, stroke_width=2, stroke_fill='#201824',
                      font=ImageFont.load_default(size=17))
    figure.save(HERE / 'pose-meshes.png')


def outline_card(foot, silhouette, art, extension):
    panel = Image.new('RGB', art.size, '#242932')
    panel.paste(art, mask=art.getchannel('A'))
    panel.paste('#bc7ad1', mask=extension.getchannel('A').point(lambda a: a * .64))
    original = silhouette.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    edge = np.asarray(original.filter(ImageFilter.MaxFilter(3))) - np.asarray(original.filter(ImageFilter.MinFilter(3)))
    panel.paste('#55e7d8', mask=Image.fromarray(edge[:, :]))
    draw = ImageDraw.Draw(panel)
    draw.text((20, 14), f'{foot.upper()}  /  native alpha outline', fill='#55e7d8', font=ImageFont.load_default(size=20))
    draw.text((20, 44), 'Violet = outline extension', fill='#d697e8', font=ImageFont.load_default(size=20))
    return panel


def supplement(atlas, geometry, anchor, paint, keep_alpha, foot_alpha):
    target = np.asarray(paint, dtype=np.float32)[:, :, 3] / 255
    # The native draw has priority. Fill only what its cut and textured outline
    # leaves open, then put this small extension underneath the native foot.
    native = foot_alpha * keep_alpha
    alpha = np.divide(np.maximum(target - native, 0), 1 - native, out=np.zeros_like(target), where=native < .998)
    rgba = np.array(paint)
    rgba[:, :, 3] = np.rint(alpha * 255).astype(np.uint8)
    tile = Image.fromarray(rgba)
    crop = tile.getbbox()
    pixel_region = [value / ART_SCALE for value in crop]
    left, top, right, bottom = pixel_region
    region = atlas.add(tile.crop(crop))
    projected = mesh_pixels(anchor, geometry)
    center = projected.mean(axis=0)
    a = int(np.argmin(projected[:, 0]))
    b = int(np.argmax(projected[:, 0]))
    c = int(np.argmax(np.linalg.norm(projected - center, axis=1)))
    # Convert the paint plane to model-space units for the existing 2×2 form.
    scale = geometry['canvas'][0] * geometry['matrix'][0] / 2
    pins = list(dict.fromkeys([a, b, c]))
    rigid = ((projected[pins] - [left, top]) / scale).tolist()
    form = {'anchor': anchor['id'], 'grid': [2, 2], 'size': [(right-left)/scale, (bottom-top)/scale],
            'rigid': rigid, 'bindings': [[[vertex, 1]] for vertex in pins],
            'layers': [{'id': 'outline-extension', 'region': region, 'behind': True}]}
    share = float(np.minimum(alpha, target).sum() / target.sum())
    return {'over': [anchor['id']], 'forms': [form]}, share, tile


def build():
    geometry = json.loads((HERE / 'geometry.local.json').read_text(encoding='utf8'))
    assert geometry['crop'] == list(FRAME) and geometry['artScale'] == ART_SCALE
    models = {mesh['id']: mesh for mesh in geometry['drawables']}
    originals = [Image.open(SOURCE / f'texture_{i:02d}.png').convert('RGBA') for i in range(2)]
    atlas = Atlas()
    definition = {'atlas': 'outfit_01_repaint.png', 'patches': [], 'attachments': []}
    metrics = {'framebufferPixels': geometry['canvas'], 'projectionCrop': FRAME, 'texturePixels': geometry['textures'],
               'patches': {}, 'extensions': {}, 'sharedUV': {}, 'ankleOverlapPixels3x': {}, 'sourceSha256': {}}
    entries = {}
    outlines = Image.new('RGB', (WIDTH * ART_SCALE * 2, HEIGHT * ART_SCALE))
    for foot, ids in FOOT_IDS.items():
        art = load_local(f'{foot}-paint')
        keep = load_local(f'{foot}-keep')
        keep_alpha = np.asarray(keep, dtype=np.float32)[:, :, 3] / 255
        silhouette = Image.new('RGBA', art.size)
        for id in sorted(ids, key=lambda id: models[id]['order']):
            silhouette = Image.alpha_composite(silhouette, load_local(id))
        silhouette.crop(silhouette.getbbox()).save(HERE / f'{foot}-original-extracted.png')
        foot_alpha = np.asarray(silhouette.getchannel('A'), dtype=np.float32) / 255
        attachment, share, extension = supplement(atlas, geometry, models[ids[0]], art, keep_alpha, foot_alpha)
        definition['attachments'].append(attachment)
        metrics['extensions'][foot] = {'alphaWeightedShare': round(share, 4), 'crop': extension.getbbox()}
        art.crop(art.getbbox()).save(HERE / f'{foot}-repaint.png')
        outlines.paste(outline_card(foot, silhouette, art, extension), (list(FOOT_IDS).index(foot) * art.width, 0))
        for id in ids + LEG_IDS[foot]:
            mesh = models[id]
            assert mesh['texture'] == 0 and not mesh['masks']
            uv = uv_pixels(mesh, geometry)
            projected = mesh_pixels(mesh, geometry)
            triangles = np.array(mesh['triangles']).reshape(-1, 3)
            image = originals[mesh['texture']]
            bounds = uv_bounds(uv, image)
            if id in LEG_IDS[foot]:
                leg = load_local(id).getchannel('A')
                overlap = (np.array(art.getchannel('A')) > 8) & (np.array(leg) > 8)
                metrics['ankleOverlapPixels3x'][id] = int(overlap.sum())
                if overlap.sum() < 9:
                    continue
            xy, valid, folds = uv_projection(uv, projected, triangles, bounds)
            rgba = sample(art, xy, [0, 0, 0, 0])
            rgba[~valid] = 0
            patch = {'drawables': [id], 'source': list(bounds[:2]), 'region': atlas.add(to_image(rgba))}
            if id in ids:
                coverage = sample(keep, xy, [1, 1, 1, 1])
                coverage[~valid] = 1
                patch['coverage'] = atlas.add(to_image(coverage))[:2]
            else:
                patch['overlay'] = True
            definition['patches'].append(patch)
            metrics['patches'][id] = {'renderOrder': mesh['order'], 'texture': mesh['texture'], 'uvBounds': bounds,
                                      'vertices': len(uv), 'triangles': len(triangles),
                                      'overlappingPaintedTexels': int(np.count_nonzero(folds & (rgba[:, :, 3] > .05)))}
            entries[id] = {'foot': foot, 'uv': uv, 'projected': projected, 'bounds': bounds, 'triangles': triangles}
    # Count actual intersecting UV-triangle occupancy, including inactive meshes.
    for id, entry in entries.items():
        bounds = entry['bounds']
        target = Image.new('1', (bounds[2] - bounds[0], bounds[3] - bounds[1]))
        for triangle in entry['uv'][entry['triangles']] - bounds[:2]:
            ImageDraw.Draw(target).polygon(list(map(tuple, triangle)), fill=1)
        shared = []
        for other in geometry['drawables']:
            if other['id'] == id or other['texture'] != models[id]['texture']:
                continue
            uv = uv_pixels(other, geometry)
            if (uv.max(axis=0) < bounds[:2]).any() or (uv.min(axis=0) > bounds[2:]).any():
                continue
            coverage = Image.new('1', target.size)
            for triangle in uv[np.array(other['triangles']).reshape(-1, 3)] - bounds[:2]:
                ImageDraw.Draw(coverage).polygon(list(map(tuple, triangle)), fill=1)
            count = int((np.array(target) & np.array(coverage)).sum())
            if count:
                shared.append({'id': other['id'], 'approximatelySharedTexels': count, 'visible': other['visible']})
        metrics['sharedUV'][id] = shared
    for model in sorted(SOURCE.rglob('*')):
        if model.is_file():
            metrics['sourceSha256'][model.relative_to(SOURCE).as_posix()] = hashlib.sha256(model.read_bytes()).hexdigest()
    atlas.save(OUTPUT / definition['atlas'])
    (OUTPUT / 'outfit_01_repaint.json').write_text(json.dumps(definition, indent=2) + '\n', encoding='utf8')
    (HERE / 'analysis.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf8')
    (HERE / 'foot-meshes.json').write_text(json.dumps({
        'canvas': geometry['canvas'], 'matrix': geometry['matrix'], 'textureSizes': geometry['textures'],
        'drawables': {id: models[id] for id in entries},
    }, separators=(',', ':')) + '\n', encoding='utf8')
    plot_uv(entries, originals)
    plot_meshes(entries)
    outlines.save(HERE / 'outline-coverage.png')


if __name__ == '__main__':
    build()
