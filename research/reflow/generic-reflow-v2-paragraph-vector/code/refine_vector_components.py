"""Repartition old all-vector composites into bounded source-geometric components.

A previous composite is a proposal, not an indivisible truth. Whole existing
native-word primitives are retained; no glyph is sliced or reconstructed as text.
"""
from dataclasses import dataclass,asdict
import argparse,collections,copy,json,pathlib
from flow_refinements import FlowRefinementConfig
@dataclass(frozen=True)
class ComponentConfig:
    maximum_script_size_ratio:float=.85
    minimum_baseline_offset_em:float=.08
    maximum_baseline_offset_em:float=.85
    minimum_ink_gap_em:float=-.25
    maximum_ink_gap_em:float=.45
    maximum_script_run_baseline_difference_em:float=.12
    maximum_script_run_size_difference_em:float=.12
    maximum_width_em:float=12.
    maximum_height_em:float=2.5
    maximum_glyphs:int=48

def connected(cluster,right,all_glyphs,body,cfg=ComponentConfig()):
    out={'rule':'source_vector_component_script_edge','accepted':False}
    if not cluster or not right:return out|{'reason':'empty'}
    base=max(g['size'] for g in cluster);first=right[0]
    if max(g['size'] for g in right)>cfg.maximum_script_size_ratio*base:return out|{'reason':'new_baseline_primitive'}
    edges=[]
    for anchor in cluster:
        gap=(first['box'][0]-anchor['box'][2])/body;dy=(first['baseline']-anchor['baseline'])/body
        if not cfg.minimum_ink_gap_em<=gap<=cfg.maximum_ink_gap_em:continue
        nested=first['size']<=cfg.maximum_script_size_ratio*anchor['size'] and cfg.minimum_baseline_offset_em<=abs(dy)<=cfg.maximum_baseline_offset_em
        run=anchor['size']<=cfg.maximum_script_size_ratio*base and abs(dy)<=cfg.maximum_script_run_baseline_difference_em and abs(first['size']-anchor['size'])/body<=cfg.maximum_script_run_size_difference_em
        if nested or run:edges.append({'anchor_source_index':anchor['source_index'],'ink_gap_em':gap,'baseline_offset_em':dy,'edge':'nested_script' if nested else 'same_script_run'})
    if not edges:return out|{'reason':'no_source_geometric_script_edge'}
    gs=cluster+right;ids={g['source_index'] for g in gs};inside={g['source_index'] for g in all_glyphs if min(ids)<=g['source_index']<=max(ids) and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1]}
    if not inside<=ids:return out|{'reason':'foreign_logical_glyph_between'}
    width=(max(g['box'][2] for g in gs)-min(g['box'][0] for g in gs))/body;height=(max(g['box'][3] for g in gs)-min(g['box'][1] for g in gs))/body
    if len(ids)>cfg.maximum_glyphs or width>cfg.maximum_width_em or height>cfg.maximum_height_em:return out|{'reason':'bounded_component_limit'}
    return out|{'accepted':True,'reason':'continuous_bounded_component','edges':edges}

def refine(data,plan,assets,bridge,cfg=ComponentConfig()):
    data=copy.deepcopy(data);units={u['id']:u for u in plan['units']};assets={a['id']:a for a in assets['results']};body=data['body_font_pdf'];scale=data['source_capture_scale'];trace=[]
    def gs(ids):return sorted([g for uid in ids for g in units[uid]['glyphs']],key=lambda g:g['source_index'])
    before=collections.Counter(e for b in data['blocks'] for t in b['tokens'] for e in t.get('native_event_ids',[]))
    for block in data['blocks']:
        tokens=[]
        for token in block['tokens']:
            if token['kind']!='vector' or len(token['members'])<2:tokens.append(token);continue
            members=sorted(token['members'],key=lambda uid:min(g['source_index'] for g in units[uid]['glyphs']));clusters=[]
            for uid in members:
                relation=connected(gs(clusters[-1]),gs([uid]),plan['glyphs'],body,cfg) if clusters else {'accepted':False,'reason':'first_component'}
                trace.append(relation|{'old_token':token['id'],'member':uid})
                if relation['accepted']:clusters[-1].append(uid)
                else:clusters.append([uid])
            if len(clusters)==1:tokens.append(token);continue
            baseline=token['source_pixel_box'][3]/scale+token['vertical_em']*body;created=[]
            for cluster in clusters:
                aa=[assets[uid] for uid in cluster];box=[min(a['asset_pixel_box'][0] for a in aa),min(a['asset_pixel_box'][1] for a in aa),max(a['asset_pixel_box'][2] for a in aa),max(a['asset_pixel_box'][3] for a in aa)];events=sorted(e for uid in cluster for e in bridge['converted'][uid]['native_event_ids']);created.append({'id':'component-'+str(len(tokens))+'-'+str(len(created))+'-'+token['id'],'kind':'vector','members':cluster,'source_pixel_box':box,'width_em':(box[2]-box[0])/scale/body,'height_em':(box[3]-box[1])/scale/body,'vertical_em':(baseline-box[3]/scale)/body,'gap_em':0.,'native_event_ids':events})
            for a,b in zip(created,created[1:]):a['gap_em']=(b['source_pixel_box'][0]-a['source_pixel_box'][2])/scale/body
            created[-1]['gap_em']=token['gap_em'];tokens.extend(created)
            trace.append({'rule':'old_vector_composite_repartition','old_token':token['id'],'components':len(created),'glyphs_sliced':False,'printed_paints_added_or_removed':False})
        block['tokens']=tokens
    after=collections.Counter(e for b in data['blocks'] for t in b['tokens'] for e in t.get('native_event_ids',[]))
    if before!=after:raise RuntimeError('source native paint multiset changed')
    data['component_config']=asdict(cfg);return data,trace
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('plan');p.add_argument('assets');p.add_argument('bridge');p.add_argument('out');a=p.parse_args();r,t=refine(*[json.loads(pathlib.Path(x).read_text()) for x in [a.reader,a.plan,a.assets,a.bridge]]);out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,separators=(',',':')));(out.parent/'component-trace-private.json').write_text(json.dumps(t,indent=2));print(json.dumps({'repartitioned_composites':sum(x.get('rule')=='old_vector_composite_repartition' for x in t),'native_paint_multiset_unchanged':True}))
