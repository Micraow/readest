"""Partition each independently rendered native text object's real alpha pixels.

A pixel with overlapping candidate owners is never guessed. It is reported as a
conflict; uncovered ink is retained separately. This establishes object-domain
conservation, not full-page visibility under occlusion or arbitrary compositing.
"""
from __future__ import annotations
import collections,ctypes,hashlib,importlib.util,json,math,pathlib,sys,time
from dataclasses import replace
import numpy as np
from components import label,find_objects
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_config import InkConfig

FROZEN=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2/code'
sys.path.insert(0,str(FROZEN))
import prototype as frozen
from config import Config as FrozenConfig

def active(handle,value):
    if not raw.FPDFPageObj_SetIsActive(handle,bool(value)):raise RuntimeError('native activation failure')

def global_pixel_box(box,W,H,config):
    s=config.render_scale;p=config.crop_padding_pixels
    return [max(0,math.floor(box[0]*s)-p),max(0,math.floor(box[1]*s)-p),min(math.ceil(W*s),math.ceil(box[2]*s)+p),min(math.ceil(H*s),math.ceil(box[3]*s)+p)]

def isolated_native_layer(page,handle,pixel_box,config):
    W,H=page.get_size();s=config.render_scale;x0,y0,x1,y1=pixel_box
    if (x1-x0)*(y1-y0)>config.maximum_bitmap_pixels:raise RuntimeError('native-layer pixel budget')
    active(handle,True)
    try:
        bitmap=page.render(scale=s,crop=(x0/s,H-y1/s,W-x1/s,y0/s),fill_color=(0,0,0,0),draw_annots=False,may_draw_forms=False)
        image=bitmap.to_pil().convert('RGBA').copy();bitmap.close()
    finally:active(handle,False)
    if image.size!=(x1-x0,y1-y0):raise RuntimeError('native-layer global-pixel alignment mismatch')
    return np.array(image)

def stable_native_layer(page,handle,box,config):
    """Require exact ink/color stability when the local viewport is enlarged.

    PDFium can change glyph rasterization at a tight device clip edge. This
    guard compares two native renders, not a heuristic pixel correction.
    """
    W,H=page.get_size();previous=None;calls=0;attempts=[]
    for padding in range(config.crop_padding_pixels,config.crop_padding_limit_pixels+1,config.crop_padding_step_pixels):
        cfg=replace(config,crop_padding_pixels=padding);pbox=global_pixel_box(box,W,H,cfg)
        rgba=isolated_native_layer(page,handle,pbox,cfg);calls+=1
        if previous is not None:
            old,oldbox=previous;l=oldbox[0]-pbox[0];t=oldbox[1]-pbox[1];h,w=old.shape[:2];inner=rgba[t:t+h,l:l+w]
            inside=np.zeros(rgba.shape[:2],bool);inside[t:t+h,l:l+w]=True
            outside_ink=int(np.count_nonzero((rgba[:,:,3]>0)&~inside));same=np.array_equal(inner,old)
            attempts.append(dict(padding_pixels=padding,common_rgba_equal=same,outside_prior_viewport_ink_pixels=outside_ink))
            if same and outside_ink==0:return rgba,pbox,dict(stable=True,native_renders=calls,attempts=attempts)
        previous=(rgba,pbox)
    return rgba,pbox,dict(stable=False,native_renders=calls,attempts=attempts)

def partition_alpha(rgba,pixel_box,glyphs,glyph_owners,config):
    """All pixels come from one native object; rectangle tests only propose owners.

    Exact partition is accepted only when every nonzero-alpha pixel has one
    owner. No alpha threshold drops faint ink. The input RGBA value is copied,
    never recolored, duplicated or re-rasterized by a replacement font.
    """
    H,W=rgba.shape[:2];ink=rgba[:,:,3]>0
    owners=sorted({glyph_owners[g['id']] for g in glyphs if g['id'] in glyph_owners})
    support=np.full((H,W),-1,np.int32);ambiguous=np.zeros((H,W),bool)
    if len(owners)==1:
        support[ink]=0
    else:
        x0,y0,_,_=pixel_box;s=config.render_scale;fringe=config.glyph_support_fringe_pixels
        for oi,owner in enumerate(owners):
            owner_support=np.zeros((H,W),bool)
            for g in glyphs:
                if glyph_owners.get(g['id'])!=owner:continue
                b=g['box'];l=max(0,math.floor(b[0]*s)-x0-fringe);t=max(0,math.floor(b[1]*s)-y0-fringe);r=min(W,math.ceil(b[2]*s)-x0+fringe);bt=min(H,math.ceil(b[3]*s)-y0+fringe)
                if l<r and t<bt:owner_support[t:bt,l:r]=True
            hits=owner_support&ink;ambiguous|=hits&(support>=0);support[hits&(support<0)]=oi
    initial_missing=ink&(support<0);initial_conflict=ink&ambiguous;component_decisions=[]
    if config.resolve_single_owner_components and len(owners)>1:
        confident=support.copy();confident[ambiguous]=-1
        structure=np.ones((3,3),np.uint8) if config.alpha_component_connectivity==8 else np.array([[0,1,0],[1,1,1],[0,1,0]],np.uint8)
        labels,count=label(ink,structure)
        for cid,sl in enumerate(find_objects(labels),1):
            if sl is None:continue
            mask=labels[sl]==cid;seeds=np.unique(confident[sl][mask]);seeds=seeds[seeds>=0]
            if len(seeds)==1:
                support[sl][mask]=seeds[0];ambiguous[sl][mask]=False
                component_decisions.append({'component':cid,'ink_pixels':int(mask.sum()),'unique_confident_owner':owners[int(seeds[0])],'accepted':True})
            elif np.any((initial_missing|initial_conflict)[sl][mask]):
                component_decisions.append({'component':cid,'ink_pixels':int(mask.sum()),'confident_owners':[owners[int(x)] for x in seeds],'accepted':False})
    missing=ink&(support<0);conflict=ink&ambiguous
    # Ambiguities and residuals stay in a retained quarantine layer, not guessed.
    support[conflict]=-1;quarantine=missing|conflict
    slices={};reconstructed=np.zeros_like(rgba);ownership=np.zeros((H,W),np.uint16)
    for oi,owner in enumerate(owners):
        mask=ink&(support==oi)
        out=np.zeros_like(rgba);out[mask]=rgba[mask];slices[owner]=out;reconstructed[mask]=out[mask];ownership[mask]+=1
    residual=np.zeros_like(rgba);residual[quarantine]=rgba[quarantine];reconstructed[quarantine]=residual[quarantine];ownership[quarantine]+=1
    # Transparent RGB bytes have no painted meaning; compare all RGBA bytes where alpha > 0.
    same=np.array_equal(reconstructed[ink],rgba[ink]);once=bool(np.all(ownership[ink]==1))
    result=dict(native_ink_pixels=int(ink.sum()),initial_ambiguous_ink_pixels=int(initial_conflict.sum()),initial_unassigned_ink_pixels=int(initial_missing.sum()),component_decisions=component_decisions,owner_count=len(owners),assigned_ink_pixels=int((ink&~quarantine).sum()),ambiguous_ink_pixels=int(conflict.sum()),unassigned_ink_pixels=int(missing.sum()),quarantined_ink_pixels=int(quarantine.sum()),conservation_with_quarantine=same and once,all_ink_uniquely_assigned=not bool(quarantine.any()),premultiplied_or_color_bytes_changed=False)
    return slices,residual,result

def ownership_units(items):
    units=[];owners={}
    for item in items:
        if item['kind']=='text':
            for line in item['lines']:
                for word in line['words']:
                    unit=dict(id=word['id'],kind='native_word',box=word['box'],glyphs=word['glyphs'],paragraph=item['id'],baseline=word['baseline'],text=word['text'])
                    units.append(unit)
                    for g in unit['glyphs']:owners[g['id']]=unit['id']
        else:
            unit=dict(id=item['id'],kind=item['kind'],box=item['box'],glyphs=item['glyphs'],objects=item.get('objects',[]));units.append(unit)
            for g in unit['glyphs']:owners[g['id']]=unit['id']
    return units,owners

def extract_partitioned_layers(pdfpath,out,config=InkConfig(),page_index=0):
    start=time.perf_counter();out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    doc=pdfium.PdfDocument(pdfpath);page=doc[page_index];W,H=page.get_size();trace=[]
    objects,handles,glyphs,body,limits=frozen.native_inventory(page,FrozenConfig(),trace)
    items,backgrounds,expected,old_failures=frozen.plan(objects,glyphs,W,H,body,FrozenConfig(),trace)
    units,owners=ownership_units(items);by_obj=collections.defaultdict(list)
    for g in glyphs:
        if not g['char'].isspace() and frozen.area(g['box'])>0:by_obj[g['object_id']].append(g)
    states={}
    for oid,h in handles.items():
        state=ctypes.c_int()
        if not raw.FPDFPageObj_GetIsActive(h,state):raise RuntimeError('cannot read activation state')
        states[oid]=bool(state.value);active(h,False)
    records=[];patches=collections.defaultdict(list);renders=0
    try:
        for obj in objects:
            if obj['type']!=raw.FPDF_PAGEOBJ_TEXT:continue
            pbox=global_pixel_box(obj['box'],W,H,config)
            if pbox[2]<=pbox[0] or pbox[3]<=pbox[1]:continue
            rgba,pbox,stability=stable_native_layer(page,handles[obj['id']],obj['box'],config);renders+=stability['native_renders']
            parts,residual,stats=partition_alpha(rgba,pbox,by_obj[obj['id']],owners,config)
            record=dict(object_id=obj['id'],seq=obj['seq'],pixel_box=pbox,crop_stability=stability,**stats);records.append(record)
            for owner,pixels in parts.items():
                if not np.any(pixels[:,:,3]):continue
                name=f'{obj["id"]}-{owner}.png';Image.fromarray(pixels,'RGBA').save(out/name);patches[owner].append(dict(file=name,pixel_box=pbox,paint_seq=obj['seq'],native_object=obj['id']))
            if stats['quarantined_ink_pixels']:
                Image.fromarray(residual,'RGBA').save(out/f'{obj["id"]}-UNRESOLVED.png')
    finally:
        for oid,h in handles.items():active(h,states[oid])
    problematic=[r for r in records if not r['all_ink_uniquely_assigned'] or not r['crop_stability']['stable']]
    summary=dict(schema=1,scope='independently rendered text-object alpha domain; not complete page visibility or reading-order proof',input_sha256=hashlib.sha256(pathlib.Path(pdfpath).read_bytes()).hexdigest(),page_index=page_index,pdfium=str(pdfium.PDFIUM_INFO),config=config.json(),text_objects=len(records),native_renders=renders,body_font=body,unit_count=len(units),native_ink_pixels=sum(r['native_ink_pixels'] for r in records),ambiguous_ink_pixels=sum(r['ambiguous_ink_pixels'] for r in records),unassigned_ink_pixels=sum(r['unassigned_ink_pixels'] for r in records),all_object_pixels_conserved_with_quarantine=all(r['conservation_with_quarantine'] for r in records),all_object_pixels_uniquely_assigned=all(r['all_ink_uniquely_assigned'] for r in records),all_crops_stable=all(r['crop_stability']['stable'] for r in records),problem_objects=[r['object_id'] for r in problematic],shared_native_objects=sum(r['owner_count']>1 for r in records),old_planner_failures=old_failures,limitations=limits,processing_seconds_before_evidence_write=time.perf_counter()-start)
    (out/'ownership-summary.json').write_text(json.dumps(summary,indent=2));(out/'ownership-records.json').write_text(json.dumps(records,indent=2));(out/'plan-private.json').write_text(json.dumps(dict(units=units,patches=patches,items=items,backgrounds=backgrounds,objects=objects,glyphs=glyphs,page_size=[W,H]),ensure_ascii=False,indent=2));(out/'trace-private.json').write_text(json.dumps(trace,indent=2))
    page.close();doc.close();return summary

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('output');args=ap.parse_args();print(json.dumps(extract_partitioned_layers(args.pdf,args.output)))
