import copy,unittest
from relations import relation,unique_relations,region_members

def fixture():
 def glyph(i,x,y,char='x',size=10):return {'id':str(i),'source_index':i,'box':[x,y-8,x+4,y+2],'baseline':y,'size':size,'char':char,'unicode_known':True}
 core={'id':'core','kind':'closed_graphic','box':[20,20,80,42],'glyphs':[glyph(0,20,30),glyph(1,26,30),glyph(2,35,40,'x',6)],'prior_source':{'label':'formula','score':.9}}
 label={'id':'label','kind':'native_word','box':[150,22,162,32],'glyphs':[glyph(3,150,30,'('),glyph(4,154,30,'1'),glyph(5,158,30,')')]}
 region={'key':'column','box':[10,0,180,200]}
 return {'core':core,'label':label,'units':[core,label],'glyphs':core['glyphs']+label['glyphs'],'regions':{'core':region,'label':region},'page':[200,220],'body':10,'formula_proof':True}
class RelationsTest(unittest.TestCase):
 def test_nonmapping_provenance_keeps_native_tokens(self):
  from build_hierarchy import build
  for prior in ['native geometry',None,[],0]:
   unit={'id':'u','prior_source':prior};data={'body_font_pdf':10,'source_capture_scale':2,'blocks':[{'kind':'paragraph','tokens':[{'id':'t','members':['u']}]}]};plan={'units':[unit]};order={'tree':{'kind':'leaf','box':[0,0,20,20],'unit_ids':['u']}}
   result,trace=build(data,plan,order,{'results':[]},{'assets':{}});self.assertEqual(result['blocks'],data['blocks']);self.assertEqual(trace['native_unit_count'],1);self.assertFalse(trace['applied'])
 def test_string_provenance_is_not_formula_prior(self):
  d=fixture();d['core']['prior_source']='native paint';self.assertEqual(relation(**d)['reason'],'no_independent_formula_evidence')
 def test_numbered_display(self):self.assertTrue(relation(**fixture())['accepted'])
 def test_multiline_core(self):
  d=fixture();d['core']['glyphs'][0]['baseline']=20;self.assertTrue(relation(**d)['accepted'])
 def test_no_label(self):
  d=fixture();d['label']['glyphs']=[];self.assertEqual(relation(**d)['reason'],'children_not_independent_native_core_and_word')
 def test_unknown_mapping(self):
  d=fixture();d['label']['glyphs'][1]['unicode_known']=False;self.assertEqual(relation(**d)['reason'],'mapped_numeric_candidate_unavailable')
 def test_prose_not_formula(self):
  d=fixture();d['formula_proof']=False;self.assertEqual(relation(**d)['reason'],'no_independent_formula_evidence')
 def test_citation_in_prose(self):
  d=fixture();d['core']['prior_source']['label']='text';self.assertFalse(relation(**d)['accepted'])
 def test_foreign_interval(self):
  d=fixture();g=copy.deepcopy(d['glyphs'][0]);g['source_index']=2.5;d['glyphs'].append(g);self.assertEqual(relation(**d)['reason'],'foreign_visible_glyph_in_native_interval')
 def test_corridor_intrusion(self):
  d=fixture();d['units'].append({'id':'foreign','box':[100,25,110,35]});self.assertEqual(relation(**d)['reason'],'corridor_has_foreign_unit')
 def test_competing_cores(self):
  a=relation(**fixture());b=a|{'core':'second'};self.assertTrue(all(not r['accepted'] for r in unique_relations([a,b])))
 def test_cross_column(self):
  d=fixture();d['regions']['label']={'key':'other','box':[100,0,180,200]};self.assertEqual(relation(**d)['reason'],'different_or_unknown_column')
 def test_bounded_width(self):
  d=fixture();d['label']['box']=[178,22,190,32];self.assertEqual(relation(**d)['reason'],'outside_column')
 def test_indivisible_group(self):
  d=fixture();d['label']['kind']='closed_graphic';self.assertFalse(relation(**d)['accepted'])
 def test_compact_singleton_pair(self):
  d=fixture();children=[{'kind':'leaf','box':u['box'],'unit_ids':[u['id']]} for u in d['units']];tree={'kind':'bands','box':[10,0,180,200],'children':[{'kind':'columns','box':[20,20,162,42],'children':children}]};d['regions']=region_members(tree,10);r=relation(**d);self.assertTrue(r['accepted']);self.assertEqual(r['region_reason'],'compact_two_singleton_band_not_established_columns')
 def test_tall_singleton_columns(self):
  d=fixture();children=[{'kind':'leaf','box':u['box'],'unit_ids':[u['id']]} for u in d['units']];tree={'kind':'bands','box':[10,0,180,200],'children':[{'kind':'columns','box':[20,0,162,100],'children':children}]};d['regions']=region_members(tree,10);self.assertFalse(relation(**d)['accepted'])
 def test_extra_column_units(self):
  d=fixture();children=[{'kind':'leaf','box':u['box'],'unit_ids':[u['id']]} for u in d['units']];children[1]['unit_ids'].append('other');tree={'kind':'bands','box':[10,0,180,200],'children':[{'kind':'columns','box':[20,20,162,42],'children':children}]};d['regions']=region_members(tree,10);self.assertFalse(relation(**d)['accepted'])
 def test_ambiguous_baseline_rows(self):
  d=fixture();d['core']['glyphs'][1]['baseline']=35;self.assertEqual(relation(**d)['reason'],'ambiguous_or_missing_core_baseline_row')
if __name__=='__main__':unittest.main()
