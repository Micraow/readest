"""Experimental whole-page flow from the region tree; no old y-sorted items.

Composites copy already verified native support at integer source pixel offsets;
there is no page screenshot crop, alpha-threshold erasure or Unicode redraw.
"""
import argparse,collections,html,json,pathlib,statistics,sys
from dataclasses import dataclass,asdict
import numpy as np
from PIL import Image
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-inkownership/code'))
from reader_spacing import separators
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from paragraph_geometry import annotate,estimate,can_join,ParagraphGeometryConfig
@dataclass(frozen=True)
class FlowConfig:
    maximum_paragraph_baseline_gap_em:float=1.7
    maximum_first_line_return_em:float=1.2
    new_paragraph_indent_em:float=.35
    maximum_inline_group_width_em:float=12.
    maximum_inline_group_height_em:float=2.5
    maximum_inline_group_characters:int=48
    transparent_rgb_policy:str="same_as_native_flat_backdrop"
    def json(self):return asdict(self)

def build(folder,treefolder,cfg=FlowConfig()):
    folder=pathlib.Path(folder);treefolder=pathlib.Path(treefolder);plan=json.loads((folder/'plan-private.json').read_text());data=json.loads((folder/'native-unit-assets-private.json').read_text());order=json.loads((treefolder/'order-tree-private.json').read_text());leaves={l['id']:l for l in json.loads((treefolder/'source-leaves-private.json').read_text())}
    if not order['order_tree_built']:raise RuntimeError('ambiguous region tree: no reading output allowed')
    if order['line_diagnostics']['unresolved_small_units']:raise RuntimeError('unresolved native inline units')
    body=data['body_font'];scale=data['scale'];assets={a['id']:a for a in data['results']};units={u['id']:u for u in plan['units']};trace=[];composites=[];emitted=[];paths={}
    def walk(n,path='root'):
        if n['kind']=='leaf':paths[n['id']]=path;return
        for i,ch in enumerate(n['children']):walk(ch,path+('/col'+str(i) if n['kind']=='columns' else ''))
    walk(order['tree']);bundle_dir=folder/'flow-bundles';bundle_dir.mkdir(exist_ok=True)
    def bundle(ids,baseline,tag,inline=True):
        if len(ids)==1:return ids[0]
        aas=[assets[i] for i in ids];l=min(a['asset_pixel_box'][0] for a in aas);t=min(a['asset_pixel_box'][1] for a in aas);r=max(a['asset_pixel_box'][2] for a in aas);b=max(a['asset_pixel_box'][3] for a in aas);gs=sorted([g for uid in ids for g in units[uid]['glyphs']],key=lambda g:g['source_index'])
        if inline and ((r-l)/scale/body>cfg.maximum_inline_group_width_em or (b-t)/scale/body>cfg.maximum_inline_group_height_em or len(gs)>cfg.maximum_inline_group_characters):raise RuntimeError('inline bundle exceeds hard bounds: '+tag)
        canvas=np.zeros((b-t,r-l,4),np.uint8)
        if len({tuple(a['background']) for a in aas})!=1:raise RuntimeError('inline bundle crosses different native flat backdrops')
        canvas[:,:,:3]=np.asarray(aas[0]['background'],np.uint8)
        coverage=np.zeros((b-t,r-l),np.uint16);overlap=0
        for uid,a in zip(ids,aas):
            im=np.array(Image.open(folder/a['file']).convert('RGBA'));x,y=a['asset_pixel_box'][:2];view=canvas[y-t:y-t+im.shape[0],x-l:x-l+im.shape[1]];count=coverage[y-t:y-t+im.shape[0],x-l:x-l+im.shape[1]];mask=im[:,:,3]>0
            if np.any(im[:,:,3][mask]!=255):raise RuntimeError('bundle requires native final-RGB support, not fractional RGBA replay')
            overlap+=int(np.count_nonzero(mask&(count>0)));view[mask]=im[mask];count[mask]+=1
        if overlap:raise RuntimeError('unit supports overlap before local relocation')
        uid='bundle-'+str(len(composites));name='flow-bundles/'+uid+'.png';Image.fromarray(canvas,'RGBA').save(folder/name)
        assets[uid]=dict(id=uid,kind='inline_native_group' if inline else 'closed_graphic',file=name,asset_pixel_box=[l,t,r,b],width_em=(r-l)/scale/body,height_em=(b-t)/scale/body,descent_em=(b/scale-baseline)/body,background=aas[0]['background'],all_unicode_known=False,mapped_unicode='',source_support_members=ids)
        units[uid]=dict(id=uid,kind=assets[uid]['kind'],box=[l/scale,t/scale,r/scale,b/scale],glyphs=gs,baseline=baseline)
        composites.append(dict(id=uid,members=ids,reason=tag,overlapping_support_pixels=overlap,source_pixel_copy_only=True));return uid
    byscript=collections.defaultdict(set)
    for a in order['line_diagnostics']['script_attachments']:byscript[a['script']].add(a['parent']);byscript[a['parent']].add(a['script'])
    structured=[]
    for lid in order['sequence']:
        line=leaves[lid];ids=line['unit_ids'];current=set(ids)
        if line['role']=='protected_local':
            baseline=line['box'][3];uid=bundle(ids,baseline,'protected display region',False);structured.append(dict(kind='object',id=lid,unit_ids=[uid],source_unit_ids=ids,path=paths[lid],box=line['box']));continue
        components=[];pending=set(ids)
        while pending:
            first=pending.pop();todo=[first];comp={first}
            while todo:
                for v in byscript[todo.pop()]&current-comp:comp.add(v);pending.discard(v);todo.append(v)
            # Local native interval closure includes intervening whole units.
            if len(comp)>1:
                lo=min(g['source_index'] for u in comp for g in units[u]['glyphs']);hi=max(g['source_index'] for u in comp for g in units[u]['glyphs']);inside={u for u in ids if any(lo<=g['source_index']<=hi for g in units[u]['glyphs'])};comp|=inside;pending-=inside
            components.append(comp)
        # Merge components that meet through interval closure.
        merged=[]
        for comp in components:
            touches=[c for c in merged if c&comp]
            for c in touches:comp|=c;merged.remove(c)
            merged.append(comp)
        tokens=[]
        for comp in sorted(merged,key=lambda c:min(g['source_index'] for u in c for g in units[u]['glyphs'])):
            members=sorted(comp,key=lambda u:min(g['source_index'] for g in units[u]['glyphs']));tokens.append(bundle(members,line['baseline'],'script/unknown-glyph local interval',True))
        structured.append(dict(kind='line',id=lid,unit_ids=tokens,source_unit_ids=ids,path=paths[lid],box=line['box'],baseline=line['baseline']))
    annotate(structured,units,body);leading=estimate(structured,body)
    blocks=[]
    for item in structured:
        if item['kind']=='object':blocks.append(dict(kind='object',items=[item]));continue
        previous=blocks[-1]['items'][-1] if blocks and blocks[-1]['kind']=='paragraph' else None
        join=can_join(previous,item,body,leading,cfg)
        trace.append(dict(rule='source_line_paragraph_join',line=item['id'],previous=previous['id'] if previous else None,accepted=join))
        if join:blocks[-1]['items'].append(item)
        else:blocks.append(dict(kind='paragraph',items=[item]))
    def token(uid,gap=0,linebaseline=None):
        a=assets[uid];u=units[uid];members=a.get('source_support_members',[uid]);emitted.extend(members);known=u['kind']=='native_word' and a['all_unicode_known'];text=html.escape(a['mapped_unicode']) if known else '';shift=(linebaseline-u.get('baseline',linebaseline))/body if linebaseline is not None else 0
        return f'<span class="token" data-unit="{uid}" data-members="{" ".join(members)}" style="width:{a["width_em"]}em;height:{a["height_em"]}em;vertical-align:{-a["descent_em"]+shift}em;margin-right:{gap}em"><img src="{a["file"]}" alt="" draggable="false"><span class="selection">{text}</span></span>'
    content=[]
    for block in blocks:
        if block['kind']=='object':content.append('<figure>'+token(block['items'][0]['unit_ids'][0])+'</figure>');continue
        ids=[uid for line in block['items'] for uid in line['unit_ids']];gaps=separators(ids,units,assets,plan['glyphs'],body,scale);byid={g['left']:g for g in gaps};chunks=[]
        for line in block['items']:
            for uid in line['unit_ids']:chunks.append(token(uid,byid.get(uid,{}).get('gap_em',0),line['baseline']))
        content.append('<p>'+''.join(chunks)+'</p>')
    for uid in order['line_diagnostics']['auxiliary_units']:
        if uid in assets and not assets[uid].get('empty'):content.append('<aside>'+token(uid)+'</aside>')
    expected=[u['id'] for u in plan['units'] if u['id'] in assets and not assets[u['id']].get('empty')]
    if collections.Counter(emitted)!=collections.Counter(expected):raise RuntimeError('reading-unit conservation failed')
    css='*{box-sizing:border-box}body{margin:0;padding:12px;font:20px/1.5 sans-serif;background:white;color:#111}main{max-width:46em;margin:auto}p{margin:0 0 .8em}.token{display:inline-block;position:relative;white-space:nowrap}.token img{width:100%;height:100%;display:block}.selection{position:absolute;inset:0;color:transparent;white-space:pre}figure{margin:.8em 0;max-width:100%;overflow:auto}figure .token{max-width:100%;height:auto!important}figure .token img{height:auto}aside{font-size:.7em;color:#777}nav{font-size:12px}'
    (folder/'tree-reader.html').write_text('<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body><nav>Research preview: source-light theme; interaction and semantic selection unverified</nav><main>'+''.join(content)+'</main></body></html>')
    result=dict(config=cfg.json(),paragraph_geometry_config=ParagraphGeometryConfig().json(),native_leading_estimates=leading,paragraphs=sum(b['kind']=='paragraph' for b in blocks),objects=sum(b['kind']=='object' for b in blocks),source_unit_bijection=True,emitted_native_units=len(emitted),bundles=composites,paragraph_trace=trace,reading_acceptance=False,selection_semantics_certified=False,zoom_interaction_tested=False)
    (folder/'tree-reader-audit-private.json').write_text(json.dumps(result,indent=2));(folder/'tree-reader-assets-private.json').write_text(json.dumps({**data,'results':list(assets.values())},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in {'bundles','paragraph_trace'}}));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('treefolder');a=p.parse_args();build(a.folder,a.treefolder)
