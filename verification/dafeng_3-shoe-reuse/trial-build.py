"""Repaint the isolated white-phoenix atlas from Taihou's original shoe artwork."""
import numpy as np
from PIL import Image, ImageFilter

from analyze import HERE, ROOT, WORK, mesh_uv, pairs, png, rasterize, read, sample, write

TRIAL = HERE / 'trial'
CURRENT = ROOT / 'azur_lane/config/outfits/baifeng_3'

# Corresponding heel, collar, tongue, vamp, toe and outsole landmarks in the
# two recorded detail cameras. Opposite toe direction implies a mirrored fit.
LANDMARKS = {
    'fore': [
        [[852, 385], [301, 573]], [[878, 489], [284, 626]], [[875, 560], [290, 691]],
        [[782, 637], [397, 721]], [[762, 510], [443, 624]], [[699, 548], [548, 643]],
        [[607, 424], [590, 569]], [[567, 474], [629, 596]], [[704, 571], [518, 685]],
        [[520, 535], [704, 632]], [[417, 589], [802, 693]], [[402, 647], [841, 727]],
        [[427, 694], [815, 774]], [[500, 713], [735, 799]], [[646, 661], [537, 755]],
    ],
    'rear': [
        [[580, 308], [266, 431]], [[606, 373], [272, 505]], [[602, 467], [290, 552]],
        [[542, 544], [377, 577]], [[536, 424], [429, 463]], [[484, 469], [544, 477]],
        [[374, 361], [589, 416]], [[343, 418], [628, 447]], [[495, 482], [519, 523]],
        [[309, 472], [693, 497]], [[237, 550], [770, 563]], [[212, 615], [812, 610]],
        [[242, 660], [801, 647]], [[313, 669], [735, 659]], [[420, 630], [589, 620]],
    ],
}


def transform(landmarks, points):
    """Thin-plate spline inverse map from white-phoenix pose to donor pose."""
    source, target = np.moveaxis(np.array(landmarks, dtype=float) / 500, 1, 0)

    def radial(points_a, points_b):
        r2 = np.sum((points_a[..., None, :] - points_b) ** 2, axis=-1)
        return .5 * r2 * np.log(np.maximum(r2, 1e-12))

    affine = np.c_[np.ones(len(target)), target]
    upper = np.c_[radial(target, target) + .002 * np.eye(len(target)), affine]
    weights = np.linalg.solve(np.r_[upper, np.c_[affine.T, np.zeros((3, 3))]],
                              np.r_[source, np.zeros((3, 2))])
    points = points / 500
    return 500 * (radial(points, target) @ weights[:-3] + points @ weights[-2:] + weights[-3])


def warp_donor(side, size):
    donor = Image.open(WORK / f'donor-{side}-canvas.png').convert('RGBA')
    assert donor.size == tuple(size)
    row, col = np.mgrid[:size[1], :size[0]] + .5
    target = np.dstack((col, row))
    warped = sample(donor, transform(LANDMARKS[side], target))
    image = png(warped)
    image.crop(image.getbbox()).save(TRIAL / f'{side}-mapped-donor.png')
    # Extend color a few pixels around the forefoot where the inherited outline
    # is wider. This avoids retaining a second highlight from the old shoe.
    spread = np.asarray(image.getchannel('A').filter(ImageFilter.MaxFilter(23)), dtype=np.float32) / 255
    edge_color = np.asarray(image.convert('RGBa').filter(ImageFilter.GaussianBlur(5)), dtype=np.float32) / 255
    coverage = edge_color[..., 3:]
    np.divide(edge_color[..., :3], coverage, out=edge_color[..., :3], where=coverage > 0)
    toe = np.clip((target[..., 0] - 630) / 100, 0, 1)
    blend = np.minimum(np.clip(coverage[..., 0] * 15, 0, 1), spread) * toe * (1 - warped[..., 3])
    alpha = warped[..., 3:] + blend[..., None]
    mixed = warped[..., :3] * warped[..., 3:] + edge_color[..., :3] * blend[..., None]
    np.divide(mixed, alpha, out=mixed, where=alpha > 0)
    return png(np.concatenate([mixed, alpha], axis=-1))


def rigid_corners(form, mesh):
    """Apply the existing 2x2 rigid attachment fit at the frozen pose."""
    positions = pairs(mesh['screen'])
    pins = np.array([sum(positions[i] * weight for i, weight in binding) for binding in form['bindings']])
    landmarks = np.asarray(form['rigid'])
    pivot = landmarks.mean(axis=0)
    delta = landmarks - pivot
    length = np.sum(delta ** 2)
    delta_target = pins - pins.mean(axis=0)
    along = np.sum(delta * delta_target) / length
    across = np.sum(delta[:, 0] * delta_target[:, 1] - delta[:, 1] * delta_target[:, 0]) / length
    w, h = form['size']
    corners = np.asarray([[0, 0], [w, 0], [0, h], [w, h]]) - pivot
    return corners @ np.asarray([[along, across], [-across, along]]) + pins.mean(axis=0)


def paint_tile(original, donor, screen, covered):
    current = np.asarray(original, dtype=np.float32) / 255
    reuse = sample(donor, screen)
    # Feather only at the mapped donor silhouette. The pre-existing RGBA
    # alpha and coverage tiles still establish the recipient silhouette.
    weight = np.clip((reuse[..., 3] - .16) / .7, 0, 1) * covered
    current[..., :3] = current[..., :3] * (1 - weight[..., None]) + reuse[..., :3] * weight[..., None]
    effective = (np.asarray(original)[..., 3] > 16) & covered
    return png(current), {'measuredTilePixels': int(effective.sum()),
                          'donorWeightMean': round(float(weight[effective].mean()), 4) if effective.any() else 0,
                          'majorityDonorTilePixels': int(((weight >= .5) & effective).sum())}


def main():
    geometry = read(WORK / 'baifeng_3-detail-geometry.json')
    meshes = {d['id']: d for d in geometry['drawables']}
    selection = read(HERE / 'selection.json')['baifeng']
    side_for = {id: side for side in ('fore', 'rear') for id in selection[side]}
    definition = read(CURRENT / 'outfit_01_final_repaint.json')
    current = Image.open(CURRENT / definition['atlas']).convert('RGBA')
    result = current.copy()
    donors = {side: warp_donor(side, geometry['image']) for side in ('fore', 'rear')}
    metrics = {'landmarks': LANDMARKS, 'patches': {}, 'attachments': {}}
    for patch in definition['patches']:
        id, = patch['drawables']
        if id not in side_for:
            continue  # Keep the existing local ankle overlays and their alpha.
        d = meshes[id]
        x, y = patch['source']
        ax, ay, w, h = patch['region']
        uv = mesh_uv(d, geometry['textures'][d['texture']])
        screen, covered = rasterize(uv, pairs(d['screen']), d['triangles'], (x, y, x+w, y+h), bleed=1.8)
        box = (ax, ay, ax+w, ay+h)
        tile, stats = paint_tile(current.crop(box), donors[side_for[id]], screen, covered)
        assert tile.getchannel('A').tobytes() == current.crop(box).getchannel('A').tobytes()
        result.paste(tile, box)
        metrics['patches'][id] = stats

    for attachment in definition['attachments']:
        form, = attachment['forms']
        layer, = form['layers']
        id = form['anchor']
        x, y, w, h = layer['region']
        corners = rigid_corners(form, meshes[id])
        row, col = np.mgrid[:h, :w] + .5
        screen = corners[0] + (col/w)[..., None] * (corners[1] - corners[0]) + (row/h)[..., None] * (corners[2] - corners[0])
        box = (x, y, x+w, y+h)
        tile, stats = paint_tile(current.crop(box), donors[side_for[id]], screen, np.ones((h, w), dtype=bool))
        result.paste(tile, box)
        metrics['attachments'][id] = stats

    assert result.getchannel('A').tobytes() == current.getchannel('A').tobytes()
    for patch in definition['patches']:
        if patch.get('coverage'):
            x, y = patch['coverage']
            w, h = patch['region'][2:]
            box = (x, y, x+w, y+h)
            assert result.crop(box).tobytes() == current.crop(box).tobytes()
    definition['atlas'] = 'native-reuse.png'
    result.save(TRIAL / definition['atlas'], optimize=True)
    write(TRIAL / 'outfit.json', definition)
    write(TRIAL / 'fit-metrics.json', metrics)


if __name__ == '__main__':
    main()
