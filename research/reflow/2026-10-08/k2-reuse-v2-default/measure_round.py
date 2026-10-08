import collections,json,math,os,pathlib,resource
import numpy as np
from PIL import Image
B=pathlib.Path(__file__).resolve().parent;V1=B.parent/'k2-reuse-v1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
def font_scale_descriptors(raw,maps):
    chars=[]
    for block in raw['blocks']:
      for line in block.get('lines',[]):
       for span in line.get('spans',[]):
        for c in span.get('chars',[]):
         if c['c'].strip():chars.append((round(span['size'],1),c['bbox']))
    modal=collections.Counter(s for s,box in chars).most_common(1)[0][0]
    sizes=[];ambiguous=0
    for size,(x0,y0,x1,y1) in chars:
      if size!=modal:continue
      cx=(x0+x1)*2;cy=(y0+y1)*2
      matched=[]
      for mp in maps:
        x,y,w,h=mp['source_xywh']
        if x<=cx<x+w and y<=cy<y+h:matched.append(mp)
      if len(matched)==1:
        mp=matched[0];sizes.append(size*4*mp['target_xywh'][3]/mp['source_xywh'][3])
      else:ambiguous+=1
    return {'source_modal_em_points':modal,'native_chars_at_source_modal_em':sum(s==modal for s,b in chars),'uniquely_mapped_chars':len(sizes),'ambiguous_or_unmapped_centers':ambiguous,'estimated_output_em_px_quantiles':dict(zip(['min','p10','median','p90','max'],[float(x) for x in np.quantile(sizes,[0,.1,.5,.9,1])])),'method':'Same native characters at the source-page modal font size, weighted by nonspace character count. Target em is derived from the rectangle vertical scale, not OCR or measured glyph-height. This describes scaling uniformity, not scientific correctness.'}
rows=[]
for run in json.loads((B/'RUN-RESULTS.json').read_text()):
    m=json.loads((B/'output'/(run['key']+'.json')).read_text());maps=m['maps']
    im=np.asarray(Image.open(run['source_png']));ink=np.any(im<255,axis=2);h,w=ink.shape
    count=np.zeros((h,w),np.uint16)
    for mp in maps:
      x,y,bw,bh=mp['source_xywh'];a=max(0,math.floor(x+1e-6));b=max(0,math.floor(y+1e-6));c=min(w,math.ceil(x+bw-1e-6));d=min(h,math.ceil(y+bh-1e-6));count[b:d,a:c]+=1
    raw=json.loads(pathlib.Path(run['rawdict']).read_text())
    r={'key':run['key'],'partition':run['partition'],'all_source_nonwhite_pixels':int(ink.sum()),'source_nonwhite_in_map_union':int((ink&(count>0)).sum()),'source_nonwhite_in_multiple_maps':int((ink&(count>1)).sum()),'geometry_is_not_fidelity':True,'font_scaling':font_scale_descriptors(raw,maps)}
    if run['partition']=='paired_regression':
      oldkey=run['key'].removeprefix('paired-');old=json.loads((V1/'output'/(oldkey+'.json')).read_text());r['prior_word_spacing_minus_1_font_scaling']=font_scale_descriptors(raw,old['maps'])
    rows.append(r);print(run['key'],r['source_nonwhite_in_map_union'],r['all_source_nonwhite_pixels'],r['font_scaling']['estimated_output_em_px_quantiles'],flush=True)
(B/'GEOMETRY-MEASUREMENTS.json').write_text(json.dumps(rows,indent=2))
