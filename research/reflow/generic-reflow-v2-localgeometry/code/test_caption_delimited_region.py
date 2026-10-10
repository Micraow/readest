import copy,unittest
from atomic_native_regions import build
from caption_delimited_region import close
class Controls(unittest.TestCase):
 def fixture(self):
  originals=[dict(id='p'+str(i),box=[20+i*30,20,45+i*30,50],role='protected_local',native_indexes=[],unit_ids=['u'+str(i)]) for i in range(3)]
  image=dict(id='image',box=[20,20,105,50],role='protected_local',native_indexes=[],unit_ids=['u0','u1','u2'],source_leaf_ids=['p0','p1','p2'])
  tail=[dict(id='t'+str(i),box=[25+i*30,57,35+i*30,64],baseline=62,role='source_line',native_indexes=[i+1],unit_ids=['t'+str(i)]) for i in range(3)]
  caption=dict(id='caption',box=[20,70,105,78],baseline=77,role='source_line',native_indexes=[9],unit_ids=['c'])
  leaves=[image]+tail+[caption];tree,_,_=build(leaves,[200,300],10);priors=[dict(label='image',score=.9,box=[19,19,106,51]),dict(label='figure_title',score=.9,box=[19,69,106,79])]
  return [leaves,tree,originals,priors,[200,300],10]
 def check(self,a):return close(*a)
 def test_closed_repeated_tail_stays_spatial_without_semantic_order(self):
  a=self.fixture();before=copy.deepcopy(a);tree,ls,t=self.check(a);self.assertTrue(t[0]['accepted']);self.assertEqual(len(ls),2);self.assertEqual(a,before);self.assertTrue(tree['native_character_bijection'])
 def test_no_caption_prior_cannot_expand_image(self):
  a=self.fixture();a[3]=a[3][:1];_,ls,t=self.check(a);self.assertEqual(ls,a[0]);self.assertEqual(t,[])
 def test_low_confidence_caption_does_not_expand(self):
  a=self.fixture();a[3][-1]['score']=.5;_,ls,t=self.check(a);self.assertEqual(ls,a[0]);self.assertEqual(t,[])
 def test_conflicting_caption_priors_refuse(self):
  a=self.fixture();a[3].append(copy.deepcopy(a[3][-1]));self.assertTrue(all(not t['accepted'] for t in self.check(a)[2]))
 def test_multiline_body_tail_refuses(self):
  a=self.fixture();a[0][2]['baseline']+=4;self.assertEqual(self.check(a)[2][0]['reason'],'tail_has_multiple_native_baselines')
 def test_body_prior_inside_tail_refuses(self):
  a=self.fixture();a[3].append(dict(label='text',score=.99,box=[20,54,106,63]));self.assertEqual(self.check(a)[2][0]['reason'],'independent_nonfigure_region_in_tail')
 def test_footnote_prior_inside_tail_refuses(self):
  a=self.fixture();a[3].append(dict(label='footnote',score=.99,box=[20,54,106,63]));self.assertEqual(self.check(a)[2][0]['reason'],'independent_nonfigure_region_in_tail')
 def test_incomplete_panel_row_refuses(self):
  a=self.fixture();a[2].pop();self.assertEqual(self.check(a)[2][0]['reason'],'panel_and_native_text_row_counts_differ')
 def test_text_column_not_corresponding_to_panel_refuses(self):
  a=self.fixture();a[0][2]['box']=[46,55,49,62];self.assertEqual(self.check(a)[2][0]['reason'],'no_unique_native_panel_column')
 def test_reused_native_column_refuses(self):
  a=self.fixture();a[0][2]['box']=[25,55,35,62];self.assertEqual(self.check(a)[2][0]['reason'],'native_panel_column_reused')
 def test_caption_boundary_crossing_refuses(self):
  a=self.fixture();a[0][1]['box'][3]=71;self.assertFalse(self.check(a)[2][0]['accepted'])
 def test_caption_too_far_refuses(self):
  a=self.fixture();a[0][-1]['box']=[20,90,105,98];a[3][-1]['box']=[19,89,106,99];self.assertEqual(self.check(a)[2][0]['reason'],'no_unique_nearby_image_anchor')
 def test_foreign_source_interval_refuses(self):
  a=self.fixture();a[0].append(dict(id='body',box=[20,100,100,110],role='source_line',native_indexes=[2.5],unit_ids=['b']));a[1]['sequence'].append('body');self.assertEqual(self.check(a)[2][0]['reason'],'foreign_native_character_interval')
if __name__=='__main__':unittest.main()
