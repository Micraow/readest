/** Atomic, abortable page ownership; no shared page/token identities. */
export class PaperSession {
 constructor(documents, load, commit, status=()=>{}) {
  this.documents=documents;this.load=load;this.commit=commit;this.status=status;
  this.generation=0;this.pending=null;this.current=null;this.resource=null;this.closed=false;
  this.positions=new Map();
 }
 async open(documentId,pageIndex,mode='source',anchor=null) {
  if(this.closed)throw Error('Session is closed');
  const doc=this.documents.find(d=>d.id===documentId);
  if(!doc||!Number.isInteger(pageIndex)||!doc.pages[pageIndex])throw Error('Unknown source page');
  const page=doc.pages[pageIndex];if(!['source','reflow'].includes(mode)||mode==='reflow'&&!page.reflow)throw Error('Uncertified reflow request');
  const state={documentId,pageIndex,mode,anchor,key:`${doc.pdf.sha256}:${pageIndex}:${mode}`};
  this.pending?.abort();const controller=new AbortController();this.pending=controller;const generation=++this.generation;
  this.status('loading',state);
  let candidate;
  try {
   candidate=await this.load(doc,page,state,controller.signal);
   if(this.closed||controller.signal.aborted||generation!==this.generation){candidate.dispose();return false;}
   // A failed prepare leaves the current reader and source identity coherent.
   this.commit(candidate,state,doc,page);const previous=this.resource;
   this.resource=candidate;this.current=state;this.positions.set(documentId,pageIndex);
   previous?.dispose();this.pending=null;this.status('ready',state);return true;
  } catch(error) {
   if(candidate&&candidate!==this.resource)candidate.dispose();
   if(controller.signal.aborted||generation!==this.generation||this.closed)return false;
   this.pending=null;this.status('error',state,error);throw error;
  }
 }
 destroy(){if(this.closed)return;this.closed=true;this.generation++;this.pending?.abort();this.pending=null;this.resource?.dispose();this.resource=null;this.current=null;this.status('closed');}
}

/** Moving a live iframe reloads its document and loses source-return listeners. */
export function replaceOwnedView(view,element) {
 if(element.parentElement!==view){view.replaceChildren(element);return;}
 for(const child of Array.from(view.children))if(child!==element)child.remove();
}
