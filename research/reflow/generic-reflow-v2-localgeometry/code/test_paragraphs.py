import unittest
from types import SimpleNamespace
from paragraph_geometry import estimate,can_join
F=SimpleNamespace(maximum_paragraph_baseline_gap_em=1.7,maximum_first_line_return_em=1.2,new_paragraph_indent_em=.35)
def line(y,x=20,font=10,path='root'):return {'kind':'line','path':path,'baseline':y,'box':[x,y-7,240,y],'native_dominant_font':font}
class Controls(unittest.TestCase):
 def test_clearance_estimated_from_repeated_native_rows(self):
  e=estimate([line(y) for y in [100,110,120,130]],10)['root'];self.assertEqual(e['native_ink_clearance_pdf'],3);self.assertEqual(e['native_line_ink_height_pdf'],7);self.assertEqual(e['clearance_supporting_pairs'],3)
 def test_clearance_not_estimated_from_one_pair(self):
  self.assertNotIn('root',estimate([line(100),line(110)],10))
 def clearance_fixture(self):
  a=line(100);a['box']=[20,90,240,104];b=line(114);b['box']=[20,107,240,116]
  evidence={'root':{'leading_pdf':11,'native_ink_clearance_pdf':3,'native_line_ink_height_pdf':9,'clearance_supporting_pairs':3}}
  return a,b,evidence
 def test_tall_inline_ink_can_preserve_paragraph(self):
  a,b,e=self.clearance_fixture();self.assertTrue(can_join(a,b,10,e,F));self.assertIn('ink_clearance_join_evidence',b)
 def test_extra_paragraph_whitespace_is_not_joined(self):
  a,b,e=self.clearance_fixture();b['box'][1]=109;self.assertFalse(can_join(a,b,10,e,F))
 def test_no_repeated_clearance_evidence_refuses(self):
  a,b,e=self.clearance_fixture();del e['root']['native_ink_clearance_pdf'];self.assertFalse(can_join(a,b,10,e,F))
 def test_regular_height_gap_is_not_reclassified(self):
  a,b,e=self.clearance_fixture();a['box']=[20,95,240,104];self.assertFalse(can_join(a,b,10,e,F))
 def test_tall_inline_cannot_cross_column_or_indent(self):
  a,b,e=self.clearance_fixture();b['path']='right';self.assertFalse(can_join(a,b,10,e,F));b['path']='root';b['box'][0]=30;self.assertFalse(can_join(a,b,10,e,F))
 def test_tall_inline_still_obeys_absolute_gap_bound(self):
  a,b,e=self.clearance_fixture();b['baseline']=120;self.assertFalse(can_join(a,b,10,e,F))

 def test_wide_repeated_leading(self):
  xs=[line(y) for y in [100,124,148,172]];e=estimate(xs,10);self.assertEqual(e['root']['leading_pdf'],24);self.assertTrue(can_join(xs[0],xs[1],10,e,F))
 def test_paragraph_gap_not_joined(self):
  xs=[line(y) for y in [100,124,148,190]];e=estimate(xs,10);self.assertFalse(can_join(xs[-2],xs[-1],10,e,F))
 def test_indentation_still_breaks(self):self.assertFalse(can_join(line(100),line(112,x=28),10,{},F))
 def test_small_type_after_body_not_joined(self):self.assertFalse(can_join(line(100),line(112,font=7),10,{},F))
 def test_column_leading_is_separate(self):
  xs=[line(y) for y in [100,124,148]]+[line(y,path='right') for y in [100,112,124]];e=estimate(xs,10);self.assertEqual(e['root']['leading_pdf'],24);self.assertEqual(e['right']['leading_pdf'],12)
if __name__=='__main__':unittest.main()
