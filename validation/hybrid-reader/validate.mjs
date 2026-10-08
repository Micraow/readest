import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {asset,pages} from './fixture.mjs';

const root = new URL('.',import.meta.url);
const html = await readFile(new URL('index.html',root),'utf8');
const manifest = JSON.parse(await readFile(new URL('source-manifest.json',root),'utf8'));
assert.equal(createHash('sha256').update(html).digest('hex'),manifest.rendererSha256);
assert.equal(pages.length,2);
assert.ok(pages.every(p=>p.key.startsWith('Synthetic-') && p.asset==='synthetic.svg'));
assert.ok(!/https?:\/\//.test(JSON.stringify(pages)));
assert.equal((html.match(/fetch\(/g)||[]).length,1);
assert.ok(html.includes("fetch('pages.json')"));
if(process.argv.includes('--check-fixture')) {
  console.log('Fixture and exact renderer hash passed. Browser has not run.');
  process.exit(0);
}

const {chromium,expect} = await import('@playwright/test');
const output = new URL('evidence/',root);
await mkdir(output,{recursive:true});
const resources = new Map([
  ['/', ['text/html; charset=utf-8',html]],
  ['/pages.json',['application/json',JSON.stringify(pages)]],
  ['/synthetic.svg',['image/svg+xml',asset]],
]);
const server = createServer((req,res)=>{
  if(req.url==='/favicon.ico'){res.writeHead(204);res.end();return;}
  const item=resources.get(req.url);
  res.writeHead(item?200:404,{
    'Content-Type':item?.[0]||'text/plain',
    'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; object-src 'none'",
  });
  res.end(item?.[1]||'Not found');
});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve)});
const origin=`http://127.0.0.1:${server.address().port}`;
const failures=[];
const checks=[];
let browser,context,page;
const report={scope:'Synthetic fixture and Chromium only. No PDF semantic, native-shell, or Android acceptance.',source:manifest,checks};
const check=async(name,fn)=>{await fn();checks.push(name);console.log(`PASS ${name}`)};
const shot=async(name)=>page.screenshot({path:fileURLToPath(new URL(`${name}.png`,output)),fullPage:true});
const noOverflow=async()=>{
  const geometry=await page.evaluate(()=>({
    width:document.documentElement.clientWidth,
    scrollWidth:document.documentElement.scrollWidth,
    readerWidth:document.querySelector('.reader').clientWidth,
    readerScrollWidth:document.querySelector('.reader').scrollWidth,
  }));
  assert.ok(geometry.scrollWidth<=geometry.width+1,JSON.stringify(geometry));
  assert.ok(geometry.readerScrollWidth<=geometry.readerWidth+1,JSON.stringify(geometry));
};
try {
  // Keep Chromium's sandbox enabled. Do not weaken runner or browser security.
  browser=await chromium.launch({headless:true,chromiumSandbox:true});
  report.chromiumVersion=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});
  await context.route('**/*',route=>{
    if(new URL(route.request().url()).origin!==origin){
      failures.push(`Unexpected network request: ${route.request().url()}`);
      return route.abort();
    }
    return route.continue();
  });
  page=await context.newPage();
  page.on('pageerror',error=>failures.push(error.message));
  page.on('console',message=>{if(message.type()==='error')failures.push(message.text())});
  await page.goto(origin,{waitUntil:'load'});
  await check('initial selectable body and source image',async()=>{
    await expect(page.locator('#content')).toContainText('Selectable synthetic body text.');
    await expect(page.locator('#page option')).toHaveCount(2);
    await expect(page.locator('#original')).toHaveJSProperty('naturalWidth',600);
    await expect(page.locator('.source')).toBeVisible();
    await noOverflow();
  });
  await shot('desktop-light');
  await check('font bounds and repeated changes',async()=>{
    for(let i=0;i<10;i++)await page.locator('#larger').click();
    await expect(page.locator('#size')).toHaveText('32px');
    await noOverflow();
    await shot('desktop-font-32');
    for(let i=0;i<12;i++)await page.locator('#smaller').click();
    await expect(page.locator('#size')).toHaveText('14px');
    for(let i=0;i<3;i++)await page.locator('#larger').click();
    await expect(page.locator('#size')).toHaveText('20px');
  });
  await check('dark theme toggle',async()=>{
    await page.locator('#theme').click();
    await expect(page.locator('body')).toHaveClass(/dark/);
    await shot('desktop-dark');
    await page.locator('#theme').click();
    await expect(page.locator('body')).not.toHaveClass(/dark/);
  });
  await check('desktop source toggle twice',async()=>{
    await page.locator('#source').click();
    await expect(page.locator('.source')).toBeHidden();
    await page.locator('#source').click();
    await expect(page.locator('.source')).toBeVisible();
  });
  await check('inline zoom close escape and repeat',async()=>{
    for(let i=0;i<2;i++){
      await page.locator('#content .inlinecrop').click();
      await expect(page.locator('#zoom')).toBeVisible();
      await shot(`inline-zoom-${i}`);
      if(i===0)await page.locator('#zoom button').click();
      else await page.keyboard.press('Escape');
      await expect(page.locator('#zoom')).toBeHidden();
    }
  });
  await check('page switch and switch back',async()=>{
    await page.locator('#page').selectOption('1');
    await expect(page.locator('#content')).toHaveText('Second page selectable content.');
    await page.locator('#page').selectOption('0');
    await expect(page.locator('#content')).toContainText('Synthetic heading');
  });
  await check('mobile viewport and source return',async()=>{
    await page.setViewportSize({width:390,height:844});
    await expect(page.locator('.source')).toBeHidden();
    await expect(page.locator('.reader')).toBeVisible();
    await noOverflow();
    await shot('mobile-light');
    await page.locator('#source').click();
    await expect(page.locator('.source')).toBeVisible();
    await expect(page.locator('.reader')).toBeHidden();
    await shot('mobile-source');
    await page.locator('#source').click();
    await expect(page.locator('.reader')).toBeVisible();
    await expect(page.locator('.source')).toBeHidden();
  });
  assert.deepEqual(failures,[],'Browser errors or unexpected network');
  report.status='passed';
} catch(error) {
  report.status='failed';
  report.error=error.stack||String(error);
  if(page)await shot('failure').catch(()=>{});
  process.exitCode=1;
} finally {
  report.browserErrors=failures;
  await writeFile(new URL('report.json',output),JSON.stringify(report,null,2)+'\n');
  await context?.close();
  await browser?.close();
  await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify(report,null,2));
}
