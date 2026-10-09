import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createDialogController,selectParagraph} from './interaction_helpers.mjs';
import {readSelection} from '../../generic-reflow-v2-text-selection/code/selection_layer.mjs';
const require=createRequire(process.env.SELECTION_TEST_PACKAGE||import.meta.url),{JSDOM}=require('jsdom');
const doc=new JSDOM('<button id="source">Source</button><select></select><main><div class="selection-layer"><span data-selection-piece="character">Alpha</span><span data-selection-piece="separator"> </span><span style="top:40px" data-selection-piece="character">Beta</span><span data-selection-piece="paragraph">\n</span></div></main><p role="status"></p><dialog><button id="close">Close</button><p id="title"></p><div class="focus"></div></dialog>').window.document;
const dialog=doc.querySelector('dialog'),status=doc.querySelector('[role=status]'),layer=doc.querySelector('.selection-layer'),root=doc.querySelector('main'),source=doc.querySelector('#source'),fallback=doc.querySelector('select'),area=doc.querySelector('.focus'),title=doc.querySelector('#title'),button=doc.querySelector('#close');
// Only dialog state/events are simulated. This is deliberately not browser evidence.
dialog.showModal=()=>dialog.setAttribute('open','');dialog.close=()=>dialog.removeAttribute('open');
const control=createDialogController(dialog,title,area,button,fallback);
let count=0;function check(name,fn){fn();count++;console.log('PASS',name);}
check('keyboard action selects paragraph across visual line break',()=>{assert.equal(selectParagraph(layer,status),true);assert.equal(readSelection(root,doc.getSelection()).text,'Alpha Beta\n');});
check('unknown paragraph remains selected but warns and refuses copy',()=>{layer.children[2].dataset.unresolved='true';selectParagraph(layer,status);assert.equal(readSelection(root,doc.getSelection()).ok,false);assert.match(status.textContent,/拒绝/);delete layer.children[2].dataset.unresolved;});
check('detached layer refuses keyboard selection',()=>{const old=layer.cloneNode(true);assert.equal(selectParagraph(old,status),false);});
check('source dialog focuses close control',()=>{source.focus();control.open('Source view',doc.createElement('div'));assert.equal(doc.activeElement,button);assert.equal(dialog.open,true);});
check('button close clears source and restores source trigger',()=>{button.click();assert.equal(dialog.open,false);assert.equal(area.childNodes.length,0);assert.equal(doc.activeElement,source);});
check('Escape native close event cleans and restores focus',()=>{source.focus();control.open('Source view',doc.createElement('div'));dialog.close();dialog.dispatchEvent(new doc.defaultView.Event('close'));assert.equal(area.childNodes.length,0);assert.equal(doc.activeElement,source);});
check('resize replacing opener uses connected fallback',()=>{const old=doc.createElement('button');root.append(old);old.focus();control.open('View',doc.createElement('div'));old.remove();control.close();assert.equal(doc.activeElement,fallback);});
check('page reset removes old view',()=>{source.focus();control.open('Old page',doc.createElement('div'));control.reset();assert.equal(dialog.open,false);assert.equal(area.childNodes.length,0);assert.equal(title.textContent,'');});
check('late close event cannot erase newly opened view',()=>{control.open('New page',doc.createElement('div'),source);dialog.dispatchEvent(new doc.defaultView.Event('close'));assert.equal(title.textContent,'New page');assert.equal(area.childNodes.length,1);assert.equal(dialog.open,true);});
check('repeated close is harmless',()=>{control.close();control.close();assert.equal(doc.activeElement,source);});
console.log(JSON.stringify({passed:count,browserVerified:false}));
