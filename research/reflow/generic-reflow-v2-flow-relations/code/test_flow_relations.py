import unittest,copy
from flow_relations import apply_relations,caption_pairs

def fixture():
 def line(id,c,y,x=0,r=100,size=10,end='x'):
  b=[x+120*c,y,r+120*c,y+8];return dict(id=id,column=c,role='source_line',box=b,baseline=y+8,main_size=size,native_indexes=[ord(id[0])*10],terminal_known=True,terminal_character=end)
 ls=[line('a',0,80),line('b',0,92),dict(id='fig',column=1,role='protected_local',box=[120,0,220,25],native_indexes=[300],provenance={'label':'chart'}),line('cap',1,30),line('c',1,60),line('d',1,72),line('e',1,88,x=10)]
 return [x['id'] for x in ls],{x['id']:x for x in ls},[dict(graphic='fig',caption=['cap'],column=1)]
class FlowTests(unittest.TestCase):
 def test_continuation_before_column_prefix_float(self):
  s,l,p=fixture();r=apply_relations(s,l,p,10);self.assertEqual(r['sequence'],['a','b','c','d','fig','cap','e']);self.assertEqual(r['forced_line_joins'],[['b','c']]);self.assertFalse(r['native_index_monotonicity_claimed'])
 def rejected(self,change):
  s,l,p=fixture();change(s,l,p);r=apply_relations(s,l,p,10);self.assertEqual(r['sequence'],s);self.assertFalse(r['relations'])
 def test_early_left_end_abstains(self):self.rejected(lambda s,l,p:l['b']['box'].__setitem__(2,60))
 def test_sentence_end_abstains(self):self.rejected(lambda s,l,p:l['b'].__setitem__('terminal_character','.'))
 def test_indented_next_body_abstains(self):self.rejected(lambda s,l,p:l['c']['box'].__setitem__(0,130))
 def test_columns_from_different_bands_abstain(self):self.rejected(lambda s,l,p:l["b"].__setitem__("column_group","another_band"))
 def test_crossing_protected_caption_abstains(self):
  s,l,p=fixture();l["cap"]["role"]="protected_local";self.assertEqual(caption_pairs(s,l,[dict(label="chart_title",score=.9,box=[120,29,220,39])],10)[0],[])
 def test_size_change_abstains(self):self.rejected(lambda s,l,p:l['c'].__setitem__('main_size',14))
 def test_nonprefix_float_abstains(self):self.rejected(lambda s,l,p:s.__setitem__(slice(2,5),['c','fig','cap']))
 def test_missing_pair_is_noop(self):
  s,l,p=fixture();self.assertEqual(apply_relations(s,l,[],10)['sequence'],s)
 def test_caption_valid_complete_lines(self):
  s,l,p=fixture();pairs,t=caption_pairs(s,l,[dict(id='m',label='chart_title',score=.9,box=[120,29,220,39])],10);self.assertEqual(pairs[0]['caption'],['cap'])
 def test_low_confidence_caption_abstains(self):
  s,l,p=fixture();self.assertEqual(caption_pairs(s,l,[dict(label='chart_title',score=.5,box=[120,29,220,39])],10)[0],[])
 def test_competing_caption_abstains(self):
  s,l,p=fixture();c=dict(label='chart_title',score=.9,box=[120,29,220,39]);self.assertEqual(caption_pairs(s,l,[dict(c),dict(c)],10)[0],[])
 def test_partial_caption_line_abstains(self):
  s,l,p=fixture();self.assertEqual(caption_pairs(s,l,[dict(label='chart_title',score=.9,box=[150,29,190,39])],10)[0],[])
if __name__=='__main__':unittest.main()
