"use strict";
/** 跨游戏画廊行为回归，不需要浏览器及任何版权图片。 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {test} = require("node:test");

const script = fs.readFileSync(path.join(__dirname, "../shared/skin_gallery.js"), "utf8");

class Node {
  constructor(tag) {
    this.tagName=tag;this.children=[];this.dataset={};this.listeners={};
    this.hidden=false;this.value="";this.textContent="";this.isConnected=true;
    this.classList={add(){},remove(){}};
  }
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  addEventListener(type,handler){this.listeners[type]=handler;}
  dispatch(type){this.listeners[type]?.();}
  setAttribute(name,value){this[name]=value;}
  querySelector(selector){
    const match=/data-key='([^']+)'/.exec(selector);
    return this.children.find(row=>row.dataset.key===match?.[1])||null;
  }
  focus(options){this.focusOpts=options;}
  remove(){this.isConnected=false;}
}
function setup() {
  const scrollCalls=[],keyCallbacks={};
  const document={
    body:new Node("body"),
    createElement:tag=>new Node(tag),
    addEventListener:(type,handler)=>{keyCallbacks[type]=handler;},
  };
  const window={
    scrollY:737,
    scrollTo:opts=>scrollCalls.push(opts),
  };
  const sandbox={window,document,CSS:{escape:x=>x},console,Intl};
  vm.runInNewContext(script,sandbox);
  const grid=new Node("grid"),search=new Node("search"),sort=new Node("sort"),
    count=new Node("count"),detail=new Node("main");
  detail.hidden=true;
  const selected=[];
  const gallery=window.SkinGallery.create({
    grid,search,sort,count,detail,
    onOpen:item=>{selected.push(item.key);return !!item.ready;},
  });
  return {gallery,grid,search,sort,count,detail,selected,scrollCalls,keyCallbacks,window};
}

test("one card per skin even if upstream declares two rendering engines",()=>{
  const x=setup();
  x.gallery.setItems([
    {key:"313403",title:"贝丽尔",ready:true},
    {key:"313403",title:"贝丽尔",ready:true,preview:"../data/full_scenes/313403.png"},
    {key:"315901",title:"佩施塔",ready:true},
  ]);
  assert.equal(x.grid.children.length,2);
  assert.equal(x.count.textContent,"2 套 / 共 2 套");
});

test("opening a full-screen detail and returning retains original list DOM and scroll",()=>{
  const x=setup();
  x.gallery.setItems([
    {key:"313403",title:"贝丽尔",ready:true},
    {key:"315901",title:"佩施塔",ready:true},
  ]);
  const cards=x.grid.children.slice();
  assert.equal(x.gallery.open("313403",cards[0]),true);
  assert.equal(x.detail.hidden,false);
  assert.equal(x.gallery.navigate(1),true);
  assert.deepEqual(x.selected,["313403","315901"]);
  x.window.scrollY=0; // 模拟极端浏览器在关闭 overlay 时错误重置了滚动位置。
  x.gallery.close();
  assert.equal(x.detail.hidden,true);
  assert.equal(x.grid.children[0],cards[0]);
  assert.equal(x.grid.children[1],cards[1]);
  assert.equal(x.scrollCalls.length,1);
  assert.equal(x.scrollCalls[0].top,737);
  assert.equal(x.scrollCalls[0].behavior,"instant");
  assert.equal(cards[0].focusOpts.preventScroll,true);
});

test("a pending skin does not open an empty stage",()=>{
  const x=setup();
  x.gallery.setItems([{key:"300001",title:"未下载",ready:false}]);
  assert.equal(x.gallery.open("300001",x.grid.children[0]),false);
  assert.equal(x.detail.hidden,true);
});

test("search only changes the card list and never introduces collection tabs",()=>{
  const x=setup();
  x.gallery.setItems([
    {key:"313403",title:"贝丽尔",ready:true},
    {key:"315901",title:"佩施塔",ready:true,searchText:"白雪"},
  ]);
  x.search.value="白雪";x.search.dispatch("input");
  assert.equal(x.grid.children.length,1);
  assert.equal(x.grid.children[0].dataset.key,"315901");
});

test("normal back does not trigger a scroll or rebuild cards",()=>{
  const x=setup();
  x.gallery.setItems([{key:"315901",title:"佩施塔",ready:true}]);
  const card=x.grid.children[0];
  x.gallery.open("315901",card);
  x.gallery.close();
  assert.equal(x.scrollCalls.length,0);
  assert.equal(x.grid.children[0],card);
});

test("previous-next skips unavailable skins without closing current viewer",()=>{
  const x=setup();
  x.gallery.setItems([
    {key:"1",title:"已安装甲",ready:true},
    {key:"2",title:"未安装乙",ready:false},
    {key:"3",title:"已安装丙",ready:true}
  ]);
  assert.equal(x.gallery.open("1"),true);
  assert.equal(x.gallery.navigate(1),true);
  assert.equal(x.gallery.selectedKey,"3");
  assert.equal(x.detail.hidden,false);
  assert.equal(x.gallery.navigate(1),true);
  assert.equal(x.gallery.selectedKey,"1");
  assert.equal(x.detail.hidden,false);
});
