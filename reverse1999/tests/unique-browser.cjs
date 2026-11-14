/* 全部 UNIQUE 女性衣着动态显示验收：实际资源 + Chromium + PNG 前景像素对比。 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const {PNG} = require('pngjs');

const root=path.resolve(__dirname,'../viewer');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'unique-catalog.json'),'utf8')).skins;

async function verifySkin(browser, row) {
  const page=await browser.newPage({viewport:{width:1366,height:900},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  try{
    await page.goto('http://127.0.0.1:8000/reverse1999/viewer/',{waitUntil:'domcontentloaded',timeout:25000});
    // 页面要等 manifest + 静态目录加载完，筛选按钮才会绑定 onclick。
    await page.waitForFunction(()=>typeof document.querySelector('#filter-unique')?.onclick==='function',null,{timeout:30000});
    await page.locator('#filter-unique').click();
    const buttons=page.locator('#models button.item');
    await page.waitForFunction(()=>document.querySelectorAll('#models button.item').length===12,{timeout:25000});
    assert.equal(await buttons.count(),12);
    const btn=buttons.filter({hasText:row.name+' · '+row.skin});
    assert.equal(await btn.count(),1,'Expected unique skin button for '+row.id);
    await btn.click();
    await page.waitForFunction(id=>{
      const bg=document.querySelector('#live2d-background');
      const overlay=document.querySelector('#status');
      const motions=document.querySelectorAll('#motions button');
      return selected && String(selected.id)===String(id) && selected.tier==='UNIQUE'
        && active && active.width>100 && !document.querySelector('#stage-area').hidden
        && bg && !bg.hidden && bg.complete && bg.naturalWidth>500
        && overlay.hidden && motions.length>0;
    },row.id,{timeout:90000});

    const info=await page.evaluate(()=>({
      id:selected.id, name:selected.name, skin:selected.skin,
      modelWidth:active.width,
      motions:[...document.querySelectorAll('#motions button')].map(x=>x.textContent),
      expressions:[...document.querySelectorAll('#expressions button')].map(x=>x.textContent),
      backgroundWidth:document.querySelector('#live2d-background').naturalWidth
    }));
    assert.equal(String(info.id),String(row.id));
    assert.ok(info.motions.length>=10,'Expected numerous motions for '+row.id);
    assert.ok(info.backgroundWidth>500);
    await page.waitForTimeout(300);
    const stage=page.locator('#stage-area');
    // 隐去背景（只用于测试时的前景像素对比），避免 DOM 微小宽度变化让背景整体错位。
    await page.evaluate(()=>{
      const area=document.querySelector('#stage-area');
      const rect=area.getBoundingClientRect();
      area.style.width=Math.round(rect.width)+'px';
      area.style.height=Math.round(rect.height)+'px';
      document.querySelector('#live2d-background').style.visibility='hidden';
    });
    await page.waitForTimeout(200);
    const full=PNG.sync.read(await stage.screenshot());
    await page.evaluate(()=>{active.visible=false;});
    await page.waitForTimeout(220);
    const bg=PNG.sync.read(await stage.screenshot());
    const width=Math.min(full.width,bg.width);
    const height=Math.min(full.height,bg.height);
    let modelPixels=0;
    let left=width,top=height,right=-1,bottom=-1;
    for(let y=0;y<height;y++){
      for(let x=0;x<width;x++){
        const i=(y*full.width+x)*4;
        const j=(y*bg.width+x)*4;
        const diff=Math.abs(full.data[i]-bg.data[j])+
          Math.abs(full.data[i+1]-bg.data[j+1])+
          Math.abs(full.data[i+2]-bg.data[j+2]);
        if(diff>50){
          modelPixels++;
          left=Math.min(left,x);right=Math.max(right,x);
          top=Math.min(top,y);bottom=Math.max(bottom,y);
        }
      }
    }
    // 区分“确实渲染出人物”和“人物被裁掉头部/下半身”。
    // 验证实际前景像素不触及画布边缘，覆盖所有 UNIQUE 衣着。
    assert.ok(top>=height*.015 && bottom<=height*.985 &&
      left>=width*.015 && right<=width*.985,
      'Model clipped or too close to stage edge: '+row.id+' bounds='+
        JSON.stringify({left,top,right,bottom,width,height}));
    assert.ok(modelPixels>500,'Live2D foreground visually absent: '+row.id+' '+modelPixels);
    await page.evaluate(()=>{
      active.visible=true;
      document.querySelector('#live2d-background').style.visibility='visible';
    });
    // 触发第一组可用动作，实际检查运行时没有抛异常。
    await page.locator('#motions button').first().click();
    await page.waitForTimeout(220);
    assert.deepEqual(errors,[],'Unexpected browser JS error for skin '+row.id);
    console.log('UNIQUE-BROWSER-PASS',JSON.stringify({
      id:row.id,name:row.name,skin:row.skin,
      motions:info.motions.length,expressions:info.expressions.length,
      backgroundWidth:info.backgroundWidth,visibleModelPixels:modelPixels,
      modelBounds:{left,top,right,bottom,width,height}
    }));
  }finally{
    await page.close();
  }
}

(async()=>{
  assert.equal(catalog.length,12,'Expected exactly 12 UNIQUE skin records');
  const browser=await chromium.launch({headless:true,args:[
    '--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl'
  ]});
  try{
    for(const [index,row] of catalog.entries()){
      console.log('UNIQUE-BROWSER-VERIFY',index+1,'/',catalog.length,row.id,row.name);
      await verifySkin(browser,row);
    }
    console.log('UNIQUE-BROWSER-ALL-PASS: 12 / 12');
  }finally{
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1);});
