import base64
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
manifest = json.loads((OUT / 'assets-manifest.json').read_text(encoding='utf-8'))
bundle = (OUT / 'js/assets.bundle.js').read_text(encoding='utf-8')
uris = json.loads(bundle[len('window.BD2_ASSETS='):].strip().removesuffix(';'))
verified = []
for item in manifest['files']:
    packed = OUT / item['file']
    source = ROOT / manifest['localSource'] / packed.name
    data = packed.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == item['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(data) == item['bytes']
    assert base64.b64decode(uris[item['file']].split(',', 1)[1]) == data
    verified.append(item['file'])
runtime = (OUT / 'js/spine-player4.1.js').read_bytes()
assert runtime == (ROOT / 'shared/vendor/spine-player4.1.js').read_bytes()
assert hashlib.sha256(runtime).hexdigest() == manifest['runtimeSha256']
assert set(uris) == set(verified)
gallery = (ROOT / 'brown_dust2/viewer/index.html').read_text(encoding='utf-8')
wallpaper = (OUT / 'js/wallpaper.js').read_text(encoding='utf-8')
for name, next_name in [('idleSceneKey', 'skinForAnimation'), ('skinForAnimation', 'pickInitialScene'), ('applySkin', 'getCharacterBounds')]:
    chunk = gallery[gallery.index('function ' + name + '('):gallery.index('function ' + next_name + '(')]
    # Match the complete function, omitting comments following the closing brace.
    chunk = chunk[:chunk.rfind('\n}') + 2]
    assert chunk in wallpaper, name + ' must remain the gallery implementation'
report = {'originalAssetsVerified': verified, 'bundleBytesMatchOriginals': True,
          'runtimeByteIdentical': True, 'gallerySkinFunctionsIdentical': True}
(OUT / 'verification/package-test.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
