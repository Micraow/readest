import copy,unittest
from overhead_support import seeds
class Controls(unittest.TestCase):
 def fixture(self):
  return [dict(id='joined',kind='inline_native_group',objects=['p'],glyphs=[dict(char='?',box=[0,0,6,10])]),dict(id='under',kind='native_word',glyphs=[dict(char='x',box=[6,2,10,8])])],[dict(id='p',horizontal_stroke=True,box=[5,0,12,1])]
 def test_native_content_beneath_joined_stroke(self):
  units,objects=self.fixture();self.assertEqual(seeds(units,objects),[{'joined','under'}])
 def test_next_line_is_not_captured(self):
  units,objects=self.fixture();units[1]['glyphs'][0]['box']=[6,12,10,18];self.assertEqual(seeds(units,objects),[])
 def test_plain_underline_has_no_downward_shoulder(self):
  units,objects=self.fixture();units[0]['glyphs'][0]['box']=[0,-9,6,-1];self.assertEqual(seeds(units,objects),[])
 def test_outside_horizontal_projection_is_not_captured(self):
  units,objects=self.fixture();units[1]['glyphs'][0]['box']=[14,2,18,8];self.assertEqual(seeds(units,objects),[])
 def test_character_and_font_names_are_irrelevant(self):
  units,objects=self.fixture();before=copy.deepcopy((units,objects));units[0]['glyphs'][0].update(char='A',font='arbitrary');self.assertEqual(seeds(units,objects),seeds(*before))
if __name__=='__main__':unittest.main()
