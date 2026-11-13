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
    await page.getByRole('button',{name:/露西 · 生如行棋/}).click({timeout:15000});
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
    await page.screenshot({path:path.join(dir,'308603-showcase.png'),fullPage:true});
    await page.locator('#scene-bg-toggle').click();
    await page.screenshot({path:path.join(dir,'308603-foreground-only.png'),fullPage:true});
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
