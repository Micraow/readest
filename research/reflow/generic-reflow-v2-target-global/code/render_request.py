"""Rerasterize requested native units at target density; no old-mask resize."""
import argparse,collections,ctypes,hashlib,json,math,pathlib,sys,time
from dataclasses import replace
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'generic-reflow-v2-inkownership/code'))
from ink_ownership import active,partition_alpha,global_pixel_box
from ink_config import InkConfig
sys.path.insert(0,str(ROOT/'generic-reflow-v2-localcanvas/code'))
from render_native_localcanvas import render_units
sys.path.insert(0,str(HERE))
from target_grid import TargetConfig,choose_grid,cache_key,renderer_identity,ownership_proof
from device_alpha import DeviceAlphaCanvas,DeviceAlphaConfig

def run(pdf,folder,out,unit_ids,font_css=28,dpr=2,enlargement=1.,cfg=TargetConfig()):
    start=time.perf_counter();cpu=time.process_time();pdf=pathlib.Path(pdf);folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    source_sha=hashlib.sha256(pdf.read_bytes()).hexdigest();plan_bytes=(folder/'plan-private.json').read_bytes();plan_sha=hashlib.sha256(plan_bytes+(folder/'ownership-summary.json').read_bytes()).hexdigest();plan=json.loads(plan_bytes);base=json.loads((folder/'ownership-summary.json').read_text());body=base['body_font'];selection=choose_grid(font_css,dpr,body,enlargement,cfg);scale=selection['grid'];W,H=plan['page_size']
    if source_sha!=base['input_sha256']:raise ValueError('source PDF does not match native plan')
    if math.ceil(W*scale)*math.ceil(H*scale)>cfg.maximum_reference_pixels:raise ValueError('reference bitmap exceeds pixel budget')
    if not unit_ids or len(unit_ids)>cfg.maximum_requested_units or len(set(unit_ids))!=len(unit_ids):raise ValueError('invalid requested unit count')
    units={u['id']:u for u in plan['units']};selected=[units[u] for u in unit_ids];owners={g['id']:u['id'] for u in plan['units'] for g in u['glyphs']};objmap={o['id']:o for o in plan['objects']};target_objects={g['object_id'] for u in selected for g in u['glyphs'] if not g['char'].isspace()};by_obj=collections.defaultdict(list)
    for g in plan['glyphs']:
        if g['object_id'] in target_objects and g['id'] in owners and not g['char'].isspace() and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1]:by_obj[g['object_id']].append(g)
    inkcfg=replace(InkConfig(**base['config']),render_scale=scale,maximum_bitmap_pixels=cfg.maximum_object_crop_pixels)
    doc=pdfium.PdfDocument(pdf);page=doc[base['page_index']];handles={f'p{i}':h for i,h in enumerate(page.get_objects(max_depth=1))};states={};records=[];patches=collections.defaultdict(list);renders=0;failure=None
    alpha_canvas=DeviceAlphaCanvas(page,scale,DeviceAlphaConfig(maximum_reference_pixels=cfg.maximum_reference_pixels))
    for oid,h in handles.items():
        s=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(h,s);states[oid]=bool(s.value);active(h,False)
    try:
        object_owners=ownership_proof(plan['units'],plan['glyphs'],target_objects);closed=set()
        # Exact object-membership closure is a precondition, never a model role.
        # The full native set creates its complete alpha once; it is not a sum
        # of independently rounded RGBA layers or a bbox crop of the full page.
        for unit in selected:
            ids=sorted([oid for oid in target_objects if object_owners.get(oid)=={unit['id']}],key=lambda x:int(x[1:]))
            if not ids:continue
            if any(not states[oid] for oid in ids):raise RuntimeError('inactive object in closed native set')
            pbox=global_pixel_box(unit['box'],W,H,replace(inkcfg,crop_padding_pixels=inkcfg.crop_padding_limit_pixels))
            if (pbox[2]-pbox[0])*(pbox[3]-pbox[1])>cfg.maximum_unit_mask_pixels:raise ValueError('unit mask exceeds pixel budget')
            rgba,outside=alpha_canvas.read([handles[oid] for oid in ids],pbox,cfg.maximum_unit_mask_pixels);renders+=1
            records.append(dict(scope='closed_native_text_set',owner=unit['id'],object_ids=ids,full_native_composite_alpha=True,original_native_paint_order=True,full_object_ink_outside_local_viewport=outside,ink_pixels=int(np.count_nonzero(rgba[:,:,3]))))
            if outside:failure='closed_native_text_set_outside_fixed_unit';break
            name='closed-text-'+unit['id']+'.png';Image.fromarray(rgba,'RGBA').save(out/name)
            shared_in_unit=any(object_owners.get(g['object_id'],set())-{unit['id']} for g in unit['glyphs'])
            needs_action_masks=bool(unit.get('objects') and shared_in_unit)
            # For action replay, every closed text operation may use the common
            # owner-domain mask, while only that operation is painted once.
            # In one native batch only one union mask is needed; the remaining
            # references enable original objects without duplicating support.
            blank='enable-only-transparent.png'
            if not (out/blank).exists():Image.fromarray(np.zeros((1,1,4),np.uint8),'RGBA').save(out/blank)
            for i,oid in enumerate(ids):
                covered=needs_action_masks or i==0
                patches[unit['id']].append(dict(file=name if covered else blank,pixel_box=pbox if covered else [0,0,1,1],paint_seq=objmap[oid]['seq'],native_object=oid,mask_scope='closed_text_set_owner_domain' if covered else 'native_object_activation_only',closed_set_owner=unit['id']))
            closed.update(ids)
        if failure:target_objects=set()
        for oid in sorted(target_objects-closed,key=lambda o:int(o[1:])):
            if not states[oid]:raise RuntimeError('requested glyph has inactive source object')
            pbox=global_pixel_box(objmap[oid]['box'],W,H,replace(inkcfg,crop_padding_pixels=inkcfg.crop_padding_pixels+inkcfg.crop_padding_step_pixels))
            reference,outside=alpha_canvas.read([handles[oid]],pbox,cfg.maximum_object_crop_pixels);renders+=1
            stability=dict(stable=outside==0,native_renders=1,attempts=[],local_crop_stability_tested=False,full_object_alpha_compared=True,full_object_ink_outside_local_viewport=outside,mask_source='one complete global native alpha; fixed window outside-ink proof; no local raster')
            if outside:failure='full_native_object_ink_outside_target_viewport';records.append(dict(object_id=oid,crop_stability=stability));break
            parts,residual,stats=partition_alpha(reference,pbox,by_obj[oid],owners,inkcfg);records.append(dict(object_id=oid,crop_stability=stability,**stats))
            if not stability['stable'] or not stats['all_ink_uniquely_assigned']:failure='new_grid_native_ownership_or_clip_ambiguity';break
            for owner,pixels in parts.items():
                if not np.any(pixels[:,:,3]):continue
                name=oid+'-'+owner+'.png';Image.fromarray(pixels,'RGBA').save(out/name);patches[owner].append(dict(file=name,pixel_box=pbox,paint_seq=objmap[oid]['seq'],native_object=oid))
    finally:
        for oid,h in handles.items():active(h,states[oid])
        alpha_trace=alpha_canvas.trace();alpha_canvas.close();page.close();doc.close()
    summary=dict(schema=2,input_sha256=source_sha,page_index=base['page_index'],pdfium=str(pdfium.PDFIUM_INFO),config=inkcfg.json(),body_font=body,scope='requested-unit target-grid mask regeneration only; no whole-page counts inherited',requested_unit_ids=unit_ids,native_mask_renders=renders,source_preprocessing_summary_sha256=hashlib.sha256((folder/'ownership-summary.json').read_bytes()).hexdigest(),whole_page_target_grid_verified=False);(out/'ownership-summary.json').write_text(json.dumps(summary,indent=2));(out/'ownership-records.json').write_text(json.dumps(records,indent=2));(out/'plan-private.json').write_text(json.dumps({**plan,'units':selected,'patches':patches},ensure_ascii=False,indent=2))
    assets=None
    if not failure:
        assets=render_units(pdf,out)
        if assets['unsupported_source_support_units']:failure='new_grid_source_rgb_mismatch'
        # Layout anchors derive from immutable PDF geometry, not scale-dependent
        # antialias pixel extents. A UI must draw the raster at this offset.
        for asset in assets['results']:
            if asset.get('empty'):continue
            logical=units[asset['id']]['box'];ink=[x/scale for x in asset['asset_pixel_box']];asset.update(logical_box_pdf=logical,ink_box_pdf=ink,drawing_offset_pdf=[ink[0]-logical[0],ink[1]-logical[1]],logical_size_pdf=[logical[2]-logical[0],logical[3]-logical[1]],geometry_policy='fixed native layout box plus native-raster origin offset; never use pixel-crop dimensions as layout advance')
        (out/'native-unit-assets-private.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2))
    result=dict(global_alpha_canvas=alpha_trace,config=cfg.json(),request=dict(unit_ids=unit_ids,font_css_px=font_css,dpr=dpr,enlargement=enlargement),grid_selection=selection,source_sha256=source_sha,plan_policy_sha256=plan_sha,cache_key=cache_key(source_sha,plan_sha,unit_ids,scale,renderer_identity(str(pdfium.PDFIUM_INFO)),'source_flat_backdrop'),cache_hit=False,native_mask_renders=renders,native_asset_renders=assets['native_renders'] if assets else 0,wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,failure=failure,target_grid_accepted=failure is None,original_low_resolution_mask_reused=False,source_units_expanded=False,semantic_selection_certified=False,interactive_zoom_tested=False)
    (out/'target-grid-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');p.add_argument('out');p.add_argument('--unit',action='append',required=True);p.add_argument('--font-size',type=float,default=28);p.add_argument('--dpr',type=float,default=2);p.add_argument('--enlargement',type=float,default=1);a=p.parse_args();run(a.pdf,a.folder,a.out,a.unit,a.font_size,a.dpr,a.enlargement)
