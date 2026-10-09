import unittest
from types import SimpleNamespace
from baseline_evidence import select,normalize
from paragraph_evidence import estimate,can_join
F=SimpleNamespace(maximum_paragraph_baseline_gap_em=1.7,maximum_first_line_return_em=1.2,new_paragraph_indent_em=.35)
def g(y,size=10):return {'baseline':y,'size':size,'unicode_known':False}
def row(y,x=20,width=220,font=10):return {'kind':'line','path':'root','box':[x,y-7,x+width,y],'baseline':y,'native_dominant_font':font}
class Controls(unittest.TestCase):
 def test_stale_cache_replaced(self):
  p,t=normalize({'units':[{'id':'w','kind':'native_word','baseline':97.5,'glyphs':[g(100)]*8}]});self.assertEqual(p['units'][0]['baseline'],100);self.assertTrue(t[0]['changed'])
 def test_script_not_main_baseline(self):self.assertEqual(select([g(100)]*4+[g(94,6)]*3)[0],100)
 def test_equal_distinct_baselines_abstain(self):self.assertIsNone(select([g(100)]*4+[g(112)]*4)[0])
 def test_protected_multiline_group_not_flattened(self):
  u={'id':'p','kind':'closed_graphic','baseline':99,'glyphs':[g(100),g(112)]};p,t=normalize({'units':[u]});self.assertEqual(p['units'][0],u);self.assertFalse(t)
 def test_first_line_return_to_repeated_edge(self):
  lines=[row(100,x=35),row(124),row(148),row(172),row(196)];e=estimate(lines,10);self.assertTrue(can_join(lines[0],lines[1],10,e,F))
 def test_short_centered_line_does_not_join(self):
  lines=[row(100,x=35,width=25),row(124),row(148),row(172),row(196)];e=estimate(lines,10);self.assertFalse(can_join(lines[0],lines[1],10,e,F))
 def test_arbitrary_outdent_does_not_join(self):
  lines=[row(100,x=35),row(124,x=10),row(148),row(172),row(196)];e=estimate(lines,10);self.assertFalse(can_join(lines[0],lines[1],10,e,F))
 def test_positive_indent_still_breaks(self):
  lines=[row(100),row(124,x=35),row(148),row(172),row(196)];e=estimate(lines,10);self.assertFalse(can_join(lines[0],lines[1],10,e,F))
if __name__=='__main__':unittest.main()
