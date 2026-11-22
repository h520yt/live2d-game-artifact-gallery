(() => {
  'use strict';

  const motionName = 'idle5';
  const playbackSpeed = 1 / 3;
  const maxPixels = 3840 * 2160;
  const canvas = document.getElementById('wallpaper');
  const status = document.getElementById('error');
  let renderer, stage, model;
  let animationFrame = 0;
  let paused = false;
  let contextLost = false;
  let fps = 30;
  let lastFrame = 0;
  let frameBudget = 0;

  function scheduleFrame() {
    if (model && !animationFrame && !paused && !contextLost && !document.hidden) {
      animationFrame = requestAnimationFrame(drawFrame);
    }
  }

  function resetClock() {
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    lastFrame = 0;
    frameBudget = 0;
    scheduleFrame();
  }

  function drawFrame(now) {
    animationFrame = 0;
    const elapsed = lastFrame ? Math.min(now - lastFrame, 100) : 0;
    lastFrame = now;
    frameBudget += elapsed;
    const interval = 1000 / fps;
    if (frameBudget >= interval) {
      const remainder = frameBudget % interval;
      // Keep display pacing independent of how quickly the animation advances.
      model.update((frameBudget - remainder) * playbackSpeed);
      renderer.render(stage);
      frameBudget = remainder;
    }
    scheduleFrame();
  }

  function resize() {
    if (!model || contextLost) return;
    const width = Math.max(1, innerWidth * devicePixelRatio);
    const height = Math.max(1, innerHeight * devicePixelRatio);
    const density = Math.min(1, Math.sqrt(maxPixels / (width * height)));
    renderer.resize(Math.round(width * density), Math.round(height * density));

    const screen = renderer.screen;
    // Fit the reference composition when the painted scene can fill the extra space.
    const heightScale = screen.height / 21800;
    const referenceScale = Math.min(screen.width / 42600, heightScale);
    const scale = Math.max(referenceScale, screen.width / 55000, screen.height / 26000);
    // Keep the top of the head in view when a very wide display needs a tighter crop.
    const verticalOffset = 4000 * Math.min(scale, heightScale);
    model.scale.set(scale);
    model.position.set(screen.width / 2 + 140 * scale, screen.height / 2 - verticalOffset);
    renderer.render(stage);
  }

  function makeAssetURLs(assets) {
    return Object.fromEntries(Object.entries(assets).map(([filename, [type, base64]]) => {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < bytes.length; i++) bytes[i] = binary.charCodeAt(i);
      return [filename, URL.createObjectURL(new Blob([bytes], { type }))];
    }));
  }

  async function start() {
    const bundle = window.live2dBundle;
    if (!bundle) throw new Error('缺少 model.bundle.js');
    delete window.live2dBundle;

    const { Cubism4ModelSettings, Live2DModel, MotionPriority, config } = PIXI.live2d;
    config.sound = false;
    const settings = new Cubism4ModelSettings({ ...bundle.settings, url: 'kewei_6.model3.json' });
    const assetURLs = makeAssetURLs(bundle.assets);
    settings.resolveURL = filename => assetURLs[filename];

    renderer = new PIXI.Renderer({
      view: canvas, backgroundColor: 0x252829, antialias: true,
      autoDensity: false, resolution: 1,
    });
    // Pixi restores its renderer first, including when playback is paused.
    canvas.addEventListener('webglcontextrestored', () => {
      contextLost = false;
      resize();
      resetClock();
    });
    stage = new PIXI.Container();
    const live2d = await Live2DModel.from(settings, {
      autoUpdate: false, autoInteract: false, motionPreload: 'NONE',
    });
    const manager = live2d.internalModel.motionManager;
    const motion = await manager.loadMotion(motionName, 0);
    if (!motion) throw new Error('无法加载 idle5');
    motion.setIsLoop(true);
    motion.setIsLoopFadeIn(false);
    motion.setFadeInTime(0);
    if (!await live2d.motion(motionName, 0, MotionPriority.FORCE)) throw new Error('无法播放 idle5');

    model = live2d;
    model.anchor.set(0.5);
    stage.addChild(model);
    model.update(1);
    resize();
    document.documentElement.dataset.ready = 'true';
    scheduleFrame();
  }

  window.wallpaperPropertyListener = {
    applyGeneralProperties(properties) {
      if (Number.isFinite(properties.fps) && properties.fps > 0) {
        fps = Math.min(30, properties.fps);
      }
    },
    setPaused(value) {
      paused = Boolean(value);
      resetClock();
    },
  };
  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', resetClock);
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    contextLost = true;
    resetClock();
  });

  start().catch(error => {
    console.error(error);
    status.textContent = `壁纸加载失败：${error.message}`;
    status.hidden = false;
  });
})();
