"""Crop and compare the original and dressed frames captured in the viewer."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
metrics = json.loads((HERE / 'analysis.json').read_text(encoding='utf8'))
with Image.open(HERE / 'original.png') as original, Image.open(HERE / 'dressed.png') as dressed:
    changed = np.any(np.asarray(original) != np.asarray(dressed), axis=2)
y, x = np.where(changed)
left, top, right, bottom = metrics['projectionCrop']
assert len(x) > 0
assert len(metrics['sourceSha256']) == 88
assert all(len(items) == 0 for items in metrics['sharedUV'].values())
assert all(patch['overlappingPaintedTexels'] == 0 for patch in metrics['patches'].values())
outside = (x < left) | (x >= right) | (y < top) | (y >= bottom)
assert not outside.any(), 'Outfit changed pixels outside the recorded foot area'
(HERE / 'render-check.json').write_text(json.dumps({
    'framebuffer': metrics['framebufferPixels'],
    'changedPixels': len(x),
    'changedBounds': [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1],
    'changedOutsideFootCrop': int(outside.sum()),
}, indent=2) + '\n', encoding='utf8')

with Image.open(HERE / 'original-detail.local.png') as original, Image.open(HERE / 'dressed-detail.local.png') as dressed:
    before, after = [im.crop((70, 290, 786, 820)).convert('RGB') for im in (original, dressed)]
    dressed.crop((78, 477, 776, 816)).save(HERE / 'foreground-detail.png')
    dressed.crop((224, 302, 748, 635)).save(HERE / 'rear-detail.png')

margin, gap, heading = 18, 12, 38
panel = Image.new('RGB', (before.width * 2 + margin * 2 + gap, before.height + margin + heading), '#172128')
draw = ImageDraw.Draw(panel)
font = ImageFont.load_default(size=17)
for label, image, x in [('Original outfit', before, margin),
                        ('Outfit 01', after, margin + before.width + gap)]:
    draw.text((x, 10), label, fill='white', font=font)
    panel.paste(image, (x, heading))
panel.save(HERE / 'comparison.png')
