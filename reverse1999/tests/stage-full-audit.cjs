/* 统一大舞台全类型回归测试：捕捉真实 WebGL 像素与背景，并生成证据截图。 */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");

const ROOT=path.resolve(__dirname,"../test-output/stage-audit");
const catalog=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../viewer/manifest.json"),"utf8"));
const ids=["308303","308603","315503","313403","306604","311604","308804"];
const widths=[{width:1776,height:800},{width:1366,height:900}];
fs.mkdirSync(ROOT,{recursive:true});

async function verify(page,id,viewport){
  const errors=[];
  page.on("pageerror",error=>errors.push(error.message));
  await page.goto("http://127.0.0.1:8000/reverse1999/viewer/",{waitUntil:"domcontentloaded"});
  const card=page.locator('#models .sg-card[data-key="'+id+'"]');
  await card.waitFor({state:"visible",timeout:40000});
  await card.click();
  await page.waitForFunction(skinId=>{
    const status=document.querySelector("#status");
    const area=document.querySelector("#stage-area");
    return selected && String(selected.id)===skinId && active &&
      area && !area.hidden && status.hidden;
  },id,{timeout:95000});
  await page.waitForTimeout(500);
  const report=await page.evaluate(()=>{
    const area=document.querySelector("#stage-area");
    const background=document.querySelector("#live2d-background");
    return {
      name:selected.name, skin:selected.skin, type:selected.type, id:String(selected.id),
      dims:{width:area.clientWidth,height:area.clientHeight},
      drawn:visiblePixels(),
      bg:{
        present:!!selected.background,visible:!background.hidden,
        loaded:background.complete&&background.naturalWidth>500,
        width:background.naturalWidth,
      },
      canvas:{width:document.querySelector("#canvas").width,
        height:document.querySelector("#canvas").height},
      note:{visible:!document.querySelector("#background-note").hidden,
        text:document.querySelector("#background-note").textContent},
    };
  });
  await page.screenshot({path:path.join(ROOT,id+"-"+viewport.width+"x"+viewport.height+".png")});
  const b=report.drawn, w=report.dims.width,h=report.dims.height;
  const problems=[];
  if(!b)problems.push("no alpha pixels");
  else{
    if(b.top<h*.020)problems.push("head clipped");
    if(b.bottom>h*.980)problems.push("bottom clipped");
    if(b.left<w*.016||b.right>w*.984)problems.push("horizontal crop");
    if((b.bottom-b.top)<h*.35)problems.push("portrait too small");
  }
  if(report.type==="scene-live2d" && (!report.bg.visible||!report.bg.loaded)){
    problems.push("UNIQUE same-skin background unavailable");
  }
  if(report.type==="cubism"&&report.bg.present===false&&!report.note.visible){
    problems.push("Jukebox missing-bg disclosure unavailable");
  }
  if(errors.length)problems.push("JS exceptions "+errors.join("; "));
  report.problems=problems;
  console.log("GALLERY-AUDIT",JSON.stringify({...viewport,...report}));
  return report;
}

(async()=>{
  const browser=await chromium.launch({
    headless:true,args:["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"]
  });
  const failures=[];
  try{
    for(const id of ids){
      const model=catalog.models.find(m=>String(m.id)===id);
      if(!model)throw new Error("not indexed "+id);
      for(const viewport of widths){
        const page=await browser.newPage({viewport,deviceScaleFactor:1});
        try{
          const report=await verify(page,id,viewport);
          if(report.problems.length)failures.push({id,viewport,problems:report.problems});
        }catch(error){
          failures.push({id,viewport,error:error.message});
          try{await page.screenshot({path:path.join(ROOT,id+"-"+viewport.width+"x"+viewport.height+"-error.png")});}catch{}
        }finally{await page.close();}
      }
    }
  }finally{await browser.close();}
  console.log("TOTAL",ids.length*widths.length,"FAILURES",JSON.stringify(failures));
  assert.deepEqual(failures,[]);
})().catch(error=>{console.error(error);process.exit(1);});
