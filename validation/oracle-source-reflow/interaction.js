'use strict';
const fixture=window.ORACLE_FIXTURE;
const reader=document.querySelector('#reading');
const modal=document.querySelector('#source-dialog');
const plane=document.querySelector('.source-plane');
let activePage=fixture.sections[0].page, opener=null;
function sourceView(page,bbox,id){
  const p=fixture.pages[String(page)];activePage=page;
  const unit=id?fixture.sections.flatMap(s=>s.nodes.flatMap(n=>n.units)).find(u=>u.id===id):null;
  const preview=document.querySelector('.object-preview');preview.hidden=!unit||!['table','equation'].includes(unit.role);
  if(!preview.hidden)preview.querySelector('img').src=unit.image;
  document.querySelector('#source-image').src=p.image;
  const mark=document.querySelector('.highlight');mark.hidden=!bbox;
  if(bbox)Object.assign(mark.style,{left:`${100*bbox[0]/p.width}%`,top:`${100*bbox[1]/p.height}%`,width:`${100*(bbox[2]-bbox[0])/p.width}%`,height:`${100*(bbox[3]-bbox[1])/p.height}%`});
  plane.style.width='100%';
  document.querySelector('#source-status').textContent=`Original page ${page}${id?' · '+id:''}${bbox?' · PDF coordinates '+bbox.map(x=>x.toFixed(2)).join(', '):''}`;
  if(!modal.open)modal.showModal();
}
document.querySelectorAll('[data-font]').forEach(b=>b.addEventListener('click',()=>{
  reader.style.fontSize=`${b.dataset.font}px`;
  document.querySelectorAll('[data-font]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
}));
document.querySelectorAll('[data-unit]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();opener=a;sourceView(Number(a.dataset.page),JSON.parse(a.dataset.bbox),a.dataset.unit);}));
document.querySelector('#show-original').addEventListener('click',e=>{opener=e.currentTarget;sourceView(activePage,null,null);});
document.querySelector('#close-source').addEventListener('click',()=>modal.close());
modal.addEventListener('close',()=>opener?.focus({preventScroll:true}));
document.querySelector('#zoom-source').addEventListener('click',()=>plane.style.width=plane.style.width==='200%'?'100%':'200%');
window.oracleReady=true;
