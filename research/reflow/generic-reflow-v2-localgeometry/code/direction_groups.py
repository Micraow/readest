"""Preserve a rotated native run as one bounded local item, without Unicode."""
import collections,json,math,pathlib
from geometry_evidence import GeometryConfig,union

def angledistance(a,b):return abs(math.atan2(math.sin(a-b),math.cos(a-b)))
def group(plan,cfg=GeometryConfig()):
    units=plan['units'];W,H=plan['page_size'];owner={g['id']:u['id'] for u in units for g in u['glyphs']};um={u['id']:u for u in units};byobject=collections.defaultdict(list);traces=[];replacements={};groups=[]
    for g in plan['glyphs']:
        if g['id'] in owner and g.get('native_object_ink_observed',True):byobject[g['object_id']].append(g)
    for oid,gs in byobject.items():
        angles=[g.get('native_angle_radians',0) for g in gs]
        if all(angledistance(a,0)<=cfg.angle_tolerance_radians for a in angles):continue
        ids={owner[g['id']] for g in gs};us=[um[i] for i in ids]
        # Existing paint/figure/math groups may legitimately contain multiple
        # directions. They already preserve geometry and must not be sliced.
        if any(u['kind']!='native_word' for u in us):
            traces.append({'rule':'already_preserved_nonword_direction','object':oid,'accepted':False,'changes_required':False});continue
        angle=angles[0];box=union([u['box'] for u in us]);lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs);interval={owner[g['id']] for g in plan['glyphs'] if g['id'] in owner and lo<=g['source_index']<=hi and g.get('native_object_ink_observed',True)}
        ok=all(angledistance(a,angle)<=cfg.angle_tolerance_radians for a in angles) and interval==ids and len(gs)<=cfg.maximum_rotated_glyphs and (box[2]-box[0])*(box[3]-box[1])<=cfg.maximum_rotated_page_area*W*H and box[2]-box[0]<=cfg.maximum_rotated_page_extent*W and box[3]-box[1]<=cfg.maximum_rotated_page_extent*H
        trace={'rule':'closed_native_direction_run','object':oid,'accepted':ok,'angle_radians':angle,'glyphs':len(gs),'interval_closed':interval==ids,'source_units':sorted(ids),'native_orientation_retained':True,'upright_rotation_applied':False};traces.append(trace)
        if not ok:continue
        marginal=box[2]<=cfg.marginal_band_fraction*W or box[0]>=(1-cfg.marginal_band_fraction)*W
        uid='direction-'+oid;groups.append({'id':uid,'kind':'closed_orientation','box':box,'glyphs':sorted(gs,key=lambda g:g['source_index']),'objects':[],'source_interval':[lo,hi+1],'former_units':sorted(ids),'native_angle_radians':angle,'geometry_auxiliary':marginal,'prior_source':{'label':'native_rotated_text','provenance':'PDFium character angle, source interval and bounded geometry'}});replacements.update({i:uid for i in ids})
    patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():patches[replacements.get(uid,uid)].extend(ps)
    return {**plan,'units':[u for u in units if u['id'] not in replacements]+groups,'patches':dict(patches)},traces

def run(folder,out):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text())
    for ps in plan['patches'].values():
        for p in ps:p['file']=str((folder/p['file']).resolve())
    result,trace=group(plan);(out/'plan-private.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'direction-trace-private.json').write_text(json.dumps(trace,indent=2))
    for n in ['ownership-summary.json','ownership-records.json']:(out/n).write_bytes((folder/n).read_bytes())
    unresolved=[t for t in trace if not t['accepted'] and t.get('changes_required',True)]
    if unresolved:raise RuntimeError('mixed or nonclosed native direction cannot be safely ordered')
    return {'direction_groups':sum(t['accepted'] for t in trace),'unresolved_direction_groups':len(unresolved)}
