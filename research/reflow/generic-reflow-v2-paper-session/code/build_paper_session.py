"""Private full-paper original-page assets, with explicit pinned local candidates.

The input names exact PDFs and optional already-built readers. It does not discover
files, infer reading order, run models, or admit arbitrary reflow capabilities.
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import shutil

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter


def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
def build(config, out):
    config=json.loads(pathlib.Path(config).read_text());out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
    manifest=dict(schema='readest-paper-session-v1',documents=[],pageCount=0);assets={};receipt=dict(original_page_mode=True,reflow_full_papers_accepted='0/2',cold='0/1 unchanged',browser_verified=False,papers=[])
    def asset(route,path,mime):
        if route in assets:raise ValueError('duplicate route')
        assets[route]=dict(path=str(path.relative_to(out)),sha256=sha(path),bytes=path.stat().st_size,mime=mime)
    for spec in config['documents']:
        did=spec['id'];need(re.fullmatch('[a-z][a-z0-9-]{0,31}',did),'invalid document identity')
        source=pathlib.Path(spec['pdf']);need(sha(source)==spec['sha256'],'original PDF hash mismatch')
        native=pdfium.PdfDocument(source);parsed=PdfReader(source);count=len(native);need(count==spec['page_count']==len(parsed.pages),'original PDF page count mismatch')
        folder=out/did;folder.mkdir();copy=folder/'original.pdf';shutil.copyfile(source,copy);pdfroute=f'/document/{did}/original.pdf';asset(pdfroute,copy,'application/pdf')
        doc=dict(id=did,title=spec['title'],pdf=dict(url=pdfroute,sha256=sha(copy)),pages=[])
        for index in range(count):
            page=native[index];width,height=page.get_size();rotation=page.get_rotation();bm=page.render(scale=2,draw_annots=False,may_draw_forms=False);image=bm.to_pil().convert('RGB');png=folder/f'page-{index:03}.png';image.save(png);bm.close();page.close()
            prefix=f'/document/{did}/page-{index:03}';asset(prefix+'.png',png,'image/png')
            row=dict(index=index,label=str(index+1),limitation='原页保真模式。该页尚未取得整页重排与复制验收；保留原有图、公式、脚注及版式，可缩放阅读。',source=dict(url=prefix+'.png',sha256=sha(png),width=image.width,height=image.height,pdfWidth=width,pdfHeight=height,rotation=rotation),reflow=None)
            candidate=next((r for r in spec.get('readers',[]) if r['page_index']==index),None)
            if candidate:
                r=pathlib.Path(candidate['folder']);html=r/'plan/tree-reader-selectable.html';need(sha(html)==candidate['html_sha256'],'reader HTML pin mismatch');mapping=json.loads((r/'text-map-private.json').read_text())
                stream=io.BytesIO();writer=PdfWriter();writer.add_page(parsed.pages[index]);writer.write(stream);page_sha=hashlib.sha256(stream.getvalue()).hexdigest()
                if page_sha!=mapping['summary']['source_sha256']:raise ValueError('reader is not bound to this exact original PDF page')
                dest=folder/f'page-{index:03}';dest.mkdir();target=dest/'reader.html';shutil.copyfile(html,target);asset(prefix+'/reader.html',target,'text/html; charset=utf-8')
                catalog=json.loads((r/'plan/tree-reader-assets-private.json').read_text())
                for item in catalog['results']:
                    name=item['file'];p=pathlib.PurePosixPath(name)
                    if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('units','flow-bundles') or p.suffix!='.png':raise ValueError('unsafe reader asset')
                    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/'plan'/name,target);asset(prefix+'/'+name,target,'image/png')
                row['reflow']=dict(url=prefix+'/reader.html',sha256=sha(html),extractedSourceSha256=page_sha,acceptance='partial-probes-only',limitation=candidate['limitation'])
            doc['pages'].append(row)
        native.close();need(sha(source)==spec['sha256'],'source changed during build');manifest['documents'].append(doc);manifest['pageCount']+=count;receipt['papers'].append(dict(id=did,source_sha256=sha(source),source_pages=count,rendered_original_pages=count,selectable_reflow_candidates=sum(p['reflow'] is not None for p in doc['pages'])))
    p=out/'session-manifest.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');asset('/session-manifest.json',p,'application/json; charset=utf-8')
    (out/'ASSET-ALLOWLIST.json').write_text(json.dumps(dict(schema=1,assets=assets),indent=2)+'\n');receipt['manifest_sha256']=sha(p);receipt['asset_count']=len(assets);receipt['private_materials']=True;(out/'BUILD-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('out');a=p.parse_args();print(json.dumps(build(a.config,a.out)))
