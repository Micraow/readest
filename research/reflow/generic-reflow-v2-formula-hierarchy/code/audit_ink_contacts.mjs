/** Requested-pixel-grid diagnostic. Does not modify source groups or reader ink. */
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {compileResources,layoutBlocks,drawBlock} from './reader_engine.mjs';import {inkContact} from './ink_contact.mjs';
const [runtime,input,geometryInput,out]=process.argv.slice(2),require=createRequire(path.resolve(runtime,'package.json')),canvas=require('@napi-rs/canvas'),data=JSON.parse(fs.readFileSync(input)),geometry=JSON.parse(fs.readFileSync(geometryInput)),paths=compileResources(data,canvas.Path2D),images=new Map(),results=[];
for(const b of data.blocks)for(const t of b.tokens)if(t.kind==='native_image'&&!images.has(t.id))images.set(t.id,await canvas.loadImage(t.data_uri));
const pairs=new Map();for(const r of geometry.output_geometry)for(const p of r.contour_or_asset_box_contacts)pairs.set([p.a,p.b].sort().join('\n'),[p.a,p.b]);
for(const font of [20,24,28])for(const width of [320,390,800])for(const dpr of [1,2]){
 const blocks=layoutBlocks(data,font,width);
 for(const [a,b] of pairs.values()){
  const block=blocks.find(x=>x.placements.some(p=>p.token.id===a)&&x.placements.some(p=>p.token.id===b));if(!block)throw Error('contact pair not in a single output block');
  const w=Math.ceil(block.width*dpr),h=Math.ceil(block.height*dpr);if(w*h>32000000)throw Error('ink-contact canvas budget');
  const render=id=>{const c=canvas.createCanvas(w,h),ctx=c.getContext('2d');let backgrounds=0;ctx.fillRect=()=>{backgrounds++;};drawBlock(ctx,{...block,placements:block.placements.filter(p=>p.token.id===id)},data,paths,images,dpr);if(backgrounds!==1)throw Error('unexpected painter background contract');return ctx.getImageData(0,0,w,h).data;};
  results.push({font_css:font,viewport_css:width,dpr,block:block.index,...inkContact(render(a),render(b),w,h)});
 }
}
const report={method:'unchanged native token painter on transparent canvases at actual requested placements; only its one white page-background rectangle omitted',candidate_pairs:pairs.size,cases:results,all_sampled_contacts_disjoint:results.length>0&&results.every(x=>x.disjoint_nonzero_alpha),automatic_merges:0,browser_verified:false,arbitrary_scale_proven:false,source_ownership_gate_replaced:false};fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({...report,cases:results.length}));
