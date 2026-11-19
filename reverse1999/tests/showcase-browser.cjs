/* 在真实上游资源下载后，用无头 Chrome 验证同皮肤背景和 Spine 商城动画能加载。 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

async function main(){
  const dir = path.resolve(__dirname,'../test-output');
  fs.mkdirSync(dir,{recursive:true});
  const browser = await chromium.launch({
    headless:true,
    args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']
  });
  let page;
  try{
    page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',err=>errors.push(err.message));
    await page.goto('http://127.0.0.1:8000/reverse1999/viewer/',{waitUntil:'domcontentloaded',timeout:20000});
    // 新版画廊按钮 aria-label 采用角色名 + 衣着名，不再依赖旧侧栏按钮文案。
    await page.locator('#models .sg-card[data-key="308603"]').click({timeout:15000});
    await page.waitForFunction(()=>{
      const background=document.querySelector('#showcase-background');
      const canvas=document.querySelector('#spine-container canvas');
      return background && background.complete && background.naturalWidth>0
        && canvas && canvas.width>0 && canvas.height>0;
    },null,{timeout:45000});
    await page.waitForFunction(()=>{
      const overlay=document.querySelector('#status');
      const motions=document.querySelectorAll('#motions button');
      return overlay.hidden && motions.length>0;
    },null,{timeout:45000});
    const canvasInfo=await page.evaluate(()=>({
      playerCanvas:!!spinePlayer?.canvas,
      canvasList:[...document.querySelectorAll('#spine-container canvas')].map(x=>({
        width:x.width,height:x.height,className:x.className,
        parent:x.parentElement?.className,hidden:x.hidden,
        opacity:getComputedStyle(x).opacity
      }))
    }));
    console.log('SPINE_CANVAS_INFO',JSON.stringify(canvasInfo));
    const result=await page.evaluate(()=>({
      backgroundWidth:document.querySelector('#showcase-background').naturalWidth,
      canvasWidth:document.querySelector('#spine-container canvas').width,
      motions:[...document.querySelectorAll('#motions button')].map(b=>b.textContent),
      label:document.querySelector('#model-title').textContent,
      mode:document.querySelector('#spine-stage').classList.contains('showcase')
    }));
    assert.equal(result.mode,true);
    assert.equal(result.label,'露西');
    assert.ok(result.backgroundWidth>100);
    assert.ok(result.canvasWidth>100);
    assert.ok(result.motions.length>0);
    assert.deepEqual(errors,[]);
    // 核对人物真实出现在最终合成图中，而不是被一张不透明 PNG 覆盖。
    await page.waitForTimeout(900); // 给 Spine WebGL 动画和背景图留出真实绘制帧
    const { PNG } = require('pngjs');
    // fixed 模式下绝不能 fullPage：浏览器整页截图会把背后的卡片列表一起带进来。
    const stage=page.locator('#spine-stage');
    const fullImage = await stage.screenshot({path:path.join(dir,'308603-showcase.png')});
    await page.evaluate(()=>{sceneScale=0;updateSceneControls();});
    await page.waitForTimeout(550);
    const backgroundOnly = await stage.screenshot({path:path.join(dir,'308603-background-only.png')});
    await page.evaluate(()=>{sceneScale=1.8;updateSceneControls();});
    await page.waitForTimeout(220);
    const foreground = PNG.sync.read(fullImage);
    const background = PNG.sync.read(backgroundOnly);
    assert.equal(foreground.width,background.width);
    // 背景不能只有人物后面一小张贴纸：要求填充大部分舞台可见范围。
    let stageBackgroundPixels=0;
    // 裁剪到实际的舞台截图，而不是旧版三栏页面上硬编码的绝对像素。
    for(let y=0;y<background.height;y+=2){
      for(let x=0;x<background.width;x+=2){
        const i=(y*background.width+x)*4;
        if(background.data[i]+background.data[i+1]+background.data[i+2]>240)stageBackgroundPixels++;
      }
    }
    assert.ok(stageBackgroundPixels>16000,
      'Spine 商城背景颜色像素不足，背景可能未真正绘制：'+stageBackgroundPixels);
    result.backgroundVisiblePixels=stageBackgroundPixels;
    let modelPixels=0;
    for(let y=0;y<foreground.height;y+=2){
      for(let x=0;x<foreground.width;x+=2){
        const i=(y*foreground.width+x)*4;
        const diff=Math.abs(foreground.data[i]-background.data[i])+
          Math.abs(foreground.data[i+1]-background.data[i+1])+
          Math.abs(foreground.data[i+2]-background.data[i+2]);
        if(diff>55)modelPixels++;
      }
    }
    assert.ok(modelPixels>400,'商城人物被背景遮挡：前景与纯背景差异像素太少: '+modelPixels);
    result.modelVisiblePixels=modelPixels;
    await page.locator('#viewer-tools summary').click();
    await page.locator('#scene-bg-toggle').click();
    await stage.screenshot({path:path.join(dir,'308603-foreground-only.png')});
    await page.locator('#scene-bg-toggle').click();
    fs.writeFileSync(path.join(dir,'validation.json'),JSON.stringify(result,null,2));
    console.log('BROWSER-SMOKE-PASS',JSON.stringify(result));
  }finally{
    if(page && !fs.existsSync(path.join(dir,'308603-showcase.png'))){
      await page.screenshot({path:path.join(dir,'failure.png'),fullPage:true}).catch(()=>{});
    }
    await browser.close();
  }
}
main().catch(error=>{console.error(error);process.exit(1);});
