/* 对 313403 原始 Cubism 动态衣着、专属背景和动作做真实浏览器验收。 */
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium}=require('playwright');
const {PNG}=require('pngjs');

(async()=>{
  const dir=path.resolve(__dirname,'../test-output');
  fs.mkdirSync(dir,{recursive:true});
  const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  let page;
  try{
    page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8000/reverse1999/viewer/',{waitUntil:'domcontentloaded',timeout:20000});
    await page.locator('button.item').filter({hasText:'Live2D 动态衣着+专属背景'}).click({timeout:15000});
    await page.waitForFunction(()=>{
      const bg=document.querySelector('#live2d-background');
      return bg && !bg.hidden && bg.complete && bg.naturalWidth>100 &&
        !document.querySelector('#stage-area').hidden &&
        document.querySelector('#status').hidden && active && active.width>100 &&
        [...document.querySelectorAll('#motions button')].some(b=>b.textContent==='b_ruchang');
    },null,{timeout:80000});
    const info=await page.evaluate(()=>({
      type:selected.type,
      title:document.querySelector('#model-title').textContent,
      backgroundWidth:document.querySelector('#live2d-background').naturalWidth,
      motions:[...document.querySelectorAll('#motions button')].map(b=>b.textContent),
      expressions:[...document.querySelectorAll('#expressions button')].map(b=>b.textContent),
      modelWidth:active.width
    }));
    assert.equal(info.type,'scene-live2d');
    assert.equal(info.title,'贝丽尔');
    for(const name of ['b_idle','b_ruchang','b_yanzou','b_jiaohu01','b_jiaohu02','b_jiaohu03','b_jiaohu04'])
      assert.ok(info.motions.includes(name),'Missing animation '+name);
    assert.ok(info.expressions.length>=7,'Expected original expression assets');
    const stage=page.locator('#stage-area');
    await page.waitForTimeout(1000);
    const full=PNG.sync.read(await stage.screenshot({path:path.join(dir,'313403-live2d-background.png')}));
    await page.evaluate(()=>{active.visible=false;});
    await page.waitForTimeout(300);
    const bg=PNG.sync.read(await stage.screenshot({path:path.join(dir,'313403-background-only.png')}));
    assert.equal(full.width,bg.width);
    let changed=0;
    for(let i=0;i<full.data.length;i+=4){
      const diff=Math.abs(full.data[i]-bg.data[i])+Math.abs(full.data[i+1]-bg.data[i+1])+Math.abs(full.data[i+2]-bg.data[i+2]);
      if(diff>45)changed++;
    }
    assert.ok(changed>800,'Cubism model not visibly painted over the original background: '+changed);
    await page.evaluate(()=>{active.visible=true;});
    await page.getByRole('button',{name:'b_ruchang',exact:true}).click();
    await page.waitForTimeout(400);
    assert.equal((await page.locator('#status').isHidden()),true);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(dir,'313403-validation.json'),JSON.stringify({...info,modelPixelsComparedToBackground:changed},null,2));
    console.log('BERYL-LIVE2D-BROWSER-SMOKE-PASS',JSON.stringify({...info,modelPixelsComparedToBackground:changed}));
  }finally{
    if(page)await page.screenshot({path:path.join(dir,'313403-debug-final.png')}).catch(()=>{});
    await browser.close();
  }
})().catch(err=>{console.error(err);process.exit(1);});
