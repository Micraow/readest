/** Six actual native-Canvas render grids. No browser or whole-page claim. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
import {compileResources,layoutBlocks,drawBlock} from '../../generic-reflow-v2-formula-hierarchy/code/reader_engine.mjs';
const [runtime,input,out]=process.argv.slice(2),require=createRequire(path.resolve(runtime,'package.json')),canvas=require('@napi-rs/canvas'),data=JSON.parse(fs.readFileSync(input));fs.mkdirSync(out,{recursive:false});
const paths=compileResources(data,canvas.Path2D),images=new Map();for(const b of data.blocks)for(const t of b.tokens)if(t.kind==='native_image')images.set(t.id,await canvas.loadImage(t.data_uri));
const vectorBounds=new Map(),probe=canvas.createCanvas(1,1).getContext('2d');
for(const b of data.blocks)for(const t of b.tokens)if(t.kind==='vector'){
 let bounds=[Infinity,Infinity,-Infinity,-Infinity];
 for(const id of t.native_event_ids){const e=data.events[id];probe.setTransform(1,0,0,1,0,0);for(const op of data.affine_programs[e.program])probe[op.name](...op.args);probe.translate(e.x,e.y);probe.scale(e.fontSize,-e.fontSize);const p=new canvas.Path2D();p.addPath(paths[e.resource],probe.getTransform());const q=p.computeTightBounds();bounds=[Math.min(bounds[0],q[0]),Math.min(bounds[1],q[1]),Math.max(bounds[2],q[2]),Math.max(bounds[3],q[3])];}
 vectorBounds.set(t.id,bounds);
}
const results=[];const expectedVectorPaints=Object.keys(data.events).length;
for(const font of [20,24,28])for(const width of [320,390]){
 const layouts=layoutBlocks(data,font,width),folder=path.join(out,`${font}-${width}`);fs.mkdirSync(folder);let glyphs=0,undersampled=0,imagePaints=0;const logicalBounds=[],actualAssetBounds=[],actualVectorBounds=[];
 for(const b of layouts){const c=canvas.createCanvas(Math.ceil(b.width*2),Math.ceil(b.height*2)),stats=drawBlock(c.getContext('2d'),b,data,paths,images,2);glyphs+=stats.glyph_paints;imagePaints+=stats.local_image_paints;undersampled+=stats.undersampled_local_images;
  for(const p of b.placements){const box=[p.x,p.y,p.x+p.width,p.y+p.height];if(box[0]<0||box[1]<0||box[2]>b.width+1e-9||box[3]>b.height+1e-9)logicalBounds.push({block:b.index,token:p.token.id});
   if(p.token.kind==='vector'){const t=p.token,a=vectorBounds.get(t.id),s=p.fontScale/data.body_font_pdf/data.source_capture_scale;const actual=[p.x+(a[0]-t.source_pixel_box[0])*s,p.y+(a[1]-t.source_pixel_box[1])*s,p.x+(a[2]-t.source_pixel_box[0])*s,p.y+(a[3]-t.source_pixel_box[1])*s];if(actual[0]<0||actual[1]<0||actual[2]>b.width+1e-9||actual[3]>b.height+1e-9)actualVectorBounds.push({block:b.index,token:t.id});}
   if(p.token.kind==='native_image'){const t=p.token,s=p.fontScale/data.body_font_pdf,q=data.source_capture_scale,a=t.asset_pixel_box;const actual=[p.x+(a[0]/t.asset_scale-t.source_pixel_box[0]/q)*s,p.y+(a[1]/t.asset_scale-t.source_pixel_box[1]/q)*s,p.x+(a[2]/t.asset_scale-t.source_pixel_box[0]/q)*s,p.y+(a[3]/t.asset_scale-t.source_pixel_box[1]/q)*s];if(actual[0]<0||actual[1]<0||actual[2]>b.width+1e-9||actual[3]>b.height+1e-9)actualAssetBounds.push({block:b.index,token:t.id});}}
  fs.writeFileSync(path.join(folder,`block-${String(b.index).padStart(2,'0')}.png`),c.toBuffer('image/png'));
 }
 assert.equal(glyphs,expectedVectorPaints);assert.equal(undersampled,0);assert.equal(logicalBounds.length,0);assert.equal(actualAssetBounds.length,0);assert.equal(actualVectorBounds.length,0);
 results.push({font,width,dpr:2,blocks:layouts.length,vector_paints:glyphs,native_images:imagePaints,logical_placements_outside_canvas:0,native_asset_boxes_outside_canvas:0,native_vector_contours_outside_canvas:0,undersampled_images:0});
}
const result={scope:'actual native Node Canvas renders; not browser evidence',cases:results,browser_verified:false,reading_acceptance:false,mixed_engine_pixel_ownership_proven:false};fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
