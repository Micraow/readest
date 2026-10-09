"""Resolve inseparable ink with bounded native-character interval groups.

No character string, source page ID or font-name special case. Source-native
index adjacency is evidence for a *local* interval, not global reading order.
"""
import argparse,collections,json,pathlib,statistics,unicodedata,sys
from dataclasses import dataclass
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-inkownership/code'))
import numpy as np
from PIL import Image
from ink_config import InkConfig,LocalGroupConfig
from ink_ownership import partition_alpha,frozen

@dataclass(frozen=True)
class InlineConfig(LocalGroupConfig):
    fraction_nearest_row_tolerance_em: float = .25

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
  return gs,paints,frozen.box_union(boxes) if boxes else None
 for iteration in range(len(units)+1):
  before=set(selected);gs,paints,box=current()
  if not gs:return None,trace+[{'rule':'native_interval_requires_visible_glyphs','accepted':False,'retained_paint_ids':sorted(paints)}]
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
   above=[g for g in near if g['box'][3]<b[1]];below=[g for g in near if g['box'][1]>b[3]]
   if above and below:
    atop=min(b[1]-g['box'][3] for g in above);btop=min(g['box'][1]-b[3] for g in below);tol=cfg.fraction_nearest_row_tolerance_em*body
    nearest=[g for g in above if b[1]-g['box'][3]<=atop+tol]+[g for g in below if g['box'][1]-b[3]<=btop+tol]
    selected.update(owner[g['id']] for g in nearest);trace.append({'rule':'nearest_fraction_rows','paint':obj['id'],'glyphs':[g['id'] for g in nearest],'rejected_farther_glyphs':[g['id'] for g in near if g not in nearest],'accepted':True})
  for u in units:
   if u['id'] in selected or u['kind']!='native_word':continue
   ugs=u['glyphs']
   if not ugs:trace.append({'rule':'neighbor_requires_native_glyphs','owner':u['id'],'accepted':False});continue
   usize=max(g['size'] for g in ugs);ubase=statistics.median(g['baseline'] for g in ugs)
   script=usize<largest*cfg.script_size_ratio and abs(ubase-baseline)<=cfg.script_baseline_reach_em*body and any(frozen.dist(u['box'],g['box'])<=cfg.script_near_em*body for g in gs)
   inline=mathlike(u.get('text',''),cfg) and abs(ubase-baseline)<=cfg.same_baseline_em*body and frozen.dist(u['box'],box)<=cfg.math_neighbor_gap_em*body
   if script or inline:selected.add(u['id']);trace.append({'rule':'script_or_short_math_neighbor','owner':u['id'],'script':script,'same_baseline_mathlike':inline,'accepted':True})
  if selected==before:
   gs,paints,box=current();lo=min(g['source_index'] for g in gs);hi=max(g['source_index'] for g in gs);inside={g['id'] for g in visible if lo<=g['source_index']<=hi};owned={g['id'] for g in gs}
   if inside!=owned:return None,trace+[{'rule':'native_interval_contiguity','accepted':False}]
   merged=dict(id='interval-'+str(lo)+'-'+str(hi),kind='inline_native_group',box=box,glyphs=sorted(gs,key=lambda g:g['source_index']),objects=sorted(paints,key=lambda p:int(p[1:])),source_interval=[lo,hi+1],baseline=baseline,former_units=sorted(selected),selection_mapping='not certified: mathematical structure is not a plain-text Unicode string')
   return merged,trace+[{'rule':'bounded_local_group','accepted':True,'width_em':(box[2]-box[0])/body,'height_em':(box[3]-box[1])/body,'characters':len(gs)}]
 raise RuntimeError('local closure did not converge')
