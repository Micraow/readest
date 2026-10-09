/** Experimental semantic overlay. Native paint remains the only visible text. */
export function selectionGeometry(reader, layout, mapping) {
 if (!mapping || mapping.tokens.length !== layout.placements.length) throw Error('selection token count mismatch');
 const scale = layout.placements.length ? reader.source_capture_scale : 1;
 return layout.placements.map((p, i) => {
  const m = mapping.tokens[i], t = p.token;
  if (m.id !== t.id) throw Error('selection token identity mismatch');
  const ratio = p.fontScale / reader.body_font_pdf;
  const characters = m.eligible ? m.characters.map(c => {
   const b=c.box_pdf;
   if (!Array.isArray(b)||b.length!==4||!b.every(Number.isFinite)||b[2]<=b[0]||b[3]<=b[1]||typeof c.text!=='string'||[...c.text].length!==1) throw Error('invalid selection glyph');
   return {...c,x:p.x+(b[0]-t.source_pixel_box[0]/scale)*ratio,y:p.y+(b[1]-t.source_pixel_box[1]/scale)*ratio,width:(b[2]-b[0])*ratio,height:(b[3]-b[1])*ratio};
  }) : [];
  if (m.eligible && (!characters.length || characters.map(c=>c.text).join('')!==m.text)) throw Error('selection text mismatch');
  return {id:t.id,source_box_pdf:t.source_pixel_box.map(v=>v/scale),eligible:m.eligible===true,reasons:m.reasons,characters,x:p.x,y:p.y,width:p.width,height:p.height,separator:i+1<layout.placements.length&&t.gap_em>0?' ':''};
 });
}
export function copyPieces(pieces) {
 if (!pieces.length) return {ok:false,reason:'未选中可复制的正文。'};
 if (pieces.some(p=>p.unresolved)) return {ok:false,reason:'选区包含未确认文字、图片或公式；未复制，请回原页核对。'};
 const text=pieces.map(p=>p.text).join('');
 if([...text].some(c=>{const n=c.codePointAt(0);return n>=0xD800&&n<=0xDFFF;}))return {ok:false,reason:'选区截断了 Unicode 字符；请重新选择。'};
 return {ok:true,text};
}
export function createSelectionTextMeasure(doc) {
 let context;try{context=doc.createElement('canvas').getContext('2d');}catch{return ()=>null;}
 const cache=new Map();return (text,height)=>{
  if(!context)return null;const key=height+':'+text;if(cache.has(key))return cache.get(key);
  context.font=height+'px monospace';const width=context.measureText(text).width,result=Number.isFinite(width)&&width>0?width:null;
  if(cache.size>=4096)cache.clear();cache.set(key,result);return result;
 };
}
export function mountSelectionLayer(doc,reader,layout,mapping,measure) {
 const layer=doc.createElement('div');layer.className='selection-layer';layer.style.width=layout.width+'px';layer.style.height=layout.height+'px';
 for (const token of selectionGeometry(reader,layout,mapping)) {
  const chars=token.eligible?token.characters:[{text:'\uFFFC',x:token.x,y:token.y,width:token.width,height:token.height}];
  for (const c of chars) {
   const span=doc.createElement('span');span.dataset.selectionPiece='character';span.dataset.token=token.id;
   if (!token.eligible) {span.dataset.unresolved='true';span.title='此处文字或公式未确认，跨越此处的复制会被拒绝。';}
   if(c.source_glyph)span.dataset.sourceGlyph=c.source_glyph;
   const advance=token.eligible&&typeof measure==='function'?measure(c.text,c.height):null;
   if(token.eligible&&!(Number.isFinite(advance)&&advance>0)){span.dataset.unresolved='true';span.title='无法确定该字符的选择范围；复制会被拒绝。';}
   span.dataset.sourceBox=JSON.stringify(c.box_pdf||token.source_box_pdf);span.textContent=c.text;Object.assign(span.style,{left:c.x+'px',top:c.y+'px',width:(advance||c.width)+'px',height:c.height+'px',fontFamily:'monospace',transform:advance?`scaleX(${c.width/advance})`:'none',transformOrigin:'top left',fontSize:c.height+'px',lineHeight:c.height+'px'});layer.append(span);
  }
  if(token.separator){const space=doc.createElement('span');space.dataset.selectionPiece='separator';space.textContent=' ';Object.assign(space.style,{left:(token.x+token.width)+'px',top:token.y+'px',width:'1px',height:token.height+'px'});layer.append(space);}
 }
 const end=doc.createElement('span');end.dataset.selectionPiece='paragraph';end.textContent='\n';Object.assign(end.style,{left:'0px',top:(layout.height-1)+'px',width:'1px',height:'1px'});layer.append(end);
 return layer;
}
export function readSelection(root,selection) {
 if(!selection||selection.rangeCount!==1||selection.isCollapsed)return copyPieces([]);
 const range=selection.getRangeAt(0);
 if(!root.contains(range.startContainer)||!root.contains(range.endContainer))return {ok:false,reason:'请只选择阅读正文后复制。'};
 const pieces=[];
 for(const span of root.querySelectorAll('[data-selection-piece]')) {
  if(!range.intersectsNode(span))continue;
  const text=span.firstChild;
  let start=range.startContainer===text?range.startOffset:0,end=range.endContainer===text?range.endOffset:text.length;
  // Exact element-boundary selections can intersect a parent without selecting its text.
  if(range.comparePoint(text,0)===1||range.comparePoint(text,text.length)===-1)continue;
  if(start>=end)continue;
  pieces.push({text:text.data.slice(start,end),unresolved:span.dataset.unresolved==='true'});
 }
 return copyPieces(pieces);
}
export function installCopyGuard(doc,root,status) {
 const handler=event=>{
  const selection=doc.getSelection();if(!selection||!selection.rangeCount)return;
  if(!Array.from({length:selection.rangeCount},(_,i)=>selection.getRangeAt(i)).some(r=>r.intersectsNode(root)))return;
  event.preventDefault();const result=readSelection(root,selection);
  if(!result.ok){status.textContent=result.reason;return;}
  if(!event.clipboardData){status.textContent='当前浏览器未提供复制接口；未复制。';return;}
  event.clipboardData.setData('text/plain',result.text);status.textContent='已复制选中正文；Unicode 映射仍需按原页核对。';
 };
 doc.addEventListener('copy',handler);return ()=>doc.removeEventListener('copy',handler);
}

export function selectionSourceBoxes(root,selection,scale) {
 if(!selection||selection.rangeCount!==1||selection.isCollapsed)return [];
 const range=selection.getRangeAt(0);
 if(!root.contains(range.startContainer)||!root.contains(range.endContainer))return [];
 return [...root.querySelectorAll('[data-source-box]')].filter(span=>{
  if(!range.intersectsNode(span))return false;const t=span.firstChild;
  const start=range.startContainer===t?range.startOffset:0,end=range.endContainer===t?range.endOffset:t.length;
  return start<end&&range.comparePoint(t,0)!==1&&range.comparePoint(t,t.length)!==-1;
 }).map(span=>JSON.parse(span.dataset.sourceBox).map(v=>v*scale));
}
