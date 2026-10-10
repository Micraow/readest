import assert from 'node:assert/strict';import {retainedSourceRows,layoutBlocks} from './reader_engine.mjs';
const token=(id,width,gap=.2,flag=false)=>({id,width_em:width,height_em:1,vertical_em:-.2,gap_em:gap,...(flag?{retained_source_break_after:true}:{})});
let count=0;
const source=[token('a',4),token('b',4),token('prefix',2,0,true),token('suffix',3),token('tail',4,0)];
for(const font of [20,24,28])for(const width of [320,390]){
 const rows=retainedSourceRows(source,font,width-24,width-12);assert.deepEqual(rows.flat(),source);assert(rows.some(r=>r.at(-1).id==='prefix'));assert(!rows.some(r=>r.length===1&&r[0].id==='prefix'));const d={blocks:[{kind:'paragraph',tokens:source}],retained_source_break_policy:'native-retained-line-v1'},l=layoutBlocks(d,font,width)[0];assert.deepEqual(l.placements.map(p=>p.token),source);const baseline=p=>p.y+(p.token.height_em+p.token.vertical_em)*font;const a=l.placements.find(p=>p.token.id==='prefix'),b=l.placements.find(p=>p.token.id==='suffix');assert(baseline(b)>baseline(a));for(const p of l.placements)assert(p.x>=0&&p.y>=0&&p.x+p.width<=width+1e-8&&p.y+p.height<=l.height);count++;
}
const plain={blocks:[{kind:'paragraph',tokens:source.map(({retained_source_break_after,...t})=>t)}]},legacy=layoutBlocks(plain,28,390);assert.deepEqual(layoutBlocks({...plain,retained_source_break_policy:'native-retained-line-v1'},28,390),legacy);count++;
const marked=structuredClone(plain);marked.blocks[0].tokens[2].retained_source_break_after=true;const noPolicy=layoutBlocks(marked,28,390);assert.deepEqual(noPolicy.map(x=>x.placements.map(p=>[p.x,p.y,p.width,p.height])),legacy.map(x=>x.placements.map(p=>[p.x,p.y,p.width,p.height])));count++;
assert.throws(()=>retainedSourceRows(source,28,296,308,1),/budget/);count++;
assert.throws(()=>retainedSourceRows([token('too-wide',40,0,true)],28,296,308),/fit safely/);count++;
const long=[token('bounded-long-word',10.8,0,true),token('next',2)];assert.deepEqual(retainedSourceRows(long,28,296,308).flat(),long);count++;
const overlap=[token('a',4,-.5),token('b',2,0,true),token('next',2)];const rows=retainedSourceRows(overlap,20,296,308);assert(rows.some(r=>r[0].id==='a'&&r[1]?.id==='b'));count++;
console.log(JSON.stringify({source_break_layout_controls:count,token_order_preserved:true,negative_gap_pair_not_split:true,unmarked_geometry_identical:true,browser_verified:false}));
