"""Authored separator controls; printed characters are never rewritten."""
import copy,unittest
from flow_refinements import hyphen_relation,refine

def glyph(i,c,x=30,y=10,size=10):
 return dict(id=f'g{i}',source_index=i,char=c,unicode_known=True,map_error=0,size=size,baseline=y,box=[x,y-7,x+4,y])
def fixture(prefix='(ab-',suffix='cd)'):
 left=[glyph(i,c,30+i*4) for i,c in enumerate(prefix)]
 right=[glyph(len(left)+i,c,10+i*4,22) for i,c in enumerate(suffix)]
 return left,right
class Controls(unittest.TestCase):
 def test_one_open_parenthesis_keeps_hyphen_without_extra_space(self):
  a,b=fixture();r=hyphen_relation(a,b,10,all_glyphs=a+b);self.assertTrue(r['accepted']);self.assertFalse(r['printed_hyphen_deleted'])
 def test_open_square_bracket_is_generic(self):
  a,b=fixture('[xy-','z]');self.assertTrue(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_existing_plain_prefix_still_works(self):
  a,b=fixture('ab-','cd');self.assertTrue(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_backwards_line_abstains(self):
  a,b=fixture('ab-','cd')
  for g in b:g['baseline']=-2
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_distant_line_abstains(self):
  a,b=fixture('ab-','cd')
  for g in b:g['baseline']=70
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_rightward_column_transition_abstains(self):
  a,b=fixture('ab-','cd')
  for g in b:g['box'][0]+=200;g['box'][2]+=200
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_nonmonotone_source_order_abstains(self):
  a,b=fixture('ab-','cd');b[0]['source_index']=-1
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_foreign_visible_source_content_abstains(self):
  a,b=fixture('ab-','cd')
  for g in b:g['source_index']+=1
  foreign=glyph(3,'x',20,16)
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+[foreign]+b)['accepted'])
 def test_nonpainted_source_separator_does_not_block(self):
  a,b=fixture('ab-','cd')
  for g in b:g['source_index']+=1
  sep=glyph(3,' ',20,16);sep['native_object_ink_observed']=False
  self.assertTrue(hyphen_relation(a,b,10,all_glyphs=a+[sep]+b)['accepted'])
 def test_font_size_change_abstains(self):
  a,b=fixture('ab-','cd');b[0]['size']=6
  self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_unknown_prefix_or_continuation_abstains(self):
  for side in ['left','right']:
   a,b=fixture();(a if side=='left' else b)[0]['unicode_known']=False
   self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_numbers_minus_and_closing_punctuation_do_not_join(self):
  for prefix in ['(12-',')ab-','ab−','((ab-','a-','ab+']:
   a,b=fixture(prefix);self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_uppercase_continuation_abstains(self):
  a,b=fixture('(ab-','Cd)');self.assertFalse(hyphen_relation(a,b,10,all_glyphs=a+b)['accepted'])
 def test_separator_change_preserves_all_source_and_paints(self):
  a,b=fixture();units=[dict(id='left',glyphs=a),dict(id='right',glyphs=b)];plan=dict(units=units,glyphs=a+b)
  tokens=[dict(id=u['id'],kind='vector',members=[u['id']],gap_em=.2,native_event_ids=[g['source_index'] for g in u['glyphs']]) for u in units]
  d=dict(body_font_pdf=10,source_capture_scale=2,blocks=[dict(kind='paragraph',tokens=tokens)]);before=copy.deepcopy((d,plan));out,trace=refine(d,plan)
  self.assertEqual((d,plan),before);self.assertEqual(out['blocks'][0]['tokens'][0],tokens[0]|dict(gap_em=0));self.assertEqual(out['blocks'][0]['tokens'][1],tokens[1]);self.assertTrue(any(t['accepted'] and t['rule'].startswith('source_line') for t in trace))
if __name__=='__main__':unittest.main()
