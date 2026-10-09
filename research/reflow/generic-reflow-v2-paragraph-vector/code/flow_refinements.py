"""Small source-geometric flow relations; preserve all native printed glyphs."""
from dataclasses import dataclass,asdict
import argparse,copy,json,pathlib
@dataclass(frozen=True)
class FlowRefinementConfig:
    maximum_script_size_ratio:float=.85
    minimum_script_baseline_offset_em:float=.08
    maximum_script_baseline_offset_em:float=.85
    minimum_anchor_script_gap_em:float=-.25
    maximum_anchor_script_gap_em:float=.45
    maximum_group_width_em:float=12.
    maximum_group_height_em:float=2.5
    maximum_group_glyphs:int=48
    maximum_argument_baseline_difference_em:float=.15
    maximum_script_run_baseline_difference_em:float=.12
    maximum_script_run_size_difference_em:float=.12
    minimum_hyphen_prefix_letters:int=2
    hyphen_characters:tuple=('-', '\u2010')
    hyphen_opening_punctuation:tuple=('(', '[')
    maximum_source_line_shift_em:float=3.
    maximum_hyphen_font_ratio:float=1.12
    source_line_return_tolerance_em:float=.5
    minimum_source_line_shift_em:float=.5
    minimum_dash_aspect_ratio:float=2.5
    minimum_dash_width_em:float=.15
    maximum_dash_width_em:float=.75
    maximum_dash_height_em:float=.12
    minimum_dash_baseline_lift_em:float=.15
    maximum_dash_baseline_lift_em:float=.55

def script_prefix_relation(left,right,all_glyphs,body,cfg=FlowRefinementConfig()):
    reason={'rule':'leading_script_reconnect_to_previous_baseline_anchor','accepted':False}
    if not left or not right:return reason|{'reason':'empty_interval'}
    # Prefer a real baseline anchor immediately before the leading smaller run.
    maximum_size=max(g['size'] for g in left);anchor=max((g for g in left if g['size']==maximum_size),key=lambda g:g['source_index']);script=right[0];ratio=script['size']/maximum_size;edges=[]
    for member in left:
        dy=(script['baseline']-member['baseline'])/body;gap=(script['box'][0]-member['box'][2])/body
        if not cfg.minimum_anchor_script_gap_em<=gap<=cfg.maximum_anchor_script_gap_em:continue
        nested=script['size']<=cfg.maximum_script_size_ratio*member['size'] and cfg.minimum_script_baseline_offset_em<=abs(dy)<=cfg.maximum_script_baseline_offset_em
        run=member['size']<=cfg.maximum_script_size_ratio*maximum_size and abs(dy)<=cfg.maximum_script_run_baseline_difference_em and abs(script['size']-member['size'])/body<=cfg.maximum_script_run_size_difference_em
        if nested or run:edges.append({'anchor_source_index':member['source_index'],'baseline_offset_em':dy,'ink_gap_em':gap,'kind':'nested' if nested else 'same_script_run'})
    reason|={'size_ratio':ratio,'edges':edges}
    if ratio>cfg.maximum_script_size_ratio or not edges:return reason|{'reason':'script_geometry_not_supported'}
    indices={g['source_index'] for g in left+right};inside={g['source_index'] for g in all_glyphs if min(indices)<=g['source_index']<=max(indices) and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1]}
    if not inside<=indices:return reason|{'reason':'intervening_logical_glyph_owned_elsewhere'}
    b=[min(g['box'][0] for g in left+right),min(g['box'][1] for g in left+right),max(g['box'][2] for g in left+right),max(g['box'][3] for g in left+right)]
    if len(indices)>cfg.maximum_group_glyphs or (b[2]-b[0])/body>cfg.maximum_group_width_em or (b[3]-b[1])/body>cfg.maximum_group_height_em:return reason|{'reason':'bounded_group_limit'}
    return reason|{'accepted':True,'reason':'continuous_bounded_script_prefix','baseline_pdf':anchor['baseline']}

def scripted_argument_relation(left,right,all_glyphs,body,cfg=FlowRefinementConfig()):
    result={'rule':'scripted_base_with_adjacent_parenthesized_argument','accepted':False}
    if not left or not right:return result|{'reason':'empty_interval'}
    anchor=max(left,key=lambda g:g['size']);last=left[-1];first=right[0]
    if last['size']/anchor['size']>cfg.maximum_script_size_ratio:return result|{'reason':'left_does_not_end_in_script'}
    if not first.get('unicode_known') or first['char']!='(':return result|{'reason':'not_known_parenthesized_argument'}
    depth=0;closed=False
    for g in right:
        if not g.get('unicode_known'):continue
        if g['char']=='(':depth+=1
        elif g['char']==')':
            depth-=1
            if depth==0:closed=True;break
    if not closed:return result|{'reason':'no_closing_argument_boundary'}
    gap=(first['box'][0]-max(g['box'][2] for g in left))/body;dy=abs(first['baseline']-anchor['baseline'])/body
    result|={'ink_gap_em':gap,'baseline_offset_em':dy}
    if not cfg.minimum_anchor_script_gap_em<=gap<=cfg.maximum_anchor_script_gap_em or dy>cfg.maximum_argument_baseline_difference_em:return result|{'reason':'argument_geometry_not_supported'}
    indices={g['source_index'] for g in left+right};inside={g['source_index'] for g in all_glyphs if min(indices)<=g['source_index']<=max(indices) and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1]}
    if not inside<=indices:return result|{'reason':'intervening_logical_glyph_owned_elsewhere'}
    box=[min(g['box'][0] for g in left+right),min(g['box'][1] for g in left+right),max(g['box'][2] for g in left+right),max(g['box'][3] for g in left+right)]
    if len(indices)>cfg.maximum_group_glyphs or (box[2]-box[0])/body>cfg.maximum_group_width_em or (box[3]-box[1])/body>cfg.maximum_group_height_em:return result|{'reason':'bounded_group_limit'}
    return result|{'accepted':True,'reason':'continuous_bounded_scripted_argument','baseline_pdf':anchor['baseline']}

def hyphen_relation(left,right,body,cfg=FlowRefinementConfig(),all_glyphs=None):
    result={'rule':'source_line_hyphen_kept_with_zero_separator','accepted':False,'printed_hyphen_deleted':False}
    if not left or not right:return result|{'reason':'empty_interval'}
    if not all(g.get('unicode_known') and not g.get('map_error') for g in left[:-1]+[right[0]]):return result|{'reason':'unreliable_lexical_prefix_candidate'}
    last=left[-1];terminal=last['char'];secondary=False
    if not last.get('unicode_known'):
        box=last['box'];w=(box[2]-box[0])/body;h=(box[3]-box[1])/body;lift=(last['baseline']-(box[1]+box[3])/2)/body
        secondary=last.get('secondary_native_unicode_candidate') in cfg.hyphen_characters and h>0 and w/h>=cfg.minimum_dash_aspect_ratio and cfg.minimum_dash_width_em<=w<=cfg.maximum_dash_width_em and h<=cfg.maximum_dash_height_em and cfg.minimum_dash_baseline_lift_em<=lift<=cfg.maximum_dash_baseline_lift_em
        if not secondary:return result|{'reason':'unknown_terminal_not_corroborated_by_native_candidate_and_bar_geometry'}
        terminal=last['secondary_native_unicode_candidate']
    if last.get('map_error'):return result|{'reason':'terminal_mapping_error'}
    chars=[g['char'] for g in left[:-1]];opening=chars[0] if chars and chars[0] in cfg.hyphen_opening_punctuation else None
    prefix=chars[1:] if opening else chars
    result|={'secondary_native_candidate_used':secondary,'semantic_selection_certified':False,'opening_punctuation_retained':opening is not None}
    if terminal not in cfg.hyphen_characters or len(prefix)<cfg.minimum_hyphen_prefix_letters or not all(x.isalpha() for x in prefix) or not right[0]['char'].islower():return result|{'reason':'not_lexical_hyphen_continuation'}
    # A source line transition is directional and local, not any baseline change.
    delta=(right[0]['baseline']-last['baseline'])/body
    if not cfg.minimum_source_line_shift_em<=delta<=cfg.maximum_source_line_shift_em:return result|{'reason':'not_next_local_source_line'}
    if right[0]['box'][0]>left[0]['box'][0]+cfg.source_line_return_tolerance_em*body:return result|{'reason':'not_source_line_return'}
    sizes=[g['size'] for g in left]+[right[0]['size']]
    if min(sizes)<=0 or max(sizes)/min(sizes)>cfg.maximum_hyphen_font_ratio:return result|{'reason':'incompatible_source_type_size'}
    indices=[g['source_index'] for g in left+right]
    if any(a>=b for a,b in zip(indices,indices[1:])):return result|{'reason':'nonmonotone_source_interval'}
    if all_glyphs is not None:
        ids=set(indices);foreign=[g for g in all_glyphs if min(ids)<=g['source_index']<=max(ids) and g['source_index'] not in ids and g.get('native_object_ink_observed',True) and g['box'][2]>g['box'][0] and g['box'][3]>g['box'][1]]
        if foreign:return result|{'reason':'foreign_visible_source_interval'}
    return result|{'accepted':True,'reason':'source_line_transition_with_retained_lexical_hyphen'}

def refine(data,plan,cfg=FlowRefinementConfig()):
    data=copy.deepcopy(data);units={u['id']:u for u in plan['units']};body=data['body_font_pdf'];scale=data['source_capture_scale'];trace=[]
    def glyphs(t):return sorted([g for m in t['members'] for g in units[m]['glyphs']],key=lambda x:x['source_index'])
    for block in data['blocks']:
        if block['kind']!='paragraph':continue
        tokens=[]
        for token in block['tokens']:
            if tokens:
                left=tokens[-1];r=script_prefix_relation(glyphs(left),glyphs(token),plan['glyphs'],body,cfg);r|={'left':left['id'],'right':token['id']}
                if not r['accepted']:
                    trace.append(r);r=scripted_argument_relation(glyphs(left),glyphs(token),plan['glyphs'],body,cfg)|{'left':left['id'],'right':token['id']}
                if r['accepted'] and left['kind']==token['kind']=='vector':
                    a=left['source_pixel_box'];b=token['source_pixel_box'];box=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])];merged={'id':'source-group-'+str(len(trace)),'kind':'vector','members':left['members']+token['members'],'source_pixel_box':box,'width_em':(box[2]-box[0])/scale/body,'height_em':(box[3]-box[1])/scale/body,'vertical_em':(r['baseline_pdf']-box[3]/scale)/body,'gap_em':token['gap_em'],'native_event_ids':sorted(left['native_event_ids']+token['native_event_ids'])};tokens[-1]=merged;trace.append(r);continue
                if r['accepted']:r|={'accepted':False,'reason':'mixed_native_primitive_group_requires_separate_closure'}
                trace.append(r)
            tokens.append(token)
        for left,right in zip(tokens,tokens[1:]):
            r=hyphen_relation(glyphs(left),glyphs(right),body,cfg,all_glyphs=plan['glyphs']);r|={'left':left['id'],'right':right['id'],'previous_gap_em':left['gap_em']}
            if r['accepted']:left['gap_em']=0.
            trace.append(r)
        block['tokens']=tokens
    data['flow_refinement_config']=asdict(cfg);return data,trace
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('plan');p.add_argument('out');p.add_argument('--events');p.add_argument('--bridge');a=p.parse_args();plan=json.loads(pathlib.Path(a.plan).read_text())
    if a.events and a.bridge:
        ee={x['id']:x for x in json.loads(pathlib.Path(a.events).read_text())};bb=json.loads(pathlib.Path(a.bridge).read_text());candidates={pair['source_glyph']:ee[pair['native_event']].get('unicodeCandidate') for u in bb['converted'].values() for pair in u['correspondence']}
        for u in plan['units']:
            for g in u['glyphs']:g['secondary_native_unicode_candidate']=candidates.get(g['id'])
    data,trace=refine(json.loads(pathlib.Path(a.reader).read_text()),plan);out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,separators=(',',':')));(out.parent/'flow-refinement-trace-private.json').write_text(json.dumps(trace,indent=2));print(json.dumps({'rules_tested':len(trace),'accepted_script_groups':sum(x['accepted'] and x['rule'].startswith('leading') for x in trace),'accepted_scripted_arguments':sum(x['accepted'] and x['rule'].startswith('scripted') for x in trace),'accepted_retained_hyphen_joins':sum(x['accepted'] and x['rule'].startswith('source_line') for x in trace),'printed_glyphs_deleted':0}))
