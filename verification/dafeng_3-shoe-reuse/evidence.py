"""Summarize model probes and compare the actual browser captures."""
import hashlib
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from analyze import COLORS, HERE, NATIVE, ROOT, WORK, pairs, read, wires, write

TRIAL = HERE / 'trial'
FONT = ImageFont.load_default(size=20)


def source_hashes():
    base = ROOT / 'azur_lane'
    sources = [base / 'viewer/manifest.json', base / 'config/outfits/index.json', ROOT / 'shared/cubism_outfits.js']
    for model in ('dafeng_3', 'baifeng_3'):
        sources.extend((base / f'data/models/{model}').rglob('*'))
    sources.extend((base / 'config/outfits/baifeng_3').glob('*final_repaint.*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(sources) if p.is_file()}


def rgb(file):
    image = Image.open(file).convert('RGBA')
    background = Image.new('RGBA', image.size, '#242c39')
    return Image.alpha_composite(background, image).convert('RGB')


def montage(path, panels, patch, columns, width):
    height = round(width * (patch[3] - patch[1]) / (patch[2] - patch[0]))
    row = height + 37
    card = Image.new('RGB', (columns*(width+12)+12, math.ceil(len(panels)/columns)*row+12), '#242c39')
    draw = ImageDraw.Draw(card)
    for i, (label, panel) in enumerate(panels):
        x, y = 12 + i % columns * (width+12), 12 + i // columns * row
        card.paste(panel.crop(patch).resize((width, height), Image.Resampling.LANCZOS), (x, y+26))
        draw.text((x, y), label, font=FONT, fill='white')
    card.save(path)


def pixels():
    checks = read(TRIAL / 'browser-checks.json')
    for label, a, b, cap in [('full', '03-current-full', '05-trial-full', [647, 645, 760, 734]),
                              ('detail', '04-current-detail', '06-trial-detail', [265, 340, 855, 830])]:
        a, b = (np.asarray(Image.open(TRIAL / f'{n}.png').convert('RGBA'), dtype=np.int16) for n in (a, b))
        delta = np.max(np.abs(a-b), axis=2)
        y, x = np.where(delta)
        bbox = [int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)]
        assert bbox[0] >= cap[0] and bbox[1] >= cap[1] and bbox[2] <= cap[2] and bbox[3] <= cap[3]
        assert np.array_equal(a[..., 3], b[..., 3])
        checks[label] = {'changedPixelCount': len(y), 'changedPixelBounds': bbox,
                         'rgbDeltaGreaterThan8': int((delta > 8).sum()), 'alphaChangedPixelCount': 0,
                         'outsideFootPixelChanges': 0}
    write(TRIAL / 'browser-checks.json', checks)
    panels = [(title, rgb(TRIAL / f'{name}.png')) for title, name in [
        ('Original model', '02-original-detail'), ('Existing outfit 01', '04-current-detail'),
        ('Native leather proof', '06-trial-detail')]]
    montage(HERE / 'comparison.png', panels, (262, 352, 861, 829), 3, 455)


def motions():
    raw = read(WORK / 'sweep-results.json')
    ids = read(WORK / 'probes.json')['ids']
    out = {'meshOrder': ids, 'sampleFields': ['opacity', 'resolvedRenderOrder', 'maxVertexDisplacementCubismUnits', 'visible'],
           'motionSamples': {}, 'isolatedParameterSamples': {}, 'renderedExamples': {}}
    for name, group in raw.items():
        probes = group['probes']
        if name.startswith('key/'):
            if any(max(row[2] for row in mesh) > .00002 or max(row[0] for row in mesh)-min(row[0] for row in mesh) > .001
                   for mesh in zip(*(probe[1] for probe in probes))) or name == 'key/xiebianhua':
                out['isolatedParameterSamples'][name[4:]] = group
            continue
        meshes = {}
        for index, id in enumerate(ids):
            rows = [entry[1][index] for entry in probes]
            meshes[id] = {'opacityBounds': [min(row[0] for row in rows), max(row[0] for row in rows)],
                          'renderOrders': sorted({row[1] for row in rows}),
                          'maxDisplacement': max(row[2] for row in rows),
                          'visibleFrames': sum(bool(row[3] and row[0] > .01) for row in rows)}
        out['motionSamples'][name] = {'samples': len(probes), 'meshes': meshes, 'appearedDrawables': group['appeared']}
    frames = [('touch_body', '6.2'), ('touch_body', '8.4'), ('touch_body', '12'), ('home', '2.4')]
    panel = []
    for group, time in frames + [('login', '7')]:
        name = f'action-{group}-{time}'
        proof = read(WORK / f'{name}.json')
        sample_time, values, _ = proof['sample']
        out['renderedExamples'][name] = {'sampleTime': sample_time,
            'parameters': {id: values.get(id) for id in ('tuoxie', 'chatui', 'JIAOXIEx', 'youjiaoxuanzhuan')},
            'meshes': {d['id']: {k: d[k] for k in ('opacity', 'visible', 'order')}
                       for d in proof['meshes'] if d['id'] in ids}}
        if (group, time) in frames:
            panel.append((f'{group}  {sample_time:.2f}s', rgb(WORK / f'{name}.png')))
    out['totalMotionSampleCount'] = sum(v['samples'] for v in out['motionSamples'].values())
    write(HERE / 'motion-sweep.json', out)
    montage(NATIVE / 'shoe-state-motion.png', panel, (80, 200, 1030, 835), 2, 520)


def fitted_guide():
    data = read(HERE / 'artmeshes.json')
    selection = read(HERE / 'selection.json')
    measurements = {'unit': 'detail framebuffer px. Compare angles and ratios across separately zoomed cameras.',
                    'landmarkMethod': 'Manual screen landmarks on default-pose WebGL and isolated ArtMesh renderings.',
                    'poses': {}, 'overlaps': {}, 'outsoleSections': {}, 'nonRigidDeformation': {}}
    poses = {
        'dafeng_3': {'fore': [[868, 571], [404, 665]], 'rear': [[601, 479], [217, 632]]},
        'baifeng_3': {'fore': [[322, 679], [827, 727]], 'rear': [[300, 449], [793, 627]]},
    }
    panels = []
    for name, axes in poses.items():
        image = rgb(NATIVE / f'{name}-default.png')
        layer = ImageDraw.Draw(image)
        inventory = data[name]['meshes']
        short = name.split('_')[0]
        measures = {}
        for i, (side, points) in enumerate(axes.items()):
            length = math.dist(*points)
            dx, dy = np.subtract(points[1], points[0]).tolist()
            measures[side] = {'heelToeLandmarks': points, 'axisLength': round(length, 1),
                              'angleClockwiseFromImageRight': round(math.degrees(math.atan2(dy, dx)), 1)}
            ids = selection[short][side]
            for id in ids:
                d = inventory[id]
                wires(layer, pairs(d['screen']), d['triangles'], COLORS[i])
            layer.line([tuple(p) for p in points], fill=COLORS[i], width=4)
            for x, y in points:
                layer.ellipse((x-5, y-5, x+5, y+5), fill=COLORS[i], outline='black')
        measurements['poses'][name] = measures
        panels.append((f'{name} / default / fore (cyan) / rear (amber)', image))
    montage(HERE / 'structure-comparison.png', panels, (184, 265, 907, 823), 2, 620)

    def alpha(name, id):
        im = Image.open(WORK / f'{name}-{id}.png').getchannel('A')
        return np.array(im) > 127

    for a, b in [('ArtMesh34', 'ArtMesh135'), ('ArtMesh193', 'ArtMesh170'), ('ArtMesh194', 'ArtMesh170')]:
        first, second = [alpha('dafeng_3', id) for id in (a, b)]
        count = int((first & second).sum())
        measurements['overlaps'][f'{a}/{b}'] = {'pixels': count, 'shareOfFirstAlphaGT127': round(count/first.sum(), 4)}
    for a, b in [('ArtMesh13', 'ArtMesh12'), ('ArtMesh18', 'ArtMesh217')]:
        first, second = [alpha('baifeng_3', id) for id in (a, b)]
        count = int((first & second).sum())
        measurements['overlaps'][f'{a}/{b}'] = {'pixels': count, 'shareOfFirstAlphaGT127': round(count/first.sum(), 4)}

    sections = [
        ('dafeng_3', 'fore', 'forefoot', WORK / 'dafeng_3-ArtMesh34.png', 480, 710, 728),
        ('dafeng_3', 'rear', 'forefoot', WORK / 'dafeng_3-ArtMesh193.png', 278, 668, 682),
        ('baifeng_3', 'fore', 'forefoot', TRIAL / '04-current-detail.png', 747, 777, 798),
        ('baifeng_3', 'rear', 'forefoot', TRIAL / '04-current-detail.png', 775, 641, 653),
        ('dafeng_3', 'fore', 'heel', WORK / 'dafeng_3-ArtMesh34.png', 784, 594, 639),
        ('dafeng_3', 'rear', 'heel', WORK / 'dafeng_3-ArtMesh193.png', 543, 511, 538),
        ('baifeng_3', 'fore', 'heel', TRIAL / '04-current-detail.png', 347, 698, 718),
    ]
    sheet = Image.new('RGB', (1120, 630), '#242c39')
    for i, (name, side, place, file, x, top, bottom) in enumerate(sections):
        axis = measurements['poses'][name][side]['axisLength']
        measurements['outsoleSections'][f'{name}/{side}/{place}'] = {
            'framebufferSegment': [[x, top], [x, bottom]], 'projectedThickness': bottom-top,
            'thicknessToAxisPercent': round((bottom-top)/axis*100, 1),
        }
        left, y = x-60, top-24
        panel = rgb(file).crop((left, y, left+120, y+90)).resize((288,216))
        draw = ImageDraw.Draw(panel)
        tick_x = 144
        y1, y2 = round((top-y)*2.4), round((bottom-y)*2.4)
        draw.line((tick_x, y1, tick_x, y2), fill=COLORS[0], width=2)
        for tick_y in (y1, y2):
            draw.line((tick_x-6, tick_y, tick_x+6, tick_y), fill=COLORS[0], width=2)
        px, py = (i % 4)*280+8, (i//4)*305+20
        sheet.paste(panel.resize((264,198)), (px, py+35))
        ImageDraw.Draw(sheet).text((px, py), f'{name} {side} {place}', font=FONT, fill='white')
        ImageDraw.Draw(sheet).text((px, py+240), f'{bottom-top} px / {(bottom-top)/axis*100:.1f}% of axis', font=FONT, fill='white')
    sheet.save(HERE / 'outsole-comparison.png')

    for id in ('Param28', 'youjiaoxuanzhuan'):
        key = read(WORK / f'key-{id}.json')
        mesh = data['dafeng_3']['meshes'][key['meshID']]
        reference = pairs(mesh['vertices'])
        triangles = np.asarray(mesh['triangles']).reshape(-1, 3)
        edges = np.unique(np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1), axis=0)
        edge_lengths = np.linalg.norm(reference[edges[:, 0]] - reference[edges[:, 1]], axis=-1)
        valid = edge_lengths > .01
        samples = []
        for state in key['states']:
            shape = pairs(state['vertices'])
            lengths = np.linalg.norm(shape[edges[:, 0]] - shape[edges[:, 1]], axis=-1)
            ratios = lengths[valid] / edge_lengths[valid]
            samples.append({'value': state['value'], 'edgeLengthRatioPercentiles':
                            dict(zip(['p10', 'p50', 'p90'], [round(float(x), 4) for x in np.percentile(ratios, [10,50,90])]))})
        measurements['nonRigidDeformation'][key['meshID']] = {'parameter': id, 'samples': samples}
    write(HERE / 'measurements.json', measurements)


def main():
    if '--hash-before' in sys.argv:
        WORK.mkdir(exist_ok=True)
        return write(WORK / 'before-sha256.json', source_hashes())
    pixels()
    motions()
    fitted_guide()
    before = read(WORK / 'before-sha256.json')
    after = source_hashes()
    assert before == after, sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    write(HERE / 'source-integrity.json', {'unchangedFileCount': len(after), 'matchedBeforeAndAfter': True, 'sha256': after})


if __name__ == '__main__':
    main()
