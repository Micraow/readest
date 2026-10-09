"""Old-page diagnostic only; consume existing weak predictions, never OCR."""
import argparse,hashlib,json,pathlib,statistics,time
from flow_relations import caption_pairs,apply_relations,RelationConfig

def diagnose(folder,treefolder,prediction,image_size,out,cfg=RelationConfig()):
    start=time.perf_counter();folder=pathlib.Path(folder);treefolder=pathlib.Path(treefolder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    plan=json.loads((folder/'plan-private.json').read_text());data=json.loads((folder/'native-unit-assets-private.json').read_text());order=json.loads((treefolder/'order-tree-private.json').read_text());ls={x['id']:x for x in json.loads((treefolder/'source-leaves-private.json').read_text())};units={u['id']:u for u in plan['units']};body=data['body_font'];W,H=plan['page_size'];pred=json.loads(pathlib.Path(prediction).read_text())
    def walk(node,path='root',column=None,group=None,ordinal=None):
        if node['kind']=='leaf':ls[node['id']].update(column=column or 'no_columns',column_group=group,column_ordinal=ordinal);return
        for i,ch in enumerate(node['children']):walk(ch,path+'/'+str(i),path+'/col'+str(i) if node['kind']=='columns' else column,path if node['kind']=='columns' else group,i if node['kind']=='columns' else ordinal)
    walk(order['tree'])
    for l in ls.values():
        if l['role']!='source_line':continue
        gs=sorted([g for uid in l['unit_ids'] for g in units[uid]['glyphs'] if g.get('native_object_ink_observed',True)],key=lambda g:g['source_index']);sizes=[g['size'] for g in gs if g['unicode_known']];l['main_size']=statistics.median(sizes or [body]);g=gs[-1];l['terminal_known']=g['unicode_known'];l['terminal_character']=g['char'] if g['unicode_known'] else None
    predictions=[dict(id=i,label=p['label'],score=p['score'],box=[p['coordinate'][0]*W/image_size[0],p['coordinate'][1]*H/image_size[1],p['coordinate'][2]*W/image_size[0],p['coordinate'][3]*H/image_size[1]],provenance='existing local PP-S file, independently verified caption hypothesis') for i,p in enumerate(pred['res']['boxes'])]
    pairs,ptrace=caption_pairs(order['sequence'],ls,predictions,body,cfg);r=apply_relations(order['sequence'],ls,pairs,body,cfg);r.update(caption_pairs=pairs,caption_trace=ptrace,prediction_sha256=hashlib.sha256(pathlib.Path(prediction).read_bytes()).hexdigest(),new_inference_calls=0,phase_seconds=time.perf_counter()-start,source_geometry_tree_unchanged=True)
    (out/'flow-relations-private.json').write_text(json.dumps(r,indent=2));(out/'enriched-source-leaves-private.json').write_text(json.dumps(list(ls.values()),indent=2));print(json.dumps({'caption_pairs':len(pairs),'accepted_relations':len(r['relations']),'phase_seconds':r['phase_seconds'],'trace':r['trace']}));return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('treefolder');p.add_argument('prediction');p.add_argument('out');p.add_argument('--image-width',type=int,required=True);p.add_argument('--image-height',type=int,required=True);a=p.parse_args();diagnose(a.folder,a.treefolder,a.prediction,(a.image_width,a.image_height),a.out)
