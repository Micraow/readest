"""Reversible main-flow constraints; source paint and native ranges stay separate."""
from dataclasses import dataclass,asdict
import statistics

@dataclass(frozen=True)
class RelationConfig:
    minimum_caption_confidence:float=.65
    caption_labels:tuple[str,...]=('chart_title','figure_title','figure_caption','table_title')
    graphic_labels:tuple[str,...]=('chart','figure','table')
    caption_margin_em:float=1.
    maximum_caption_height_em:float=15.
    maximum_caption_gap_em:float=2.5
    minimum_horizontal_overlap:float=.6
    conflict_iou:float=.2
    maximum_column_width_difference:float=.15
    maximum_previous_right_remainder_em:float=1.
    maximum_continuation_indent_em:float=.25
    maximum_relative_size_difference:float=.08
    maximum_paragraph_baseline_gap_em:float=1.7
    paragraph_indent_em:float=.35
    terminal_marks:str='.!?。！？'
    def json(self):return asdict(self)

def union(boxes):
    boxes=list(boxes);return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def area(b):return max(0,b[2]-b[0])*max(0,b[3]-b[1])
def overlap(a,b):return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
def iou(a,b):
    q=area(overlap(a,b));return q/(area(a)+area(b)-q) if q else 0.
def inside(box,outer,margin=0):return all(x>=y-margin for x,y in zip(box[:2],outer[:2])) and all(x<=y+margin for x,y in zip(box[2:],outer[2:]))
def source_ranges(indexes):
    out=[]
    for i in sorted(set(indexes)):
        if out and i==out[-1][1]:out[-1][1]=i+1
        else:out.append([i,i+1])
    return out

def caption_pairs(sequence,leaves,predictions,body,cfg=RelationConfig()):
    """Only complete contiguous source lines can become a caption hypothesis."""
    candidates=[p for p in predictions if p['label'] in cfg.caption_labels];pairs=[];trace=[];pos={uid:i for i,uid in enumerate(sequence)}
    for p in candidates:
        reason=None;selected=[];target=None
        if p['score']<cfg.minimum_caption_confidence:reason='low_caption_confidence'
        if not reason and any(q is not p and q['score']>=cfg.minimum_caption_confidence and iou(p['box'],q['box'])>cfg.conflict_iou for q in candidates):reason='conflicting_caption_proposals'
        if not reason:
            touched=[l for l in leaves.values() if area(overlap(l['box'],p['box']))>0]
            if any(l['role']!='source_line' or not inside(l['box'],p['box'],cfg.caption_margin_em*body) for l in touched):reason='partial_line_or_protected_region_in_caption'
            else:selected=sorted(touched,key=lambda l:pos[l['id']])
            if not selected and not reason:reason='no_native_caption_lines'
        if not reason:
            indexes=[pos[l['id']] for l in selected];box=union(l['box'] for l in selected)
            if indexes!=list(range(indexes[0],indexes[-1]+1)):reason='caption_not_source_sequence_interval'
            elif box[3]-box[1]>cfg.maximum_caption_height_em*body:reason='caption_height_limit'
            else:
                choices=[]
                for l in leaves.values():
                    prov=l.get('provenance',{});role=prov.get('label') if isinstance(prov,dict) else None
                    if l['role']!='protected_local' or role not in cfg.graphic_labels:continue
                    b=l['box'];gap=box[1]-b[3];ox=max(0,min(b[2],box[2])-max(b[0],box[0]))/max(1e-9,min(b[2]-b[0],box[2]-box[0]))
                    if 0<=gap<=cfg.maximum_caption_gap_em*body and ox>=cfg.minimum_horizontal_overlap and pos[l['id']]+1==indexes[0] and l['column']==selected[0]['column']:choices.append(l)
                if len(choices)!=1:reason='no_unique_immediately_adjacent_graphic'
                else:target=choices[0]
        if not reason:pairs.append(dict(graphic=target['id'],caption=[l['id'] for l in selected],column=target['column'],provenance=p.get('provenance','weak_model_caption'),confidence=p['score']))
        trace.append(dict(rule='bounded_native_caption_pair',candidate=p.get('id'),accepted=not reason,reason=reason or 'complete_lines_unique_adjacent_graphic',source_lines=[l['id'] for l in selected],graphic=target['id'] if target else None))
    return pairs,trace

def apply_relations(sequence,leaves,pairs,body,cfg=RelationConfig()):
    """Infer only adjacent equal-column continuation with a column-prefix float."""
    original=list(sequence);result=list(sequence);trace=[];relations=[];forced=[]
    columns=[]
    for lid in original:
        c=leaves[lid]['column']
        if c not in columns:columns.append(c)
    for pair in pairs:
        floatids=[pair['graphic'],*pair['caption']];column=pair['column'];ci=columns.index(column);reason=None;stats={};target=[]
        if ci==0:reason='no_previous_column'
        own=[lid for lid in original if leaves[lid]['column']==column]
        if not reason and own[:len(floatids)]!=floatids:reason='float_not_column_prefix'
        prev=[lid for lid in original if leaves[lid]['column']==columns[ci-1]] if ci else []
        after=own[len(floatids):]
        if not reason and (leaves[prev[-1]].get('column_group')!=leaves[own[0]].get('column_group') or leaves[prev[-1]].get('column_ordinal',ci-1)+1!=leaves[own[0]].get('column_ordinal',ci)):reason='columns_not_adjacent_siblings'
        if not reason and (not prev or not after or leaves[prev[-1]]['role']!='source_line' or leaves[after[0]]['role']!='source_line'):reason='no_adjacent_main_prose'
        if not reason:
            a,b=leaves[prev[-1]],leaves[after[0]];leftlines=[leaves[x] for x in prev if leaves[x]['role']=='source_line'];rightlines=[leaves[x] for x in after if leaves[x]['role']=='source_line'];lb=union(x['box'] for x in leftlines);rb=union(x['box'] for x in rightlines);lw=lb[2]-lb[0];rw=rb[2]-rb[0]
            stats=dict(previous=prev[-1],continuation=after[0],width_relative_difference=abs(lw-rw)/max(lw,rw),previous_right_remainder_em=(lb[2]-a['box'][2])/body,continuation_indent_em=(b['box'][0]-rb[0])/body,relative_size_difference=abs(a['main_size']-b['main_size'])/max(a['main_size'],b['main_size']),terminal_known=a.get('terminal_known',False),terminal_mark=a.get('terminal_character','') if a.get('terminal_known') else None)
            if stats['width_relative_difference']>cfg.maximum_column_width_difference:reason='incompatible_column_width'
            elif stats['previous_right_remainder_em']>cfg.maximum_previous_right_remainder_em:reason='previous_line_ends_early'
            elif stats['continuation_indent_em']>cfg.maximum_continuation_indent_em:reason='next_main_line_indented'
            elif stats['relative_size_difference']>cfg.maximum_relative_size_difference:reason='heading_or_font_size_change'
            elif a.get('terminal_known') and a.get('terminal_character') in cfg.terminal_marks:reason='reliable_terminal_sentence_mark'
            else:
                target=[after[0]]
                for lid in after[1:]:
                    l=leaves[lid];previous=leaves[target[-1]]
                    if l['role']!='source_line' or not (0<l['baseline']-previous['baseline']<=cfg.maximum_paragraph_baseline_gap_em*body) or l['box'][0]-rb[0]>cfg.paragraph_indent_em*body:break
                    target.append(lid)
        if not reason:
            start=result.index(floatids[0]);end=start+len(floatids)+len(target)
            if result[start:end]!=floatids+target:reason='conflicting_relocation_or_noncontiguous_target'
            else:
                result[start:end]=target+floatids;forced.append([prev[-1],target[0]]);relations.append(dict(rule='cross_column_main_prose_continuation',from_line=prev[-1],to_lines=target,moved_float=floatids,source_ranges=source_ranges(i for lid in [prev[-1],*target] for i in leaves[lid]['native_indexes']),native_interval_contiguous=False,source_range_note='paint-native gaps belong to a separate float; not filled or hidden',semantic_certainty='geometry-supported hypothesis; independent visual review required'))
        trace.append(dict(rule='column_prefix_float_after_continuation',accepted=not reason,reason=reason or 'bounded_adjacent_column_continuation',float_ids=floatids,**stats))
    if len(result)!=len(set(result)) or set(result)!=set(original):raise ValueError('flow relation lost or duplicated source leaf')
    positions={v:i for i,v in enumerate(result)}
    for pair in pairs:
        ids=[pair['graphic'],*pair['caption']]
        if [positions[x] for x in ids]!=list(range(positions[ids[0]],positions[ids[0]]+len(ids))):raise ValueError('graphic-caption relation broken')
    return dict(config=cfg.json(),original_sequence=original,sequence=result,forced_line_joins=forced,relations=relations,trace=trace,leaf_bijection=True,native_index_monotonicity_claimed=False,reading_acceptance=False)
