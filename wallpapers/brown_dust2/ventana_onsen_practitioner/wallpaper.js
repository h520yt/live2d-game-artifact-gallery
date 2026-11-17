/* Standalone BD2 wallpaper. Source logic: brown_dust2/viewer/index.html
 * applySkin, skinForAnimation, selectAnimation, patchTextureUpload, resetCamera.
 * Original skeleton, atlas, texture pixels, and gallery files are unchanged.
 */
(() => {
  'use strict';
  const WIDTH = 3840, HEIGHT = 2160;
  const ANIMATION = 'idle2';
  const PLAYBACK_SPEED = 4 / 9;
  const FRAMING = new URLSearchParams(location.search).get('framing') === 'contain' ? 'contain' : 'cover';
  document.documentElement.dataset.framing = FRAMING;
  let player = null, paused = false, fps = 30;
  const status = window.wallpaperStatus = { ready: false, frames: 0, loops: 0,
    width: WIDTH, height: HEIGHT, skin: null, animation: ANIMATION, track: 0,
    framing: FRAMING, errors: [], excludedSlots: [], camera: null };

  // Like the gallery, upload straight-alpha PNG pixels as PMA and use PMA blending.
  // Both parts are required to avoid black fringes and bright additive edges.
  for (const api of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
    if (!api) continue;
    const original = api.prototype.texImage2D;
    api.prototype.texImage2D = function (...args) {
      if (this.canvas?.closest?.('#spine-root')) this.pixelStorei(this.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
      return original.apply(this, args);
    };
  }

  function fail(error) {
    const message = String(error?.message || error);
    status.errors.push(message);
    console.error('Ventana wallpaper:', message);
  }

  // Reuse the gallery's exact-name -> same idle group -> default skin matching.
  function skinForAnimation(skins, name) {
    const byName = new Map(skins.map(s => [s.name.toLowerCase(), s]));
    const group = /^idle(\d+)/i.exec(name)?.[1];
    return byName.get(name.toLowerCase()) || byName.get('idle' + group)
      || skins.find(s => new RegExp('^idle' + group + '(?:_|$)', 'i').test(s.name))
      || byName.get('default');
  }

  function vertices(slot) {
    const a = slot.getAttachment();
    if (!a || typeof a.computeWorldVertices !== 'function') return null;
    const v = new Float32Array(a.worldVerticesLength || 8);
    if (a.worldVerticesLength) a.computeWorldVertices(slot, 0, v.length, v, 0, 2);
    else a.computeWorldVertices(slot.bone, v, 0, 2);
    let left = Infinity, right = -Infinity, bottom = Infinity, top = -Infinity;
    for (let i = 0; i < v.length; i += 2) {
      left = Math.min(left, v[i]); right = Math.max(right, v[i]);
      bottom = Math.min(bottom, v[i + 1]); top = Math.max(top, v[i + 1]);
    }
    return { left, right, bottom, top };
  }

  function configureScene(pl) {
    const skeleton = pl.skeleton, state = pl.animationState;
    pl.speed = PLAYBACK_SPEED;
    // The stock 64 ms delta clamp would slow the animation below 16 FPS.
    // Pause/resume resets the clock separately; 1 FPS still advances in real time.
    pl.time.maxDelta = 1.1;
    const skin = skinForAnimation(skeleton.data.skins, ANIMATION);
    if (!skin || !skeleton.data.findAnimation(ANIMATION)) throw new Error('Required idle2 scene is missing');
    skeleton.setSkin(skin);
    skeleton.setToSetupPose();
    state.clearTracks();
    const base = state.setAnimation(0, ANIMATION, true);
    base.trackEnd = Number.MAX_VALUE;
    base.mixDuration = 0;
    state.apply(skeleton);
    skeleton.updateWorldTransform();
    status.skin = skin.name;

    // FR is the sole geometric outlier in this exact asset. Require BOTH name and
    // measured size; never hide the actual room, sky, bedding or normal foreground.
    const excluded = skeleton.slots.filter(slot => {
      if (slot.data.name !== 'FR') return false;
      const b = vertices(slot);
      return b && Math.max(b.right - b.left, b.top - b.bottom) > 10000;
    });
    status.excludedSlots = excluded.map(s => s.data.name);
    pl.excludedSlots = excluded;

    // Sample one complete loop once, then lock the camera. Include every visible
    // normal attachment (room + character), not just the character bounding box.
    const sample = new spine41.Skeleton(skeleton.data);
    sample.setSkin(skin); sample.setToSetupPose();
    const sampleState = new spine41.AnimationState(new spine41.AnimationStateData(skeleton.data));
    sampleState.setAnimation(0, ANIMATION, true);
    let left = Infinity, right = -Infinity, bottom = Infinity, top = -Infinity;
    const character = { left: Infinity, right: -Infinity, bottom: Infinity, top: -Infinity };
    const duration = base.animation.duration;
    for (let n = 0; n <= 64; n++) {
      if (n) sampleState.update(duration / 64);
      sampleState.apply(sample); sample.updateWorldTransform();
      for (const slot of sample.drawOrder) {
        if (status.excludedSlots.includes(slot.data.name) || slot.color.a < .001 || !slot.bone.active) continue;
        const a = slot.getAttachment();
        if (a?.color && a.color.a < .001) continue;
        const b = vertices(slot);
        if (!b) continue;
        left = Math.min(left, b.left); right = Math.max(right, b.right);
        bottom = Math.min(bottom, b.bottom); top = Math.max(top, b.top);
        if (/(?:head|face|hair|arm|hand|leg|foot)/i.test(slot.data.name)) {
          character.left = Math.min(character.left, b.left); character.right = Math.max(character.right, b.right);
          character.bottom = Math.min(character.bottom, b.bottom); character.top = Math.max(character.top, b.top);
        }
      }
    }
    if (![left, right, bottom, top].every(Number.isFinite)) throw new Error('Scene bounds are invalid');
    const zoom = FRAMING === 'cover'
      ? Math.min((right - left) / WIDTH, (top - bottom) / HEIGHT) * .994
      : Math.max((right - left) / WIDTH, (top - bottom) / HEIGHT) * 1.005;
    let centerY = (bottom + top) / 2;
    if (FRAMING === 'cover') {
      // Crop spare ceiling/floor rather than centering the crop on the room.
      // Keep the sampled head/hands/legs inside the fixed 16:9 camera.
      const minY = character.top + 36 - HEIGHT * zoom / 2;
      const maxY = character.bottom - 36 + HEIGHT * zoom / 2;
      centerY = minY <= maxY ? Math.max(minY, Math.min(maxY, 150)) : (character.top + character.bottom) / 2;
    }
    status.camera = { x: (left + right) / 2, y: centerY, zoom,
      bounds: { left, right, bottom, top }, characterBounds: character };
    state.addListener({ complete: entry => { if (entry.trackIndex === 0) status.loops++; } });

    // Only this instance uses a fixed 4K backing store, independent of Windows DPI.
    // A second 8K render target on a 200% scaled 4K desktop is deliberately avoided.
    pl.sceneRenderer.resize = function () {
      const canvas = this.canvas;
      if (canvas.width !== WIDTH || canvas.height !== HEIGHT) {
        canvas.width = WIDTH; canvas.height = HEIGHT;
      }
      this.context.gl.viewport(0, 0, WIDTH, HEIGHT);
      this.camera.setViewport(WIDTH, HEIGHT);
      this.camera.update();
    };
    // Data URIs have been decoded/uploaded. Drop the bundle and downloader copies.
    pl.config.rawDataURIs = null;
    pl.assetManager.downloader.rawDataUris = {};
    delete window.BD2_ASSETS;
    status.duration = duration;
    // The player's constructor starts paused. Since track 0 already exists here,
    // loadSkeleton does not necessarily call play() on our behalf.
    pl.play();
    status.ready = true;
    document.documentElement.dataset.ready = 'true';
  }

  class WallpaperPlayer extends spine41.SpinePlayer {
    drawFrame(requestNextFrame = true) {
      if (this.disposed || this.error) return;
      if (requestNextFrame) requestAnimationFrame(() => this.drawFrame());
      const now = performance.now();
      if (paused && status.ready) { this.time.update(); return; }
      const interval = 1000 / fps;
      if (this.lastWallpaperFrame !== undefined && now - this.lastWallpaperFrame < interval) return;
      this.lastWallpaperFrame = now - ((now - (this.lastWallpaperFrame ?? now)) % interval);
      super.drawFrame(false);
    }
  }

  // Register early, per Wallpaper Engine's API contract.
  window.wallpaperPropertyListener = {
    applyGeneralProperties(properties) {
      if (Number.isFinite(properties.fps)) fps = Math.max(1, Math.min(30, properties.fps));
    },
    setPaused(value) {
      paused = Boolean(value);
      if (player) { player.time.update(); player.lastWallpaperFrame = undefined; }
    }
  };
  document.addEventListener('visibilitychange', () => {
    if (player) player.time.update();
  });
  window.addEventListener('error', event => fail(event.error || event.message));
  window.addEventListener('unhandledrejection', event => fail(event.reason));
  try {
    player = new WallpaperPlayer('spine-root', {
      skelUrl: 'assets/illust_dating15.skel', atlasUrl: 'assets/illust_dating15.atlas',
      rawDataURIs: window.BD2_ASSETS, animation: ANIMATION,
      premultipliedAlpha: true, alpha: true, backgroundColor: '#00000000',
      preserveDrawingBuffer: false, mipmaps: false,
      showControls: false, showLoading: false, defaultMix: 0,
      viewport: { transitionTime: 0, animations: {} },
      success: pl => { try { configureScene(pl); } catch (e) { fail(e); pl.pause(); } },
      update: pl => {
        if (!status.ready) return;
        for (const slot of pl.excludedSlots) slot.color.a = 0;
        const camera = pl.sceneRenderer.camera, view = status.camera;
        camera.position.x = view.x; camera.position.y = view.y; camera.zoom = view.zoom;
        status.frames++;
      },
      error: (_, message) => fail(message)
    });
    player.canvas.addEventListener('webglcontextlost', () => { status.contextLost = true; });
    player.canvas.addEventListener('webglcontextrestored', () => { status.contextLost = false; });
    // Read-only diagnostic snapshot; no controls, input handling or animation switching.
    window.getWallpaperDiagnostics = () => ({ ...status,
      canvas: [player.canvas.width, player.canvas.height], fpsLimit: fps,
      playbackSpeed: player.speed, loopSeconds: status.duration / player.speed,
      paused: player.paused,
      tracks: player.animationState?.tracks.filter(Boolean).map(t => ({ index: t.trackIndex,
        animation: t.animation.name, loop: t.loop, time: t.trackTime })),
      textureCount: player.assetManager?.get('assets/illust_dating15.atlas')?.pages.length,
      renderer: player.context.gl.getParameter(player.context.gl.RENDERER) });
  } catch (error) { fail(error); }
})();
