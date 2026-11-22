const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '../..');
const base = '/verification/dafeng_3-shoe-reuse';
const origin = 'http://local-shoe-proof.test';
const mime = {'.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.png': 'image/png'};
const writeJSON = (file, data) => fs.writeFile(path.join(__dirname, file), JSON.stringify(data, null, 2));

async function main() {
  await fs.mkdir(path.join(__dirname, 'work'), {recursive: true});
  const browser = await chromium.launch({channel: 'chrome',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage({viewport: {width: 1100, height: 1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route(`${origin}/**`, async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (!['/shared/vendor/', '/shared/cubism_outfits.js', '/azur_lane/data/models/dafeng_3/',
        '/azur_lane/data/models/baifeng_3/', '/azur_lane/config/outfits/baifeng_3/', `${base}/`]
        .some(prefix => pathname.startsWith(prefix))) return route.fulfill({status: 404});
      const file = path.join(root, pathname);
      try {
        await fs.access(file);
        return route.fulfill({path: file, contentType: mime[path.extname(file)] || 'application/octet-stream'});
      } catch {
        return route.fulfill({status: 404});
      }
    });
    await page.goto(`${origin}${base}/preview.html?capture`);
    const load = (name, outfit) => page.evaluate(params => proof.load(...params), [name, outfit]);
    const geo = () => page.evaluate(() => proof.geometry());
    const detail = ids => page.evaluate(ids => proof.detail(ids), ids);
    const frame = async (file, {keep = [], omit = []} = {}) => {
      const {error, png} = await page.evaluate(({keep, omit}) => proof.frame(keep, omit), {keep, omit});
      assert.equal(error, 0);
      const bytes = Buffer.from(png, 'base64');
      if (file) await fs.writeFile(path.join(__dirname, `${file}.png`), bytes);
      return bytes;
    };
    {
      const {dafeng, baifeng} = JSON.parse(await fs.readFile(path.join(__dirname, 'selection.json'), 'utf8'));
      const all = def => [...def.fore, ...def.rear];
      if (process.argv.includes('--native')) {
        for (const [name, def] of [['dafeng_3', dafeng], ['baifeng_3', baifeng]]) {
          await load(name);
          await detail(all(def));
          await writeJSON(`work/${name}-detail-geometry.json`, await geo());
          await frame(`native/${name}-default`);
          for (const id of [...all(def), ...(def.context || [])]) {
            await frame(`work/${name}-${id}`, {keep: [id]});
          }
          if (name === 'dafeng_3') {
            await frame('work/dafeng_3-no-shoes', {omit: all(def)});
            for (const side of ['fore', 'rear']) await frame(`work/dafeng_3-${side}`, {keep: def[side]});
          }
        }
      } else if (process.argv.includes('--sweep')) {
        await load('dafeng_3');
        const data = JSON.parse(await fs.readFile(path.join(__dirname, 'work/probes.json'), 'utf8'));
        const result = await page.evaluate(data => {
          const core = proof.model.internalModel.coreModel;
          const {parameters: p, drawables: d, parts} = core._model;
          const snapshot = data.ids.map(id => d.ids.indexOf(id));
          const opacity = () => Array.from(d.opacities);
          const neutral = opacity();
          const defaultVertices = snapshot.map(i => [...d.vertexPositions[i]]);
          const parameterIndex = new Map(p.ids.map((id, i) => [id, i]));
          const partIndex = new Map(parts.ids.map((id, i) => [id, i]));
          const partDefault = [...parts.opacities];
          const output = {};
          for (const [group, samples] of Object.entries(data.groups)) {
            const probes = [];
            const appeared = new Set();
            for (const [time, values, partValues] of samples) {
              p.values.set(p.defaultValues);
              parts.opacities.set(partDefault);
              for (const [id, value] of Object.entries(values)) {
                const index = parameterIndex.get(id);
                if (index !== undefined) p.values[index] = Math.min(p.maximumValues[index], Math.max(p.minimumValues[index], value));
              }
              for (const [id, value] of Object.entries(partValues || {})) {
                const index = partIndex.get(id);
                if (index !== undefined) parts.opacities[index] = value;
              }
              core.update();
              for (let i = 0; i < d.ids.length; i++) {
                if (neutral[i] < 0.01 && d.opacities[i] > 0.01) appeared.add(d.ids[i]);
              }
              probes.push([time, snapshot.map((i, j) => {
                const v = d.vertexPositions[i];
                let displacement = 0;
                for (let k = 0; k < v.length; k += 2) {
                  displacement = Math.max(displacement,
                    Math.hypot(v[k] - defaultVertices[j][k], v[k + 1] - defaultVertices[j][k + 1]));
                }
                return [d.opacities[i], d.renderOrders[i], +displacement.toFixed(6), core.getDrawableDynamicFlagIsVisible(i)];
              })]);
            }
            output[group] = {probes, appeared: [...appeared]};
          }
          return output;
        }, data);
        await writeJSON('work/sweep-results.json', result);
      } else if (process.argv.includes('--action')) {
        await load('dafeng_3');
        await detail(all(dafeng), 1.85);
        const {groups} = JSON.parse(await fs.readFile(path.join(__dirname, 'work/probes.json'), 'utf8'));
        const timings = {touch_body: [6.2, 8.4, 12], home: [2.4], login: [7]};
        for (const [group, times] of Object.entries(timings)) {
          for (const time of times) {
            const sample = groups[group].reduce((a, b) => Math.abs(b[0] - time) < Math.abs(a[0] - time) ? b : a);
            await page.evaluate(sample => proof.setMotionSample(sample), sample);
            await frame(`work/action-${group}-${time}`);
            const ids = [...all(dafeng), ...dafeng.context];
            const meshes = (await geo()).drawables.filter(d => ids.includes(d.id));
            await writeJSON(`work/action-${group}-${time}.json`, {sample, meshes});
          }
        }
        for (const [id, meshID] of [['Param28', 'ArtMesh34'], ['youjiaoxuanzhuan', 'ArtMesh193']]) {
          const states = [];
          for (const sample of groups[`key/${id}`]) {
            await page.evaluate(sample => proof.setMotionSample(sample), sample);
            const mesh = (await geo()).drawables.find(d => d.id === meshID);
            states.push({value: sample[0], vertices: mesh.vertices});
          }
          await writeJSON(`work/key-${id}.json`, {parameter: id, meshID, states});
        }
      } else if (process.argv.includes('--trial')) {
        await load('baifeng_3');
        const original = await frame('trial/01-original-full');
        await detail(all(baifeng));
        await frame('trial/02-original-detail');
        await load('baifeng_3', 'current');
        const current = await frame('trial/03-current-full');
        await detail(all(baifeng));
        await frame('trial/04-current-detail');
        await load('baifeng_3', 'trial');
        const trial = await frame('trial/05-trial-full');
        assert.notDeepEqual(trial, current);
        assert.notDeepEqual(trial, original);
        await detail(all(baifeng));
        await frame('trial/06-trial-detail');
        for (const side of ['fore', 'rear']) {
          for (const choice of ['current', 'trial']) {
            await load('baifeng_3', choice);
            await detail(baifeng[side]);
            await frame(`trial/${side}-${choice}`);
          }
        }
        await load('baifeng_3', 'original');
        assert.deepEqual(await frame(), original);
        await load('baifeng_3', 'trial');
        assert.deepEqual(await frame(), trial);
        await page.goto(`${origin}${base}/preview.html`);
        const quiet = async () => {
          await page.waitForFunction(() => [...document.querySelectorAll('nav button')].every(button => !button.disabled));
          assert.equal(await page.locator('output').textContent(), '');
        };
        const ui = async (label, expected) => {
          await page.getByRole('button', {name: label, exact: true}).click();
          await quiet();
          assert.deepEqual(await frame(), expected);
        };
        await quiet();
        assert.deepEqual(await frame(), trial);
        await ui('白凤原装', original);
        await ui('白凤现版换装', current);
        await ui('白凤隔离试验', trial);
        await page.getByRole('button', {name: '足部近景', exact: true}).click();
        assert.notDeepEqual(await frame(), trial);
        await page.getByRole('button', {name: '角色全景', exact: true}).click();
        assert.deepEqual(await frame(), trial);
        await page.getByRole('button', {name: '大凤原装', exact: true}).click();
        await quiet();
        assert.equal((await geo()).name, 'dafeng_3');
        await ui('白凤隔离试验', trial);
        await writeJSON('trial/browser-checks.json', {chrome: await browser.version(), webgl: 'no errors',
          pageErrors: errors, originalRestoredByteIdentically: true, trialReselectedByteIdentically: true,
          previewButtonsVerified: true});
      }
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
