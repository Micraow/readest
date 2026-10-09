"""Direct native glyph origins outrank derived word/row cache values."""
import collections,copy,json,pathlib,statistics
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class BaselineConfig:
    substantial_size_ratio:float=.86
    cluster_tolerance_em:float=.08
    minimum_dominant_fraction:float=.6
    comparison_epsilon_pt:float=.0001
    def json(self):return asdict(self)
def select(glyphs,cfg=BaselineConfig()):
    gs=[g for g in glyphs if g.get('native_object_ink_observed',True) and g['size']>0]
    if not gs:return None,{'accepted':False,'reason':'no observed native glyph'}
    largest=max(g['size'] for g in gs);gs=[g for g in gs if g['size']>=largest*cfg.substantial_size_ratio];clusters=[]
    for g in sorted(gs,key=lambda g:g['baseline']):
        c=next((c for c in clusters if abs(statistics.median(x['baseline'] for x in c)-g['baseline'])<=cfg.cluster_tolerance_em*largest),None)
        if c is None:clusters.append([g])
        else:c.append(g)
    clusters.sort(key=lambda c:(-len(c),statistics.median(g['baseline'] for g in c)));fraction=len(clusters[0])/len(gs);tie=len(clusters)>1 and len(clusters[0])==len(clusters[1]);ok=not tie and fraction>=cfg.minimum_dominant_fraction
    return (statistics.median(g['baseline'] for g in clusters[0]) if ok else None),{'accepted':ok,'major_glyphs':len(gs),'clusters':[{'native_baseline':statistics.median(g['baseline'] for g in c),'glyphs':len(c)} for c in clusters],'dominant_fraction':fraction,'semantic_unicode_used':False}
def normalize(plan,cfg=BaselineConfig()):
    result=copy.deepcopy(plan);trace=[]
    for u in result['units']:
        if u['kind']!='native_word':continue
        baseline,evidence=select(u['glyphs'],cfg);old=u.get('baseline');row={'unit':u['id'],'old_cached_baseline':old,'native_baseline':baseline,**evidence};trace.append(row)
        if baseline is None:raise ValueError('ambiguous substantial native baselines: '+u['id'])
        u['baseline']=baseline;u['baseline_provenance']='dominant direct native glyph origin';row['changed']=old is None or abs(old-baseline)>cfg.comparison_epsilon_pt
    return result,trace

def run(folder):
    folder=pathlib.Path(folder);p=folder/'plan-private.json';plan=json.loads(p.read_text());result,trace=normalize(plan);p.write_text(json.dumps(result,ensure_ascii=False,indent=2));(folder/'baseline-evidence-private.json').write_text(json.dumps({'config':BaselineConfig().json(),'trace':trace},indent=2));return {'native_words':len(trace),'stale_baselines_repaired':sum(r['changed'] for r in trace)}

def update_asset_baselines(folder):
    folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());um={u['id']:u for u in plan['units']};p=folder/'native-unit-assets-private.json';data=json.loads(p.read_text());s=data['scale'];body=data['body_font'];trace=[]
    for a in data['results']:
        u=um[a['id']]
        if u['kind']!='native_word' or a.get('empty'):continue
        old=a['descent_em'];a['descent_em']=(a['asset_pixel_box'][3]/s-u['baseline'])/body;trace.append({'unit':u['id'],'old_descent_em':old,'new_descent_em':a['descent_em'],'asset_pixels_changed':False})
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2));(folder/'baseline-asset-metadata-private.json').write_text(json.dumps(trace,indent=2))
