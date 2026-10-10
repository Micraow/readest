"""Opt-in retain already-supported native line boundaries; no glyph deletion."""
import argparse,copy,json,pathlib
from flow_refinements import hyphen_relation
POLICY='native-retained-line-v1'
def annotate(reader,source_plan,events,bridge):
 data=copy.deepcopy(reader);plan=copy.deepcopy(source_plan);units={u['id']:u for u in plan['units']};ee={e['id']:e for e in events};candidates={p['source_glyph']:ee[p['native_event']].get('unicodeCandidate') for u in bridge['converted'].values() for p in u['correspondence']}
 for u in units.values():
  for g in u['glyphs']:g['secondary_native_unicode_candidate']=candidates.get(g['id'])
 gs=lambda t:sorted([g for u in t['members'] for g in units[u]['glyphs']],key=lambda g:g['source_index']);trace=[]
 for block in data['blocks']:
  if block['kind']!='paragraph':continue
  for a,b in zip(block['tokens'],block['tokens'][1:]):
   r=hyphen_relation(gs(a),gs(b),data['body_font_pdf'],all_glyphs=plan['glyphs'])
   if not r['accepted']:continue
   if a['gap_em']!=0 or b['source_pixel_box'][1]<=a['source_pixel_box'][1]:continue
   a['retained_source_break_after']=True;trace.append(dict(left=a['id'],right=b['id'],secondary_native_candidate_used=r['secondary_native_candidate_used'],semantic_selection_certified=False,printed_glyphs_deleted=0))
 if trace:data['retained_source_break_policy']=POLICY
 return data,trace
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('plan');p.add_argument('events');p.add_argument('bridge');p.add_argument('out');a=p.parse_args();read=lambda p:json.loads(pathlib.Path(p).read_text());data,trace=annotate(read(a.reader),read(a.plan),read(a.events),read(a.bridge));out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=False);out.write_text(json.dumps(data,separators=(',',':')));(out.parent/'retained-break-trace-private.json').write_text(json.dumps(trace,indent=2));print(json.dumps(dict(retained_source_boundaries=len(trace),printed_glyphs_deleted=0,semantic_selection_certified=False,cold_request=False,browser_verified=False)))
