"""Rewire existing native assets; never slice an image or subdivide a unit."""
import argparse,base64,collections,copy,io,json,pathlib,sys,time
import numpy as np
from PIL import Image
from relations import FormulaRelationConfig,relation,region_members,unique_relations
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-localgeometry/code'))
from geometry_evidence import formula_evidence

def native_token(uid,source,target,body,scale):
    a=source[uid];b=target[uid]
    if b['changed_source_support_pixels'] or b['max_channel_delta']:raise RuntimeError('unverified target native asset')
    return {'id':'formula-child-'+uid,'kind':'native_image','members':[uid],'source_pixel_box':a['asset_pixel_box'],'width_em':a['width_em'],'height_em':a['height_em'],'vertical_em':-a['descent_em'],'gap_em':0.,'asset_scale':b['grid'],'asset_pixel_box':b['asset_pixel_box'],'data_uri':'data:image/png;base64,'+base64.b64encode(pathlib.Path(b['absolute_file']).read_bytes()).decode()}

def verify_unbundle(old,children):
    if old['kind']!='native_image' or len({c['asset_scale'] for c in children})!=1 or children[0]['asset_scale']!=old['asset_scale']:raise RuntimeError('unbundle needs identical native image grids')
    expected=np.array(Image.open(io.BytesIO(base64.b64decode(old['data_uri'].split(',')[1]))).convert('RGBA'));actual=np.zeros_like(expected);actual[:,:,:3]=expected[:,:,:3];coverage=np.zeros(expected.shape[:2],np.uint8)
    for child in children:
        im=np.array(Image.open(io.BytesIO(base64.b64decode(child['data_uri'].split(',')[1]))).convert('RGBA'));x=child['asset_pixel_box'][0]-old['asset_pixel_box'][0];y=child['asset_pixel_box'][1]-old['asset_pixel_box'][1];h,w=im.shape[:2]
        if x<0 or y<0 or x+w>expected.shape[1] or y+h>expected.shape[0]:raise RuntimeError('child outside former composite')
        mask=im[:,:,3]>0;counts=coverage[y:y+h,x:x+w];view=actual[y:y+h,x:x+w]
        if np.any(im[:,:,3][mask]!=255) or np.any(counts[mask]):raise RuntimeError('fractional or overlapping independent child support')
        view[mask]=im[mask];counts[mask]+=1
    diff=int(np.count_nonzero(np.any(actual!=expected,axis=2)))
    if diff:raise RuntimeError('children do not exactly reproduce old target composite')
    return {'target_grid_rgba_different_pixels':diff,'overlapping_support_pixels':0,'source_composite_dimensions':list(expected.shape[:2]),'proof_scope':'same-coordinate existing native assets only'}

def build(data,plan,order,source,target):
    start=time.perf_counter();data=copy.deepcopy(data);source={a['id']:a for a in source['results']};target=target['assets'];units={u['id']:u for u in plan['units']};body=data['body_font_pdf'];scale=data['source_capture_scale'];regions=region_members(order['tree'],body);cores=[u for u in plan['units'] if u.get('prior_source',{}).get('label')=='formula'];records=[]
    for core in cores:
        proof=formula_evidence([core],plan['objects'],body)['pass_native_structure']
        for u in plan['units']:
            if u['id']==core['id'] or u['kind']!='native_word':continue
            record=relation(core,u,plan['units'],plan['glyphs'],regions,plan['page_size'],body,proof);records.append(record)
    unique_relations(records);before=collections.Counter(uid for b in data['blocks'] for t in b['tokens'] for uid in t['members']);accepted=[];rebuild=[];skip=set()
    for i,block in enumerate(data['blocks']):
        if i in skip:continue
        candidates=[r for r in records if r['accepted'] and any(r['core'] in t['members'] for t in block['tokens'])]
        if block['kind']!='object' or len(block['tokens'])!=1 or len(candidates)!=1:rebuild.append(block);continue
        r=candidates[0];old=block['tokens'][0];core,label=r['core'],r['label'];proof={};labeltoken=None
        if set(old['members'])=={core,label}:
            if core not in target or label not in target:r.update(accepted=False,reason='child_target_resource_unavailable');rebuild.append(block);continue
            coretoken=native_token(core,source,target,body,scale);labeltoken=native_token(label,source,target,body,scale);proof=verify_unbundle(old,[coretoken,labeltoken])
        elif old['members']==[core] and i+1<len(data['blocks']):
            nxt=data['blocks'][i+1]
            if nxt['kind']=='paragraph' and len(nxt['tokens'])==1 and nxt['tokens'][0]['members']==[label]:coretoken=old;labeltoken=nxt['tokens'][0];skip.add(i+1);proof={'already_independent_resources':True}
        if labeltoken is None:r.update(accepted=False,reason='reader_block_structure_not_independent');rebuild.append(block);continue
        coretoken=copy.deepcopy(coretoken);labeltoken=copy.deepcopy(labeltoken);coretoken['formula_role']='core';labeltoken['formula_role']='label';labeltoken['gap_em']=0
        rebuild.append({'kind':'formula','tokens':[coretoken,labeltoken],'source_interval':r['source_interval'],'label_anchor_em':(r['label_baseline']-coretoken['source_pixel_box'][1]/scale)/body,'hierarchy_provenance':'independent native units, geometry-closed weak label candidate'});accepted.append(r|proof)
    data['blocks']=rebuild;after=collections.Counter(uid for b in data['blocks'] for t in b['tokens'] for uid in t['members'])
    if before!=after or any(v!=1 for v in after.values()):raise RuntimeError('native unit multiset changed or was not unique')
    data['formula_relation_config']=FormulaRelationConfig().json();data['formula_hierarchy_native_unit_multiset_unchanged']=True;trace={'candidate_relations':records,'applied':accepted,'native_unit_count':len(after),'native_unit_multiset_unchanged':True,'glyphs_sliced':False,'selection_semantics_certified':False,'whole_source_paint_ownership_proven':False,'elapsed_seconds':time.perf_counter()-start};return data,trace
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('plan');p.add_argument('order');p.add_argument('source_assets');p.add_argument('target_assets');p.add_argument('out');a=p.parse_args();data,trace=build(*[json.loads(pathlib.Path(x).read_text()) for x in [a.reader,a.plan,a.order,a.source_assets,a.target_assets]]);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);(out/'reader-data-private.json').write_text(json.dumps(data,separators=(',',':')));(out/'formula-trace-private.json').write_text(json.dumps(trace,indent=2));print(json.dumps({'formulas_restructured':len(trace['applied']),'native_unit_count':trace['native_unit_count'],'native_unit_multiset_unchanged':True,'payload_bytes':(out/'reader-data-private.json').stat().st_size,'seconds':trace['elapsed_seconds']}))
