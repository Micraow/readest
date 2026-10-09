import assert from 'node:assert/strict';import {layoutBlocks} from './reader_engine.mjs';
function data(w){return {blocks:[{kind:'formula',label_anchor_em:1,tokens:[{id:'core',formula_role:'core',width_em:w,height_em:3,vertical_em:0},{id:'label',formula_role:'label',width_em:1.6,height_em:1,vertical_em:0}]}]};}
let count=0;
for(const font of [20,28])for(const width of [320,390,800])for(const coreWidth of [5,15,30]){
 const l=layoutBlocks(data(coreWidth),font,width)[0],[a,b]=l.placements;assert.equal(l.placements.length,2);assert(a.fontScale>0);assert(Math.abs(a.width/a.token.width_em-a.height/a.token.height_em)<1e-12);assert.equal(b.fontScale,font);for(const p of [a,b]){assert(p.x>=12-1e-9&&p.x+p.width<=width-12+1e-9);assert(p.y>=12&&p.y+p.height<=l.height);}assert(Math.min(a.x+a.width,b.x+b.width)<=Math.max(a.x,b.x)||Math.min(a.y+a.height,b.y+b.height)<=Math.max(a.y,b.y));count++;
}
console.log(JSON.stringify({layout_cases:count,positive_uniform_scale:true,unclipped:true,no_child_overlap:true}));
