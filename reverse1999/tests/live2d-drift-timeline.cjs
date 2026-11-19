"use strict";
/* 真实 1999 Cubism 动态画面时序检查：
 * 同一角色从加载到 8 秒后不应持续改变容器坐标，
 * 图片实际 alpha 中心不能一路朝屏幕一侧漂移。
 */
const fs=require("node:fs");
const path=require("node:path");
const assert=require("node:assert/strict");
const {chromium}=require("playwright");
const ids=["300306","308203","308804","311604","308303","315503"];
const out=path.resolve(__dirname,"../test-output/drift-timeline");
fs.mkdirSync(out,{recursive:true});
const timings=[0,250,750,1250,2000,3000,5000,8000];

async function snapshot(page,id,milliseconds) {
  const metrics=await page.evaluate(()=>{
    if(!active) return {missing:true};
    const area=document.querySelector("#stage-area");
    const canvas=document.querySelector("#canvas");
    const px=document.createElement("canvas");
    const ratio=canvas.width/canvas.height;
    px.width=Math.min(460,Math.round(260*ratio));
    px.height=260;
    const c=px.getContext("2d",{willReadFrequently:true});
    c.drawImage(canvas,0,0,px.width,px.height);
    const rgba=c.getImageData(0,0,px.width,px.height).data;
    let minX=px.width,minY=px.height,maxX=-1,maxY=-1,pixels=0;
    for(let y=0;y<px.height;y++){
      for(let x=0;x<px.width;x++){
        if(rgba[(y*px.width+x)*4+3]<65)continue;
        pixels++;minX=Math.min(minX,x);minY=Math.min(minY,y);
        maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);
      }
    }
    const bounds=pixels>80?{
      left:minX/px.width*area.clientWidth,
      right:(maxX+1)/px.width*area.clientWidth,
      top:minY/px.height*area.clientHeight,
      bottom:(maxY+1)/px.height*area.clientHeight
    }:null;
    return {x:active.position.x,y:active.position.y,scale:active.scale.x,
      width:area.clientWidth,height:area.clientHeight,
      statusVisible:!document.querySelector("#status").hidden,
      canvasOpacity:getComputedStyle(canvas).opacity,
      bounds,frameSeq:framingSequence};
  });
  await page.locator("#stage-area").screenshot({
    path:path.join(out,id+"-"+String(milliseconds).padStart(5,"0")+".png"),
    animations:"disabled"
  });
  console.log("DRIFT-TIMELINE",JSON.stringify({id,ms:milliseconds,...metrics}));
  return metrics;
}

(async()=>{
  const browser=await chromium.launch({headless:true,args:[
    "--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"
  ]});
  const failures=[];
  try{
    for(const id of ids){
      const page=await browser.newPage({viewport:{width:1776,height:800},deviceScaleFactor:1});
      const errors=[];
      page.on("pageerror",error=>errors.push(error.message));
      try{
        await page.goto("http://127.0.0.1:8000/reverse1999/viewer/",{waitUntil:"domcontentloaded"});
        await page.locator('#models .sg-card[data-key="'+id+'"]').click();
        await page.waitForFunction(id=>active&&String(selected?.id)===id,
          id,{timeout:90000});
        const first=Date.now(), samples=[];
        for(const time of timings){
          const delay=Math.max(0,time-(Date.now()-first));
          if(delay)await page.waitForTimeout(delay);
          samples.push(await snapshot(page,id,time));
        }
        const stable=samples.slice(4);
        const sx=stable.map(s=>s.x),sy=stable.map(s=>s.y);
        const zoom=stable.map(s=>s.scale);
        const swingX=Math.max(...sx)-Math.min(...sx);
        const swingY=Math.max(...sy)-Math.min(...sy);
        const swingScale=Math.max(...zoom)-Math.min(...zoom);
        const center=stable.filter(s=>s.bounds).map(s=>({
          x:(s.bounds.left+s.bounds.right)/2,
          y:(s.bounds.top+s.bounds.bottom)/2
        }));
        const movementX=center.length?Math.max(...center.map(x=>x.x))-Math.min(...center.map(x=>x.x)):null;
        const movementY=center.length?Math.max(...center.map(x=>x.y))-Math.min(...center.map(x=>x.y)):null;
        const earlyVisible=samples.some(s=>s.statusVisible&&s.canvasOpacity!=="0");
        const hiddenAfterReady=samples.some(s=>!s.statusVisible&&s.canvasOpacity!=="1");
        const beforeResize={...stable.at(-1)};
        // 历史回归：没有真正改变舞台尺寸时，重复触发 resize 不能重启自动定位。
        await page.evaluate(()=>{
          for(let i=0;i<7;i++)window.dispatchEvent(new Event("resize"));
        });
        await page.waitForTimeout(500);
        const afterResize=await page.evaluate(()=>({
          x:active.x,y:active.y,scale:active.scale.x,seq:framingSequence,
          statusVisible:!document.querySelector("#status").hidden
        }));
        const resizeStable=Math.abs(beforeResize.x-afterResize.x)<.5&&
          Math.abs(beforeResize.y-afterResize.y)<.5&&
          Math.abs(beforeResize.scale-afterResize.scale)<.0001&&
          beforeResize.frameSeq===afterResize.seq;
        const outcome={id,swingX,swingY,swingScale,movementX,movementY,
          earlyVisible,hiddenAfterReady,resizeStable,
          loading:stable.some(s=>s.statusVisible),errors};
        // 真实调整浏览器宽度，只允许在布局稳定后做一次重新定位。
        if(id==="308203"){
          const seqBefore=afterResize.seq;
          await page.setViewportSize({width:1366,height:900});
          await page.waitForFunction(seq=>{
            const stage=document.getElementById("stage-area");
            return stage.clientWidth===1366&&framingSequence>seq&&
              document.getElementById("status").hidden&&
              getComputedStyle(document.getElementById("canvas")).opacity==="1";
          },seqBefore,{timeout:15000});
          const resized=await page.evaluate(()=>({
            x:active.x,y:active.y,scale:active.scale.x,
            bounds:visiblePixels(),seq:framingSequence,
            width:document.getElementById("stage-area").clientWidth,
            height:document.getElementById("stage-area").clientHeight
          }));
          await page.waitForTimeout(1100);
          const settled=await page.evaluate(()=>({
            x:active.x,y:active.y,scale:active.scale.x,seq:framingSequence,
            bounds:visiblePixels()
          }));
          const br=settled.bounds;
          outcome.actualResizeStable=Math.abs(resized.x-settled.x)<.5&&
            Math.abs(resized.y-settled.y)<.5&&
            Math.abs(resized.scale-settled.scale)<.0001&&
            resized.seq===settled.seq&&!!br&&
            br.left>resized.width*.018&&br.right<resized.width*.98&&
            br.top>resized.height*.018&&br.bottom<resized.height*.98;
          await page.locator("#stage-area").screenshot({
            path:path.join(out,id+"-actual-resize.png"),animations:"disabled"
          });
        }
        console.log("DRIFT-RESULT",JSON.stringify(outcome));
        if(outcome.actualResizeStable===false||
          swingX>1||swingY>1||swingScale>.005||outcome.loading||
          earlyVisible||hiddenAfterReady||!resizeStable||
          movementX>stable[0].width*.12||movementY>stable[0].height*.16||
          errors.length||stable.some(s=>!s.bounds)){
          failures.push(outcome);
        }
      }catch(error){failures.push({id,error:error.message})}
      finally{await page.close()}
    }
  }finally{await browser.close()}
  console.log("DRIFT-SUMMARY",JSON.stringify(failures));
  assert.deepEqual(failures,[]);
})().catch(e=>{console.error(e);process.exitCode=1;});
