import {readdir, readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';

const output = resolve('evidence');
const browser = await chromium.launch({headless:true, chromiumSandbox:true});
const report = {scope:'Chromium export rendering only, pending semantic review', chromium:browser.version(), pages:[]};
const failures=[];
try {
  for (const dir of await readdir(output, {withFileTypes:true})) {
    if (!dir.isDirectory()) continue;
    const file = resolve(output,dir.name,'reflow.html');
    try { await readFile(file); } catch { continue; }
    for (const width of [1000,390]) {
      const context = await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
      const blocked=[];
      await context.route('**/*', route=>{
        const protocol = new URL(route.request().url()).protocol;
        if (protocol==='file:' || protocol==='data:') return route.continue();
        blocked.push(route.request().url());
        return route.abort();
      });
      const page=await context.newPage();
      const errors=[];
      page.on('pageerror', e=>errors.push(e.message));
      await page.goto(pathToFileURL(file).href, {waitUntil:'load'});
      await page.evaluate(async()=>{
        await document.fonts.ready;
        await Promise.all([...document.images].map(i=>i.decode().catch(()=>null)));
        await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      });
      await page.screenshot({path:resolve(output,dir.name,`reflow-${width}.png`),fullPage:true});
      if(width===1000) await page.pdf({path:resolve(output,dir.name,'reflow.pdf'),format:'A4',printBackground:true});
      const geometry=await page.evaluate(()=>({textCharacters:document.body.innerText.length,
        clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,
        images:[...document.images].map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight}))}));
      report.pages.push({key:dir.name,width,blocked,errors,...geometry});
      if(geometry.textCharacters===0) failures.push(`${dir.name}/${width}: empty body text`);
      if(geometry.images.some(i=>!i.loaded)) failures.push(`${dir.name}/${width}: an embedded image failed to decode`);
      if(errors.length) failures.push(`${dir.name}/${width}: browser page errors: ${errors.join('; ')}`);
      await context.close();
    }
  }
} finally {
  report.renderFailures=failures;
  await writeFile(resolve(output,'browser.json'),JSON.stringify(report,null,2));
  await browser.close();
}
if(report.pages.length!==8) throw new Error(`Expected eight render views; got ${report.pages.length}`);
if(failures.length) throw new Error(failures.join('\n'));
