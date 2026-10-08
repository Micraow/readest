"""Post-run descriptive geometry. These metrics do NOT score scientific correctness."""
import json, math, os, pathlib, resource
import numpy as np
from PIL import Image

B=pathlib.Path(__file__).resolve().parent
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
rows=[]
old=json.loads((B.parent/'native-structure-v1/evidence/coverage-summary.json').read_text())
for run in json.loads((B/'RUN-RESULTS.json').read_text()):
    key=run['key'];m=json.loads((B/'output'/(key+'.json')).read_text());maps=m['maps']
    im=np.asarray(Image.open(B/'evidence'/(key+'-source.png')))
    ink=np.any(im<255,axis=2); h,w=ink.shape;count=np.zeros((h,w),dtype=np.uint16)
    bounds=[];out_of_bounds=0
    for mp in maps:
        x,y,bw,bh=mp['source_xywh'];x0=max(0,math.floor(x+1e-6));y0=max(0,math.floor(y+1e-6));x1=min(w,math.ceil(x+bw-1e-6));y1=min(h,math.ceil(y+bh-1e-6))
        count[y0:y1,x0:x1]+=1;bounds.append((x,y,x+bw,y+bh))
        tx,ty,tw,th=mp['target_xywh']
        if tx<0 or ty<0 or tx+tw>m['output_size'][0]+1 or ty+th>m['output_size'][1]+1:out_of_bounds+=1
    data=json.loads((B/'inputs'/(key+'-rawdict.json')).read_text())
    chars=[];line_desc=[]
    for block in data['blocks']:
      for line in block.get('lines',[]):
        lc=[];targets=[]
        for span in line.get('spans',[]):
          for c in span.get('chars',[]):
            if not c['c'].strip():continue
            x0,y0,x1,y1=c['bbox'];cx=(x0+x1)*2;cy=(y0+y1)*2
            ids=[i for i,(a,b,d,e) in enumerate(bounds) if a<=cx<d and b<=cy<e]
            item={'bbox':c['bbox'],'center_mapped':bool(ids),'map_count':len(ids)}
            lc.append(item);chars.append(item)
            if len(ids)==1:
                mp=maps[ids[0]];sx,sy,sw,sh=mp['source_xywh'];tx,ty,tw,th=mp['target_xywh']
                targets.append(ty+(cy-sy)/sh*th)
        # This only indicates coordinate rearrangement; superscripts or bad splitting also trigger it.
        if lc:
            line_desc.append({'native_nonspace_chars':len(lc),'unique_map_target_y_span':max(targets)-min(targets) if targets else None,'mapped_chars':sum(x['center_mapped'] for x in lc)})
    total=int(ink.sum());covered=int((ink&(count>0)).sum());overlap=int((ink&(count>1)).sum())
    r={'key':key,'measurement_type':'Geometric source representation only, not content fidelity or valid reflow',
       'all_source_nonwhite_pixels':total,'source_nonwhite_pixels_in_map_union':covered,'map_union_nonwhite_fraction':covered/total,
       'source_nonwhite_pixels_in_multiple_maps':overlap,'native_nonspace_char_count':len(chars),'native_char_centers_in_map_union':sum(x['center_mapped'] for x in chars),
       'native_char_centers_in_multiple_maps':sum(x['map_count']>1 for x in chars),'target_maps_outside_output_bounds':out_of_bounds,
       'source_line_descriptors':line_desc,'same_body_regions_as_native_structure_v1':[]}
    prior=next((x for x in old if x['key']==key),None)
    if prior:
      for reg in prior['regions']:
        x0,y0,x1,y1=[int(v*4) for v in reg['coarseBbox']]
        ii=ink[y0:y1,x0:x1];cc=count[y0:y1,x0:x1]
        r['same_body_regions_as_native_structure_v1'].append({'id':reg['id'],'old_reference_nonwhite_count':reg['allBodyNonwhitePixels'],'current_nonwhite_count':int(ii.sum()),'source_nonwhite_in_map_union':int((ii&(cc>0)).sum()),'warning':'Map coverage cannot be compared with the prior accepted-reflow coverage as if they were the same metric.'})
    missing=ink&(count==0)
    overlay=im.copy();overlay[missing]=[255,0,0];Image.fromarray(overlay).save(B/'evidence'/(key+'-unmapped-ink-red.png'))
    rows.append(r)
    print(key,covered,total,covered/total,'overlap',overlap,'chars',r['native_char_centers_in_map_union'],len(chars),flush=True)
(B/'GEOMETRY-MEASUREMENTS.json').write_text(json.dumps(rows,indent=2))
