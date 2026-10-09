"""Evaluation-only glyph/region inventory, not an input to any reflow arm."""
import pathlib,json,collections,fitz
from PIL import Image,ImageDraw
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';ref=json.loads((B/'QA-REFERENCE.json').read_text());out=[]
for item in ref['pages']:
 m=item['metadata'];key=m['key'];page=fitz.open(B/'inputs'/(key+'.pdf'))[0];glyphs=[]
 for bi,b in enumerate(page.get_text('rawdict')['blocks']):
  for li,line in enumerate(b.get('lines',[])):
   for si,s in enumerate(line['spans']):
    for ci,ch in enumerate(s['chars']):
     if ch['c'].strip():glyphs.append({'id':f'{bi}:{li}:{si}:{ci}','char':ch['c'],'box':ch['bbox'],'size':s['size'],'origin':ch['origin']})
 im=Image.open(B/'inputs'/(key+'-native.png')).convert('RGB');im.thumbnail((1000,1400));draw=ImageDraw.Draw(im);regions=[]
 for j,a in enumerate(sorted(item['annotations'],key=lambda a:(a['bbox'][1],a['bbox'][0]))):
  x,y,w,h=a['bbox'];pb=[x/m['width']*page.rect.width,y/m['height']*page.rect.height,(x+w)/m['width']*page.rect.width,(y+h)/m['height']*page.rect.height];ids=[g for g in glyphs if pb[0]<=(g['box'][0]+g['box'][2])/2<=pb[2] and pb[1]<=(g['box'][1]+g['box'][3])/2<=pb[3]];role=ref['categories'][str(a['category_id'])];rid=key+'-R'+str(j+1);font=collections.Counter(round(g['size'],2) for g in ids if g['char'].isalpha()).most_common(1);regions.append({'id':rid,'official_role':role,'source_box':pb,'native_char_count':len(ids),'native_ids':[g['id'] for g in ids],'source_text':''.join(g['char'] for g in ids),'body_font':font[0][0] if font else None});rb=[pb[0]/page.rect.width*im.width,pb[1]/page.rect.height*im.height,pb[2]/page.rect.width*im.width,pb[3]/page.rect.height*im.height];color='blue' if role in ['Text','List-item'] else 'red';draw.rectangle(rb,outline=color,width=1);draw.text((rb[0],max(0,rb[1]-11)),f'R{j+1}:'+role,fill=color)
 im.save(B/'evidence'/(key+'-qa-source.png'));out.append({'key':key,'regions':regions,'glyphs':glyphs})
(B/'QA-INVENTORY.json').write_text(json.dumps({'note':'Official regions may be fragments rather than paragraphs. Glyph positions are geometric evidence, not semantic truth. QA source uses the actual native PDF raster, not official square PNG.','pages':out},ensure_ascii=False,indent=2));print(sum(r['official_role'] in ['Text','List-item'] for p in out for r in p['regions']))
