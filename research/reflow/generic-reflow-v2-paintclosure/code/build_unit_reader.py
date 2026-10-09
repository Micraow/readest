"""Experimental native-unit reader. Semantics/interaction gates remain separate."""
import argparse,collections,html,json,pathlib,unicodedata,sys
PREVIOUS=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-inkownership/code';sys.path.insert(0,str(PREVIOUS))
from reader_spacing import separators
from ink_config import ReaderLayoutConfig

def build(folder,cfg=ReaderLayoutConfig()):
 folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());assets=json.loads((folder/'native-unit-assets-private.json').read_text());asset={a['id']:a for a in assets['results']};units={u['id']:u for u in plan['units']};replaced={};anchors={}
 for unit in units.values():
  if unit.get('former_units'):
   ids=set(unit['former_units']);minimum=min(g['source_index'] for g in unit['glyphs']);anchor=None
   for old in plan['items']:
    if old['kind']=='text':
     for line in old['lines']:
      for w in line['words']:
       if w['id'] in ids and any(g['source_index']==minimum for g in w['glyphs']):anchor=w['id']
    elif old['id'] in ids and any(g['source_index']==minimum for g in old['glyphs']):anchor=old['id']
   if anchor is None:raise RuntimeError('merged native interval has no emitted anchor')
   anchors[anchor]=unit['id']
   for old in ids:replaced[old]=unit['id']
 sequence=[];content=[];unknown_selection=0;spacing_trace=[]
 def emit(old,gap_em=0,space=False):
  nonlocal unknown_selection
  if old in replaced and old not in anchors:return ''
  uid=anchors.get(old,old)
  if uid not in asset:return ''
  a=asset[uid];u=units[uid]
  if a.get('empty'):return ''
  sequence.append(uid);image=f'<img src="{a["file"]}" alt="" draggable="false" style="width:100%;height:100%">'
  style=f'margin-right:{gap_em}em;width:{a["width_em"]}em;height:{a["height_em"]}em;vertical-align:{-a["descent_em"]}em;--bg:rgb({",".join(str(x) for x in a["background"])})'
  if u['kind']=='native_word':
   selectable=a['all_unicode_known'];text=html.escape(a['mapped_unicode'])+(' ' if space else '') if selectable else '';unknown_selection+=not selectable
   return f'<span class="token" data-unit="{uid}" style="{style}">{image}<span class="selection" aria-hidden="{str(not selectable).lower()}">{text}</span></span>'
  return f'<span class="token local" data-unit="{uid}" style="{style}" tabindex="0" role="button" aria-label="Enlarge local original object" onclick="showLocal(this)" onkeydown="if(event.key===\'Enter\')showLocal(this)">{image}</span>'
 for index,item in enumerate(plan['items']):
  for bg in plan['backgrounds']:
   if bg.get('range') and bg['range'][0]==index:content.append(f'<section class="background" data-background="{bg["id"]}" style="background:rgb({",".join(str(x) for x in bg["rgba"][:3])})">')
  if item['kind']=='text':
   emitted=[]
   for line in item['lines']:
    for w in line['words']:
     old=w['id']
     if old in replaced and old not in anchors:continue
     uid=anchors.get(old,old)
     if uid in asset and not asset[uid].get('empty'):emitted.append((old,uid))
   gaps=separators([uid for old,uid in emitted],units,asset,plan['glyphs'],assets['body_font'],assets['scale'],cfg)
   spacing_trace.extend(dict(paragraph=item['id'],**g) for g in gaps)
   byleft={g['left']:g for g in gaps};words=[]
   for old,uid in emitted:
    g=byleft.get(uid,{})
    words.append(emit(old,g.get('gap_em',0),g.get('semantic_space') in {'native_whitespace','inferred_line_join'}))
   if words:content.append(f'<p data-paragraph="{item["id"]}" class="{"auxiliary" if item["auxiliary"] else "prose"}">'+''.join(words)+'</p>')
  else:
   token=emit(item['id'])
   if token:content.append('<div class="object-row">'+token+'</div>')
  for bg in reversed(plan['backgrounds']):
   if bg.get('range') and bg['range'][1]==index+1:content.append('</section>')
 planned=[u for u in units if u in asset and not asset[u].get('empty')];dups=[u for u,n in collections.Counter(sequence).items() if n!=1];missing=sorted(set(planned)-set(sequence))
 if dups or missing:raise RuntimeError('reader unit emission failure: '+repr((dups,missing)))
 doc='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{box-sizing:border-box}body{margin:0;padding:12px;background:white;color:#111;font:20px/1.5 sans-serif}main{max-width:46em;margin:auto}.token{display:inline-block;position:relative;white-space:nowrap}.token img{display:block;pointer-events:none}.selection{position:absolute;inset:0;color:transparent;white-space:pre;line-height:1}.local{cursor:zoom-in}.object-row{margin:.7em 0;overflow:auto;max-width:100%}.object-row .token{max-width:100%;height:auto!important;vertical-align:baseline!important}.object-row .token img{height:auto!important}.background{padding:.5em;margin:.5em 0}p{margin:0 0 .7em}.auxiliary{font-size:.8em;color:#555}nav{position:sticky;top:0;background:white;z-index:2;font:14px sans-serif}dialog{max-width:94vw;max-height:90vh;overflow:auto}dialog img{display:block;max-width:none}dialog button{position:sticky;top:0}</style></head><body><nav><span>Research preview: source-light theme only; link mapping and selection geometry unverified.</span><button onclick="document.querySelector('main').style.fontSize='20px'">20 px</button><button onclick="document.querySelector('main').style.fontSize='28px'">28 px</button></nav><main>'''+''.join(content)+'''</main><dialog id="detail"><button onclick="this.parentElement.close()">Close</button><img alt="Enlarged original local object"></dialog><script>function showLocal(el){let d=document.getElementById('detail');let img=d.querySelector('img');img.src=el.querySelector('img').src;img.style.width=Math.max(el.getBoundingClientRect().width*2,320)+'px';d.showModal()}</script></body></html>'''
 (folder/'unit-reader.html').write_text(doc);result=dict(emitted_units=len(sequence),duplicate_units=dups,missing_units=missing,sequence=sequence,unknown_word_selection=unknown_selection,math_group_selection='not certified; omitted rather than inventing a semantic string',annotation_interaction='not yet mapped',layout_config=cfg.json(),spacing_trace=spacing_trace,source_support_mismatched_units=assets['unsupported_source_support_units'],reader_scope='native local assets and experimental inherited paragraph ordering; not complete-body readability acceptance')
 (folder/'unit-reader-audit-private.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();r=build(a.folder);print(json.dumps({k:v for k,v in r.items() if k not in {'sequence','spacing_trace'}}))
