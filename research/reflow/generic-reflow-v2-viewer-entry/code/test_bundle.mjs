import assert from 'node:assert/strict';
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {validateResearchBundle} from './bundle_contract.mjs';
import {layoutBlocks} from '../../generic-reflow-v2-formula-hierarchy/code/reader_engine.mjs';
import {selectionGeometry} from '../../generic-reflow-v2-text-selection/code/selection_layer.mjs';
const input=process.argv[2];if(!input)throw Error('Pass an existing private precomputed JSON bundle; never copy it into source.');
const start=performance.now(),text=fs.readFileSync(input,'utf8'),parsed=performance.now(),bundle=validateResearchBundle(JSON.parse(text)),validated=performance.now();
const reports=[];
for(const [pageIndex,page] of bundle.pages.entries())for(const font of [20,24,28])for(const width of [320,390]){
 const layouts=layoutBlocks(page.reader,font,width);let glyphs=0,unresolved=0;
 for(const layout of layouts)for(const token of selectionGeometry(page.reader,layout,page.text_map.blocks[layout.index])){glyphs+=token.characters.length;unresolved+=!token.eligible;}
 reports.push({page:pageIndex,font,width,blocks:layouts.length,glyphs,unresolved});
}
const complete=performance.now();let negatives=0;
function reject(name,edit){const copy=structuredClone(bundle);edit(copy);assert.throws(()=>validateResearchBundle(copy),undefined,name);negatives++;}
reject('network image',b=>b.pages[0].source.png='https://example.invalid/private.png');
reject('network PDF',b=>b.pages[0].source.pdf='https://example.invalid/private.pdf');
reject('script URI',b=>b.pages[0].source.png='javascript:alert(1)');
reject('page bound',b=>b.pages.push(...structuredClone(b.pages)));
reject('invalid source image dimensions',b=>b.pages[0].source.width++);
reject('infinite scale',b=>b.pages[0].reader.body_font_pdf=Infinity);
reject('unknown canvas operation',b=>b.pages[0].reader.affine_programs[0][0].name='drawImage');
reject('external filter',b=>b.pages[0].reader.states[0].filter='url(https://example.invalid)');
reject('unbounded source box',b=>b.pages[0].reader.blocks[0].tokens[0].source_pixel_box[2]=1e9);
reject('wrong text map identity',b=>b.pages[0].text_map.blocks[0].tokens[0].id='wrong');
reject('invalid event',b=>Object.values(b.pages[0].reader.events)[0].resource=-1);
reject('active SVG',b=>b.pages[0].source.png='data:image/svg+xml;base64,PHN2Zy8+');
reject('active HTML',b=>b.pages[0].source.pdf='data:text/html;base64,PGh0bWw+');
reject('prototype key',b=>{b.pages[0].reader.extra=JSON.parse('{"__proto__":{"polluted":true}}');});
reject('constructor key',b=>{b.pages[0].reader.extra={constructor:{prototype:{polluted:true}}};});
reject('excessive geometry',b=>b.pages[0].reader.blocks[0].tokens[0].width_em=10000);
reject('excessive nesting',b=>{let x=b;for(let i=0;i<40;i++)x=x.extra={};});
reject('fake PNG header',b=>b.pages[0].source.png=b.pages[0].source.png.replace('iVBOR','aVBOR'));
reject('broken formula hierarchy',b=>{const f=b.pages[0].reader.blocks.find(x=>x.kind==='formula');f.tokens[0].formula_role='label';});
assert.equal({}.polluted,undefined);
console.log(JSON.stringify({passed:true,real_page_layouts:reports,negative_controls:negatives,timing_ms:{read:parsed-start,parse_and_validate:validated-parsed,layouts_and_geometry:complete-validated},cold_pdf_request:false,browser_verified:false},null,2));
