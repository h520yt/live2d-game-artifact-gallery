/* NIKKE 静态立绘、场景与 PNG 导出，独立于 Spine runtime。 */
(function () {
  'use strict';

  const view = document.getElementById('stage-view');
  const stage = view.querySelector('.stage');
  const playerHost = document.getElementById('player-container');
  const background = document.createElement('img');
  background.className = 'nikke-scene-bg';
  background.alt = '';
  background.hidden = true;
  stage.insertBefore(background, stage.firstChild);

  const still = document.createElement('img');
  still.className = 'nikke-art-preview';
  still.alt = '静态立绘';
  still.hidden = true;
  stage.appendChild(still);

  const toolbar = document.createElement('div');
  toolbar.className = 'nikke-art-tools';
  const modes = document.createElement('div');
  modes.className = 'nikke-view-modes';
  const labels = { art: '原画 / 静态', dynamic: '动态模型', scene: '场景合成' };
  Object.keys(labels).forEach(function (key) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.mode = key;
    button.textContent = labels[key];
    button.addEventListener('click', function () { switchMode(key); });
    modes.appendChild(button);
  });
  const options = document.createElement('div');
  options.className = 'nikke-scene-options';
  const backgrounds = document.createElement('select');
  backgrounds.title = '选择场景背景';
  backgrounds.setAttribute('aria-label', '场景背景');
  const none = document.createElement('option');
  none.value = '';
  none.textContent = '透明背景 / 未选择';
  backgrounds.appendChild(none);
  backgrounds.addEventListener('change', function () {
    setBackground(backgrounds.value);
  });
  const upload = document.createElement('label');
  upload.className = 'nikke-upload-label';
  upload.textContent = '导入背景';
  const file = document.createElement('input');
  file.type = 'file';
  file.accept = 'image/png,image/jpeg,image/webp';
  file.setAttribute('aria-label', '导入背景');
  upload.appendChild(file);
  file.addEventListener('change', function () {
    const image = file.files && file.files[0];
    if (!image) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(image.type)) {
      setHint('只支持 PNG / JPEG / WebP 图片');
      return;
    }
    const url = URL.createObjectURL(image);
    if (customUrl) URL.revokeObjectURL(customUrl);
    customUrl = url;
    let opt = backgrounds.querySelector('option[data-custom="1"]');
    if (!opt) {
      opt = document.createElement('option');
      opt.dataset.custom = '1';
      backgrounds.appendChild(opt);
    }
    opt.value = url;
    opt.textContent = '本次导入：' + image.name;
    backgrounds.value = url;
    setBackground(url);
    switchMode('scene');
    file.value = '';
  });
  const save = document.createElement('button');
  save.type = 'button';
  save.className = 'nikke-save-image';
  save.textContent = '导出 PNG';
  save.addEventListener('click', exportPNG);
  options.appendChild(backgrounds);
  options.appendChild(upload);
  options.appendChild(save);

  const hint = document.createElement('div');
  hint.className = 'nikke-art-hint';
  hint.setAttribute('role', 'status');
  toolbar.appendChild(modes);
  toolbar.appendChild(options);
  toolbar.appendChild(hint);
  view.appendChild(toolbar);

  let mode = 'art';
  let currentBackground = '';
  let customUrl = '';
  let frameData = '';
  let ready = false;
  let token = 0;

  function setHint(message) { hint.textContent = message; }

  function canvas() {
    const canvases = playerHost.querySelectorAll('canvas');
    return canvases.length ? canvases[canvases.length - 1] : null;
  }

  // 保留透明通道并裁掉画布空白，避免将骨骼贴图 atlas 误作完整原画。
  function cropCanvas(source) {
    if (!source || !source.width || !source.height) return null;
    const copy = document.createElement('canvas');
    copy.width = source.width;
    copy.height = source.height;
    const ctx = copy.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(source, 0, 0);
    const pixels = ctx.getImageData(0, 0, copy.width, copy.height).data;
    let left = copy.width, top = copy.height, right = -1, bottom = -1;
    for (let y = 0; y < copy.height; y++) {
      for (let x = 0; x < copy.width; x++) {
        if (pixels[(y * copy.width + x) * 4 + 3] <= 16) continue;
        left = Math.min(left, x); top = Math.min(top, y);
        right = Math.max(right, x); bottom = Math.max(bottom, y);
      }
    }
    if (right < left || bottom < top) return null;
    const pad = 12;
    left = Math.max(0, left - pad); top = Math.max(0, top - pad);
    right = Math.min(copy.width - 1, right + pad);
    bottom = Math.min(copy.height - 1, bottom + pad);
    const out = document.createElement('canvas');
    out.width = right - left + 1;
    out.height = bottom - top + 1;
    out.getContext('2d').drawImage(copy, left, top, out.width, out.height, 0, 0, out.width, out.height);
    return out;
  }

  function capturePose() {
    try {
      const clipped = cropCanvas(canvas());
      return clipped ? clipped.toDataURL('image/png') : '';
    } catch (err) {
      console.warn('NIKKE Spine 静态立绘截图失败', err);
      return '';
    }
  }

  function showStill(url, expectedToken, source) {
    const img = new Image();
    img.onload = function () {
      if (expectedToken !== token) return;
      still.src = url;
      still.dataset.source = source;
      ready = true;
      applyMode();
      setHint(source === 'render' ? '静态图来自 Spine 渲染，非独立官方原画' : '已加载本地静态立绘');
    };
    img.onerror = function () {
      if (expectedToken !== token) return;
      if (source !== 'render' && frameData) showStill(frameData, expectedToken, 'render');
      else { ready = true; applyMode(); setHint('静态原画不可用，可切换动态模型'); }
    };
    img.src = url;
  }

  function applyMode() {
    const stillVisible = mode === 'art' && ready && !!still.src && still.complete && !!still.naturalWidth;
    still.hidden = !stillVisible;
    // visibility 不会改变 SpinePlayer 的容器大小，切换模式不需重建骨骼。
    playerHost.style.visibility = stillVisible ? 'hidden' : 'visible';
    background.hidden = mode !== 'scene' || !currentBackground || !background.naturalWidth;
    backgrounds.disabled = mode !== 'scene';
    upload.classList.toggle('disabled', mode !== 'scene');
    document.querySelectorAll('.nikke-view-modes button').forEach(function (button) {
      button.classList.toggle('on', button.dataset.mode === mode);
    });
    if (mode === 'scene' && !currentBackground) {
      setHint('可导入本地背景，或把图片放入 nikke/data/backgrounds 后重建清单');
    } else if (mode === 'dynamic') {
      setHint('Spine 动态模型 · 点击动作按钮切换');
    }
  }

  function switchMode(next) {
    if (!labels[next]) return;
    mode = next;
    applyMode();
  }

  function setBackground(url) {
    currentBackground = url;
    if (!url) {
      background.removeAttribute('src');
      background.hidden = true;
      applyMode();
      return;
    }
    background.onload = function () {
      applyMode();
      if (mode === 'scene') setHint('场景与角色为独立图层，不代表官方皮肤专属背景');
    };
    background.onerror = function () {
      background.hidden = true;
      setHint('背景加载失败，请检查文件路径');
    };
    background.src = url;
    applyMode();
  }

  function onStageEnter() {
    ++token;
    frameData = '';
    ready = false;
    still.removeAttribute('src');
    still.hidden = true;
    // 保留用户上一次选的背景，但在原画模式下隐藏它。
    switchMode('art');
    setHint('正在生成静态人物预览…');
  }

  function onPoseChanging() {
    ++token;
    frameData = '';
    ready = false;
    still.removeAttribute('src');
    still.hidden = true;
    playerHost.style.visibility = 'visible';
    if (mode === 'art') setHint('正在生成静态人物预览…');
  }

  // SpinePlayer success 表示资源加载成功；待首帧绘制结束后提取透明画面。
  function onPoseReady() {
    const expectedToken = token;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        setTimeout(function () {
          if (expectedToken !== token) return;
          frameData = capturePose();
          const c = manifest.characters[current.idx];
          const sourcePath = current.pose === 'fb' && c ? c.art : '';
          if (sourcePath) showStill(sourcePath, expectedToken, 'file');
          else if (frameData) showStill(frameData, expectedToken, 'render');
          else { ready = true; applyMode(); setHint('未获取到透明画面，建议尝试其他姿态'); }
        }, 180);
      });
    });
  }

  function onStageExit() {
    ++token;
    ready = false;
    frameData = '';
    still.removeAttribute('src');
    playerHost.style.visibility = 'visible';
  }

  function fillBackgrounds() {
    if (backgrounds.dataset.filled || !manifest) return;
    backgrounds.dataset.filled = '1';
    // manifest 只登记实际存在的图片，不强行把第三方宣传图算作官方原画。
    (manifest.backgrounds || []).forEach(function (entry) {
      if (!entry || !entry.file) return;
      const option = document.createElement('option');
      option.value = entry.file;
      option.textContent = (entry.category ? entry.category + ' · ' : '') + (entry.name || entry.id);
      backgrounds.appendChild(option);
    });
  }

  function drawCover(ctx, img, w, h) {
    const iw = img.naturalWidth, ih = img.naturalHeight;
    if (!iw || !ih) return;
    const scale = Math.max(w / iw, h / ih);
    const rw = iw * scale, rh = ih * scale;
    ctx.drawImage(img, (w - rw) / 2, (h - rh) / 2, rw, rh);
  }

  function toDownload(source, filename) {
    const link = document.createElement('a');
    link.href = source;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function exportPNG() {
    const c = manifest.characters[current.idx];
    if (!c) return;
    const filename = c.id + '_' + current.pose + '_' + mode + '.png';
    if (mode === 'art') {
      if (still.complete && still.naturalWidth) {
        const out = document.createElement('canvas');
        out.width = still.naturalWidth;
        out.height = still.naturalHeight;
        out.getContext('2d').drawImage(still, 0, 0);
        toDownload(out.toDataURL('image/png'), filename);
        return;
      }
      setHint('静态立绘仍在加载，无法导出');
      return;
    }
    if (mode === 'dynamic') {
      const frame = capturePose();
      if (frame) toDownload(frame, filename);
      else setHint('模型画布暂不可用，无法导出');
      return;
    }
    const spineCanvas = canvas();
    if (!spineCanvas) { setHint('模型尚未加载，无法导出场景'); return; }
    const out = document.createElement('canvas');
    out.width = spineCanvas.width;
    out.height = spineCanvas.height;
    const ctx = out.getContext('2d');
    if (currentBackground && background.complete && background.naturalWidth) {
      drawCover(ctx, background, out.width, out.height);
    }
    ctx.drawImage(spineCanvas, 0, 0, out.width, out.height);
    try {
      toDownload(out.toDataURL('image/png'), filename);
    } catch (err) {
      setHint('背景跨域或画布不可读，无法导出：' + err.message);
    }
  }

  window.NikkeArt = {
    onStageEnter, onStageExit, onPoseChanging, onPoseReady,
    fillBackgrounds, switchMode,
    exportPoseFrame: function () { return frameData || capturePose(); },
    get ready() { return ready; },
  };
  if (typeof manifest !== 'undefined' && manifest) fillBackgrounds();
})();
