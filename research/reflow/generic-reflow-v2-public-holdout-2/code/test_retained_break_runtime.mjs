/** Check actual selection refusal across every retained source boundary. */
import fs from 'node:fs';import assert from 'node:assert/strict';
await import('../../generic-reflow-v2-viewer-entry/code/test_import_smoke.mjs');
const bundle=JSON.parse(fs.readFileSync(process.argv[3])),reader=bundle.pages[0].reader,doc=globalThis.document,win=globalThis.window;let checked=0;
for(const [index,block] of reader.blocks.entries())for(let i=0;i<block.tokens.length;i++){
 const t=block.tokens[i];if(!t.retained_source_break_after)continue;const next=block.tokens[i+1],section=doc.querySelectorAll('section')[index],spans=[...section.querySelectorAll('[data-token]')],left=spans.filter(s=>s.dataset.token===t.id),right=spans.filter(s=>s.dataset.token===next.id);assert(left.length&&right.length);assert(left.some(s=>s.dataset.unresolved==='true'));assert(parseFloat(right[0].style.top)>parseFloat(left[0].style.top));
 const range=doc.createRange();range.setStart(left[0].firstChild,0);range.setEnd(right.at(-1).firstChild,right.at(-1).firstChild.length);const selection=doc.getSelection();selection.removeAllRanges();selection.addRange(range);const payload={},e=new win.Event('copy',{cancelable:true});Object.defineProperty(e,'clipboardData',{value:{setData:(k,v)=>payload[k]=v}});doc.dispatchEvent(e);assert(e.defaultPrevented);assert.equal(payload['text/plain'],undefined);checked++;
}
assert(checked>0);console.log(JSON.stringify({scope:'actual shipped-module jsdom/native Canvas',retained_boundaries_checked:checked,next_fragment_visually_on_following_row:true,uncertain_copy_still_blocked:true,no_clipboard_payload_written:true,browser_verified:false}));
