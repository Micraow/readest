import assert from 'node:assert/strict';
import {PaperSession,replaceOwnedView} from './paper_session.mjs';
import {validateSession} from './session_contract.mjs';
const h='a'.repeat(64),mk=(id,n)=>({id,title:id,pdf:{url:`/document/${id}/original.pdf`,sha256:h},pages:Array.from({length:n},(_,i)=>({index:i,label:String(i+1),limitation:'original only',source:{url:`/document/${id}/page-${String(i).padStart(3,'0')}.png`,sha256:h,width:200,height:300,pdfWidth:100,pdfHeight:150,rotation:0},reflow:null}))});
const input={schema:'readest-paper-session-v1',documents:[mk('one',9),mk('two',10)],pageCount:19};
validateSession(input);let controls=1;
for(const edit of [x=>x.pageCount=18,x=>x.documents[1].id='one',x=>x.documents[0].pages[0].index=9,x=>x.documents[0].pdf.url='https://example.invalid/x',x=>x.documents[0].pages[0].source.url='/document/one/../file.png',x=>x.documents[0].pages[0].source.sha256='wrong',x=>x.documents[0].pages[0].source.rotation=17,x=>x.documents[0].pages[0].reflow={url:'/arbitrary.html',sha256:h,acceptance:'passed'},x=>x.documents[0].pages[0].source.width=1e9]){const x=structuredClone(input);edit(x);assert.throws(()=>validateSession(x));controls++;}
const queue=[],commits=[],statuses=[],disposed=[];
const session=new PaperSession(input.documents,(d,p,s,signal)=>new Promise((resolve,reject)=>queue.push({d,p,s,signal,resolve,reject})),(resource,s)=>commits.push(s),(type)=>statuses.push(type));
const resource=id=>({id,dispose(){disposed.push(id);}});
let promise=session.open('one',0);queue.shift().resolve(resource('first'));assert.equal(await promise,true);assert.equal(session.current.key,h+':0:source');controls++;
const stale=session.open('one',1),staleJob=queue.shift();const latest=session.open('one',2),latestJob=queue.shift();assert.equal(staleJob.signal.aborted,true);latestJob.resolve(resource('latest'));assert.equal(await latest,true);staleJob.resolve(resource('stale'));assert.equal(await stale,false);assert.deepEqual(disposed,['first','stale']);assert.equal(session.current.pageIndex,2);controls++;
promise=session.open('two',9);queue.shift().reject(Error('image corrupt'));await assert.rejects(promise,/image corrupt/);assert.equal(session.current.documentId,'one');assert.equal(session.current.pageIndex,2);assert.equal(disposed.includes('latest'),false);controls++;
await assert.rejects(session.open('one',9),/Unknown source page/);await assert.rejects(session.open('one',0,'reflow'),/Uncertified/);controls+=2;
promise=session.open('two',9);queue.shift().resolve(resource('last-page'));await promise;assert.equal(session.current.pageIndex,9);assert.equal(session.positions.get('one'),2);assert.equal(session.positions.get('two'),9);controls++;
const closing=session.open('one',0),closingJob=queue.shift();session.destroy();session.destroy();assert.equal(closingJob.signal.aborted,true);closingJob.resolve(resource('after-close'));assert.equal(await closing,false);assert.equal(session.current,null);assert.equal(disposed.filter(x=>x==='last-page').length,1);assert.equal(disposed.filter(x=>x==='after-close').length,1);await assert.rejects(session.open('one',0),/closed/);controls++;
assert.equal(commits.length,3);assert.equal(statuses.at(-1),'closed');console.log(JSON.stringify({controls,whole_source_pages:19,stale_loads_disposed:true,failed_page_preserves_current:true,source_identity_scoped:true,browser_verified:false}));

const removed=[],container={children:[],replaceChildren(){throw Error('live iframe was moved');}},frame={parentElement:container,remove(){throw Error('live iframe removed');}},prior={remove(){removed.push('prior');}};container.children=[prior,frame];replaceOwnedView(container,frame);assert.deepEqual(removed,['prior']);console.log('connected iframe identity preserved');
