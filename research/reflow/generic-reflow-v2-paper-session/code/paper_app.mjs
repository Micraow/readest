import {PaperSession,replaceOwnedView} from './paper_session.mjs';
import {validateSession} from './session_contract.mjs';
const $=id=>document.getElementById(id),view=$('view'),events=[];
let session,manifest,locating=false,narrow=false,last={documentId:null,pageIndex:0},sourceAnchor=null,tokenAnchor=null;
let activeResources=0,createdResources=0,releasedResources=0;
function record(type,data={}){events.push({type,...data});if(events.length>50)events.shift();$('diagnostics').textContent=JSON.stringify({activeResources,createdResources,releasedResources,current:session?.current,events},null,2);}
function clearSelection(){window.getSelection()?.removeAllRanges();try{view.querySelector('iframe')?.contentWindow.getSelection()?.removeAllRanges();}catch{}}
async function checkedAsset(url,sha,signal){
 const response=await fetch(url,{signal,cache:'no-store'});if(!response.ok)throw Error('资源载入失败');
 const buffer=await response.arrayBuffer();if(buffer.byteLength>32*1024*1024)throw Error('资源超出预算');
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),x=>x.toString(16).padStart(2,'0')).join('');
 if(digest!==sha)throw Error('原始资源校验不一致');if(signal.aborted)throw new DOMException('Aborted','AbortError');return buffer;
}
function resource(element,cleanup){let disposed=false;createdResources++;activeResources++;return {element,dispose(){if(disposed)return;disposed=true;cleanup();element.remove();activeResources--;releasedResources++;record('disposed');}};}
function waitAbort(promise,signal){return new Promise((resolve,reject)=>{const abort=()=>reject(new DOMException('Aborted','AbortError'));signal.addEventListener('abort',abort,{once:true});promise.then(resolve,reject).finally(()=>signal.removeEventListener('abort',abort));});}
async function load(doc,page,state,signal){
 if(state.mode==='source'){
  const bytes=await checkedAsset(page.source.url,page.source.sha256,signal),url=URL.createObjectURL(new Blob([bytes],{type:'image/png'})),sheet=document.createElement('div'),img=new Image();sheet.className='source-sheet';img.alt=`${doc.title} 原 PDF 第 ${page.index+1} 页`;img.src=url;sheet.append(img);let result;
  try{await waitAbort(img.decode(),signal);if(img.naturalWidth!==page.source.width||img.naturalHeight!==page.source.height)throw Error('原页尺寸不一致');sheet.style.width=Number($('zoom').value)*100+'%';result=resource(sheet,()=>{img.removeAttribute('src');URL.revokeObjectURL(url);});
   if(state.anchor){const b=state.anchor,mark=document.createElement('span');mark.className='source-mark';Object.assign(mark.style,{left:100*b[0]/page.source.pdfWidth+'%',top:100*b[1]/page.source.pdfHeight+'%',width:100*(b[2]-b[0])/page.source.pdfWidth+'%',height:100*(b[3]-b[1])/page.source.pdfHeight+'%'});sheet.append(mark);}return result;
  }catch(e){if(result)result.dispose();else{img.removeAttribute('src');URL.revokeObjectURL(url);}throw e;}
 }
 // The server checks this exact pinned HTML and enumerates its local assets.
 await checkedAsset(page.reflow.url,page.reflow.sha256,signal);
 const frame=document.createElement('iframe');frame.title=`${doc.title} 第 ${page.index+1} 页实验重排`;frame.setAttribute('sandbox','allow-scripts allow-same-origin');
 frame.style.visibility='hidden';frame.style.position='absolute';frame.style.inset='0';
 const loaded=new Promise((resolve,reject)=>{frame.onload=()=>resolve();frame.onerror=()=>reject(Error('重排页面载入失败'));});
 frame.src=page.reflow.url;view.append(frame);
 let click;
 const result=resource(frame,()=>{if(click)frame.contentDocument?.removeEventListener('click',click,true);frame.onload=frame.onerror=null;frame.src='about:blank';});
 try{
  await waitAbort(loaded,signal);
  frame.onload=frame.onerror=null;const fd=frame.contentDocument;
  if(!fd?.querySelector('main'))throw Error('重排入口无正文');
  fd.body.style.fontSize=$('font').value+'px';frame.contentWindow.dispatchEvent(new Event('resize'));
  click=event=>{if(!locating)return;const token=event.target.closest('[data-unit]');if(!token)return;const mapping=JSON.parse(fd.querySelector('#selection-data').textContent);const item=mapping.tokens.find(t=>t.id===token.dataset.unit);if(!item)return;
   event.preventDefault();event.stopPropagation();sourceAnchor=item.source_box_pdf;tokenAnchor=token.dataset.unit;record('source-return',{pageIndex:page.index,token:tokenAnchor,box:sourceAnchor});void navigate(doc.id,page.index,'source',sourceAnchor);
  };fd.addEventListener('click',click,true);return result;
 }catch(e){result.dispose();throw e;}
}
function commit(candidate,state,doc,page){
 clearSelection();replaceOwnedView(view,candidate.element);candidate.element.style.visibility='';candidate.element.style.position='';candidate.element.style.inset='';
 $('document').value=doc.id;fillPages(doc);$('page').value=String(page.index);last={documentId:doc.id,pageIndex:page.index};
 $('page-title').textContent=`${doc.title} · 原 PDF 第 ${page.index+1} / ${doc.pages.length} 页`;
 $('limitation').textContent=state.mode==='reflow'?page.reflow.limitation:page.limitation;
 $('original').href=doc.pdf.url;$('original').download=doc.id+'-original.pdf';
 $('previous').disabled=page.index===0;$('next').disabled=page.index===doc.pages.length-1;$('reflow').disabled=!page.reflow;
 $('font').disabled=state.mode!=='reflow';$('zoom').disabled=state.mode!=='source';$('locate').disabled=state.mode!=='reflow';
 $('metadata').textContent=`模式：${state.mode==='source'?'原页保真，未重排':'局部验证的实验重排，非整页验收'}。源页索引 ${page.index}。PDF ${doc.pdf.sha256.slice(0,12)}…`;
 view.scrollTop=0;view.scrollLeft=0;
 requestAnimationFrame(()=>{candidate.element.querySelector?.('.source-mark')?.scrollIntoView({block:'center',inline:'center'});if(state.mode==='reflow'&&tokenAnchor)candidate.element.contentDocument?.querySelector(`[data-unit="${CSS.escape(tokenAnchor)}"]`)?.scrollIntoView({block:'center'});});
 record('committed',{documentId:doc.id,pageIndex:page.index,mode:state.mode,sourceVerified:true});
}
function status(type,state,error){$('status').textContent=type==='ready'?`已载入第 ${state.pageIndex+1} 页` :type==='loading'?`正在载入第 ${state.pageIndex+1} 页…`:type==='closed'?'会话已关闭，页面资源已释放。':`载入失败，保留上一页：${error.message}`;record(type);}
function fillPages(doc){if($('page').dataset.doc===doc.id)return;$('page').dataset.doc=doc.id;$('page').replaceChildren(...doc.pages.map(p=>{const o=document.createElement('option');o.value=String(p.index);o.textContent=`第 ${p.index+1} 页 · ${p.reflow?'可选实验重排':'原页'}`;return o;}));}
async function navigate(id,index,mode='source',anchor=null){try{return await session.open(id,index,mode,anchor);}catch(e){record('navigation-error',{message:e.message});return false;}}
function activeDoc(){return manifest.documents.find(d=>d.id===$('document').value);}
$('document').onchange=()=>{const doc=activeDoc();sourceAnchor=tokenAnchor=null;void navigate(doc.id,session.positions.get(doc.id)||0);};
$('page').onchange=()=>{sourceAnchor=tokenAnchor=null;void navigate(activeDoc().id,Number($('page').value));};
$('previous').onclick=()=>{sourceAnchor=tokenAnchor=null;void navigate(last.documentId,last.pageIndex-1);};$('next').onclick=()=>{sourceAnchor=tokenAnchor=null;void navigate(last.documentId,last.pageIndex+1);};
$('source').onclick=()=>navigate(last.documentId,last.pageIndex,'source',sourceAnchor);$('reflow').onclick=()=>navigate(last.documentId,last.pageIndex,'reflow');
$('zoom').onchange=()=>{clearSelection();const sheet=view.querySelector('.source-sheet');if(sheet)sheet.style.width=Number($('zoom').value)*100+'%';record('source-zoom',{zoom:Number($('zoom').value)});};
$('font').onchange=()=>{clearSelection();const frame=view.querySelector('iframe');if(frame){frame.contentDocument.body.style.fontSize=$('font').value+'px';frame.contentWindow.dispatchEvent(new Event('resize'));record('font-change',{font:Number($('font').value)});}};
$('locate').onclick=()=>{locating=!locating;$('locate').setAttribute('aria-pressed',String(locating));};
$('narrow').onclick=()=>{narrow=!narrow;$('reader-column').style.width=narrow?'390px':'100%';$('narrow').textContent=narrow?'恢复宽屏':'窄屏 390';view.querySelector('iframe')?.contentWindow.dispatchEvent(new Event('resize'));record('width-change',{narrow});};
$('close').onclick=()=>{clearSelection();session.destroy();view.replaceChildren();$('close').disabled=true;$('reopen').disabled=false;for(const id of ['document','page','previous','next','source','reflow','font','zoom','locate','narrow'])$(id).disabled=true;};
$('reopen').onclick=()=>{session=new PaperSession(manifest.documents,load,commit,status);$('close').disabled=false;$('reopen').disabled=true;for(const id of ['document','page','source','narrow'])$(id).disabled=false;void navigate(last.documentId,last.pageIndex);};
window.addEventListener('pagehide',()=>session?.destroy());
try{
 const response=await fetch('/session-manifest.json',{cache:'no-store'});if(!response.ok)throw Error('目录载入失败');const text=await response.text();if(text.length>1024*1024)throw Error('目录超出预算');manifest=validateSession(JSON.parse(text));
 $('document').replaceChildren(...manifest.documents.map(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=`${d.title}（${d.pages.length}页）`;return o;}));
 session=new PaperSession(manifest.documents,load,commit,status);await navigate(manifest.documents[0].id,0);
}catch(error){$('status').textContent='无法开始：'+error.message;record('startup-error',{message:error.message});}
