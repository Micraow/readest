import unittest
from refine_vector_components import connected
from test_flow_and_bridge import glyph
class ComponentTests(unittest.TestCase):
 def test_baseline_words_are_breakable_components(self):
  a=glyph(0);b=glyph(1,6);self.assertFalse(connected([a],[b],[a,b],10)['accepted'])
 def test_subscript_after_superscript_stays_with_base(self):
  a=glyph(0);sup=glyph(1,5,6,7);sub=glyph(2,5,12,7);self.assertTrue(connected([a,sup],[sub],[a,sup,sub],10)['accepted'])
 def test_same_script_run_can_extend_after_nested_prime(self):
  a=glyph(0);sub=glyph(1,5,12,7);prime=glyph(2,8.5,10,5);nextsub=glyph(3,10,12,7);self.assertTrue(connected([a,sub,prime],[nextsub],[a,sub,prime,nextsub],10)['accepted'])
 def test_foreign_interval_does_not_get_swallowed(self):
  a=glyph(0);sub=glyph(2,5,12,7);self.assertFalse(connected([a],[sub],[a,glyph(1,4),sub],10)['accepted'])
if __name__=='__main__':unittest.main()
