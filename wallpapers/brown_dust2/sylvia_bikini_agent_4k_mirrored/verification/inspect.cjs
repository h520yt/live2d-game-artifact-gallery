const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../../..');
const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../js/spine-player4.1.js'), 'utf8'), ctx);
const spine = ctx.spine41;
const source = path.resolve(__dirname, '../assets');
const atlas = new spine.TextureAtlas(fs.readFileSync(path.join(source, 'illust_dating8.atlas'), 'utf8'));
for (const page of atlas.pages) page.texture = { getImage: () => ({ width: page.width, height: page.height }) };
const data = new spine.SkeletonBinary(new spine.AtlasAttachmentLoader(atlas))
  .readSkeletonData(new Uint8Array(fs.readFileSync(path.join(source, 'illust_dating8.skel'))));
const skeleton = new spine.Skeleton(data);
console.log('Available skins:', data.skins.map(x => [x.name, x.getAttachments().length]));
skeleton.setSkinByName(data.findSkin('idle1') ? 'idle1' : 'default');
skeleton.setToSetupPose();
const state = new spine.AnimationState(new spine.AnimationStateData(data));
state.setAnimation(0, 'idle1', true);
state.apply(skeleton);
skeleton.updateWorldTransform();
const rows = skeleton.drawOrder.map(slot => {
  const a = slot.getAttachment();
  if (!a || !a.computeWorldVertices) return null;
  const v = new Float32Array(a.worldVerticesLength || 8);
  if (a.worldVerticesLength) a.computeWorldVertices(slot, 0, v.length, v, 0, 2);
  else a.computeWorldVertices(slot.bone, v, 0, 2);
  const xs = [...v].filter((_, i) => i % 2 === 0), ys = [...v].filter((_, i) => i % 2);
  return { slot: slot.data.name, attachment: a.name, alpha: slot.color.a,
    x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) };
}).filter(Boolean);
const result = { version: data.version,
  skins: data.skins.map(x => ({ name: x.name, attachments: x.getAttachments().length })),
  animations: data.animations.filter(x => x.name.startsWith('idle')).map(x => ({ name: x.name, duration: x.duration })),
  pages: atlas.pages.map(p => ({ name: p.name, width: p.width, height: p.height })), slots: rows };
const target = path.join(root, 'wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification');
fs.mkdirSync(target, { recursive: true });
fs.writeFileSync(path.join(target, 'scene-geometry.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ ...result, slots: rows.filter(x => x.width > 1800 || x.height > 1800) }, null, 2));
