"""Keep a proven panel/label row spatially intact between independent anchors.

No semantic label-to-panel order is inferred. Native repeated geometry supplies
one-to-one columns, and an independent figure-caption region closes the tail.
"""
import pathlib,sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-flow-relations/code'))
from flow_relations import RelationConfig,inside,overlap,area,iou
from paragraph_geometry import ParagraphGeometryConfig
from atomic_native_regions import _propose,AtomicRegionConfig,build,native_interval_conflicts

def close(leaves,tree,original_leaves,priors,page,body,cfg=AtomicRegionConfig()):
 current=list(leaves);trace=[];rc=RelationConfig();gc=ParagraphGeometryConfig();position={x:i for i,x in enumerate(tree['sequence'])};original={l['id']:l for l in original_leaves}
 for caption in priors:
  if caption['label']!='figure_title' or caption['score']<rc.minimum_caption_confidence:continue
  reason='conflicting_caption_priors' if any(p is not caption and p['label'] in rc.caption_labels and p['score']>=rc.minimum_caption_confidence and iou(p['box'],caption['box'])>rc.conflict_iou for p in priors) else None;native_caption=sorted([l for l in current if area(overlap(l['box'],caption['box']))>0],key=lambda l:position[l['id']])
  if not reason and (not native_caption or any(l['role']!='source_line' or not inside(l['box'],caption['box'],rc.caption_margin_em*body) for l in native_caption)):reason='caption_does_not_close_complete_native_lines'
  if not reason:
   positions=[position[l['id']] for l in native_caption]
   if positions!=list(range(positions[0],positions[-1]+1)):reason='caption_native_lines_not_contiguous'
  choices=[];tail=[];panels=[]
  if not reason:
   first=min(l['box'][1] for l in native_caption)
   for l in current:
    if not l.get('source_leaf_ids') or l['role']!='protected_local' or position[l['id']]>=positions[0]:continue
    image_priors=[p for p in priors if p['label']=='image' and p['score']>=cfg.minimum_image_prior_score and inside(l['box'],p['box'])]
    gap=first-l['box'][3];horizontal=max(0,min(l['box'][2],caption['box'][2])-max(l['box'][0],caption['box'][0]))/min(l['box'][2]-l['box'][0],caption['box'][2]-caption['box'][0])
    if len(image_priors)==1 and 0<=gap<=rc.maximum_caption_gap_em*body and horizontal>=rc.minimum_horizontal_overlap:choices.append(l)
   if len(choices)!=1:reason='no_unique_nearby_image_anchor'
  if not reason:
   image=choices[0];tail=[l for l in current if position[image['id']]<position[l['id']]<positions[0]]
   if len(tail)<2 or any(l['role']!='source_line' or not l.get('native_indexes') or 'baseline' not in l for l in tail):reason='tail_is_not_a_repeated_native_text_row'
   elif any(l['box'][1]<image['box'][3] or l['box'][3]>=first or l['box'][0]<image['box'][0]-rc.caption_margin_em*body or l['box'][2]>image['box'][2]+rc.caption_margin_em*body for l in tail):reason='tail_crosses_anchor_boundary'
   elif max(l['baseline'] for l in tail)-min(l['baseline'] for l in tail)>gc.leading_cluster_tolerance_em*body:reason='tail_has_multiple_native_baselines'
   elif any(p['score']>=rc.minimum_caption_confidence and p['label'] not in ('image','figure_title') and any(area(overlap(l['box'],p['box']))>0 for l in tail) for p in priors):reason='independent_nonfigure_region_in_tail'
  if not reason:
   graphics=[original[i] for i in image['source_leaf_ids'] if i in original and original[i]['role']=='protected_local' and not original[i].get('native_indexes')]
   bottom=max((l['box'][3] for l in graphics),default=float('-inf'));panels=[l for l in graphics if abs(l['box'][3]-bottom)<=gc.leading_cluster_tolerance_em*body];matches=[]
   if len(panels)!=len(tail):reason='panel_and_native_text_row_counts_differ'
   else:
    for text in tail:
     center=(text['box'][0]+text['box'][2])/2;matched=[g for g in panels if g['box'][0]<=center<=g['box'][2] and max(0,min(g['box'][2],text['box'][2])-max(g['box'][0],text['box'][0]))/min(g['box'][2]-g['box'][0],text['box'][2]-text['box'][0])>=rc.minimum_horizontal_overlap]
     if len(matched)!=1:reason='no_unique_native_panel_column';break
     matches.append(matched[0]['id'])
    if not reason and len(set(matches))!=len(panels):reason='native_panel_column_reused'
  if not reason:
   group,gate=_propose({choices[0]['id'],*[l['id'] for l in tail]},current,page,cfg,allow_text=True)
   if group is None:reason=gate['reason']
   else:
    group['provenance']='independent image and figure-caption anchors; repeated native panel/text columns; original relative geometry retained; no semantic internal order'
    replaced=set(group['member_leaf_ids']);candidate=[l for l in current if l['id'] not in replaced]+[group];newtree,newleaves,decisions=build(candidate,page,body,cfg)
    if newtree is None or native_interval_conflicts(newtree['sequence'],newleaves):reason='closed_region_has_unresolved_external_order'
    else:current=newleaves;tree=newtree;position={x:i for i,x in enumerate(tree['sequence'])}
  trace.append(dict(accepted=not reason,reason=reason or 'independent_caption_boundary_and_bijective_native_columns',tail_native_lines=len(tail),bottom_native_panels=len(panels),internal_semantic_order_inferred=False,caption_kept_reflowable=True))
 return tree,current,trace
