/** Shared browser/native-canvas layout implementation; selection is not certified. */
/** @typedef {{paddingCssPx:number,lineHeightEm:number,minimumAscentEm:number,minimumDescentEm:number,paragraphGapEm:number,maximumCanvasPixels:number}} LayoutConfig */
/** @type {Readonly<LayoutConfig>} */
export const DEFAULT_LAYOUT=Object.freeze({paddingCssPx:12,lineHeightEm:1.5,minimumAscentEm:.8,minimumDescentEm:.2,paragraphGapEm:.8,maximumCanvasPixels:32000000});
export function glyphPath(commands,Path2D){const p=new Path2D();for(let i=0;i<commands.length;){switch(commands[i++]){case 0:p.moveTo(commands[i++],commands[i++]);break;case 1:p.lineTo(commands[i++],commands[i++]);break;case 2:p.bezierCurveTo(...commands.slice(i,i+=6));break;case 3:p.quadraticCurveTo(...commands.slice(i,i+=4));break;case 4:p.closePath();break;default:throw Error('unsupported native glyph path command');}}return p;}
export function compileResources(data,Path2D){return data.resources.map(c=>glyphPath(c,Path2D));}
/** Preserve verified source line boundaries without deleting printed marks.
 * Bounded raggedness minimization avoids stranded prefixes after a forced break.
 * Ordinary unmarked readers keep their exact previous greedy layout.
 */
export function retainedSourceRows(tokens,font,usable,physicalWidth,maximumPairs=100000){
 let pairs=0;
 const balance=(chunk,hardEnd)=>{
  const n=chunk.length,cost=Array(n+1).fill(Infinity),next=Array(n);cost[n]=0;
  for(let i=n-1;i>=0;i--){let advance=0,extent=0;
   for(let j=i;j<n;j++){
    if(++pairs>maximumPairs)throw Error('native source-break layout work budget exceeded');
    const t=chunk[j],w=t.width_em*font;extent=Math.max(extent,advance+w);
    if(extent>usable+1e-8){
     // Preserve the old layout's bounded singleton behavior: a long native
     // word may use the right padding, but may never leave the actual canvas.
     if(j===i&&extent<=physicalWidth+1e-8&&!(j<n-1&&t.gap_em<0)){cost[i]=cost[i+1];next[i]=i+1;}
     break;
    }
    if(!(j<n-1&&t.gap_em<0)){
     const penalty=j===n-1&&!hardEnd?0:(usable-extent)**2,c=penalty+cost[j+1];
     if(c<cost[i]){cost[i]=c;next[i]=j+1;}
    }
    advance+=w+t.gap_em*font;
   }
  }
  if(!Number.isFinite(cost[0]))throw Error('native source-break row cannot fit safely');
  const rows=[];for(let i=0;i<n;i=next[i])rows.push(chunk.slice(i,next[i]));return rows;
 };
 const rows=[];let chunk=[];
 for(const token of tokens){chunk.push(token);if(token.retained_source_break_after===true){rows.push(...balance(chunk,true));chunk=[];}}
 if(chunk.length)rows.push(...balance(chunk,false));return rows;
}
export function layoutBlocks(data,fontCss,widthCss,cfg=DEFAULT_LAYOUT){if(!(fontCss>0&&widthCss>2*cfg.paddingCssPx))throw Error('invalid reading size');const usable=widthCss-2*cfg.paddingCssPx;return data.blocks.map((block,index)=>{let y=cfg.paddingCssPx,placed=[];if(block.kind==='object'){for(const token of block.tokens){const f=Math.min(1,usable/(token.width_em*fontCss));placed.push({token,x:cfg.paddingCssPx+(usable-token.width_em*fontCss*f)/2,y,width:token.width_em*fontCss*f,height:token.height_em*fontCss*f,fontScale:fontCss*f});y+=token.height_em*fontCss*f;}}else{let line=[],used=0;const flush=()=>{if(!line.length)return;const ascent=Math.max(cfg.minimumAscentEm*fontCss,...line.map(x=>(x.token.height_em+x.token.vertical_em)*fontCss)),descent=Math.max(cfg.minimumDescentEm*fontCss,...line.map(x=>-x.token.vertical_em*fontCss)),height=Math.max(cfg.lineHeightEm*fontCss,ascent+descent),baseline=y+(height-ascent-descent)/2+ascent;for(const x of line)placed.push({token:x.token,x:cfg.paddingCssPx+x.x,y:baseline-(x.token.height_em+x.token.vertical_em)*fontCss,width:x.token.width_em*fontCss,height:x.token.height_em*fontCss,fontScale:fontCss});y+=height;line=[];used=0;};const retained=data.retained_source_break_policy==='native-retained-line-v1'&&block.tokens.some(t=>t.retained_source_break_after===true)?new Set(retainedSourceRows(block.tokens,fontCss,usable,widthCss-cfg.paddingCssPx).map(row=>row.at(-1))):null;for(const token of block.tokens){const w=token.width_em*fontCss;if(line.length&&used+w>usable)flush();line.push({token,x:used});used+=w+token.gap_em*fontCss;if(retained?.has(token))flush();}flush();}return {index,kind:block.kind,width:widthCss,height:Math.ceil(y+cfg.paragraphGapEm*fontCss),placements:placed,fontCss,source_token_count:block.tokens.length};});}
export function drawBlock(ctx,layout,data,paths,images,dpr,cfg=DEFAULT_LAYOUT){if(layout.width*layout.height*dpr*dpr>cfg.maximumCanvasPixels)throw Error('block canvas pixel budget exceeded');ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='white';ctx.fillRect(0,0,ctx.canvas.width,ctx.canvas.height);ctx.restore();let paints=0,imagesDrawn=0,underSampled=0;for(const p of layout.placements){const t=p.token;const scale=p.fontScale/data.body_font_pdf/data.source_capture_scale*dpr;if(t.kind==='vector'){for(const id of t.native_event_ids){const e=data.events[id],state=data.states[e.state];ctx.save();ctx.setTransform(scale,0,0,scale,p.x*dpr-scale*t.source_pixel_box[0],p.y*dpr-scale*t.source_pixel_box[1]);for(const op of data.affine_programs[e.program]){if(!['translate','scale','rotate','transform'].includes(op.name))throw Error('unsupported affine program');ctx[op.name](...op.args);}ctx.fillStyle=state.fillStyle;ctx.globalAlpha=state.alpha;ctx.globalCompositeOperation=state.blend;ctx.filter=state.filter;ctx.translate(e.x,e.y);ctx.scale(e.fontSize,-e.fontSize);ctx.fill(paths[e.resource]);ctx.restore();paints++;}}else{const image=images.get(t.id);if(!image)throw Error('local native image unavailable');const cssPerPdf=p.fontScale/data.body_font_pdf,dx=(t.asset_pixel_box[0]/t.asset_scale-t.source_pixel_box[0]/data.source_capture_scale)*cssPerPdf,dy=(t.asset_pixel_box[1]/t.asset_scale-t.source_pixel_box[1]/data.source_capture_scale)*cssPerPdf;ctx.drawImage(image,(p.x+dx)*dpr,(p.y+dy)*dpr,image.width/t.asset_scale*cssPerPdf*dpr,image.height/t.asset_scale*cssPerPdf*dpr);imagesDrawn++;if(t.asset_scale+1e-9<cssPerPdf*dpr)underSampled++;}}return {glyph_paints:paints,local_image_paints:imagesDrawn,undersampled_local_images:underSampled};}
