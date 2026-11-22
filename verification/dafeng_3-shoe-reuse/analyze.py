"""Export read-only model data, texture crops, and motion inputs for Cubism Core."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / 'work'
NATIVE = HERE / 'native'
MODELS = ROOT / 'azur_lane/data/models'
DONOR = MODELS / 'dafeng_3'
sys.path.insert(0, str(HERE.parent / 'real-photo-cubism-poc/py_moc3-0.1.0-py3-none-any.whl'))
from moc3 import Moc3

FONT = ImageFont.load_default(size=17)
COLORS = ['#75eadb', '#ffd078', '#ff92ba', '#c3aafd', '#d1ef8c', '#90b7ff']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data, compact=False):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=None if compact else 2) + '\n', encoding='utf-8')


def pairs(values):
    return np.asarray(values, dtype=float).reshape(-1, 2)


def mesh_uv(d, size):
    return (pairs(d['uv']) * (1, -1) + (0, 1)) * size


def box(points):
    return tuple(int(v) for v in (*np.floor(points.min(axis=0)), *np.ceil(points.max(axis=0))))


def rasterize(domain, mapped, triangles, bounds, bleed=0):
    """Rasterize each triangle at texel centers and interpolate another field."""
    x, y, r, b = bounds
    shape = (b - y, r - x)
    score = np.full(shape, -np.inf)
    result = np.zeros((*shape, 2))
    for tri in np.asarray(triangles).reshape(-1, 3):
        a, b, c = domain[tri] - [x, y]
        basis = np.array([b - a, c - a]).T
        if abs(np.linalg.det(basis)) < 1e-8:
            continue
        inverse = np.linalg.inv(basis)
        left, top = np.maximum(np.floor(np.min([a, b, c], axis=0)).astype(int) - 2, 0)
        right, bottom = np.minimum(np.ceil(np.max([a, b, c], axis=0)).astype(int) + 2, shape[::-1])
        if left >= right or top >= bottom:
            continue
        row, col = np.mgrid[top:bottom, left:right] + .5
        bc = (np.stack((col, row), axis=-1) - a) @ inverse.T
        weights = np.dstack((1 - bc.sum(axis=-1), bc))
        gradients = np.vstack((-inverse.sum(axis=0), inverse))
        distance = (weights / np.linalg.norm(gradients, axis=1)).min(axis=-1)
        region = np.s_[top:bottom, left:right]
        previous = score[region]
        use = (distance > previous) & (distance >= -bleed - 1e-8)
        result[region][use] = weights[use] @ mapped[tri]
        previous[use] = distance[use]
    return result, np.isfinite(score)


def sample(image, coords):
    """Bilinear RGBA sampling in premultiplied color, with transparent exterior."""
    pixels = np.asarray(image, dtype=np.float32) / 255
    pixels[:, :, :3] *= pixels[:, :, 3:]
    top_left = np.floor(coords - .5).astype(int)
    delta = coords - .5 - top_left
    result = np.zeros((*coords.shape[:-1], 4), dtype=np.float32)
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        x, y = np.moveaxis(top_left + [dx, dy], -1, 0)
        valid = (x >= 0) & (y >= 0) & (x < image.width) & (y < image.height)
        weight = (delta[..., 0] if dx else 1 - delta[..., 0]) * (delta[..., 1] if dy else 1 - delta[..., 1])
        result[valid] += weight[valid, None] * pixels[y[valid], x[valid]]
    alpha = result[..., 3:]
    np.divide(result[..., :3], alpha, out=result[..., :3], where=alpha > 0)
    return result


def png(data):
    return Image.fromarray(np.rint(np.clip(data, 0, 1) * 255).astype(np.uint8))


def wires(draw, points, indices, tint):
    for a, b, c in points[np.asarray(indices).reshape(-1, 3)]:
        draw.line([tuple(a), tuple(b), tuple(c), tuple(a)], fill=tint)


def moc_inventory(geometry, selected):
    name = geometry['name']
    moc = Moc3.from_file(MODELS / name / f'{name}.moc3')
    assert moc.art_mesh_ids == [d['id'] for d in geometry['drawables']]
    assert moc.parameter_ids == [p['id'] for p in geometry['parameters']]
    assert moc.part_ids == [p['id'] for p in geometry['parts']]
    assert moc['art_mesh.texture_indices'] == [d['texture'] for d in geometry['drawables']]
    # The bundled wheel labels these two arrays in reverse for both MOC versions.
    assert moc['art_mesh.position_index_counts'] == [len(d['vertices']) // 2 for d in geometry['drawables']]
    assert moc['art_mesh.vertex_counts'] == [len(d['triangles']) for d in geometry['drawables']]
    part_ids = [moc.part_ids[i] if i >= 0 else None for i in moc['art_mesh.parent_part_indices']]
    assert part_ids == [d['part'] for d in geometry['drawables']]
    owners = {}
    for i, parameter in enumerate(moc.parameter_ids):
        start = moc['parameter.keyform_binding_begin_indices'][i]
        count = moc['parameter.keyform_binding_counts'][i]
        for binding in range(start, start + count):
            assert binding >= 0 and binding not in owners
            owners[binding] = parameter

    def bound(group, i):
        band = moc[f'{group}.keyform_binding_band_indices'][i]
        start = moc['keyform_binding_band.begin_indices'][band]
        count = moc['keyform_binding_band.counts'][band]
        bindings = moc['keyform_binding_index.indices'][start:start + count]
        return [owners[k] for k in bindings]

    for d in geometry['drawables']:
        if d['id'] not in selected:
            continue
        index = d['i']
        item = d.copy()
        item['partChain'] = []
        part = moc['art_mesh.parent_part_indices'][index]
        while part >= 0:
            item['partChain'].append(moc.part_ids[part])
            part = moc['part.parent_part_indices'][part]
        item['directParameters'] = bound('art_mesh', index)
        item['keyformCount'] = moc['art_mesh.keyform_counts'][index]
        k = moc['art_mesh.keyform_begin_indices'][index]
        item['keyformOpacity'] = moc['art_mesh_keyform.opacities'][k:k + item['keyformCount']]
        item['keyformDrawOrders'] = moc['art_mesh_keyform.draw_orders'][k:k + item['keyformCount']]
        item['deformers'] = []
        parent = moc['art_mesh.parent_deformer_indices'][index]
        while parent >= 0:
            item['deformers'].append({'id': moc.deformer_ids[parent], 'parameters': bound('deformer', parent)})
            parent = moc['deformer.parent_deformer_indices'][parent]
        item['glue'] = []
        for glue, a, b in zip(moc['glue.ids'], moc['glue.art_mesh_index_as'], moc['glue.art_mesh_index_bs']):
            if index in (a, b):
                item['glue'].append({'id': glue, 'with': moc.art_mesh_ids[b if a == index else a]})
        item['uvBounds'] = box(mesh_uv(d, geometry['textures'][d['texture']]))
        selected[d['id']] = item

    model = read(MODELS / name / f'{name}.model3.json')
    textures = []
    for texture in model['FileReferences']['Textures']:
        with Image.open(MODELS / name / texture) as image:
            textures.append({'path': texture, 'format': image.format, 'mode': image.mode, 'size': list(image.size)})
    return {'name': name, 'mocHeaderVersion': moc.header.version, 'coreVersion': geometry['version'],
            'textures': textures, 'drawableCount': len(moc.art_mesh_ids), 'partCount': len(moc.part_ids),
            'parameterCount': len(moc.parameter_ids), 'deformerCount': len(moc.deformer_ids), 'meshes': selected}


def segments(values):
    current = values[:2]
    i = 2
    while i < len(values):
        kind = values[i]
        n = 7 if kind == 1 else 3
        points = [current, *[values[j:j + 2] for j in range(i + 1, i + n, 2)]]
        yield kind, points
        current = points[-1]
        i += n


def evaluate(pieces, time):
    for kind, points in pieces:
        start, a = points[0]
        end, b = points[-1]
        if time < end:
            t = min(1, max(0, (time - start) / (end - start)))
            if kind == 0:
                return a + (b - a) * t
            if kind == 1:  # All donor files declare restricted Beziers.
                q = 1 - t
                return q**3 * a + 3 * q*q*t * points[1][1] + 3 * q*t*t * points[2][1] + t**3 * b
            if kind == 2:
                return a
            if kind == 3:
                return b
            raise ValueError(kind)
    return pieces[-1][1][-1][1]


def motion_inputs(inventory, geometry):
    model = read(DONOR / 'dafeng_3.model3.json')['FileReferences']
    physics = read(DONOR / model['Physics'])
    related = set()
    for item in inventory['meshes'].values():
        related.update(item['directParameters'])
        for deformer in item['deformers']:
            related.update(deformer['parameters'])
    parameters = {p['id']: p for p in geometry['parameters']}
    assert related <= parameters.keys()
    watch = ['ArtMesh34', 'ArtMesh193', 'ArtMesh194', 'ArtMesh182', 'ArtMesh183', 'ArtMesh135',
             'ArtMesh170', 'ArtMesh184', 'ArtMesh98', 'ArtMesh138', 'ArtMesh162']
    inputs = {'ids': watch, 'groups': {}}
    summary = {'motions': {}, 'parameterDefinitions': parameters,
               'physics': {'meta': physics['Meta'], 'relatedInputsOutputs': []}}
    for setting in physics['PhysicsSettings']:
        sources = [entry['Source']['Id'] for entry in setting['Input']]
        outputs = [entry['Destination']['Id'] for entry in setting['Output']]
        if related.intersection(sources + outputs):
            summary['physics']['relatedInputsOutputs'].append({'id': setting['Id'], 'inputs': sources, 'outputs': outputs})
    for group, files in model['Motions'].items():
        assert len(files) == 1
        file = files[0]['File']
        motion = read(DONOR / file)
        meta = motion['Meta']
        assert meta['AreBeziersRestricted']
        times = {i / meta['Fps'] for i in range(math.floor(meta['Duration'] * meta['Fps']) + 1)}
        times.add(meta['Duration'])
        curves = defaultdict(dict)
        tracks = {}
        for curve in motion['Curves']:
            pieces = list(segments(curve['Segments']))
            id = curve['Id']
            curves[curve['Target']][id] = pieces
            if id in related or any(term in id.lower() for term in ('xie', 'jiao', 'zut', 'zubi')):
                vals = [p[1] for _, points in pieces for p in points]
                tracks[id] = {'pointBounds': [min(vals), max(vals)], 'segments': len(pieces)}
                times.update(points[-1][0] for _, points in pieces)
        sorted_times = sorted(t for t in times if 0 <= t <= meta['Duration'])
        inputs['groups'][group] = [[time,
            {id: round(evaluate(p, time), 7) for id, p in curves['Parameter'].items()},
            {id: round(evaluate(p, time), 7) for id, p in curves['PartOpacity'].items()}] for time in sorted_times]
        summary['motions'][group] = {'file': file, 'duration': meta['Duration'], 'fps': meta['Fps'],
            'totalCurves': meta['CurveCount'], 'curveTargets': {k: len(v) for k, v in curves.items() if v},
            'samples': len(sorted_times), 'relatedTracks': tracks}
    for id in sorted(related | {p for p in parameters if 'xie' in p.lower()}):
        p = parameters[id]
        tested = set(p['keys'] + [p['min'], p['default'], p['max']])
        inputs['groups'][f'key/{id}'] = [[value, {id: value}, {}] for value in sorted(tested)]
    write(WORK / 'probes.json', inputs, compact=True)
    write(HERE / 'motion-inventory.json', summary)


def extract(geometry, selection):
    atlas = Image.open(DONOR / 'texture_00.png').convert('RGBA')
    drawables = {d['id']: d for d in geometry['drawables']}
    items = [('fore', 'ArtMesh34'), ('rear-outer', 'ArtMesh193'), ('rear-inner', 'ArtMesh194'),
             ('rear-detached-outer', 'ArtMesh182'), ('rear-detached-inner', 'ArtMesh183')]
    overview = Image.new('RGB', (1460, 1020), '#242c39')
    overview_atlas = atlas.resize((960, 960), Image.Resampling.LANCZOS)
    overview.paste(overview_atlas, (20, 44), overview_atlas)
    labels = ImageDraw.Draw(overview)
    labels.text((20, 12), 'dafeng_3 / texture_00.png / 4096 x 4096 / native shoe UV regions', fill='white', font=FONT)
    uv_panel = Image.new('RGB', (1430, 620), '#242c39')
    mesh_draw = ImageDraw.Draw(uv_panel)
    mesh_draw.text((20, 12), 'Native atlas crops and Cubism UV triangles / coordinates are top-left origin', fill='white', font=FONT)
    coverage = {}
    for i, (label, id) in enumerate(items):
        d = drawables[id]
        uv = mesh_uv(d, atlas.size)
        bounds = box(uv)
        x, y, r, b = bounds
        crop = atlas.crop(bounds)
        _, covered = rasterize(uv, uv, d['triangles'], bounds)
        rgba = np.array(crop)
        rgba[~covered] = 0
        transparent = Image.fromarray(rgba)
        transparent.save(NATIVE / f'{label}-{id}.png')
        if i >= 3:
            continue
        opaque_pixels = covered & (rgba[..., 3] > 0)
        overlaps = {}
        for other in geometry['drawables']:
            if other['id'] == id or other['texture'] != d['texture']:
                continue
            points = mesh_uv(other, atlas.size)
            ox1, oy1, ox2, oy2 = box(points)
            if ox1 >= r or ox2 <= x or oy1 >= b or oy2 <= y:
                continue
            _, occupied = rasterize(points, points, other['triangles'], bounds)
            overlap = int((opaque_pixels & occupied).sum())
            if overlap:
                overlaps[other['id']] = overlap
        coverage[id] = {'texturePixelsWithAlphaAndUV': int(opaque_pixels.sum()), 'overlapPixelsByDrawable': overlaps}
        tint = COLORS[i]
        labels.rectangle(tuple(20 + v*960/4096 if n % 2 == 0 else 44 + v*960/4096
                               for n, v in enumerate(bounds)), outline=tint, width=3)
        suffix = ['', ' / shared by ArtMesh182', ' / shared by ArtMesh183'][i]
        labels.text((1000, 100 + i*72), f'{label}   {id}{suffix}', fill=tint, font=FONT)
        labels.text((1000, 125 + i*72), f'[{x}, {y}, {r}, {b})    {r-x} x {b-y}', fill='white', font=FONT)
        ox, oy = 22 + i*474, 62
        uv_panel.paste(transparent, (ox, oy), transparent)
        wires(mesh_draw, uv - [x, y] + [ox, oy], d['triangles'], tint)
        mesh_draw.text((ox, 37), f'{label} / {id}', fill=tint, font=FONT)
    overview.save(NATIVE / 'atlas-location.png')
    uv_panel.save(NATIVE / 'uv-meshes.png')
    write(HERE / 'uv-occupancy.json', coverage)
    for side in ('fore', 'rear'):
        ids = selection[side]
        result = Image.new('RGBA', geometry['image'])
        for id in sorted(ids, key=lambda id: drawables[id]['order']):
            d = drawables[id]
            uv = mesh_uv(d, atlas.size)
            source_box = box(uv)
            source_box = tuple(v + o for v, o in zip(source_box, [-2, -2, 2, 2]))
            screens = pairs(d['screen'])
            b = box(screens)
            mapping, covered = rasterize(screens, uv - source_box[:2], d['triangles'], b)
            pixels = sample(atlas.crop(source_box), mapping)
            pixels[~covered] = 0
            result.alpha_composite(png(pixels), b[:2])
        result.save(WORK / f'donor-{side}-canvas.png')
        result.crop(result.getbbox()).save(NATIVE / f'{side}-default-projected.png')


def main():
    selection = read(HERE / 'selection.json')
    inventories = {}
    for short, selected in selection.items():
        name = short + '_3'
        geometry = read(WORK / f'{name}-detail-geometry.json')
        selected = dict.fromkeys(selected['fore'] + selected['rear'] + selected['context'])
        inventory = moc_inventory(geometry, selected)
        inventories[name] = inventory
        if short == 'dafeng':
            motion_inputs(inventory, geometry)
            extract(geometry, selection[short])
    write(HERE / 'artmeshes.json', inventories, compact=True)


if __name__ == '__main__':
    main()
