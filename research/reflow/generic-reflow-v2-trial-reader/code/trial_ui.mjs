const bundle=JSON.parse(document.querySelector('#trial-data').textContent);
const pageSelect=document.querySelector('#page'),fontSelect=document.querySelector('#font'),main=document.querySelector('main'),status=document.querySelector('#status'),limitations=document.querySelector('#limitations'),dialog=document.querySelector('dialog');
let current=null,paths=null,images=null,generation=0,acceptedFont=20;
const resourceCache=createPageResourceCache(reader=>compileResources(reader,Path2D),async token=>{const image=new Image();image.src=token.data_uri;await image.decode();return image;});
const sourceDialog=createDialogController(dialog,document.querySelector('#dialog-title'),dialog.querySelector('.focus'),document.querySelector('#close-dialog'),fontSelect);
function showDialog(title,node){sourceDialog.open(title,node);}
function sourceView(block,selectedBoxes=[]){
 const {source,reader}=current,boxes=selectedBoxes.length?selectedBoxes:block.tokens.map(t=>t.source_pixel_box),NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');
 const union=[Math.max(0,Math.min(...boxes.map(b=>b[0]))-20),Math.max(0,Math.min(...boxes.map(b=>b[1]))-20),Math.min(source.width,Math.max(...boxes.map(b=>b[2]))+20),Math.min(source.height,Math.max(...boxes.map(b=>b[3]))+20)];
 const setBox=b=>svg.setAttribute('viewBox',`${b[0]} ${b[1]} ${b[2]-b[0]} ${b[3]-b[1]}`);setBox(union);svg.setAttribute('width','100%');svg.style.display='block';svg.style.maxHeight='70vh';svg.setAttribute('role','img');svg.setAttribute('aria-label','原页原生渲染及本段落对应位置');
 const image=document.createElementNS(NS,'image');image.setAttribute('href',source.png);image.setAttribute('width',source.width);image.setAttribute('height',source.height);svg.append(image);
 for(const b of boxes){const r=document.createElementNS(NS,'rect');for(const [key,value] of Object.entries({x:b[0],y:b[1],width:b[2]-b[0],height:b[3]-b[1],fill:'none',stroke:'#d44','stroke-width':1.2}))r.setAttribute(key,value);svg.append(r);}
 const wrap=document.createElement('div'),full=document.createElement('button');full.textContent='查看整页位置';full.onclick=()=>setBox([0,0,source.width,source.height]);wrap.append(full,svg);showDialog('回原页：红框对应当前段落的源位置',wrap);
}
async function focusImage(token){const version=generation,page=current,original=images.get(token.id);if(!original)return;const image=original.cloneNode();await image.decode();if(version!==generation||page!==current)return;image.style.width=(original.naturalWidth/(window.devicePixelRatio||1))+'px';image.style.maxWidth='none';image.alt='已有目标字号采样的局部图或公式';showDialog('局部原生采样；超出窗口可滚动，任意放大尚未支持',image);}
function render(){
 if(!current)return;const font=Number(fontSelect.value),dpr=window.devicePixelRatio||1,width=Math.min(390,document.documentElement.clientWidth),layouts=layoutBlocks(current.reader,font,width);
 if(layouts.reduce((n,b)=>n+Math.ceil(b.width*dpr)*Math.ceil(b.height*dpr),0)>DEFAULT_LAYOUT.maximumCanvasPixels){fontSelect.value=String(acceptedFont);status.textContent='所选字号与设备像素比超过当前画布预算，保留上一字号。';return;}
 document.getSelection()?.removeAllRanges();const fragment=document.createDocumentFragment();let under=0;
 for(const block of layouts){const section=document.createElement('section'),bar=document.createElement('div'),back=document.createElement('button'),canvas=document.createElement('canvas');bar.className='sourcebar';back.textContent='回原页';back.onclick=()=>sourceView(current.reader.blocks[block.index],selectionSourceBoxes(section,document.getSelection(),current.reader.source_capture_scale));bar.append(back);canvas.width=Math.ceil(block.width*dpr);canvas.height=Math.ceil(block.height*dpr);canvas.style.width=block.width+'px';canvas.style.height=block.height+'px';canvas.setAttribute('aria-label',current.text_map?'原生字形段落；实验文字选择':'原生字形段落；文字选择尚未支持');
 const report=drawBlock(canvas.getContext('2d'),block,current.reader,paths,images,dpr);under+=report.undersampled_local_images;canvas.onclick=event=>{const r=canvas.getBoundingClientRect(),x=(event.clientX-r.left)*block.width/r.width,y=(event.clientY-r.top)*block.height/r.height,p=block.placements.find(p=>p.token.kind==='native_image'&&x>=p.x&&x<=p.x+p.width&&y>=p.y&&y<=p.y+p.height);if(p)focusImage(p.token).catch(error=>{status.textContent='局部查看失败：'+error.message;});};const surface=document.createElement('div');surface.className='reading-surface';surface.append(canvas);if(current.text_map){const layer=mountSelectionLayer(document,current.reader,block,current.text_map.blocks[block.index]);layer.ondblclick=canvas.onclick;surface.append(layer);const select=document.createElement('button');select.textContent='选择本段';select.setAttribute('aria-label',`选择第 ${block.index+1} 段正文`);select.onclick=()=>selectParagraph(layer,status);bar.prepend(select);}for(const [index,p] of block.placements.filter(p=>p.token.kind==='native_image').entries()){const focus=document.createElement('button');focus.textContent=`查看局部 ${index+1}`;focus.setAttribute('aria-label',`查看第 ${block.index+1} 段的第 ${index+1} 个局部图或公式`);focus.onclick=()=>focusImage(p.token).catch(error=>{status.textContent='局部查看失败：'+error.message;});bar.append(focus);}section.append(bar,surface);fragment.append(section);}
 main.replaceChildren(fragment);acceptedFont=font;status.textContent=under?`${under} 个局部图像在当前设备像素比下采样不足；文字仍按原生矢量绘制。`:(current.text_map?'已载入实验文字选择层；跨越未确认文字或公式将拒绝复制。浏览器交互尚未验收。':'已载入预计算阅读流。正文按原生矢量绘制；文字选择尚未支持。');
}
async function changePage(){
 const version=++generation;sourceDialog.reset();document.getSelection()?.removeAllRanges();status.textContent='正在载入本地预计算资源…';
 try {
  const next=bundle.pages[Number(pageSelect.value)],resources=await resourceCache.load(next);
  if(version!==generation)return;
  const dpr=window.devicePixelRatio||1,layouts=layoutBlocks(next.reader,20,Math.min(390,document.documentElement.clientWidth));
  if(layouts.reduce((n,b)=>n+Math.ceil(b.width*dpr)*Math.ceil(b.height*dpr),0)>DEFAULT_LAYOUT.maximumCanvasPixels)throw Error('新页面超过设备画布预算，保留当前页面。');
  current=next;paths=resources.paths;images=resources.images;limitations.textContent=next.limitations;
  const original=document.querySelector('#original');original.href=next.source.pdf;original.download=next.original_filename;acceptedFont=20;fontSelect.value='20';render();window.scrollTo(0,0);
 } catch(error){
  if(version!==generation)return;
  const prior=bundle.pages.indexOf(current);if(prior>=0)pageSelect.value=String(prior);
  throw error;
 }
}
installCopyGuard(document,main,status);
pageSelect.onchange=()=>changePage().catch(error=>{status.textContent='载入失败：'+error.message;});fontSelect.onchange=render;let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(render,100);});if(bundle.pages.length)await changePage();else status.textContent='请导入本地预计算研究数据；常规 PDF 阅读不受影响。';
