"""Opt-in indivisible graphical regions; never infer their internal reading order.

Protected native leaves, or independently supported internal graphic labels,
may be grouped. The unchanged safe-cut tree must
then prove their order relative to all remaining content. No ink is reconstructed
here; existing exact replay/support and native-composite gates remain mandatory.
"""
import collections,hashlib,json,math,pathlib,sys
from dataclasses import dataclass,asdict
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-order-tree/code'))
from region_tree import build_tree,AmbiguousOrder,bounds
@dataclass(frozen=True)
class AtomicRegionConfig:
 maximum_original_leaves:int=32
 maximum_page_width_fraction:float=.9
 maximum_page_height_fraction:float=.35
 maximum_page_area_fraction:float=.25
 maximum_group_iterations:int=16
 minimum_image_prior_score:float=.65
 minimum_graphic_coverage:float=.6
 maximum_prior_conflict_iou:float=.2
 maximum_internal_text_band_fraction:float=.2
 maximum_graphic_gap_height_ratio:float=.5
 def json(self):return asdict(self)
def valid_box(box):return isinstance(box,(list,tuple)) and len(box)==4 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in box) and box[0]<box[2] and box[1]<box[3]
def intersects(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def _propose(ids,leaves,page,cfg=AtomicRegionConfig(),allow_text=False):
 lookup={x['id']:x for x in leaves};trace=dict(accepted=False,rule='indivisible_protected_native_region',internal_order_inferred=False)
 if len(ids)<2 or any(x not in lookup for x in ids):return None,trace|dict(reason='missing_or_singleton_conflict')
 chosen=[lookup[x] for x in sorted(ids)]
 if any(not valid_box(v.get('box')) for v in leaves):return None,trace|dict(reason='invalid_source_geometry')
 original=[x for v in chosen for x in v.get('source_leaf_ids',[v['id']])]
 if any(v.get('role') not in (('protected_local','source_line') if allow_text else ('protected_local',)) for v in chosen):return None,trace|dict(reason='prose_or_unknown_leaf_cannot_be_frozen')
 if len(original)>cfg.maximum_original_leaves:return None,trace|dict(reason='leaf_budget')
 box=bounds(chosen);w,h=box[2]-box[0],box[3]-box[1];W,H=page
 if w<=0 or h<=0 or min(box[:2])<0 or box[2]>W or box[3]>H or w>cfg.maximum_page_width_fraction*W or h>cfg.maximum_page_height_fraction*H or w*h>cfg.maximum_page_area_fraction*W*H:return None,trace|dict(reason='bounded_region_limit')
 foreign=[v for v in leaves if v['id'] not in ids]
 if any(intersects(v['box'],box) for v in foreign):return None,trace|dict(reason='foreign_leaf_intersects_region')
 indexes=sorted(i for v in chosen for i in v.get('native_indexes',[]))
 if indexes and any(min(indexes)<=i<=max(indexes) for v in foreign for i in v.get('native_indexes',[])):return None,trace|dict(reason='foreign_native_character_interval')
 units=[u for v in chosen for u in v['unit_ids']]
 if len(set(units))!=len(units) or len(set(original))!=len(original):return None,trace|dict(reason='duplicate_source_membership')
 uid='atomic-native-'+hashlib.sha256('\n'.join(sorted(original)).encode()).hexdigest()[:16]
 if uid in lookup:return None,trace|dict(reason='identity_collision')
 group=dict(id=uid,box=box,unit_ids=units,native_indexes=indexes,role='protected_local',source_leaf_ids=original,member_leaf_ids=sorted(ids),provenance='bounded indivisible native region; original relative geometry retained; no internal semantic order',selection_mapping='refuse whole native composite')
 return group,trace|dict(accepted=True,reason='bounded_isolated_protected_native_leaves',original_leaves=len(original),source_units=len(units),region_box=box)
def propose(ids,leaves,page,cfg=AtomicRegionConfig()):
 return _propose(ids,leaves,page,cfg)
def rectangle_area(box):return max(0,box[2]-box[0])*max(0,box[3]-box[1])
def rectangle_union_area(boxes):
 xs=sorted({b[i] for b in boxes for i in [0,2]});total=0
 for x0,x1 in zip(xs,xs[1:]):
  ys=sorted((b[1],b[3]) for b in boxes if b[0]<x1 and b[2]>x0);length=0;end=None
  for a,b in ys:
   length+=max(0,b-max(a,end)) if end is not None else b-a;end=max(b,end) if end is not None else b
  total+=(x1-x0)*length
 return total
def propose_image_prior(prior,priors,leaves,page,cfg=AtomicRegionConfig()):
 trace=dict(accepted=False,rule='image_prior_with_closed_dominant_native_graphic_support',internal_order_inferred=False)
 if prior.get('label') not in ('image','figure') or not isinstance(prior.get('score'),(int,float)) or not math.isfinite(prior['score']) or prior['score']<cfg.minimum_image_prior_score:return None,trace|dict(reason='no_independent_image_prior')
 seed=prior.get('box')
 if not valid_box(seed):return None,trace|dict(reason='invalid_prior_geometry')
 for other in priors:
  if other is prior or other.get('score',0)<cfg.minimum_image_prior_score or other.get('label') not in ('image','figure','chart','table','formula'):continue
  b=other['box'];over=rectangle_area([max(seed[0],b[0]),max(seed[1],b[1]),min(seed[2],b[2]),min(seed[3],b[3])]);den=rectangle_area(seed)+rectangle_area(b)-over
  if den>0 and over/den>cfg.maximum_prior_conflict_iou:return None,trace|dict(reason='conflicting_prior_regions')
 inside=lambda b:seed[0]<=b[0]<=b[2]<=seed[2] and seed[1]<=b[1]<=b[3]<=seed[3]
 if any(not valid_box(v.get('box')) for v in leaves):return None,trace|dict(reason='invalid_source_geometry')
 chosen=[v for v in leaves if inside(v['box'])]
 if any(intersects(v['box'],seed) and not inside(v['box']) for v in leaves):return None,trace|dict(reason='source_leaf_crosses_prior_boundary')
 graphics=[v for v in chosen if v.get('role')=='protected_local' and not v.get('native_indexes')]
 if not graphics or len(chosen)<2:return None,trace|dict(reason='no_native_graphic_support')
 region=bounds(chosen);coverage=rectangle_union_area([v['box'] for v in graphics])/rectangle_area(region)
 if coverage<cfg.minimum_graphic_coverage:return None,trace|dict(reason='graphic_support_not_dominant',graphic_coverage=coverage)
 # Independent text/caption/footnote evidence vetoes freezing prose even if
 # an overlapping image detector box is large. Geometry cannot establish semantics.
 text=[v for v in chosen if v.get('native_indexes') or v.get('role')=='source_line']
 prose_labels={'text','paragraph','paragraph_title','footnote','footnotes','footer','caption','figure_title','chart_title','table_title','reference','reference_content'}
 if any(p.get('label') in prose_labels and p.get('score',0)>=cfg.minimum_image_prior_score and any(intersects(v['box'],p['box']) for v in text) for p in priors if valid_box(p.get('box'))):return None,trace|dict(reason='independent_prose_or_caption_evidence')
 # Only a shallow internal strip bracketed by native graphic rows may enter.
 # Tail labels/captions, footnotes, body paragraphs and broad inter-row prose
 # stay outside this narrow experimental authority. Do not extend the prior.
 for v in text:
  b=v['box'];above=[g for g in graphics if g['box'][3]<=b[1] and min(g['box'][2],b[2])>max(g['box'][0],b[0])];below=[g for g in graphics if g['box'][1]>=b[3] and min(g['box'][2],b[2])>max(g['box'][0],b[0])]
  if not above or not below:return None,trace|dict(reason='text_not_bracketed_by_native_graphic_rows')
  top=max(g['box'][3] for g in above);bottom=min(g['box'][1] for g in below);support=min(max(g['box'][3]-g['box'][1] for g in above),max(g['box'][3]-g['box'][1] for g in below))
  if bottom-top>cfg.maximum_graphic_gap_height_ratio*support:return None,trace|dict(reason='internal_text_gap_too_tall')
 if text:
  band=max(v['box'][3] for v in text)-min(v['box'][1] for v in text)
  if band>cfg.maximum_internal_text_band_fraction*(region[3]-region[1]):return None,trace|dict(reason='internal_text_band_too_tall')
 group,gate=_propose({v['id'] for v in chosen},leaves,page,cfg,allow_text=True)
 if group is None:return None,trace|dict(reason=gate['reason'],graphic_coverage=coverage)
 group['provenance']='independent image prior plus closed dominant native graphical support; all enclosed text stays at original coordinates; no internal semantic order'
 return group,trace|dict(accepted=True,reason='closed_local_native_image_region',graphic_coverage=coverage,text_leaves_kept_spatially=sum(v['role']=='source_line' for v in chosen),original_leaves=len(chosen),source_units=len(group['unit_ids']),region_box=region)
def native_interval_conflicts(sequence,leaves):
 lookup={v['id']:v for v in leaves};ordered=[v for i in sequence if (v:=lookup[i]).get('native_indexes')]
 return [[a['id'],b['id']] for a,b in zip(ordered,ordered[1:]) if min(b['native_indexes'])<max(a['native_indexes'])]
def build(leaves,page,body,cfg=AtomicRegionConfig(),image_priors=()):
 initial=collections.Counter(x for v in leaves for x in v.get('source_leaf_ids',[v['id']]));source_units=collections.Counter(u for v in leaves for u in v['unit_ids']);current=list(leaves);decisions=[]
 indexes=collections.Counter(i for v in leaves for i in v.get('native_indexes',[]))
 if any(n!=1 for n in indexes.values()):raise ValueError('input native character membership not unique')
 if any(n!=1 for n in initial.values()) or any(n!=1 for n in source_units.values()):raise ValueError('input leaf/unit membership not unique')
 for prior in image_priors:
  group,decision=propose_image_prior(prior,image_priors,current,page,cfg);decisions.append(decision)
  if group is not None:
   ids=set(group['member_leaf_ids']);current=[v for v in current if v['id'] not in ids]+[group]
 for iteration in range(cfg.maximum_group_iterations+1):
  try:
   result=build_tree(current,body);break
  except AmbiguousOrder as exc:
   error=exc.args[0]
   if iteration==cfg.maximum_group_iterations or not isinstance(error,dict) or not error.get('conflicts'):return None,current,decisions+[dict(accepted=False,reason='unresolved_safe_tree',detail=error)]
   links=collections.defaultdict(set)
   for a,b in error['conflicts']:links[a].add(b);links[b].add(a)
   remaining=set(links);groups=[]
   while remaining:
    component={min(remaining)};todo=list(component);remaining-=component
    while todo:
     new=links[todo.pop()]-component;component|=new;remaining-=new;todo.extend(new)
    groups.append(component)
   changed=False
   for ids in groups:
    group,decision=propose(ids,current,page,cfg);decisions.append(decision)
    if group is None:continue
    current=[v for v in current if v['id'] not in ids]+[group];changed=True
   if not changed:return None,current,decisions
 else:raise AssertionError('bounded iteration failure')
 if native_interval_conflicts(result['sequence'],current):return None,current,decisions+[dict(accepted=False,reason='native_interval_order_contradicts_safe_tree')]
 expanded=collections.Counter(x for v in current for x in v.get('source_leaf_ids',[v['id']]));emitted=collections.Counter(u for v in current for u in v['unit_ids'])
 final_indexes=collections.Counter(i for v in current for i in v.get('native_indexes',[]))
 if expanded!=initial or emitted!=source_units or final_indexes!=indexes:raise RuntimeError('atomic source membership changed')
 return result|dict(atomic_region_config=cfg.json(),original_leaf_bijection=True,source_unit_bijection=True,native_character_bijection=True,internal_graphic_order_inferred=False),current,decisions

def verify_native_graphic_support(leaves,plan,assets,folder,cfg=AtomicRegionConfig()):
 """Count independently rendered native support, not only graphical boxes.

 A sparse frame cannot gain graphic dominance from its large bounding box.
 This gate runs after exact source-support verification, before reader output.
 """
 import numpy as np
 from PIL import Image
 folder=pathlib.Path(folder);units={u['id']:u for u in plan['units']};lookup={a['id']:a for a in assets['results']};reports=[]
 for leaf in leaves:
  if not leaf.get('source_leaf_ids'):continue
  members=[lookup[u] for u in leaf['unit_ids']];l=min(a['asset_pixel_box'][0] for a in members);t=min(a['asset_pixel_box'][1] for a in members);r=max(a['asset_pixel_box'][2] for a in members);b=max(a['asset_pixel_box'][3] for a in members);support=np.zeros((b-t,r-l),np.uint8)
  for u,a in zip(leaf['unit_ids'],members):
   if units[u]['glyphs']:continue
   im=np.asarray(Image.open(folder/a['file']).convert('RGBA'));x0,y0,x1,y1=a['asset_pixel_box'];assert im.shape[:2]==(y1-y0,x1-x0);mask=im[:,:,3]>0;view=support[y0-t:y1-t,x0-l:x1-l];assert not np.any(view[mask]),'native graphic support overlaps';view[mask]=1
  count=int(np.count_nonzero(support));fraction=count/support.size
  reports.append(dict(native_graphic_support_pixels=count,region_pixel_area=int(support.size),native_graphic_coverage=fraction,accepted=fraction>=cfg.minimum_graphic_coverage))
 return reports
