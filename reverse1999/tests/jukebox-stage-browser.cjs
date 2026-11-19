/* 有实际模型时验证 1999 大舞台：人物可见边界、缺背景说明、全屏及窄屏构图。 */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");

const out=path.resolve(__dirname,"../test-output/stage-311604");
fs.mkdirSync(out,{recursive:true});
const shapes=[
  {width:1776,height:800},
  {width:1366,height:900}
];

(async()=>{
  const browser=await chromium.launch({headless:true,args:[
    "--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"
  ]});
  try{
    for(const viewport of shapes){
      const page=await browser.newPage({viewport,deviceScaleFactor:1});
      const errors=[];
      page.on("pageerror",e=>errors.push(e.message));
      try{
        await page.goto("http://127.0.0.1:8000/reverse1999/viewer/",{waitUntil:"domcontentloaded"});
        const card=page.locator('#models .sg-card[data-key="311604"]');
        await card.waitFor({state:"visible",timeout:30000});
        await card.click();
        await page.waitForFunction(()=>{
          const area=document.getElementById("stage-area");
          const status=document.getElementById("status");
          return area&&!area.hidden&&status.hidden&&
            typeof active!=="undefined"&&active&&active.width>30;
        },null,{timeout:90000});
        await page.waitForTimeout(500);
        const metrics=await page.evaluate(()=>{
          const area=document.getElementById("stage-area");
          const note=document.getElementById("background-note");
          const rect=area.getBoundingClientRect();
          return {
            stage:{width:rect.width,height:rect.height},
            bounds:typeof visiblePixels==="function"?visiblePixels():null,
            noteHidden:note.hidden,note:note.textContent,
            fullSceneButton:document.getElementById("full-scene-controls").hidden,
            type:selected?.type,skin:selected?.skin,
          };
        });
        await page.locator(".sg-workspace").screenshot({
          path:path.join(out,"311604-"+viewport.width+"x"+viewport.height+".png"),
          animations:"disabled",
        });
        console.log("STAGE-METRICS",JSON.stringify({viewport,...metrics}));
        assert.equal(metrics.type,"cubism");
        assert.ok(metrics.stage.width>500&&metrics.stage.height>380);
        assert.equal(metrics.noteHidden,false,"must disclose missing same-skin backdrop");
        assert.match(metrics.note,/尚无对应的专属场景背景/);
        assert.equal(metrics.fullSceneButton,true,"must not claim complete background");
        assert.ok(metrics.bounds,"could not sample character pixels");
        const b=metrics.bounds,w=metrics.stage.width,h=metrics.stage.height;
        // 与画布四边保持安全距离。特别防止人物头部被顶部边缘吞掉。
        assert.ok(b.top>h*.025,"character head clipped at top: "+JSON.stringify(b));
        assert.ok(b.bottom<h*.97,"character feet clipped at bottom: "+JSON.stringify(b));
        assert.ok(b.left>w*.015&&b.right<w*.985,
          "character outside horizontal bounds: "+JSON.stringify(b));
        assert.deepEqual(errors,[],"browser errors: "+errors.join(","));
      }finally{await page.close();}
    }
  }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exit(1);});
