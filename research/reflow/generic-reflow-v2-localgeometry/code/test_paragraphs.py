import unittest
from types import SimpleNamespace
from paragraph_geometry import estimate,can_join
F=SimpleNamespace(maximum_paragraph_baseline_gap_em=1.7,maximum_first_line_return_em=1.2,new_paragraph_indent_em=.35)
def line(y,x=20,font=10,path='root'):return {'kind':'line','path':path,'baseline':y,'box':[x,y-7,240,y],'native_dominant_font':font}
class Controls(unittest.TestCase):
 def test_wide_repeated_leading(self):
  xs=[line(y) for y in [100,124,148,172]];e=estimate(xs,10);self.assertEqual(e['root']['leading_pdf'],24);self.assertTrue(can_join(xs[0],xs[1],10,e,F))
 def test_paragraph_gap_not_joined(self):
  xs=[line(y) for y in [100,124,148,190]];e=estimate(xs,10);self.assertFalse(can_join(xs[-2],xs[-1],10,e,F))
 def test_indentation_still_breaks(self):self.assertFalse(can_join(line(100),line(112,x=28),10,{},F))
 def test_small_type_after_body_not_joined(self):self.assertFalse(can_join(line(100),line(112,font=7),10,{},F))
 def test_column_leading_is_separate(self):
  xs=[line(y) for y in [100,124,148]]+[line(y,path='right') for y in [100,112,124]];e=estimate(xs,10);self.assertEqual(e['root']['leading_pdf'],24);self.assertEqual(e['right']['leading_pdf'],12)
if __name__=='__main__':unittest.main()
