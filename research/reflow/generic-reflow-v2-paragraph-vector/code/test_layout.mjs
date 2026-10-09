import assert from 'node:assert/strict';import {layoutBlocks} from './reader_engine.mjs';
let count=0;function test(name,f){f();count++;console.log('PASS '+name);}
const token=id=>({id,kind:'vector',width_em:2,height_em:1,vertical_em:-.2,gap_em:.2});const data={blocks:[{kind:'paragraph',tokens:['a','b','c'].map(token)}]};
test('wrap preserves complete token order',()=>{const b=layoutBlocks(data,20,100)[0];assert.deepEqual(b.placements.map(p=>p.token.id),['a','b','c']);assert(b.placements[1].y>b.placements[0].y);});
test('changing body size changes geometry without splitting tokens',()=>{const a=layoutBlocks(data,20,390)[0],b=layoutBlocks(data,28,390)[0];assert.equal(a.placements.length,b.placements.length);assert.equal(b.placements[0].width/a.placements[0].width,1.4);});
test('bounded object fits width preserving aspect ratio',()=>{const t={...token('figure'),width_em:40,height_em:20};const p=layoutBlocks({blocks:[{kind:'object',tokens:[t]}]},28,390)[0].placements[0];assert(p.width<=366);assert.equal(p.width/p.height,2);});
test('invalid reading viewport rejects explicitly',()=>assert.throws(()=>layoutBlocks(data,20,20),/invalid reading size/));
console.log(JSON.stringify({tests:count,scope:'original pure-layout controls, no browser'}));
