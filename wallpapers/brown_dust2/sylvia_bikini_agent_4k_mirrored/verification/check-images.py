"""Pixel comparisons of real rendered screenshots; does not modify the artwork."""
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
a = Image.open(HERE / 'mirrored.png').convert('RGB')
b = Image.open(HERE / 'unmirrored.png').convert('RGB').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
diff = ImageChops.difference(a, b)
assert a.size == (3840, 2160)
assert diff.getbbox() is None, 'Mirror must equal a pixel-exact horizontal flip of the same frame'
report = {'resolution': list(a.size), 'mirrorPixelExact': True, 'mirrorMaxChannelError': 0}
for name in ['mirrored.png', 'after-soak.png']:
    im = Image.open(HERE / name).convert('RGB')
    small = im.resize((384, 216))
    pixels = list(small.getdata())
    near_black = sum(max(p) < 12 for p in pixels) / len(pixels)
    assert near_black < .02, 'Unexpected black region'
    report[name] = {'meanRGB': ImageStat.Stat(im).mean, 'nearBlackFraction': near_black}
(HERE / 'pixel-test.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
