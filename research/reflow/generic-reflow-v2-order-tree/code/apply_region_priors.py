"""Model rectangles propose bounded native regions; they never supply content."""
import argparse,collections,hashlib,json,pathlib,statistics,sys
from dataclasses import dataclass,asdict
from typing import Literal
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-inkownership/code'))
from ink_ownership import frozen
@dataclass(frozen=True)
class PriorConfig:
    enabled:bool=True
    minimum_confidence:float=.65
    allowed_roles:tuple[str,...]=('table','chart','figure','formula')
    conflict_iou:float=.2
    closure_margin_em:float=1.
    maximum_page_area_fraction:float=.4
    maximum_page_height_fraction:float=.55
    maximum_visible_characters:int=1500
    minimum_table_rows:int=3
    minimum_repeated_columns:int=2
    alignment_tolerance_em:float=.3
    minimum_column_separation_fraction:float=.15
    minimum_rule_width_fraction:float=.4
    maximum_formula_letters_per_word:int=2
    formula_main_size_ratio:float=.85
    rule_maximum_height_em:float=.1
    rule_minimum_aspect:float=40.
    def json(self):return asdict(self)

def area(b):return max(0,b[2]-b[0])*max(0,b[3]-b[1])
def intersect(a,b):return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
def iou(a,b):
 n=area(intersect(a,b));return n/(area(a)+area(b)-n) if n else 0

def validate_candidates(candidates,cfg=PriorConfig()):
    accepted=[];trace=[]
    for i,c in enumerate(candidates):
        reason='eligible'
        if not cfg.enabled:reason='prior disabled'
        elif c['label'] not in cfg.allowed_roles:reason='role outside this experiment'
        elif c['score']<cfg.minimum_confidence:reason='low confidence'
        conflicts=[j for j,d in enumerate(candidates) if j!=i and d['label'] in cfg.allowed_roles and d['score']>=cfg.minimum_confidence and iou(c['box'],d['box'])>cfg.conflict_iou]
        if reason=='eligible' and conflicts:reason='contradictory overlapping region proposals'
        trace.append(dict(candidate=i,accepted=reason=='eligible',reason=reason,conflicts=conflicts))
        if reason=='eligible':accepted.append({**c,'prior_id':i})
    return accepted,trace

def table_evidence(selected,objects,box,body,cfg):
    gs=[g for u in selected for g in u['glyphs'] if g.get('native_object_ink_observed',True)];rows=[]
    for g in sorted(gs,key=lambda g:g['baseline']):
        if not rows or abs(rows[-1]-g['baseline'])>cfg.alignment_tolerance_em*body:rows.append(g['baseline'])
    starts=[]
    for u in selected:
        if u['kind']=='native_word':starts.append((u['box'][0],u.get('baseline',u['box'][3])))
    columns=[]
    for x,y in sorted(starts):
        found=next((c for c in columns if abs(c['x']-x)<=cfg.alignment_tolerance_em*body),None)
        if found is None:columns.append(dict(x=x,ys=[y]))
        else:found['ys'].append(y)
    stable=[c['x'] for c in columns if len({round(y/(cfg.alignment_tolerance_em*body)) for y in c['ys']})>=cfg.minimum_table_rows];separated=[]
    for x in stable:
        if not separated or x-separated[-1]>=cfg.minimum_column_separation_fraction*(box[2]-box[0]):separated.append(x)
    paints={p for u in selected for p in u.get('objects',[])};rules=[o['id'] for o in objects if o['id'] in paints and (o.get('horizontal_stroke') or (o['box'][3]-o['box'][1]<=cfg.rule_maximum_height_em*body and (o['box'][2]-o['box'][0])/max(o['box'][3]-o['box'][1],1e-9)>=cfg.rule_minimum_aspect)) and o['box'][2]-o['box'][0]>=cfg.minimum_rule_width_fraction*(box[2]-box[0])]
    passed=len(rows)>=cfg.minimum_table_rows and len(separated)>=cfg.minimum_repeated_columns and bool(rules)
    return dict(pass_native_structure=passed,rows=len(rows),repeated_columns=separated,long_native_rules=rules)

def prior_provenance(origin:Literal["historical_cache","live_local_page"]):
    if origin not in ("historical_cache","live_local_page"):raise ValueError("unknown prediction provenance")
    return dict(prediction_generation=origin,cached_predictions_only=origin=="historical_cache",adapter_inference_calls=0,page_pipeline_inference_calls=1 if origin=="live_local_page" else 0)

def apply(folder,detector,image_size,out,cfg=PriorConfig(),origin:Literal["historical_cache","live_local_page"]="historical_cache"):
    provenance=prior_provenance(origin)
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());body=summary['body_font'];W,H=plan['page_size'];pred=json.loads(pathlib.Path(detector).read_text());candidates=[dict(label=p['label'],score=p['score'],box=[p['coordinate'][0]*W/image_size[0],p['coordinate'][1]*H/image_size[1],p['coordinate'][2]*W/image_size[0],p['coordinate'][3]*H/image_size[1]]) for p in pred['res']['boxes']];eligible,decisions=validate_candidates(candidates,cfg);units=plan['units'];groups=[];replacement={};region_traces=[]
    for prior in eligible:
        seed=prior['box'];selected={u['id'] for u in units if frozen.inside(seed,frozen.center(u['box']))};um={u['id']:u for u in units};owner={g['id']:u['id'] for u in units for g in u['glyphs']};visible=[g for g in plan['glyphs'] if g['id'] in owner and g.get('native_object_ink_observed',True)];trace=[];accepted=False
        for _ in range(len(units)+1):
            if not selected:trace.append(dict(rule='no_native_support',accepted=False));break
            us=[um[i] for i in selected];gs=[g for g in visible if owner[g['id']] in selected];box=frozen.box_union(u['box'] for u in us);safe=area(box)<=cfg.maximum_page_area_fraction*W*H and box[3]-box[1]<=cfg.maximum_page_height_fraction*H and len(gs)<=cfg.maximum_visible_characters and all(abs(a-b)<=cfg.closure_margin_em*body or (a>=b if i<2 else a<=b) for i,(a,b) in enumerate(zip(box,seed)))
            trace.append(dict(rule='bounded_native_region',accepted=safe,box=box,characters=len(gs)))
            if not safe:break
            if not gs:trace.append(dict(rule='no_native_character_interval',accepted=False));break
            old=set(selected);lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs);selected.update(owner[g['id']] for g in visible if lo<=g['source_index']<=hi);selected.update(u['id'] for u in units if frozen.inside(box,frozen.center(u['box'])))
            if old!=selected:continue
            if prior['label']=='table':
                ev=table_evidence(us,plan['objects'],box,body,cfg);trace.append(dict(rule='independent_table_structure',**ev))
                if not ev['pass_native_structure']:break
            elif prior['label'] in ('chart','figure'):
                if not any(u.get('objects') for u in us):trace.append(dict(rule='no_native_graphic_paint',accepted=False));break
            elif prior['label']=='formula':
                longwords=[u['id'] for u in us if u['kind']=='native_word' and any(len(word)>cfg.maximum_formula_letters_per_word for word in ''.join(g['char'] if g['char'].isalpha() and g['size']>=max(x['size'] for x in u['glyphs'])*cfg.formula_main_size_ratio else ' ' for g in u['glyphs']).split())]
                if longwords:trace.append(dict(rule='formula_candidate_contains_long_prose_words',accepted=False,units=longwords));break
            paints={p for u in us for p in u.get('objects',[])};uid='prior-'+str(prior['prior_id']);former=sorted({old for u in us for old in u.get('former_units',[u['id']])});group=dict(id=uid,kind='closed_graphic',box=box,glyphs=sorted(gs,key=lambda g:g['source_index']),objects=sorted(paints,key=lambda p:int(p[1:])),source_interval=[lo,hi+1],former_units=former,replaces_current_units=sorted(selected),prior_source=dict(model='PP-DocLayout-S',prediction_generation=origin,**prior),selection_mapping='not certified');groups.append(group);units=[u for u in units if u['id'] not in selected]+[group];replacement.update({u:uid for u in selected});accepted=True;break
        region_traces.append(dict(prior=prior,accepted=accepted,trace=trace))
    patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():
        for p in ps:patches[replacement.get(uid,uid)].append({**p,'file':str((folder/p['file']).resolve())})
    (out/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':patches},ensure_ascii=False,indent=2))
    for name in ['ownership-summary.json','ownership-records.json']:(out/name).write_bytes((folder/name).read_bytes())
    result=dict(config=cfg.json(),prediction_sha256=hashlib.sha256(pathlib.Path(detector).read_bytes()).hexdigest(),source_pdf_sha256=summary['input_sha256'],**provenance,image_size=list(image_size),candidate_decisions=decisions,region_decisions=region_traces,accepted_regions=len(groups),reading_acceptance=False)
    (out/'prior-result-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({'accepted_regions':len(groups),'regions':[(g['id'],g['prior_source']['label'],g['source_interval']) for g in groups]}));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('detector');p.add_argument('out');p.add_argument('--image-width',type=int,required=True);p.add_argument('--image-height',type=int,required=True);a=p.parse_args();apply(a.folder,a.detector,(a.image_width,a.image_height),a.out)
