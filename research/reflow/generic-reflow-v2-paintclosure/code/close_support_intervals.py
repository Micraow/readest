"""Resolve connected support conflicts only as bounded local intervals."""
import argparse,collections,json,pathlib,sys
PREVIOUS=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-inkownership/code';sys.path.insert(0,str(PREVIOUS))
from coalesce_local_intervals import propose
from ink_config import LocalGroupConfig
from support_interactions import scan

def close(folder,out,cfg=LocalGroupConfig(math_neighbor_gap_em=0.0,short_identifier_characters=0)):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());support=scan(folder);neighbors=collections.defaultdict(set)
    for e in support['edges']:
        a,b=e['owners'];neighbors[a].add(b);neighbors[b].add(a)
    pending=set(neighbors);components=[]
    while pending:
        todo=[pending.pop()];found=set(todo)
        while todo:
            for n in neighbors[todo.pop()]-found:found.add(n);pending.discard(n);todo.append(n)
        components.append(found)
    units=plan['units'];decisions=[];groups=[];replacement={}
    for comp in components:
        group,trace=propose(comp,units,plan['glyphs'],plan['objects'],summary['body_font'],cfg)
        decisions.append(dict(support_component=sorted(comp),accepted=group is not None,trace=trace))
        if group is None:continue
        current=set(group['former_units']);oldmap={u['id']:u for u in units};group['replaces_current_units']=sorted(current);group['former_units']=sorted({old for uid in current for old in oldmap[uid].get('former_units',[uid])});groups.append(group)
        units=[u for u in units if u['id'] not in current]+[group];replacement.update({uid:group['id'] for uid in current})
    patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():
        for p in ps:patches[replacement.get(uid,uid)].append({**p,'file':str((folder/p['file']).resolve())})
    (out/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':patches},ensure_ascii=False,indent=2))
    for name in ['ownership-summary.json','ownership-records.json']:(out/name).write_bytes((folder/name).read_bytes())
    after=scan(out);result=dict(config=cfg.json(),input_interacting_pairs=support['interacting_pairs'],groups=len(groups),rejected_components=sum(not d['accepted'] for d in decisions),remaining_interacting_pairs=after['interacting_pairs'],native_renders=0,group_summaries=[{k:g[k] for k in ['id','source_interval','former_units','box']} for g in groups])
    (out/'support-closure-result.json').write_text(json.dumps(result,indent=2));(out/'support-closure-trace-private.json').write_text(json.dumps(decisions,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('out');a=p.parse_args();print(json.dumps(close(a.folder,a.out)))
