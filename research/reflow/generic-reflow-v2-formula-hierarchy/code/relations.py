"""Geometry-closed relations between already independent formula children."""
from dataclasses import dataclass,asdict
import math,re,statistics
@dataclass(frozen=True)
class FormulaRelationConfig:
    maximum_label_glyphs:int=8
    maximum_label_width_em:float=4.
    maximum_label_height_em:float=1.5
    maximum_baseline_delta_em:float=.6
    maximum_gap_column_fraction:float=.5
    column_edge_tolerance_em:float=.3
    maximum_union_page_area_fraction:float=.4
    maximum_union_page_height_fraction:float=.55
    maximum_core_glyphs:int=1500
    main_glyph_size_ratio:float=.85
    baseline_cluster_em:float=.2
    minimum_prior_score:float=.65
    maximum_singleton_pair_height_em:float=3.
    def json(self):return asdict(self)
def bbox(units):
    return [min(u['box'][0] for u in units),min(u['box'][1] for u in units),max(u['box'][2] for u in units),max(u['box'][3] for u in units)]
def intersect(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def region_members(tree,body,cfg=FormulaRelationConfig()):
    out={}
    def walk(node,key='root',box=None):
        box=box or node['box']
        if node['kind']=='leaf':
            for uid in node['unit_ids']:out[uid]={'key':key,'box':box}
        else:
            singleton_pair=(node['kind']=='columns' and len(node['children'])==2 and all(c['kind']=='leaf' and len(c['unit_ids'])==1 for c in node['children']) and node['box'][3]-node['box'][1]<=cfg.maximum_singleton_pair_height_em*body)
            for i,child in enumerate(node['children']):
                walk(child,key+'/col'+str(i) if node['kind']=='columns' else key,child['box'] if node['kind']=='columns' else box)
                if singleton_pair:
                    uid=child['unit_ids'][0];out[uid]['singleton_pair']={'members':[c['unit_ids'][0] for c in node['children']],'parent_key':key,'parent_box':box}
    walk(tree);return out

def relation(core,label,units,glyphs,regions,page,body,formula_proof,cfg=FormulaRelationConfig()):
    record={'rule':'independent_formula_label','core':core['id'],'label':label['id'],'accepted':False,'semantic_unicode_certified':False}
    def fail(reason,**extra):return record|{'reason':reason}|extra
    prior=core.get('prior_source',{})
    if core.get('kind')!='closed_graphic' or prior.get('label')!='formula' or prior.get('score',0)<cfg.minimum_prior_score or not formula_proof:return fail('no_independent_formula_evidence')
    gs=label.get('glyphs',[]);cg=core.get('glyphs',[])
    if label.get('kind')!='native_word' or not gs or not cg or label.get('objects'):return fail('children_not_independent_native_core_and_word')
    text=''.join(g.get('char','') for g in gs)
    if not all(g.get('unicode_known',False) for g in gs) or len(gs)>cfg.maximum_label_glyphs or not re.fullmatch(r'\(?[0-9]+[a-z]?\)?',text):return fail('mapped_numeric_candidate_unavailable')
    lb=label['box'];cb=core['box'];union=bbox([core,label]);r=regions.get(core['id']);lr=regions.get(label['id'])
    region_reason='same_region_tree_column'
    if not r or not lr:return fail('different_or_unknown_column')
    if r['key']!=lr['key']:
        pair=r.get('singleton_pair')
        if not pair or pair!=lr.get('singleton_pair') or set(pair['members'])!={core['id'],label['id']}:return fail('different_or_unknown_column')
        r={'key':pair['parent_key'],'box':pair['parent_box']};region_reason='compact_two_singleton_band_not_established_columns'
    rb=r['box'];t=cfg.column_edge_tolerance_em*body
    if union[0]<rb[0]-t or union[2]>rb[2]+t:return fail('outside_column')
    gap=lb[0]-cb[2];cw=rb[2]-rb[0]
    if gap<=0 or gap>cfg.maximum_gap_column_fraction*cw:return fail('not_bounded_right_label',gap_column_fraction=gap/cw if cw else None)
    if lb[2]-lb[0]>cfg.maximum_label_width_em*body or lb[3]-lb[1]>cfg.maximum_label_height_em*body:return fail('candidate_label_extent')
    if (union[2]-union[0])*(union[3]-union[1])>cfg.maximum_union_page_area_fraction*page[0]*page[1] or union[3]-union[1]>cfg.maximum_union_page_height_fraction*page[1] or len(cg)>cfg.maximum_core_glyphs:return fail('local_region_bound')
    base=statistics.median(g['baseline'] for g in gs);mains=[g for g in cg if g['size']>=cfg.main_glyph_size_ratio*body];rows=[]
    for g in sorted(mains,key=lambda g:g['baseline']):
        row=next((row for row in rows if abs(row[0]-g['baseline'])<=cfg.baseline_cluster_em*body),None)
        if row is None:rows.append([g['baseline']])
        else:row.append(g['baseline'])
    matches=[statistics.median(row) for row in rows if abs(statistics.median(row)-base)<=cfg.maximum_baseline_delta_em*body]
    if len(matches)!=1:return fail('ambiguous_or_missing_core_baseline_row',matching_rows=len(matches))
    ci={g['source_index'] for g in cg};li={g['source_index'] for g in gs};ids=ci|li
    if max(ci)>=min(li):return fail('not_core_then_label_native_order')
    foreign=[g['source_index'] for g in glyphs if min(ids)<=g['source_index']<=max(ids) and g.get('native_object_ink_observed',True) and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1] and g['source_index'] not in ids]
    if foreign:return fail('foreign_visible_glyph_in_native_interval',foreign_count=len(foreign))
    corridor=[cb[2],min(cb[1],lb[1]),lb[0],max(cb[3],lb[3])]
    intrusion=[u['id'] for u in units if u['id'] not in {core['id'],label['id']} and intersect(u['box'],corridor)]
    if intrusion:return fail('corridor_has_foreign_unit',intrusion_count=len(intrusion))
    return record|{'accepted':True,'reason':'independent_continuous_column_bounded_children','gap_column_fraction':gap/cw,'label_baseline':base,'core_anchor_baseline':matches[0],'source_interval':[min(ids),max(ids)+1],'column':r['key'],'region_reason':region_reason}

def unique_relations(records):
    accepted=[r for r in records if r['accepted']]
    for r in records:
        if r['accepted'] and (sum(x['core']==r['core'] for x in accepted)!=1 or sum(x['label']==r['label'] for x in accepted)!=1):r.update(accepted=False,reason='ambiguous_core_label_association')
    return records
