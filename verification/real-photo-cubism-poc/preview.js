async function loadModelAssets() {
  if (window.location.protocol === 'file:') {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = './preview-data.js';
      script.onload = resolve;
      script.onerror = () => reject(new Error('无法读取本地模型数据。请在原文件夹打开 preview.html。'));
      document.head.append(script);
    });
    const data = window.portraitPreviewData;
    if (!data) throw new Error('本地模型数据缺失');
    const bytes = Uint8Array.from(atob(data.moc), character => character.charCodeAt(0)).buffer;
    return { bytes, atlasUrl: data.atlas };
  }

  const manifestResponse = await fetch('./portrait.model3.json');
  if (!manifestResponse.ok) throw new Error(`模型清单返回 ${manifestResponse.status}`);
  const { FileReferences: files } = await manifestResponse.json();
  const mocResponse = await fetch(files.Moc);
  if (!mocResponse.ok) throw new Error(`模型返回 ${mocResponse.status}`);
  return { bytes: await mocResponse.arrayBuffer(), atlasUrl: files.Textures[0] };
}

async function start() {
  const core = window.Live2DCubismCore;
  if (!core) throw new Error('无法加载 Cubism Core。请在仓库的原文件夹打开 preview.html。');
  const canvas = document.querySelector('canvas');
  const gl = canvas.getContext('webgl', { preserveDrawingBuffer: true });
  if (!gl) throw new Error('WebGL 不可用');

  function shader(type, source) {
    const handle = gl.createShader(type);
    gl.shaderSource(handle, source);
    gl.compileShader(handle);
    if (!gl.getShaderParameter(handle, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(handle));
    }
    return handle;
  }

  const program = gl.createProgram();
  gl.attachShader(program, shader(gl.VERTEX_SHADER, `
    attribute vec2 position;
    attribute vec2 uv;
    varying vec2 textureUV;
    void main() {
      gl_Position = vec4(position * 2.0, 0.0, 1.0);
      textureUV = vec2(uv.x, 1.0 - uv.y);
    }
  `));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, `
    precision mediump float;
    varying vec2 textureUV;
    uniform sampler2D atlas;
    uniform float opacity;
    void main() {
      vec4 color = texture2D(atlas, textureUV);
      gl_FragColor = vec4(color.rgb, color.a * opacity);
    }
  `));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  gl.enable(gl.BLEND);
  gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

  const { bytes, atlasUrl } = await loadModelAssets();
  const moc = core.Moc.fromArrayBuffer(bytes);
  if (!moc) throw new Error('Cubism Core 无法读取 MOC3');
  const model = core.Model.fromMoc(moc);
  if (!model) throw new Error('Cubism Core 无法创建模型');

  const atlas = new Image();
  atlas.src = atlasUrl;
  await atlas.decode();
  gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, atlas);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const position = gl.getAttribLocation(program, 'position');
  const uv = gl.getAttribLocation(program, 'uv');
  const opacity = gl.getUniformLocation(program, 'opacity');
  const vertexBuffer = gl.createBuffer();
  const uvBuffer = gl.createBuffer();
  const indexBuffer = gl.createBuffer();
  const drawables = model.drawables;
  const controls = Array.from(model.parameters.ids, id => document.getElementById(id));
  if (controls.some(control => !control)) throw new Error('缺少模型参数控件');

  function attribute(location, buffer, values) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, values, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, 2, gl.FLOAT, false, 0, 0);
  }

  function draw() {
    controls.forEach((control, index) => { model.parameters.values[index] = Number(control.value); });
    model.update();
    gl.clear(gl.COLOR_BUFFER_BIT);
    const order = Array.from(drawables.renderOrders.keys());
    order.sort((a, b) => drawables.renderOrders[a] - drawables.renderOrders[b]);
    for (const index of order) {
      if (drawables.opacities[index] <= 0) continue;
      attribute(position, vertexBuffer, drawables.vertexPositions[index]);
      attribute(uv, uvBuffer, drawables.vertexUvs[index]);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, drawables.indices[index], gl.DYNAMIC_DRAW);
      gl.uniform1f(opacity, drawables.opacities[index]);
      gl.drawElements(gl.TRIANGLES, drawables.indexCounts[index], gl.UNSIGNED_SHORT, 0);
    }
    drawables.resetDynamicFlags();
  }

  controls.forEach(control => control.addEventListener('input', draw));
  draw();
  document.getElementById('status').textContent = '已通过 Cubism Core 加载。拖动滑块查看模型参数。';
  window.portraitProof = { core, gl, model, moc };
}

start().catch(error => {
  document.getElementById('status').textContent = error.message;
  console.error(error);
});
