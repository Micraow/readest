"""Resolve inseparable ink with bounded native-character interval groups.

No character string, source page ID or font-name special case. Source-native
index adjacency is evidence for a *local* interval, not global reading order.
"""
import argparse,collections,json,pathlib,statistics,unicodedata
import numpy as np
from PIL import Image
from ink_config import InkConfig,LocalGroupConfig
from ink_ownership import partition_alpha,frozen

def mathlike(text,cfg):
 runs=[];run=''
 for c in text:
  if c.isalpha():run+=c
  elif run:runs.append(run);run=''
 if run:runs.append(run)
 return bool(text) and all(len(r)<=cfg.short_identifier_characters for r in runs)

def propose(seed_ids,units,glyphs,objects,body,cfg):
 unitmap={u['id']:u for u in units};owner={g['id']:u['id'] for u in units for g in u['glyphs']};selected=set(seed_ids);trace=[];visible=[g for g in glyphs if g['id'] in owner]
 def current():
  gs=[g for g in visible if owner[g['id']] in selected];paints={p for u in units if u['id'] in selected for p in u.get('objects',[])};boxes=[g['box'] for g in gs]+[o['box'] for o in objects if o['id'] in paints]
  return gs,paints,frozen.box_union(boxes)
 for iteration in range(len(units)+1):
  before=set(selected);gs,paints,box=current()
  if box[2]-box[0]>cfg.max_width_em*body or box[3]-box[1]>cfg.max_height_em*body or len(gs)>cfg.max_visible_characters:return None,trace+[{'rule':'bounded_local_group','accepted':False,'box':box,'characters':len(gs)}]
  lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs)
  for g in visible:
   if lo<=g['source_index']<=hi:selected.add(owner[g['id']])
  trace.append({'rule':'native_interval_closure','range_inclusive':[lo,hi],'owners':sorted(selected)})
  gs,paints,box=current();largest=max(g['size'] for g in gs);base=[g for g in gs if g['size']>=largest*cfg.script_size_ratio];baseline=statistics.median(g['baseline'] for g in base)
  # A narrow fraction bar needs both its numerator and denominator geometry.
  for obj in objects:
   if obj['id'] not in paints or not obj.get('horizontal_stroke'):continue
   b=obj['box'];near=[g for g in visible if b[0]<=frozen.center(g['box'])[0]<=b[2] and frozen.dist(b,g['box'])<=cfg.fraction_vertical_reach_em*body]
   if any(g['box'][3]<b[1] for g in near) and any(g['box'][1]>b[3] for g in near):
    selected.update(owner[g['id']] for g in near);trace.append({'rule':'fraction_geometry_closure','paint':obj['id'],'glyphs':[g['id'] for g in near],'accepted':True})
  for u in units:
   if u['id'] in selected or u['kind']!='native_word':continue
   ugs=u['glyphs'];usize=max(g['size'] for g in ugs);ubase=statistics.median(g['baseline'] for g in ugs)
   script=usize<largest*cfg.script_size_ratio and abs(ubase-baseline)<=cfg.script_baseline_reach_em*body and any(frozen.dist(u['box'],g['box'])<=cfg.script_near_em*body for g in gs)
   inline=mathlike(u.get('text',''),cfg) and abs(ubase-baseline)<=cfg.same_baseline_em*body and frozen.dist(u['box'],box)<=cfg.math_neighbor_gap_em*body
   if script or inline:selected.add(u['id']);trace.append({'rule':'script_or_short_math_neighbor','owner':u['id'],'script':script,'same_baseline_mathlike':inline,'accepted':True})
  if selected==before:
   gs,paints,box=current();lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs);inside={g['id'] for g in visible if lo<=g['source_index']<=hi};owned={g['id'] for g in gs}
   if inside!=owned:return None,trace+[{'rule':'native_interval_contiguity','accepted':False}]
   merged=dict(id='interval-'+str(lo)+'-'+str(hi),kind='inline_native_group',box=box,glyphs=sorted(gs,key=lambda g:g['source_index']),objects=sorted(paints,key=lambda p:int(p[1:])),source_interval=[lo,hi+1],baseline=baseline,former_units=sorted(selected),selection_mapping='not certified: mathematical structure is not a plain-text Unicode string')
   return merged,trace+[{'rule':'bounded_local_group','accepted':True,'width_em':(box[2]-box[0])/body,'height_em':(box[3]-box[1])/body,'characters':len(gs)}]
 raise RuntimeError('local closure did not converge')

def coalesce(folder,cfg=LocalGroupConfig()):
 folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());records=json.loads((folder/'ownership-records.json').read_text());old_summary=json.loads((folder/'ownership-summary.json').read_text());units=plan['units'];groups=[];traces=[];rejections=[]
 seeds=[]
 for rec in records:
  if rec['ambiguous_ink_pixels']:
   for decision in rec['component_decisions']:
    owners=decision.get('confident_owners',[])
    if not decision['accepted'] and len(owners)>1:seeds.append(set(owners))
 for seed in seeds:
  existing={u['id'] for u in units}
  if not seed<=existing:continue
  group,trace=propose(seed,units,plan['glyphs'],plan['objects'],old_summary['body_font'],cfg);traces.append({'seeds':sorted(seed),'decisions':trace})
  if group is None:rejections.append(sorted(seed));continue
  replaced=set(group['former_units']);units=[u for u in units if u['id'] not in replaced]+[group];groups.append(group)
 owners={g['id']:u['id'] for u in units for g in u['glyphs']};by_obj=collections.defaultdict(list)
 for g in plan['glyphs']:
  if g['id'] in owners:by_obj[g['object_id']].append(g)
 objpatches=collections.defaultdict(list)
 for owner,patches in plan['patches'].items():
  for patch in patches:objpatches[patch['native_object']].append(patch)
 newpatches=collections.defaultdict(list);newrecords=[];sub=folder/'coalesced';sub.mkdir(exist_ok=True)
 inkcfg=InkConfig(**old_summary['config'])
 for rec in records:
  oid=rec['object_id'];pbox=rec['pixel_box'];x0,y0,x1,y1=pbox;rgba=np.zeros((y1-y0,x1-x0,4),np.uint8)
  for p in objpatches[oid]:
   a=np.array(Image.open(folder/p['file']).convert('RGBA'));m=a[:,:,3]>0;rgba[m]=a[m]
  if rec['quarantined_ink_pixels']:
   a=np.array(Image.open(folder/f'{oid}-UNRESOLVED.png').convert('RGBA'));m=a[:,:,3]>0;rgba[m]=a[m]
  parts,residual,stats=partition_alpha(rgba,pbox,by_obj[oid],owners,inkcfg);newrecords.append({**rec,**stats})
  for owner,pixels in parts.items():
   if not np.any(pixels[:,:,3]):continue
   name=f'{oid}-{owner}.png';Image.fromarray(pixels,'RGBA').save(sub/name);newpatches[owner].append(dict(file=name,pixel_box=pbox,paint_seq=rec['seq'],native_object=oid))
  if stats['quarantined_ink_pixels']:Image.fromarray(residual,'RGBA').save(sub/f'{oid}-UNRESOLVED.png')
 result=dict(groups=len(groups),native_rerenders=0,config=cfg.json(),rejected_seeds=rejections,ambiguous_ink_pixels=sum(r['ambiguous_ink_pixels'] for r in newrecords),unassigned_ink_pixels=sum(r['unassigned_ink_pixels'] for r in newrecords),all_object_pixels_uniquely_assigned=all(r['all_ink_uniquely_assigned'] for r in newrecords),all_object_pixels_conserved=all(r['conservation_with_quarantine'] for r in newrecords),group_summaries=[{'id':g['id'],'source_interval':g['source_interval'],'characters':len(g['glyphs']),'width_em':(g['box'][2]-g['box'][0])/old_summary['body_font'],'height_em':(g['box'][3]-g['box'][1])/old_summary['body_font'],'former_units':g['former_units']} for g in groups],scope='local native-index contiguity + bounded geometry, not a semantic global reading-order certificate')
 (sub/'plan-private.json').write_text(json.dumps({**plan,'units':units,'patches':newpatches},ensure_ascii=False,indent=2));(sub/'ownership-records.json').write_text(json.dumps(newrecords,indent=2));(sub/'ownership-summary.json').write_text(json.dumps({**old_summary,'coalescing':result},indent=2));(sub/'coalescing-result.json').write_text(json.dumps(result,indent=2));(sub/'coalescing-trace-private.json').write_text(json.dumps(traces,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();print(json.dumps(coalesce(a.folder)))
