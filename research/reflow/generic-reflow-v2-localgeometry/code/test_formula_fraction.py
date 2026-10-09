import copy,unittest
from geometry_evidence import formula_evidence

def fixture():
 def g(i,x,y,size=10):return dict(id=str(i),source_index=i,char='x',box=[x,y-7*size/10,x+4*size/10,y],baseline=y,size=size)
 glyphs=[g(i,i*4,20) for i in range(50)]+[g(50,222,16),g(51,228,11,6),g(52,223,28),g(53,229,29,6)]
 return [dict(id='candidate',glyphs=glyphs,objects=['bar'])],[dict(id='bar',type=2,horizontal_stroke=True,box=[220,18,236,18.5])]
class Controls(unittest.TestCase):
 def test_compact_fraction_does_not_depend_on_global_script_percentage(self):
  us,os=fixture();r=formula_evidence(us,os,10);self.assertLess(r['script_fraction'],.08);self.assertTrue(r['pass_native_structure']);self.assertEqual(r['bounded_script_fraction_rules'],['bar'])
 def test_unowned_stroke_cannot_certify_formula(self):
  us,os=fixture();us[0]['objects']=[];self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_nonhorizontal_object_cannot_certify_formula(self):
  us,os=fixture();os[0]['horizontal_stroke']=False;self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_baseline_text_without_scripts_refuses(self):
  us,os=fixture()
  for g in us[0]['glyphs']:g['size']=10
  self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_missing_numerator_refuses(self):
  us,os=fixture();us[0]['glyphs']=[g for g in us[0]['glyphs'] if g['id'] not in ['50','51']];self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_unit_and_glyph_order_do_not_change_decision(self):
  us,os=fixture();a=formula_evidence(us,os,10);us[0]['glyphs'].reverse();self.assertEqual(a,formula_evidence(us,os,10))
 def test_long_separator_is_not_fraction_evidence(self):
  us,os=fixture();os[0]['box']=[0,18,236,18.5];self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_missing_denominator_refuses(self):
  us,os=fixture();us[0]['glyphs']=us[0]['glyphs'][:-2];self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_multiple_prose_rows_are_not_promoted(self):
  us,os=fixture();us[0]['glyphs'][0]['box'][1]=-20;self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_scripts_elsewhere_do_not_certify_local_rule(self):
  us,os=fixture()
  for g in us[0]['glyphs']:
   if g['size']==6:g['box'][0]-=200;g['box'][2]-=200
  self.assertFalse(formula_evidence(us,os,10)['pass_native_structure'])
 def test_glyph_characters_and_font_family_are_not_evidence(self):
  us,os=fixture();before=copy.deepcopy((us,os))
  for g in us[0]['glyphs']:g.update(char='?',font='unrelated')
  self.assertEqual(formula_evidence(us,os,10)['pass_native_structure'],formula_evidence(*before,10)['pass_native_structure'])
if __name__=='__main__':unittest.main()
