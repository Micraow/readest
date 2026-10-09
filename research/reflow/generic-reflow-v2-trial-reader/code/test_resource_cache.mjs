import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createPageResourceCache} from './resource_cache.mjs';
const bundle=JSON.parse(fs.readFileSync(process.argv[2]));let compileCalls=0,decodeCalls=0;
const cache=createPageResourceCache(reader=>{compileCalls++;return reader.resources.map((_,i)=>i);},async token=>{decodeCalls++;return {id:token.id};});
const first=cache.load(bundle.pages[0]),simultaneous=cache.load(bundle.pages[0]);assert.equal(first,simultaneous);const a=await first;const second=await cache.load(bundle.pages[1]);const counts={compileCalls,decodeCalls};const again=await cache.load(bundle.pages[0]);assert.equal(a,again);assert.deepEqual({compileCalls,decodeCalls},counts);
let fail=true,retries=0;const retry=createPageResourceCache(()=>[],async()=>{retries++;if(fail)throw Error('intentional decode failure');return {};});await assert.rejects(retry.load(bundle.pages[0]));fail=false;await retry.load(bundle.pages[0]);assert.ok(retries>1);
const replacement=structuredClone(bundle.pages[0]);await cache.load(replacement);assert.equal(compileCalls,counts.compileCalls+1);
console.log(JSON.stringify({real_pages:2,initial_resource_pass:counts,return_to_first_page_extra_compile:0,return_to_first_page_extra_decode:0,concurrent_request_shared:true,failed_decode_retry:true,new_page_identity_rebuilds:true,cold_pipeline_claimed:false,browser_verified:false}));
