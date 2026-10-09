"""Typed geometry evidence; candidate Unicode is never used as prose content."""
import math,statistics,re
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class GeometryConfig:
    baseline_tolerance_em:float=.2
    small_run_minimum_glyphs:int=4
    small_run_minimum_width_em:float=2.
    small_run_maximum_gap_em:float=1.5
    larger_font_ratio:float=1.15
    larger_anchor_reach_em:float=1.
    small_script_ratio:float=.85
    minimum_script_vertical_em:float=.12
    maximum_script_vertical_em:float=1.5
    script_horizontal_gap_em:float=.4
    minimum_script_fraction:float=.08
    maximum_fraction_bar_width_em:float=3.
    maximum_fraction_region_height_em:float=2.5
    fraction_vertical_reach_em:float=.8
    tall_glyph_height_ratio:float=1.8
    main_row_alignment_em:float=2.
    rule_maximum_height_em:float=.15
    rule_minimum_width_em:float=.5
    rule_minimum_aspect:float=3.
    angle_tolerance_radians:float=.02
    maximum_rotated_page_area:float=.15
    maximum_rotated_page_extent:float=.8
    maximum_rotated_glyphs:int=256
    marginal_band_fraction:float=.08
    maximum_equation_label_characters:int=8
    maximum_equation_label_gap_em:float=10.
    equation_label_baseline_tolerance_em:float=.6
    def json(self):return asdict(self)
def gap(a,b):return max(a[0]-b[2],b[0]-a[2],0)
def union(bs):return [min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)]
def size(u):return max((g['size'] for g in u['glyphs']),default=0)
def local_anchor_ids(units,body,cfg=GeometryConfig()):
    # Coherent small lines can be independent anchors. Never force an isolated
    # script to become a line merely because no Unicode is available.
    rows=[];trace=[];accepted=set()
    for u in sorted(units,key=lambda u:(u['baseline'],u['box'][0])):
        s=size(u);candidates=[r for r in rows if abs(r['baseline']-u['baseline'])<=cfg.baseline_tolerance_em*min(s,r['size']) and max(s,r['size'])<=cfg.larger_font_ratio*min(s,r['size'])]
        if candidates:
            r=min(candidates,key=lambda r:abs(r['baseline']-u['baseline']));r['units'].append(u)
        else:rows.append({'baseline':u['baseline'],'size':s,'units':[u]})
    for row in rows:
        chunks=[[]]
        for u in sorted(row['units'],key=lambda u:u['box'][0]):
            if chunks[-1] and gap(chunks[-1][-1]['box'],u['box'])>cfg.small_run_maximum_gap_em*row['size']:chunks.append([])
            chunks[-1].append(u)
        for us in chunks:
            b=union([u['box'] for u in us]);s=row['size'];n=sum(len(u['glyphs']) for u in us);larger=[v['id'] for v in units if size(v)>cfg.larger_font_ratio*s and gap(v['box'],b)<=cfg.larger_anchor_reach_em*size(v) and abs(v['baseline']-row['baseline'])<=cfg.larger_anchor_reach_em*size(v)]
            ok=n>=cfg.small_run_minimum_glyphs and b[2]-b[0]>=cfg.small_run_minimum_width_em*s and not larger
            trace.append({'rule':'locally_coherent_baseline_anchor','units':[u['id'] for u in us],'accepted':ok,'glyphs':n,'width_em':(b[2]-b[0])/s if s else None,'larger_nearby_anchors':larger,'semantic_unicode_used':False})
            if ok:accepted.update(u['id'] for u in us)
    return accepted,trace

def bounded_script_fraction(gs,objects,paints,body,scripts,cfg):
    # An explicit compact stacked fraction is structural evidence independent
    # of how many ordinary-size glyphs surround it. Global script density alone
    # shrinks when an otherwise unchanged expression gains baseline symbols.
    if not gs or not scripts:return []
    bounds=union([g['box'] for g in gs])
    if bounds[3]-bounds[1]>cfg.maximum_fraction_region_height_em*body:return []
    from fraction_support import propose_support
    accepted=[]
    for paint in objects:
        if paint['id'] not in paints or not paint.get('horizontal_stroke'):continue
        b=paint['box'];w,h=b[2]-b[0],b[3]-b[1]
        if not (cfg.rule_minimum_width_em*body<=w<=cfg.maximum_fraction_bar_width_em*body and 0<h<=cfg.rule_maximum_height_em*body and w/h>=cfg.rule_minimum_aspect):continue
        local=propose_support(b,gs,cfg.fraction_vertical_reach_em*body,body=body)
        if local and set(scripts)&{g['id'] for g in local}:accepted.append(paint['id'])
    return accepted

def formula_evidence(units,objects,body,cfg=GeometryConfig()):
    gs=[g for u in units for g in u['glyphs'] if g.get('native_object_ink_observed',True)];main=[g for g in gs if g['size']>=cfg.small_script_ratio*body];scripts=[]
    for g in gs:
        candidates=[a for a in main if g['size']<=cfg.small_script_ratio*a['size'] and cfg.minimum_script_vertical_em*a['size']<=abs(g['baseline']-a['baseline'])<=cfg.maximum_script_vertical_em*a['size'] and gap(g['box'],a['box'])<=cfg.script_horizontal_gap_em*a['size']]
        if candidates:scripts.append(g['id'])
    tall=[g['id'] for g in gs if g['box'][3]-g['box'][1]>=cfg.tall_glyph_height_ratio*g['size']];rows=[]
    for g in sorted(main,key=lambda g:g['baseline']):
        r=next((r for r in rows if abs(r['baseline']-g['baseline'])<=cfg.baseline_tolerance_em*body),None)
        if r is None:rows.append({'baseline':g['baseline'],'glyphs':[g]})
        else:r['glyphs'].append(g)
    rows=[r for r in rows if len(r['glyphs'])>=2];starts=[min(g['box'][0] for g in r['glyphs']) for r in rows];aligned=len(rows)>=2 and max(starts)-min(starts)<=cfg.main_row_alignment_em*body
    paints={o for u in units for o in u.get('objects',[])};rules=[o['id'] for o in objects if o['id'] in paints and o.get('type')!=1 and o['box'][2]-o['box'][0]>=cfg.rule_minimum_width_em*body and o['box'][3]-o['box'][1]<=cfg.rule_maximum_height_em*body and (o['box'][2]-o['box'][0])/max(o['box'][3]-o['box'][1],1e-9)>=cfg.rule_minimum_aspect]
    fraction=len(scripts)/max(len(gs),1);bounded=bounded_script_fraction(gs,objects,paints,body,scripts,cfg);ok=(fraction>=cfg.minimum_script_fraction and bool(tall or rules or (aligned and len(scripts)>=2))) or bool(bounded)
    return {'pass_native_structure':ok,'script_glyphs':len(scripts),'glyphs':len(gs),'script_fraction':fraction,'tall_glyphs':len(tall),'native_rules':len(rules),'main_baseline_rows':len(rows),'aligned_rows':aligned,'semantic_unicode_used':False,'bounded_script_fraction_rules':bounded}

def label_extension_ok(units,seed,allunits,body,cfg=GeometryConfig()):
    core=[u for u in units if seed[0]<=(u['box'][0]+u['box'][2])/2<=seed[2] and seed[1]<=(u['box'][1]+u['box'][3])/2<=seed[3]];outside=[u for u in units if u not in core];trace=[]
    if not core or not outside:return False,trace
    for u in outside:
        gs=u['glyphs'];text=''.join(g['char'] for g in gs);b=u['box'];baseline=statistics.median(g['baseline'] for g in gs);baseline_rows=[]
        for v in core:
            mains=[g for g in v['glyphs'] if g['size']>=cfg.small_script_ratio*body]
            if not mains:continue
            vb=statistics.median(g['baseline'] for g in mains)
            if abs(vb-baseline)>cfg.equation_label_baseline_tolerance_em*body:continue
            row=next((r for r in baseline_rows if abs(r['baseline']-vb)<=cfg.baseline_tolerance_em*body),None)
            if row is None:baseline_rows.append({'baseline':vb,'units':[v]})
            else:row['units'].append(v)
        rows=baseline_rows[0]['units'] if len(baseline_rows)==1 else []
        rb=union([v['box'] for v in rows]) if rows else None
        corridor=[min(b[0],rb[2]),min(b[1],rb[1]),max(b[0],rb[2]),max(b[3],rb[3])] if rb else None
        intruders=[v['id'] for v in allunits if v not in units and corridor and min(v['box'][2],corridor[2])>max(v['box'][0],corridor[0]) and min(v['box'][3],corridor[3])>max(v['box'][1],corridor[1])]
        ok=bool(all(g['unicode_known'] for g in gs) and len(text)<=cfg.maximum_equation_label_characters and re.fullmatch(r'(?:[0-9]+[a-z]?|\([0-9]+[a-z]?\))',text) and rb and b[0]>=rb[2] and gap(b,rb)<=cfg.maximum_equation_label_gap_em*body and not intruders)
        trace.append({'unit':u['id'],'accepted':ok,'intervening_units':intruders,'certified_numeric_label_only':True})
        if not ok:return False,trace
    return True,trace
