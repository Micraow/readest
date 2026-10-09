import copy,unittest
from bridge import bridge
from flow_refinements import script_prefix_relation,scripted_argument_relation,hyphen_relation

def glyph(i,x=0,y=10,size=10,char='a',known=True):return dict(id=f'g{i}',source_index=i,origin=x,baseline=y,size=size,char=char,unicode_known=known,map_error=0,box=[x,y-size*.7,x+size*.5,y])
def event(i,x=0,y=10):return dict(id=i,transform=[2,0,0,2,x*2,y*2],x=0,y=0,resource='r',state=dict(clips=[],blend='source-over',filter='none',absoluteTransform=False),pattern=False,missingFile=False,activeSMask=False,textRenderingMode=0)
class BridgeTests(unittest.TestCase):
 def test_unique_native_identity(self):
  g=glyph(0);r=bridge(dict(glyphs=[g],units=[dict(id='u',kind='native_word',glyphs=[g])]),[event(7)]);self.assertEqual(r['converted']['u']['correspondence'],[dict(source_glyph='g0',native_event=7)])
 def test_ambiguous_source_origin_abstains(self):
  gs=[glyph(0),glyph(1)];r=bridge(dict(glyphs=gs,units=[dict(id='u',kind='native_word',glyphs=gs)]),[event(7)]);self.assertFalse(r['converted'])
 def test_duplicate_native_paint_abstains(self):
  g=glyph(0);r=bridge(dict(glyphs=[g],units=[dict(id='u',kind='native_word',glyphs=[g])]),[event(7),event(8)]);self.assertFalse(r['converted'])
 def test_correspondence_does_not_zip_sorted_native_ids(self):
  gs=[glyph(0),glyph(1,10)];r=bridge(dict(glyphs=gs,units=[dict(id='u',kind='native_word',glyphs=gs)]),[event(8),event(7,10)]);self.assertEqual(r['converted']['u']['native_event_ids'],[7,8]);self.assertEqual(r['converted']['u']['correspondence'],[dict(source_glyph='g0',native_event=8),dict(source_glyph='g1',native_event=7)])
 def test_clipped_native_paint_abstains(self):
  g=glyph(0);e=event(1);e['state']['clips']=[{}];r=bridge(dict(glyphs=[g],units=[dict(id='u',kind='native_word',glyphs=[g])]),[e]);self.assertFalse(r['converted'])
class FlowTests(unittest.TestCase):
 def test_leading_script_links_to_previous_anchor(self):
  a=glyph(0);b=glyph(1,5.2,11.5,7);self.assertTrue(script_prefix_relation([a],[b],[a,b],10)['accepted'])
 def test_same_size_prose_does_not_link(self):
  a=glyph(0);b=glyph(1,5.2,11.5,10);self.assertFalse(script_prefix_relation([a],[b],[a,b],10)['accepted'])
 def test_foreign_intervening_glyph_blocks_link(self):
  a=glyph(0);b=glyph(2,5.2,11.5,7);self.assertFalse(script_prefix_relation([a],[b],[a,glyph(1,4),b],10)['accepted'])
 def test_remote_script_does_not_chain_whole_paragraph(self):
  a=glyph(0);b=glyph(1,20,11.5,7);self.assertFalse(script_prefix_relation([a],[b],[a,b],10)['accepted'])
 def test_known_hyphen_kept_at_source_line_transition(self):
  left=[glyph(0,char='a'),glyph(1,char='b'),glyph(2,char='-')];r=hyphen_relation(left,[glyph(3,y=24,char='c')],10);self.assertTrue(r['accepted']);self.assertFalse(r['printed_hyphen_deleted'])
 def test_same_line_hyphen_does_not_invent_join(self):
  left=[glyph(0,char='a'),glyph(1,char='b'),glyph(2,char='-')];self.assertFalse(hyphen_relation(left,[glyph(3,char='c')],10)['accepted'])
 def test_unknown_terminal_without_corroboration_abstains(self):
  left=[glyph(0),glyph(1,char='b'),glyph(2,char='?',known=False)];self.assertFalse(hyphen_relation(left,[glyph(3,y=24,char='c')],10)['accepted'])
 def test_secondary_candidate_alone_without_bar_shape_abstains(self):
  last=glyph(2,char='?',known=False);last['secondary_native_unicode_candidate']='-';self.assertFalse(hyphen_relation([glyph(0),glyph(1,char='b'),last],[glyph(3,y=24,char='c')],10)['accepted'])
 def test_secondary_candidate_and_bar_shape_only_changes_separator(self):
  last=glyph(2,char='?',known=False);last['secondary_native_unicode_candidate']='-';last['box']=[0,7,3,7.4];r=hyphen_relation([glyph(0),glyph(1,char='b'),last],[glyph(3,y=24,char='c')],10);self.assertTrue(r['accepted']);self.assertFalse(r['semantic_selection_certified']);self.assertFalse(r['printed_hyphen_deleted'])

 def test_scripted_base_keeps_complete_parenthesized_argument(self):
  a=glyph(0);s=glyph(1,5,11.5,7);r=[glyph(2,9,char='('),glyph(3,14,char='0'),glyph(4,19,char=')')];self.assertTrue(scripted_argument_relation([a,s],r,[a,s]+r,10)['accepted'])
 def test_plain_prose_before_parentheses_does_not_bind(self):
  a=glyph(0);r=[glyph(1,6,char='('),glyph(2,11,char=')')];self.assertFalse(scripted_argument_relation([a],r,[a]+r,10)['accepted'])
 def test_unclosed_argument_abstains(self):
  a=glyph(0);s=glyph(1,5,11.5,7);r=[glyph(2,9,char='('),glyph(3,14,char='0')];self.assertFalse(scripted_argument_relation([a,s],r,[a,s]+r,10)['accepted'])

 def test_script_run_after_smaller_nested_prime_keeps_same_base(self):
  left=[glyph(0),glyph(1,5,11.5,7),glyph(2,8.5,9.5,5)];right=[glyph(3,10,11.5,7)];self.assertTrue(script_prefix_relation(left,right,left+right,10)['accepted'])
if __name__=='__main__':unittest.main()
