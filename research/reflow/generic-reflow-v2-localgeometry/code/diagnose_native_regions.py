"""Reconstruct line envelopes before ordering; no text rendering or ink changes."""
import argparse,json,pathlib,statistics,sys,re
from dataclasses import dataclass,asdict
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-order-tree/code'))
from region_tree import build_tree,AmbiguousOrder,OrderConfig
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from geometry_evidence import local_anchor_ids
@dataclass(frozen=True)
class LineConfig:
    anchor_size_ratio:float=.85
    anchor_ink_height_ratio:float=.3
    baseline_tolerance_em:float=.2
    baseline_major_size_ratio:float=.86
    horizontal_chunk_gap_em:float=1.5
    script_horizontal_reach_em:float=.8
    script_baseline_reach_em:float=1.
    inline_max_width_em:float=12.
    inline_max_height_em:float=2.5
    margin_band_page_fraction:float=.05
    equation_number_maximum_characters:int=8
    equation_number_native_index_gap:int=16
    equation_number_maximum_gap_em:float=10.
    def json(self):return asdict(self)

def union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def xgap(a,b):return max(a[0]-b[2],b[0]-a[2],0)
def make_lines(plan,body,cfg=LineConfig()):
    free=[];protected=[];aux=[];trace=[];W,H=plan['page_size']
    for source in plan['units']:
        u=dict(source);gs=[g for g in u['glyphs'] if g.get('native_object_ink_observed',True)];b=u['box']
        if not gs and not u.get('objects'):trace.append(dict(unit=u['id'],rule='no_observed_native_ink_character_or_paint',accepted=False));continue
        u['baseline']=u.get('baseline',statistics.median(g['baseline'] for g in gs if g['size']>=max(x['size'] for x in gs)*cfg.baseline_major_size_ratio) if gs else b[3]);u['font_size']=max((g['size'] for g in gs),default=body)
        prior=u.get('prior_source',{});display_formula=isinstance(prior,dict) and prior.get('label')=='formula'
        inline=not display_formula and (u['kind']=='native_word' or (gs and b[2]-b[0]<=cfg.inline_max_width_em*body and b[3]-b[1]<=cfg.inline_max_height_em*body))
        if u.get('geometry_auxiliary') or b[3]<cfg.margin_band_page_fraction*H or b[1]>(1-cfg.margin_band_page_fraction)*H:aux.append(u)
        elif inline:free.append(u)
        else:protected.append(dict(id=u['id'],box=b,unit_ids=[u['id']],role='protected_local',provenance=u.get('prior_source','native paint/local geometry'),native_indexes=sorted(g['source_index'] for g in gs)))
    # A bounded display-formula prior can carry a separate source equation
    # number. Syntax is generic, not a document-specific token match.
    for region in protected:
        prior=region['provenance']
        if not isinstance(prior,dict) or prior.get('label')!='formula':continue
        candidates=[]
        for u in free:
            text=''.join(g['char'] for g in u['glyphs']);idx=[g['source_index'] for g in u['glyphs']];b=u['box'];rb=region['box']
            if len(text)<=cfg.equation_number_maximum_characters and re.fullmatch(r'\(?[0-9]+[a-z]?\)?',text) and all(g['unicode_known'] for g in u['glyphs']) and min(b[3],rb[3])>max(b[1],rb[1]) and xgap(b,rb)<=cfg.equation_number_maximum_gap_em*body and min(abs(i-j) for i in idx for j in region['native_indexes'])<=cfg.equation_number_native_index_gap:candidates.append(u)
        trace.append(dict(rule='display_formula_number_association',region=region['id'],candidates=[u['id'] for u in candidates],accepted=len(candidates)==1))
        if len(candidates)==1:
            u=candidates[0];region['unit_ids'].append(u['id']);region['box']=union([region['box'],u['box']]);region['native_indexes']=sorted(region['native_indexes']+[g['source_index'] for g in u['glyphs']]);free.remove(u)
    local_anchors,local_trace=local_anchor_ids(free,body);trace.extend(local_trace)
    anchors=[u for u in free if (u['font_size']>=body*cfg.anchor_size_ratio and any(g['box'][3]-g['box'][1]>=cfg.anchor_ink_height_ratio*g['size'] for g in u['glyphs'])) or u['id'] in local_anchors];scripts=[u for u in free if u not in anchors];rows=[]
    for u in sorted(anchors,key=lambda u:(u['baseline'],u['box'][0])):
        choices=[r for r in rows if abs(r['baseline']-u['baseline'])<=cfg.baseline_tolerance_em*body]
        if choices:min(choices,key=lambda r:abs(r['baseline']-u['baseline']))['units'].append(u)
        else:rows.append(dict(baseline=u['baseline'],units=[u]))
    lines=[]
    for row in rows:
        chunks=[[]]
        for u in sorted(row['units'],key=lambda u:u['box'][0]):
            if chunks[-1] and xgap(chunks[-1][-1]['box'],u['box'])>cfg.horizontal_chunk_gap_em*body:chunks.append([])
            chunks[-1].append(u)
        for chunk in chunks:lines.append(dict(baseline=row['baseline'],units=chunk,box=union([u['box'] for u in chunk])))
    unresolved=[];attachments=[]
    for u in scripts:
        choices=[]
        for i,line in enumerate(lines):
            dx=xgap(u['box'],line['box']);dy=abs((u['box'][1]+u['box'][3]-line['box'][1]-line['box'][3])/2)
            if dx<=cfg.script_horizontal_reach_em*body and dy<=cfg.script_baseline_reach_em*body:choices.append((dx+dy,i))
        if not choices:unresolved.append(u['id']);continue
        score,i=min(choices);line=lines[i];parent=min(line['units'],key=lambda a:xgap(u['box'],a['box'])+abs((u['box'][0]+u['box'][2]-a['box'][0]-a['box'][2])/2)*.1)
        attachments.append(dict(script=u['id'],parent=parent['id'],script_baseline=u['baseline'],line_baseline=line['baseline'],score_points=score,requires_bounded_native_group=True));line['units'].append(u);line['box']=union([x['box'] for x in line['units']])
    # Unknown-glyph/script units can fill an apparent horizontal hole between
    # anchors. Re-evaluate source-line continuity after association rather than
    # treating that temporary hole as a column boundary.
    merged=[]
    for line in sorted(lines,key=lambda l:(l['baseline'],l['box'][0])):
        match=next((other for other in reversed(merged) if abs(other['baseline']-line['baseline'])<=cfg.baseline_tolerance_em*body and xgap(other['box'],line['box'])<=cfg.horizontal_chunk_gap_em*body),None)
        if match is None:merged.append(line)
        else:match['units'].extend(line['units']);match['box']=union([match['box'],line['box']])
    lines=merged
    leaves=list(protected)
    for line in lines:
        us=sorted(line['units'],key=lambda u:u['box'][0]);indexes=sorted(g['source_index'] for u in us for g in u['glyphs'] if g.get('native_object_ink_observed',True))
        leaves.append(dict(id='line-'+min(u['id'] for u in us),box=line['box'],unit_ids=[u['id'] for u in us],baseline=line['baseline'],native_indexes=indexes,role='source_line',provenance='native geometry, not a semantic paragraph label'))
    return leaves,dict(config=cfg.json(),auxiliary_units=[u['id'] for u in aux],unresolved_small_units=unresolved,script_attachments=attachments,trace=trace,paragraphs_reconstructed=False)

def diagnose(folder,out):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());leaves,lines=make_lines(plan,summary['body_font'])
    try:
        tree=build_tree(leaves,summary['body_font']);result=dict(order_tree_built=True,**tree)
    except AmbiguousOrder as e:result=dict(order_tree_built=False,ambiguity=e.args[0])
    mapping={b['id']:b for b in leaves};inversions=[]
    for left,right in zip(result.get('sequence',[]),result.get('sequence',[])[1:]):
        a,b=mapping[left]['native_indexes'],mapping[right]['native_indexes']
        if a and b and min(b)<max(a):inversions.append(dict(left=left,right=right,left_range=[min(a),max(a)],right_range=[min(b),max(b)]))
    result.update(line_diagnostics=lines,leaf_count=len(leaves),native_index_boundary_conflicts=inversions,reading_acceptance=False,scope='seen-page local-geometry candidate; native orientation retained and semantic selection unverified')
    (out/'source-leaves-private.json').write_text(json.dumps(leaves,indent=2));(out/'order-tree-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['order_tree_built','leaf_count','reading_acceptance']}));print(json.dumps({'native_boundary_conflicts':len(inversions),'small_unresolved':len(lines['unresolved_small_units']),'script_attachments':len(lines['script_attachments'])}));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('out');a=p.parse_args();diagnose(a.folder,a.out)
