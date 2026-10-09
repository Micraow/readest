"""Spatial index only; exact original origin/uniqueness acceptance is unchanged."""
from dataclasses import dataclass,asdict
import argparse,collections,json,pathlib,math
@dataclass(frozen=True)
class BridgeConfig:
    maximum_origin_error_pdf_points:float=.002
    source_capture_scale:float=2.
    eligible_unit_kind:str='native_word'

def bridge(plan,events,cfg=BridgeConfig()):
    owners=collections.defaultdict(set);glyphs={g['id']:g for g in plan['glyphs']};units={u['id']:u for u in plan['units']}
    for u in units.values():
        for g in u['glyphs']:owners[g['id']].add(u['id'])
    epsilon=cfg.maximum_origin_error_pdf_points
    if epsilon<0:raise ValueError('negative origin tolerance')
    buckets=collections.defaultdict(list);overflow=[];safe_cell_magnitude=2**48
    for ordinal,g in enumerate(glyphs.values()):
        x,y=g['origin'],g['baseline']
        if not math.isfinite(x) or not math.isfinite(y):continue
        if epsilon and (abs(x/epsilon)>safe_cell_magnitude or abs(y/epsilon)>safe_cell_magnitude):overflow.append((ordinal,g));continue
        key=(math.floor(x/epsilon),math.floor(y/epsilon)) if epsilon else (x,y)
        buckets[key].append((ordinal,g))
    candidates={};reverse=collections.defaultdict(list);trace=[]
    for e in events:
        a,b,c,d,tx,ty=e['transform'];x=(a*e['x']+c*e['y']+tx)/cfg.source_capture_scale;y=(b*e['x']+d*e['y']+ty)/cfg.source_capture_scale
        near=[]
        if math.isfinite(x) and math.isfinite(y):
            if epsilon and (abs(x/epsilon)>safe_cell_magnitude or abs(y/epsilon)>safe_cell_magnitude):near=list(enumerate(glyphs.values()))
            elif epsilon:
                bx,by=math.floor(x/epsilon),math.floor(y/epsilon);near.extend(overflow)
                # One extra cell avoids excluding an exact accepted boundary
                # due to rounded floating division; exact filtering is unchanged.
                for dx in (-2,-1,0,1,2):
                    for dy in (-2,-1,0,1,2):near.extend(buckets.get((bx+dx,by+dy),()))
            else:near.extend(buckets[(x,y)])
        ids=[g['id'] for _,g in sorted(near,key=lambda pair:pair[0]) if abs(g['origin']-x)<=epsilon and abs(g['baseline']-y)<=epsilon]
        candidates[e['id']]=ids
        for gid in ids:reverse[gid].append(e['id'])
    by_event={e['id']:e for e in events};converted={};fallback={};mapped_events=[]
    for uid,u in units.items():
        reasons=[];gs=u['glyphs'];ids=[]
        if u['kind']!=cfg.eligible_unit_kind:reasons.append('bounded_nonword_representation_retained')
        for g in gs:
            matches=reverse[g['id']]
            if len(matches)!=1:reasons.append('source_record_missing_or_multiple_native_paints');continue
            eid=matches[0];e=by_event[eid]
            if len(candidates[eid])!=1 or owners[g['id']]!={uid}:reasons.append('nonunique_cross_renderer_correspondence');continue
            if not e.get('resource') or not e.get('state') or e['state']['clips'] or e['pattern'] or e['missingFile'] or e['activeSMask'] or e['textRenderingMode']!=0 or e['state']['blend']!='source-over' or e['state']['filter']!='none' or e['state'].get('absoluteTransform'):reasons.append('unsupported_or_clipped_native_glyph');continue
            ids.append(eid)
        if len(ids)!=len(gs) or not gs:reasons.append('incomplete_unit_native_correspondence')
        if len(set(ids))!=len(ids):reasons.append('duplicate_native_event_in_unit')
        if reasons:fallback[uid]=sorted(set(reasons))
        else:
            converted[uid]={'native_event_ids':sorted(ids),'source_glyph_ids':[g['id'] for g in gs],'correspondence':[{'source_glyph':g['id'],'native_event':eid} for g,eid in zip(gs,ids)],'paint_order':'native event sequence','semantic_unicode_certified':False};mapped_events.extend(ids)
    if len(set(mapped_events))!=len(mapped_events):raise RuntimeError('one native event assigned to more than one logical unit')
    return {'config':asdict(cfg),'converted':converted,'fallback':fallback,'native_paint_count':len(events),'converted_event_count':len(mapped_events),'native_events_without_unique_correspondence':sum(len(v)!=1 for v in candidates.values()),'candidate_unicode_used_for_matching':False,'pixel_ownership_proven':False,'unit_counts':{'total':len(units),'converted':len(converted),'fallback':len(fallback)}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('events');p.add_argument('out');a=p.parse_args();r=bridge(json.loads(pathlib.Path(a.plan).read_text()),json.loads(pathlib.Path(a.events).read_text()));out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in {'converted','fallback'}}))
