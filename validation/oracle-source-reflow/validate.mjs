import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
const root=new URL('.',import.meta.url), output=new URL('evidence/',root);
const manifest=JSON.parse(await readFile(new URL('source-manifest.json',root),'utf8'));
for(const f of manifest.files)assert.equal(createHash('sha256').update(await readFile(new URL(f.path,root))).digest('hex'),f.sha256,f.path);
const fixtureCode=await readFile(new URL('fixture.js',root),'utf8'),sandbox={window:{}};vm.runInNewContext(fixtureCode,sandbox);
const fixture=sandbox.window.ORACLE_FIXTURE;
assert.equal(fixture.source.sha256,manifest.publicSource.sha256);
assert.equal(fixture.audit.suppressedInk,0);assert.equal(fixture.audit.sourceInk,fixture.audit.renderedInk);assert.equal(fixture.audit.duplicateInk.length,0);
const units=fixture.sections.flatMap(s=>s.nodes.flatMap(n=>n.units));assert.equal(new Set(units.map(u=>u.id)).size,units.length);
if(process.argv.includes('--check-fixture')){console.log(`PASS frozen source/code hashes and ${units.length} source units; browser not run.`);process.exit(0);}
const {chromium,expect}=await import('@playwright/test');
const {PNG}=await import('pngjs');
await mkdir(output,{recursive:true});
const resources=new Map(await Promise.all(['index.html','fixture.js','interaction.js'].map(async f=>['/'+(f==='index.html'?'':f),[f.endsWith('.html')?'text/html':'text/javascript',await readFile(new URL(f,root))]])));
const server=createServer((req,res)=>{if(req.url==='/favicon.ico'){res.writeHead(204);res.end();return;}const r=resources.get(req.url);res.writeHead(r?200:404,{'Content-Type':r?.[0]||'text/plain','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; object-src 'none'"});res.end(r?.[1]||'Not found');});
await new Promise((yes,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',yes)});
const origin=`http://127.0.0.1:${server.address().port}`,errors=[],checks=[];
const report={scope:'Oracle/reference structure input, selected public excerpts. Chromium rendering and source interaction only; no automatic parser, native shell or Android claims.',manifest,checks};
let browser,context,page;
async function ready(){await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.querySelectorAll('.unit img')].map(im=>im.decode()));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});}
async function check(name,fn){await fn();checks.push(name);console.log('PASS '+name);}
async function assertInk(loc,label){const p=PNG.sync.read(await loc.screenshot());let dark=0;for(let i=0;i<p.data.length;i+=4)if(p.data[i]<180&&p.data[i+1]<180&&p.data[i+2]<180)dark++;assert.ok(dark>20,`${label} painted pixels absent`);}
try{
 browser=await chromium.launch({headless:true,chromiumSandbox:true});report.chromiumVersion=browser.version();
 context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,serviceWorkers:'block'});
 await context.route('**/*',r=>{if(new URL(r.request().url()).origin!==origin){errors.push('External request '+r.request().url());return r.abort();}return r.continue();});
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto(origin);await page.waitForFunction(()=>window.oracleReady);await ready();
 const idMap=await page.locator('[data-unit]').evaluateAll(es=>es.map(e=>[e.dataset.unit,e.dataset.page,e.dataset.bbox]));
 let heights={};
 for(const size of [20,28]){
  await page.locator(`[data-font="${size}"]`).click();await ready();
  await check(`${size}px: all original units decoded, source anchors unique and stable`,async()=>{
   assert.equal(await page.locator('[data-unit]').count(),units.length);assert.deepEqual(await page.locator('[data-unit]').evaluateAll(es=>es.map(e=>[e.dataset.unit,e.dataset.page,e.dataset.bbox])),idMap);
   const bad=await page.locator('.unit img').evaluateAll(ims=>ims.filter(i=>!i.complete||!i.naturalWidth||!i.naturalHeight).length);assert.equal(bad,0);
  });
  await check(`${size}px: body wraps within 390px while protected objects retain scale`,async()=>{
   const g=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,flows:[...document.querySelectorAll('.flow')].map(p=>({w:p.clientWidth,sw:p.scrollWidth,h:p.getBoundingClientRect().height})),table:(()=>{const p=document.querySelector('[data-node="c-table"]');return {w:p.clientWidth,sw:p.scrollWidth};})()}));
   assert.ok(g.scroll<=g.width+1,JSON.stringify(g));assert.ok(g.flows.every(x=>x.sw<=x.w+1),JSON.stringify(g));heights[size]=g.flows.map(x=>x.h);report[`${size}pxGeometry`]=g;
  });
  for(const id of ['excerpt-a','excerpt-b','excerpt-c','excerpt-d']){await page.locator('#'+id).screenshot({path:fileURLToPath(new URL(`${id}-${size}.png`,output))});}
  await assertInk(page.locator('[title^="4 superscript n plus one;"]'),'superscript original');
 }
 await check('Increasing type from 20px to 28px changes wrapping and retains baseline ratios',async()=>{
  assert.ok(heights[28].every((h,i)=>h>heights[20][i]));
  const matches=await page.locator('[data-role="inline-math"]').evaluateAll(es=>es.map(e=>({id:e.dataset.unit,w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height,va:parseFloat(getComputedStyle(e).verticalAlign)})));
  for(const m of matches){const u=units.find(x=>x.id===m.id);assert.ok(Math.abs(m.w-u.widthEm*28)<.1);assert.ok(Math.abs(m.h-u.heightEm*28)<.1);assert.ok(Math.abs(m.va+u.descentEm*28)<.1);}
 });
 await check('Table and equations scroll to their true right edge without dropping glyphs',async()=>{
  for(const id of ['c-table','a-equation-11','d-equation-44','d-equation-45']){
   const loc=page.locator(`[data-node="${id}"]`);const result=await loc.evaluate(e=>{e.scrollLeft=e.scrollWidth;return {left:e.scrollLeft,max:e.scrollWidth-e.clientWidth};});assert.ok(Math.abs(result.left-result.max)<=1);assert.ok(result.left>0);await assertInk(loc,id);await loc.screenshot({path:fileURLToPath(new URL(`${id}-right-28.png`,output))});
  }
 });
 await check('Complete 8 by 9 table preview remains accessible after horizontal scroll',async()=>{
  await page.locator('[data-node="c-table"] .unit').click();await expect(page.locator('.object-preview')).toBeVisible();await page.locator('.object-preview img').evaluate(im=>im.decode());
  const im=await page.locator('.object-preview img').evaluate(e=>({src:e.src,w:e.naturalWidth,h:e.naturalHeight,box:e.getBoundingClientRect().toJSON()}));const u=units.find(u=>u.id==='c-table-whole');assert.equal(im.src,u.image);assert.ok(im.box.right<=390);await assertInk(page.locator('.object-preview'),'whole table preview');await page.screenshot({path:fileURLToPath(new URL('table-whole-preview-mobile.png',output))});await page.locator('#close-source').click();
 });
 await check('Source anchor opens exact original page/bbox; zoom, Close and Escape are repeatable',async()=>{
  const loc=page.locator('[title^="4 superscript n plus one;"]');
  await loc.click();await expect(page.locator('#source-dialog')).toBeVisible();await page.locator('#source-image').evaluate(im=>im.decode());await expect(page.locator('#source-status')).toContainText('Original page 3');await expect(page.locator('.highlight')).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL('source-anchor-mobile.png',output))});await page.locator('#zoom-source').click();assert.equal(await page.locator('.source-plane').evaluate(e=>e.style.width),'200%');await page.locator('#close-source').click();await expect(page.locator('#source-dialog')).not.toBeVisible();
  await loc.click();await page.keyboard.press('Escape');await expect(page.locator('#source-dialog')).not.toBeVisible();
  await page.locator('[data-font="20"]').click();await page.locator('[data-font="28"]').click();await expect(page.locator('[data-font="28"]')).toHaveAttribute('aria-pressed','true');assert.deepEqual(await page.locator('[data-unit]').evaluateAll(es=>es.map(e=>[e.dataset.unit,e.dataset.page,e.dataset.bbox])),idMap);
 });
 await check('Auxiliary selectable text is separately labelled scientifically unverified',async()=>{await page.locator('#aux-text summary').click();await expect(page.locator('#aux-text pre')).toBeVisible();await expect(page.locator('#aux-text')).toContainText('上下标会被压平');});
 assert.deepEqual(errors,[]);report.result='passed';
}catch(e){report.result='failed';report.failure=String(e.stack||e);process.exitCode=1;console.error(e);}
finally{report.browserErrors=errors;await writeFile(new URL('report.json',output),JSON.stringify(report,null,2));await context?.close();await browser?.close();await new Promise(r=>server.close(r));}
