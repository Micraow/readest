"""Opt-in bounded closure over actual rendered foreground alpha intersections.

Unlike text-only support scans this also sees thin paths and images. A source
mismatch is never waived: merged assets still require exact native replay and
independent source-support rendering checks.
"""
import collections,json,pathlib,sys
import numpy as np
from PIL import Image

def edges(folder,assets):
    masks=[];out=[]
    for asset in assets:
        if asset.get('empty'):continue
        box=asset['asset_pixel_box'];mask=np.asarray(Image.open(pathlib.Path(folder)/asset['file']).convert('RGBA'))[:,:,3]>0
        if mask.shape!=(box[3]-box[1],box[2]-box[0]):raise ValueError('support asset dimensions')
        for prior,pbox,pmask in masks:
            l=max(box[0],pbox[0]);t=max(box[1],pbox[1]);r=min(box[2],pbox[2]);b=min(box[3],pbox[3])
            if l<r and t<b:
                count=int(np.count_nonzero(mask[t-box[1]:b-box[1],l-box[0]:r-box[0]]&pmask[t-pbox[1]:b-pbox[1],l-pbox[0]:r-pbox[0]]))
                if count:out.append(dict(owners=[prior,asset['id']],pixels=count))
        masks.append((asset['id'],box,mask))
    return out

def close(folder,out):
    root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'generic-reflow-v2-order-tree/code'))
    from bounded_inline import propose,InlineConfig
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(exist_ok=False)
    plan=json.loads((folder/'plan-private.json').read_text());data=json.loads((folder/'native-unit-assets-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());failed=set(data['unsupported_source_support_units']);links=edges(folder,data['results']);neighbors=collections.defaultdict(set)
    for link in links:
        a,b=link['owners'];neighbors[a].add(b);neighbors[b].add(a)
    pending=set(neighbors);components=[]
    while pending:
        todo=[pending.pop()];group=set(todo)
        while todo:
            for n in neighbors[todo.pop()]-group:group.add(n);pending.discard(n);todo.append(n)
        if group&failed:components.append(group)
    units=plan['units'];replacements={};decisions=[]
    for component in components:
        group,trace=propose(component,units,plan['glyphs'],plan['objects'],summary['body_font'],InlineConfig(math_neighbor_gap_em=0,short_identifier_characters=0));decisions.append(dict(owners=sorted(component),accepted=group is not None,trace=trace))
        if group is None:continue
        owned=set(group['former_units']);units=[u for u in units if u['id'] not in owned]+[group];replacements.update({uid:group['id'] for uid in owned})
    patches=collections.defaultdict(list)
    for uid,ps in plan['patches'].items():
        patches[replacements.get(uid,uid)].extend({**p,'file':str((folder/p['file']).resolve())} for p in ps)
    (out/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':patches},ensure_ascii=False,indent=2))
    for name in ['ownership-summary.json','ownership-records.json']:(out/name).write_bytes((folder/name).read_bytes())
    report=dict(scope='seen rendered-support closure; exact replay and source-support gates still mandatory',edges=links,decisions=decisions,merged_source_units=len(replacements),native_renders=0)
    (out/'rendered-support-closure.json').write_text(json.dumps(report,indent=2));return report
