/** Local session manifest, never an HTML or arbitrary-URL import format. */
export function validateSession(input) {
 const need=(ok,message)=>{if(!ok)throw Error('Invalid paper session: '+message);};
 const sha=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
 const finite=n=>typeof n==='number'&&Number.isFinite(n)&&n>0&&n<=32768;
 const label=s=>typeof s==='string'&&s.length>0&&s.length<=500;
 need(input?.schema==='readest-paper-session-v1','schema');
 need(Array.isArray(input.documents)&&input.documents.length>0&&input.documents.length<=4,'documents');
 const ids=new Set();let count=0;
 for(const d of input.documents){
  need(typeof d.id==='string'&&/^[a-z][a-z0-9-]{0,31}$/.test(d.id)&&!ids.has(d.id),'document identity');ids.add(d.id);need(label(d.title),'title');
  need(d.pdf?.url===`/document/${d.id}/original.pdf`&&sha(d.pdf.sha256),'original PDF binding');
  need(Array.isArray(d.pages)&&d.pages.length>0&&d.pages.length<=64,'page count');count+=d.pages.length;
  for(const [i,p] of d.pages.entries()){
   const prefix=`/document/${d.id}/page-${String(i).padStart(3,'0')}`;
   need(p.index===i&&label(p.label)&&label(p.limitation),'zero-based source page identity');
   need(p.source?.url===prefix+'.png'&&sha(p.source.sha256)&&finite(p.source.width)&&finite(p.source.height)&&finite(p.source.pdfWidth)&&finite(p.source.pdfHeight)&&p.source.width*p.source.height<=32000000,'source image binding');
   need([0,90,180,270].includes(p.source.rotation),'source rotation');
   if(p.reflow!==null){need(p.reflow&&p.reflow.url===prefix+'/reader.html'&&sha(p.reflow.sha256)&&sha(p.reflow.extractedSourceSha256)&&p.source.rotation===0&&p.reflow.acceptance==='partial-probes-only'&&label(p.reflow.limitation),'reflow provenance');}
  }
 }
 need(count===input.pageCount&&count<=128,'total page count');return input;
}
