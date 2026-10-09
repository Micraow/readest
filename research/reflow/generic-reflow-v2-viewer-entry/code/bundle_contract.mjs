/** Local precomputed research bundles only. No script, URL or PDF-parser import. */
export const BUNDLE_LIMITS=Object.freeze({bytes:16*1024*1024,pages:2,blocks:256,tokens:20000,events:50000,resources:5000,commands:2000000,imagePixels:32000000});
const finite=n=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<=1e7;
const index=(n,a)=>Number.isInteger(n)&&n>=0&&Object.hasOwn(a,n);
function need(ok,message){if(!ok)throw Error('Invalid research bundle: '+message);}
function list(value,max,name){need(Array.isArray(value)&&value.length<=max,name);return value;}
function png(uri){need(typeof uri==='string'&&/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(uri),'embedded PNG only');const header=atob(uri.slice(uri.indexOf(',')+1,uri.indexOf(',')+1+44));need(header.slice(0,8)==='\x89PNG\r\n\x1a\n'&&header.slice(12,16)==='IHDR'&&header.length>=24,'PNG header');const n=i=>((header.charCodeAt(i)*16777216)+(header.charCodeAt(i+1)<<16)+(header.charCodeAt(i+2)<<8)+header.charCodeAt(i+3));const width=n(16),height=n(20);need(width>0&&height>0&&width*height<=BUNDLE_LIMITS.imagePixels,'PNG pixel budget');return {width,height};}
function validateInputTree(value){
 const stack=[[value,0]];let nodes=0,stringBytes=0;
 while(stack.length){const [item,depth]=stack.pop();need(++nodes<=1000000&&depth<=32,'tree budget');
  if(typeof item==='number'){need(finite(item),'nonfinite or excessive number');continue;}
  if(typeof item==='string'){stringBytes+=item.length;need(stringBytes<=BUNDLE_LIMITS.bytes,'string budget');continue;}
  if(item===null||typeof item==='boolean')continue;
  need(item&&typeof item==='object'&&(Array.isArray(item)||Object.getPrototypeOf(item)===Object.prototype||Object.getPrototypeOf(item)===null),'JSON value');
  for(const key of Object.keys(item)){need(!['__proto__','prototype','constructor'].includes(key),'forbidden prototype key');stack.push([item[key],depth+1]);}
 }
}
export function validateResearchBundle(bundle){
 validateInputTree(bundle);
 need(bundle?.schema==='readest-reflow-research-v1','schema');const pages=list(bundle.pages,BUNDLE_LIMITS.pages,'pages');need(pages.length>0,'empty pages');
 for(const page of pages){
  need(typeof page.label==='string'&&page.label.length<=200&&typeof page.limitations==='string'&&page.limitations.length<=2000,'page labels');
  need(typeof page.original_filename==='string'&&/^[^/\\]{1,200}\.pdf$/i.test(page.original_filename),'PDF filename');
  const source=page.source;need(source&&finite(source.width)&&finite(source.height)&&source.width<=16384&&source.height<=16384,'source dimensions');const dims=png(source.png);need(dims.width===source.width&&dims.height===source.height,'source PNG dimensions');need(typeof source.pdf==='string'&&/^data:application\/pdf;base64,JVBER[A-Za-z0-9+/]+=*$/.test(source.pdf),'embedded PDF only');
  const r=page.reader;need(r&&r.schema===1&&finite(r.body_font_pdf)&&r.body_font_pdf>0&&r.body_font_pdf<=1000&&finite(r.source_capture_scale)&&r.source_capture_scale>0&&r.source_capture_scale<=16,'reader scale');
  const resources=list(r.resources,BUNDLE_LIMITS.resources,'resources'),events=r.events,states=list(r.states,1000,'states'),programs=list(r.affine_programs,50000,'affine programs');let commands=0,tokens=0,characters=0;need(events&&typeof events==='object'&&!Array.isArray(events)&&Object.keys(events).length<=BUNDLE_LIMITS.events&&Object.keys(events).every(k=>/^(0|[1-9][0-9]*)$/.test(k)),'events');
  for(const path of resources){list(path,BUNDLE_LIMITS.commands,'glyph path');commands+=path.length;need(commands<=BUNDLE_LIMITS.commands,'total command budget');for(let i=0;i<path.length;){const op=path[i++],count=({0:2,1:2,2:6,3:4,4:0})[op];need(count!==undefined&&i+count<=path.length,'path opcode/length');need(path.slice(i,i+count).every(finite),'path values');i+=count;}}
  for(const state of states)need(state&&typeof state.fillStyle==='string'&&/^(#[a-f0-9]{3,8}|rgba?\([\d., %]+\))$/i.test(state.fillStyle)&&finite(state.alpha)&&state.alpha>=0&&state.alpha<=1&&state.blend==='source-over'&&state.filter==='none','paint state');
  for(const program of programs)for(const op of list(program,100,'program length')){const n=({translate:2,scale:2,rotate:1,transform:6})[op.name];need(n!==undefined&&Array.isArray(op.args)&&op.args.length===n&&op.args.every(finite),'affine operation');}
  for(const e of Object.values(events))need(e&&index(e.resource,resources)&&index(e.state,states)&&index(e.program,programs)&&[e.x,e.y,e.fontSize].every(finite)&&e.fontSize>0,'event');
  for(const block of list(r.blocks,BUNDLE_LIMITS.blocks,'blocks')){
   need(['paragraph','object','formula','auxiliary'].includes(block.kind),'block kind');if(block.kind==='formula')need(Array.isArray(block.tokens)&&block.tokens.length===2&&block.tokens[0]?.formula_role==='core'&&block.tokens[1]?.formula_role==='label'&&finite(block.label_anchor_em),'formula hierarchy');
   for(const t of list(block.tokens,BUNDLE_LIMITS.tokens,'tokens')){tokens++;need(tokens<=BUNDLE_LIMITS.tokens,'total token budget');need(t&&typeof t.id==='string'&&t.id.length<=200&&[t.width_em,t.height_em,t.vertical_em,t.gap_em].every(finite)&&t.width_em>0&&t.width_em<=256&&t.height_em>0&&t.height_em<=256&&Math.abs(t.vertical_em)<=256&&t.gap_em>=0&&t.gap_em<=32,'token geometry');const box=t.source_pixel_box;need(Array.isArray(box)&&box.length===4&&box.every(finite)&&box[0]>=0&&box[1]>=0&&box[2]>box[0]&&box[3]>box[1]&&box[2]<=source.width&&box[3]<=source.height,'source box');
    if(t.kind==='vector')need(list(t.native_event_ids,10000,'event IDs').every(i=>index(i,events)),'event ID range');
    else {need(t.kind==='native_image'&&finite(t.asset_scale)&&t.asset_scale>0&&Array.isArray(t.asset_pixel_box)&&t.asset_pixel_box.length===4&&t.asset_pixel_box.every(finite),'native image');png(t.data_uri);}
   }
  }
  if(page.text_map){need(Array.isArray(page.text_map.blocks)&&page.text_map.blocks.length===r.blocks.length,'map blocks');for(let i=0;i<r.blocks.length;i++){const a=r.blocks[i].tokens,b=page.text_map.blocks[i].tokens;need(Array.isArray(b)&&a.length===b.length&&b.every((m,j)=>m.id===a[j].id&&typeof m.eligible==='boolean'&&Array.isArray(m.characters)),'map identities');for(const m of b){characters+=m.characters.length;need(characters<=50000&&m.characters.length<=512,'map character budget');if(m.eligible){need(m.characters.length>0&&typeof m.text==='string'&&m.text===m.characters.map(c=>c.text).join(''),'map text');for(const c of m.characters)need(typeof c.text==='string'&&[...c.text].length===1&&index(c.native_event,events)&&Array.isArray(c.box_pdf)&&c.box_pdf.length===4&&c.box_pdf.every(finite)&&c.box_pdf[2]>c.box_pdf[0]&&c.box_pdf[3]>c.box_pdf[1],'map character');}}}}
 }
 return bundle;
}
