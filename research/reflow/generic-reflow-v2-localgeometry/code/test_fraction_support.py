import copy,unittest
from fraction_support import propose_support

def g(i,x,y,w=2,h=2):return dict(source_index=i,char='x',box=[x,y,x+w,y+h])
class Controls(unittest.TestCase):
 def test_nearest_components_exclude_neighboring_prose_rows(self):
  glyphs=[g(0,1,0),g(1,1,7),g(2,1,12,h=6),g(3,4,14,h=3),g(4,1,19)]
  before=copy.deepcopy(glyphs);out=propose_support([0,10,8,12],glyphs,20)
  self.assertEqual({x['source_index'] for x in out},{1,2,3});self.assertEqual(glyphs,before)
 def test_horizontal_prose_is_not_included(self):
  out=propose_support([0,10,8,11],[g(0,2,7),g(1,2,13),g(2,10,7),g(3,10,13)],10)
  self.assertEqual({x['source_index'] for x in out},{0,1})
 def test_missing_denominator_refuses(self):self.assertIsNone(propose_support([0,10,8,11],[g(0,2,7)],10))
 def test_missing_numerator_refuses(self):self.assertIsNone(propose_support([0,10,8,11],[g(0,2,13)],10))
 def test_long_separator_does_not_capture_adjacent_prose(self):self.assertIsNone(propose_support([0,10,100,11],[g(0,2,7),g(1,2,13)],20,body=10))
 def test_paint_without_glyphs_refuses(self):self.assertIsNone(propose_support([0,10,8,11],[],10))
 def test_far_component_is_not_pulled_in(self):self.assertIsNone(propose_support([0,10,8,11],[g(0,2,0),g(1,2,13)],3))
 def test_unicode_and_input_order_do_not_choose_support(self):
  glyphs=[g(0,2,7),g(1,2,13)];expected={x['source_index'] for x in propose_support([0,10,8,11],glyphs,10)}
  for x in glyphs:x['char']='?'
  self.assertEqual({x['source_index'] for x in propose_support([0,10,8,11],list(reversed(glyphs)),10)},expected)
if __name__=='__main__':unittest.main()
