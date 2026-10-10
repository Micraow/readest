"""Opt-in complete native title-line joins under an independent region prior.

Does not reclassify ordinary body text, change glyphs or widen existing geometry
thresholds. Line order comes from the already verified native region tree.
"""
import collections,copy,pathlib,statistics,sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-inkownership/code'))
from reader_spacing import separators
from apply_region_priors import PriorConfig,area,intersect,iou
from paragraph_geometry import ParagraphGeometryConfig
from build_flow_reader import FlowConfig

def inside(box,outer,margin=0):return all(a>=b-margin for a,b in zip(box[:2],outer[:2])) and all(a<=b+margin for a,b in zip(box[2:],outer[2:]))
def apply_titles(reader,plan,assets,leaves,order,priors,body):
 result=copy.deepcopy(reader);units={u['id']:u for u in plan['units']};aa={a['id']:a for a in assets['results']};pc=PriorConfig();gc=ParagraphGeometryConfig();fc=FlowConfig();position={x:i for i,x in enumerate(order['sequence'])};paths={}
 def walk(n,path='root'):
  if n['kind']=='leaf':paths[n['id']]=path;return
  for i,c in enumerate(n['children']):walk(c,path+('/col'+str(i) if n['kind']=='columns' else ''))
 walk(order['tree']);traces=[]
 for p in priors:
  if p['label']!='paragraph_title':continue
  reason=None;selected=[];blockids=[]
  if p['score']<pc.minimum_confidence:reason='low_title_confidence'
  elif any(q is not p and q['score']>=pc.minimum_confidence and iou(p['box'],q['box'])>pc.conflict_iou for q in priors):reason='conflicting_region_prior'
  if not reason:
   selected=sorted([l for l in leaves if area(intersect(l['box'],p['box']))>0],key=lambda l:position[l['id']])
   if not 2<=len(selected)<=3:reason='not_a_short_multiline_title'
   elif any(l['role']!='source_line' or not inside(l['box'],p['box'],pc.closure_margin_em*body) for l in selected):reason='partial_or_nontext_title_leaf'
   elif len({paths[l['id']] for l in selected})!=1:reason='title_crosses_columns'
  if not reason:
   indexes=[position[l['id']] for l in selected];native=[i for l in selected for i in l['native_indexes']];ids={l['id'] for l in selected}
   if indexes!=list(range(indexes[0],indexes[-1]+1)):reason='title_not_contiguous_in_verified_order'
   elif len(native)!=len(set(native)) or any(min(native)<=i<=max(native) for l in leaves if l['id'] not in ids for i in l['native_indexes']):reason='foreign_native_source_interval'
   elif any(max(a['native_indexes'])>=min(b['native_indexes']) for a,b in zip(selected,selected[1:])):reason='nonmonotone_title_native_order'
  if not reason:
   sizes=[statistics.median(g['size'] for u in l['unit_ids'] for g in units[u]['glyphs']) for l in selected]
   if max(sizes)/min(sizes)>gc.maximum_font_ratio:reason='title_font_size_change'
   elif any(not 0<b['baseline']-a['baseline']<=fc.maximum_paragraph_baseline_gap_em*body for a,b in zip(selected,selected[1:])):reason='title_line_gap_outside_existing_bound'
   elif any(min(a['box'][2],b['box'][2])<=max(a['box'][0],b['box'][0]) for a,b in zip(selected,selected[1:])):reason='title_lines_not_horizontally_related'
  if not reason:
   members={u for l in selected for u in l['unit_ids']};blocks=result['blocks'];blockids=[i for i,b in enumerate(blocks) if any(u in members for t in b['tokens'] for u in t['members'])]
   if len(blockids)<2:reason='title_already_one_block'
   elif blockids!=list(range(blockids[0],blockids[-1]+1)):reason='title_blocks_not_contiguous'
   elif any(blocks[i]['kind']!='paragraph' for i in blockids):reason='protected_title_block'
   elif collections.Counter(u for i in blockids for t in blocks[i]['tokens'] for u in t['members'])!=collections.Counter(members):reason='title_block_contains_external_content'
   elif any(t['kind']!='vector' or len(t['members'])!=1 or units[t['members'][0]]['kind']!='native_word' for i in blockids for t in blocks[i]['tokens']):reason='uncertain_title_token_keeps_existing_layout'
  if not reason:
   combined=[t for i in blockids for t in blocks[i]['tokens']];sequence=[t['members'][0] for t in combined];gaps=separators(sequence,units,aa,plan['glyphs'],body,assets['scale']);gap_by_id={g['left']:g for g in gaps};changed=[]
   for i in blockids[:-1]:
    t=blocks[i]['tokens'][-1];g=gap_by_id[t['members'][0]]
    # Keep all previous native glyph/word geometry, modifying only the new
    # paragraph-internal boundary through the existing source-gap algorithm.
    if g['intervening_visible_records']:reason='visible_native_record_between_title_lines';break
    changed.append(dict(token=t['id'],previous_gap_em=t['gap_em'],new_gap_em=g['gap_em'],source=g['reason']))
   if not reason:
    for i,c in zip(blockids[:-1],changed):blocks[i]['tokens'][-1]['gap_em']=c['new_gap_em']
    blocks[blockids[0]:blockids[-1]+1]=[dict(kind='paragraph',tokens=combined)]
  traces.append(dict(accepted=not reason,reason=reason or 'independent_title_prior_closed_native_lines',native_lines=len(selected),source_blocks=len(blockids),source_line_order_changed=False,changed_boundaries=changed if not reason else []))
 # Resource tables, unit/glyph membership and source order remain untouched.
 before=[(t['id'],t['members']) for b in reader['blocks'] for t in b['tokens']];after=[(t['id'],t['members']) for b in result['blocks'] for t in b['tokens']];assert before==after
 for key in ['resources','events','states','affine_programs']:assert result[key]==reader[key]
 return result,traces
