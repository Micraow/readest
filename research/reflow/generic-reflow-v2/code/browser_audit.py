"""Real Chromium checks. Results are structural, not semantic certification."""
import argparse, collections, json, pathlib, time
from playwright.sync_api import sync_playwright

def audit(folder,widths=(390,),sizes=(20,28),chromium=None):
    folder=pathlib.Path(folder).resolve();plan=json.loads((folder/'plan-private.json').read_text());expected=plan['expected_order'];report=[];started=time.perf_counter()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=chromium,headless=True,chromium_sandbox=True)
        for width in widths:
            page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
            page.goto((folder/'reader.html').as_uri());page.wait_for_load_state('networkidle')
            for size in sizes:
                page.locator('nav button').filter(has_text=f'{size} px').click()
                sample=page.evaluate('''() => {const m=document.querySelector('main');let all=[];for(const e of m.querySelectorAll('[data-atoms]'))all.push(...e.dataset.atoms.split(' ').filter(Boolean));let selection=getSelection();let range=document.createRange();range.selectNodeContents(m);selection.removeAllRanges();selection.addRange(range);let selected=selection.toString();selection.removeAllRanges();return {emitted:all, selected_text:selected, scrollWidth:document.documentElement.scrollWidth, clientWidth:document.documentElement.clientWidth, fontSize:getComputedStyle(m).fontSize, backgrounds:[...m.querySelectorAll('[data-atom]')].map(x=>({id:x.dataset.atom,width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height})), bodyTextUnits:[...m.querySelectorAll('p.prose')].map(x=>({id:x.dataset.item,width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height,text:x.textContent}))}}''')
                sample['width']=width;sample['size']=size;sample['sequence_matches_plan']=sample['emitted']==expected;sample['ownership_matches_plan']=collections.Counter(sample['emitted'])==collections.Counter(expected)
                # Keep the copied source text and detailed DOM measurements private.
                page.screenshot(path=str(folder/f'browser-{width}-{size}.png'),full_page=True)
                report.append(sample)
            local=page.locator('figure.local-object.island').last
            if local.count():
                before=local.locator('img').bounding_box();local.locator('.object-control').click();after=local.locator('img').bounding_box();zoom={'before_width':before['width'],'after_width':after['width'],'class_toggled':'zoomed' in local.get_attribute('class'),'scroll_width':local.evaluate('(e)=>e.scrollWidth'),'viewport_width':local.evaluate('(e)=>e.clientWidth')}
            else:zoom=None
            page.close()
        browser.close()
    result={'engine':'Playwright Chromium with sandbox enabled','elapsed_seconds':time.perf_counter()-started,'settings':report,'local_zoom':zoom,'semantic_order_review':'not automatic','unicode_semantic_review':'not automatic'}
    (folder/'browser-private.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'elapsed_seconds':result['elapsed_seconds'],'settings':[{'width':r['width'],'size':r['size'],'sequence_matches_plan':r['sequence_matches_plan'],'page_overflow':r['scrollWidth']>r['clientWidth'],'selected_chars':len(r['selected_text']),'backgrounds':r['backgrounds']} for r in report],'zoom':zoom}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--all-widths',action='store_true');p.add_argument('--chromium');a=p.parse_args();audit(a.folder,(320,390,430) if a.all_widths else (390,),chromium=a.chromium)
