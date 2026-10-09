"""Native fraction closure includes thin image/filled-paint bars, not only strokes."""
import argparse,collections,json,pathlib,sys
from dataclasses import dataclass,asdict
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-inkownership/code'))
from bounded_inline import propose,InlineConfig
@dataclass(frozen=True)
class FractionConfig:
    maximum_bar_width_em:float=3.
    maximum_bar_height_em:float=.1
    minimum_bar_aspect:float=3.
    def json(self):return asdict(self)

def close(folder,out,cfg=FractionConfig()):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());body=summary['body_font'];units=plan['units'];objects=[dict(o) for o in plan['objects']];bars=set();local=InlineConfig(math_neighbor_gap_em=0,short_identifier_characters=0)
    for obj in objects:
        b=obj['box'];w,h=b[2]-b[0],b[3]-b[1]
        if obj['type']!=1 and w<=cfg.maximum_bar_width_em*body and h<=cfg.maximum_bar_height_em*body and w/max(h,1e-9)>=cfg.minimum_bar_aspect:obj['horizontal_stroke']=True;bars.add(obj['id'])
    replacements={};decisions=[];groups=[]
    for seed in list(units):
        b=seed['box']
        if seed['id'] not in {u['id'] for u in units} or not (bars&set(seed.get('objects',[]))) or b[2]-b[0]>local.max_width_em*body or b[3]-b[1]>local.max_height_em*body:continue
        group,trace=propose({seed['id']},units,plan['glyphs'],objects,body,local);changed=group is not None and len(group['former_units'])>1;decisions.append(dict(seed=seed['id'],accepted=group is not None,changed=changed,trace=trace))
        if not changed:continue
        current=set(group['former_units']);um={u['id']:u for u in units};group['replaces_current_units']=sorted(current);group['former_units']=sorted({old for uid in current for old in um[uid].get('former_units',[uid])});group['provenance']='native fraction-bar geometry plus bounded native interval';units=[u for u in units if u['id'] not in current]+[group];groups.append(group);replacements.update({uid:group['id'] for uid in current})
    def final(uid):
        while uid in replacements and replacements[uid]!=uid:uid=replacements[uid]
        return uid
    patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():
        for p in ps:patches[final(uid)].append({**p,'file':str((folder/p['file']).resolve())})
    (out/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':patches},ensure_ascii=False,indent=2))
    for name in ['ownership-summary.json','ownership-records.json']:(out/name).write_bytes((folder/name).read_bytes())
    result=dict(config=cfg.json(),local_group_config=local.json(),candidate_native_bars=len(bars),new_groups=len(groups),decisions=decisions,native_renders=0);(out/'fraction-closure-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='decisions'}));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('out');a=p.parse_args();close(a.folder,a.out)
