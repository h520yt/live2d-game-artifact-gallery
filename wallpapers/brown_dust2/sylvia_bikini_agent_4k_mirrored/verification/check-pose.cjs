const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const out = path.resolve(__dirname, '..');
const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(out, 'js/spine-player4.1.js'), 'utf8'), ctx);
const spine = ctx.spine41;
const atlas = new spine.TextureAtlas(fs.readFileSync(path.join(out, 'assets/illust_dating8.atlas'), 'utf8'));
for (const page of atlas.pages) page.texture = { getImage: () => ({ width: page.width, height: page.height }) };
const data = new spine.SkeletonBinary(new spine.AtlasAttachmentLoader(atlas))
  .readSkeletonData(new Uint8Array(fs.readFileSync(path.join(out, 'assets/illust_dating8.skel'))));
assert.equal(data.version, '4.1.11');
assert.equal(data.skins.length, 1);
assert.equal(data.skins[0].name, 'default');
const skeleton = new spine.Skeleton(data);
skeleton.setSkin(data.skins[0]);
const state = new spine.AnimationState(new spine.AnimationStateData(data));
const entry = state.setAnimation(0, 'idle1', true);

function pose(time) {
  skeleton.setToSetupPose();
  entry.trackTime = time;
  state.apply(skeleton);
  skeleton.updateWorldTransform();
  const result = {};
  for (const slot of skeleton.drawOrder) {
    const a = slot.getAttachment();
    if (!a?.computeWorldVertices || !slot.bone.active || slot.color.a < .001 || a.color?.a < .001) continue;
    const v = new Float32Array(a.worldVerticesLength || 8);
    if (a.worldVerticesLength) a.computeWorldVertices(slot, 0, v.length, v, 0, 2);
    else a.computeWorldVertices(slot.bone, v, 0, 2);
    assert([...v].every(Number.isFinite), 'No NaN/Infinity in deformed mesh');
    result[slot.data.name] = { attachment: a.name, vertices: [...v] };
  }
  return result;
}
const start = pose(0), end = pose(entry.animation.duration), last = pose(entry.animation.duration - 0.0001);
assert.deepEqual(start, end, 'Exact whole-loop pose must match');
let maxSeamVertexDelta = 0;
assert.deepEqual(Object.keys(start), Object.keys(last));
for (const [name, slot] of Object.entries(start)) {
  assert.equal(slot.attachment, last[name].attachment, 'No attachment switch at seam');
  slot.vertices.forEach((v, i) => { maxSeamVertexDelta = Math.max(maxSeamVertexDelta, Math.abs(v - last[name].vertices[i])); });
}
assert(maxSeamVertexDelta < 1, 'Loop seam must be continuous in world units');
const counts = [];
for (let n = 0; n <= 240; n++) {
  const p = pose(entry.animation.duration * n / 240);
  assert(Object.keys(p).some(k => /head|face/i.test(k)), 'Head remains visible');
  assert(Object.keys(p).some(k => /leg/i.test(k)), 'Legs remain visible');
  assert(Object.keys(p).some(k => /^BG/i.test(k)), 'Room remains visible');
  counts.push(Object.keys(p).length);
}
const report = { version: data.version, skin: data.skins[0].name, animation: entry.animation.name,
  duration: entry.animation.duration, samples: 241, minVisibleAttachments: Math.min(...counts),
  maxVisibleAttachments: Math.max(...counts), exactLoopPoseMatches: true, maxSeamVertexDelta,
  allVerticesFinite: true, headLegsBackgroundPresentAllSamples: true };
fs.writeFileSync(path.join(__dirname, 'pose-test.json'), JSON.stringify(report, null, 2));
console.log(report);
