/* 点唱机32套原始资源在真实 Chromium 中打开：按品类检查骨骼和动画。 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const staticList=JSON.parse(fs.readFileSync(
  path.resolve(__dirname,'../viewer/jukebox-catalog.json'),'utf8')).skins;
(async()=>{
  assert.equal(staticList.length,32);
  const browser=await chromium.launch({
    headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']
  });
  let tested=0;
  try{
    for(const row of staticList){
      const page=await browser.newPage({viewport:{width:1366,height:900}});
      const errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      try{
        await page.goto('http://127.0.0.1:8000/reverse1999/viewer/',{waitUntil:'domcontentloaded',timeout:30000});
        await page.waitForFunction(()=>typeof document.querySelector('#filter-jukebox')?.onclick==='function',null,{timeout:30000});
        await page.locator('#filter-jukebox').click();
        const buttons=page.locator('#models button.item');
        assert.equal(await buttons.count(),32);
        const entry=buttons.filter({hasText:row.name+' · '+row.skin});
        assert.equal(await entry.count(),1,'missing list entry '+row.id);
        await entry.click();
        if(row.type==='cubism'){
          await page.waitForFunction(id=>selected&&String(selected.id)===String(id)&&
            active&&active.width>20&&document.querySelector('#status').hidden&&
            document.querySelectorAll('#motions button').length>0,row.id,{timeout:80000});
          const dimensions=await page.evaluate(()=>({w:active.width,h:active.height}));
          assert.ok(dimensions.w>20&&dimensions.h>20,row.id+' no Cubism visible');
        }else{
          await page.waitForFunction(id=>selected&&String(selected.id)===String(id)&&
            document.querySelector('#spine-stage')&&!document.querySelector('#spine-stage').hidden&&
            document.querySelector('#status').hidden&&
            document.querySelector('#spine-container canvas')?.width>50,row.id,{timeout:80000});
          const poses=await page.locator('#poses button').allTextContents();
          assert.deepEqual(new Set(poses),new Set(['ui','room','fight']));
        }
        assert.deepEqual(errors,[],row.id+' browser errors: '+errors.join(', '));
        console.log('JUKEBOX-BROWSER-PASS',row.id,row.name,row.skin,row.type);
        tested++;
      }finally{
        await page.close();
      }
    }
    assert.equal(tested,32);
    console.log('JUKEBOX-ALL-BROWSER-PASS 32/32');
  }finally{
    await browser.close();
  }
})().catch(e=>{console.error(e);process.exit(1);});
