"""Bounded paint ownership closure; the preceding planner is a weak prior.

Fully enclosed paint belongs to a candidate local graphic only after native
character-interval closure fits the bounds. Continuous native indices do not
certify global semantic reading order. Refusal is explicit and not a page lock.
"""
import argparse,collections,json,pathlib,sys
import numpy as np
from PIL import Image
from closure_config import ClosureConfig
PREVIOUS=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-inkownership/code'
sys.path.insert(0,str(PREVIOUS))
from ink_ownership import frozen

def contains(outer,inner):return outer[0]<=inner[0] and outer[1]<=inner[1] and outer[2]>=inner[2] and outer[3]>=inner[3]

def propose_graphic(seed,units,glyphs,objects,backgrounds,page_size,body,cfg):
    selected={seed['id']};attached=set();trace=[];W,H=page_size;original=seed['box'];unitmap={u['id']:u for u in units};owner={g['id']:u['id'] for u in units for g in u['glyphs']};visible=[g for g in glyphs if g['id'] in owner and g.get('native_object_ink_observed',True)]
    def state():
        gs=[g for g in visible if owner[g['id']] in selected];paints={p for uid in selected for p in unitmap[uid].get('objects',[])}|attached
        boxes=[unitmap[u]['box'] for u in selected]+[o['box'] for o in objects if o['id'] in paints]
        return gs,paints,frozen.box_union(boxes)
    for _ in range(len(units)+len(backgrounds)+1):
        old=(set(selected),set(attached));gs,paints,b=state();bw,bh=b[2]-b[0],b[3]-b[1];seedw,seedh=original[2]-original[0],original[3]-original[1]
        limits=dict(width_fraction=bw/W,height_fraction=bh/H,area_fraction=bw*bh/(W*H),visible_characters=len(gs),width_expansion=bw/max(seedw,body),height_expansion=bh/max(seedh,body),outside_seed_margin_em=max(original[0]-b[0],original[1]-b[1],b[2]-original[2],b[3]-original[3],0)/body)
        safe=limits['width_fraction']<=cfg.maximum_page_width_fraction and limits['height_fraction']<=cfg.maximum_page_height_fraction and limits['area_fraction']<=cfg.maximum_page_area_fraction and len(gs)<=cfg.maximum_visible_characters and limits['width_expansion']<=cfg.maximum_seed_expansion_ratio and limits['height_expansion']<=cfg.maximum_seed_expansion_ratio and limits['outside_seed_margin_em']<=max(cfg.maximum_seed_margin_em,cfg.maximum_seed_margin_fraction*max(seedw,seedh)/body)
        trace.append(dict(rule='graphic_hard_bounds',accepted=safe,measurements=limits))
        if not safe:return None,trace
        if gs and cfg.close_native_character_interval:
            lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs)
            selected.update(owner[g['id']] for g in visible if lo<=g['source_index']<=hi)
            trace.append(dict(rule='native_interval_closure',range_inclusive=[lo,hi],owners=sorted(selected)))
        if cfg.close_enclosed_paint_units:
            enclosed=[u['id'] for u in units if (u.get('objects') or (cfg.close_enclosed_text_units and any(g.get('native_object_ink_observed',True) for g in u['glyphs']))) and contains(b,u['box'])]
            selected.update(enclosed);trace.append(dict(rule='enclosed_foreground_units',owners=enclosed))
        if cfg.attach_fully_enclosed_backgrounds:
            bg=[x['id'] for x in backgrounds if contains(b,x['box'])];attached.update(bg);trace.append(dict(rule='enclosed_candidate_background_becomes_local_paint',paint=bg,uses_color_or_document_identity=False))
        if old==(selected,attached):
            gs,paints,b=state();interval=[min(g['source_index'] for g in gs),max(g['source_index'] for g in gs)+1] if gs else None
            return dict(id='closed-'+seed['id'],kind='closed_graphic',box=b,glyphs=sorted(gs,key=lambda g:g['source_index']),objects=sorted(paints,key=lambda x:int(x[1:])),source_interval=interval,former_units=sorted(selected),absorbed_backgrounds=sorted(attached),prior_source='previous geometry planner; not verified semantic role',selection_mapping='not certified'),trace
    raise RuntimeError('bounded closure did not converge')

def close_graphics(folder,out,cfg=ClosureConfig()):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());units=plan['units'];backgrounds=plan['backgrounds'];decisions=[];groups=[]
    records=json.loads((folder/'ownership-records.json').read_text());inkobjects={r['object_id'] for r in records if r['native_ink_pixels']>0}
    # Native text records without any ink at this tested grid remain in the
    # ledger, but cannot enlarge a visible graphic or invent visible prose.
    for g in plan['glyphs']:g['native_object_ink_observed']=g['object_id'] in inkobjects
    glyphmap={g['id']:g for g in plan['glyphs']};objects={o['id']:o for o in plan['objects']}
    for u in units:
        u['glyphs']=[glyphmap[g['id']] for g in u['glyphs']]
        boxes=[g['box'] for g in u['glyphs'] if g['native_object_ink_observed']]+[objects[o]['box'] for o in u.get('objects',[])]
        if boxes:u['box']=frozen.box_union(boxes)
        u['nonpainting_character_records_at_tested_grid']=[g['id'] for g in u['glyphs'] if not g['native_object_ink_observed']]
    if cfg.enabled:
        for seed in sorted(list(units),key=lambda u:frozen.area(u['box']),reverse=True):
            if not seed.get('objects') or seed['id'] not in {u['id'] for u in units}:continue
            group,trace=propose_graphic(seed,units,plan['glyphs'],plan['objects'],backgrounds,plan['page_size'],summary['body_font'],cfg)
            changed=group is not None and (len(group['former_units'])>1 or group['absorbed_backgrounds'])
            decisions.append(dict(seed=seed['id'],accepted=group is not None,changed=changed,trace=trace))
            if not changed:continue
            former=set(group['former_units']);units=[u for u in units if u['id'] not in former]+[group];backgrounds=[b for b in backgrounds if b['id'] not in group['absorbed_backgrounds']];groups.append(group)
    owner={old:g['id'] for g in groups for old in g['former_units']};patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():
        for p in ps:
            new=dict(p);new['file']=str((folder/p['file']).resolve());patches[owner.get(uid,uid)].append(new)
    result=dict(config=cfg.json(),groups=len(groups),changed_units=sum(len(g['former_units'])-1 for g in groups),absorbed_backgrounds=sum(len(g['absorbed_backgrounds']) for g in groups),rejected_seeds=[d['seed'] for d in decisions if not d['accepted']],source_interval_claim='local native index, not certified semantic order',group_summaries=[{k:g[k] for k in ['id','source_interval','former_units','absorbed_backgrounds','box']} for g in groups])
    (out/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':patches,'backgrounds':backgrounds},ensure_ascii=False,indent=2));(out/'closure-result.json').write_text(json.dumps(result,indent=2));(out/'closure-trace-private.json').write_text(json.dumps(decisions,indent=2))
    for name in ['ownership-summary.json','ownership-records.json']:(out/name).write_bytes((folder/name).read_bytes())
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('out');a=p.parse_args();print(json.dumps(close_graphics(a.folder,a.out)))
