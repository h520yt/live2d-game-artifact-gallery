/* 已安装的点唱机 Spine 4.2：检查实际前景像素，而非仅仅存在 Canvas。 */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");
const {PNG}=require("pngjs");

const OUT=path.resolve(__dirname,"../test-output/spine-audit");
const ids=["301703","302003","301103","302403","301603"];
fs.mkdirSync(OUT,{recursive:true});
function foreground(full,bg){
  const a=PNG.sync.read(full),b=PNG.sync.read(bg);
  assert.equal(a.width,b.width);assert.equal(a.height,b.height);
  let count=0,left=a.width,top=a.height,right=-1,bottom=-1;
  for(let y=0;y<a.height;y+=2)for(let x=0;x<a.width;x+=2){
    const i=(y*a.width+x)*4;
    const diff=Math.abs(a.data[i]-b.data[i])+
      Math.abs(a.data[i+1]-b.data[i+1])+
      Math.abs(a.data[i+2]-b.data[i+2]);
    if(diff<=75)continue;
    count++;left=Math.min(left,x);top=Math.min(top,y);
    right=Math.max(right,x);bottom=Math.max(bottom,y);
  }
  return {count,left,top,right,bottom,width:a.width,height:a.height};
}
(async()=>{
  const browser=await chromium.launch({headless:true,args:[
    "--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"
  ]});
  const failures=[];
  try{
    for(const id of ids){
      const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
      const pageErrors=[];
      page.on("pageerror",error=>pageErrors.push(error.message));
      try{
        await page.goto("http://127.0.0.1:8000/reverse1999/viewer/",{waitUntil:"domcontentloaded"});
        await page.locator('#models .sg-card[data-key="'+id+'"]').click();
        await page.waitForFunction(id=>{
          const stage=document.querySelector("#spine-stage");
          const status=document.querySelector("#status");
          const player=document.querySelector("#spine-container canvas");
          return String(selected?.id)===id&&!stage.hidden&&status.hidden&&
            player&&player.width>100&&player.height>100;
        },id,{timeout:90000});
        await page.waitForTimeout(700);
        const stage=page.locator("#spine-stage");
        const full=await stage.screenshot({path:path.join(OUT,id+"-model.png")});
        await page.evaluate(()=>{document.getElementById("spine-container").style.visibility="hidden";});
        await page.waitForTimeout(100);
        const empty=await stage.screenshot();
        const pixels=foreground(full,empty);
        console.log("SPINE-AUDIT",JSON.stringify({id,pixels,pageErrors}));
        const issues=[];
        if(pixels.count<1000)issues.push("no significant actual Spine foreground");
        if(pixels.left<pixels.width*.005||pixels.top<pixels.height*.005||
           pixels.right>pixels.width*.995||pixels.bottom>pixels.height*.995){
           issues.push("Spine foreground touches stage bounds");
        }
        if(pageErrors.length)issues.push(pageErrors.join(";"));
        if(issues.length)failures.push({id,issues});
      }catch(e){failures.push({id,error:e.message});}
      finally{await page.close();}
    }
  }finally{await browser.close();}
  console.log("SPINE-ALL",ids.length,"FAILURES",JSON.stringify(failures));
  assert.deepEqual(failures,[]);
})().catch(err=>{console.error(err);process.exit(1);});
