import unittest,copy,pathlib,subprocess,sys
from atomic_native_regions import propose,build
from region_tree import build_tree,AmbiguousOrder

def leaf(i,x,role='protected_local',y=20,w=20,h=20,indexes=()):return dict(id=str(i),box=[x,y,x+w,y+h],role=role,unit_ids=['u'+str(i)],native_indexes=list(indexes))
class Controls(unittest.TestCase):
 def test_import_does_not_shadow_local_geometry_diagnostics(self):
  folder=pathlib.Path(__file__).resolve().parent
  subprocess.run([sys.executable,'-c',"import sys,pathlib;sys.path.insert(0,sys.argv[1]);import atomic_native_regions;import diagnose_native_regions;assert pathlib.Path(diagnose_native_regions.__file__).parent==pathlib.Path(sys.argv[1])",str(folder)],check=True)
 def fixture(self):return [leaf(i,20+i*25) for i in range(3)]+[leaf('body',20,'source_line',60,100,10,[10,11])]
 def test_original_tree_still_refuses_ambiguous_graphic_band(self):
  with self.assertRaises(AmbiguousOrder):build_tree(self.fixture(),10)
 def test_native_band_is_indivisible_and_external_order_proven(self):
  xs=self.fixture();before=copy.deepcopy(xs);r,ls,ds=build(xs,[200,300],10);self.assertIsNotNone(r);self.assertTrue(r['original_leaf_bijection']);self.assertEqual(len(ls),2);self.assertFalse(r['internal_graphic_order_inferred']);self.assertEqual(xs,before)
 def test_native_order_conflict_cannot_hide_across_graphic(self):
  xs=[leaf('a',20,'source_line',20,30,8,[8,9]),leaf('graphic',20,y=60),leaf('b',20,'source_line',100,30,8,[1,2])];r,_,ds=build(xs,[200,300],10);self.assertIsNone(r);self.assertEqual(ds[-1]['reason'],'native_interval_order_contradicts_safe_tree')
 def test_ordinary_two_columns_never_freeze_together(self):
  xs=[leaf(0,20,'source_line'),leaf(1,45,'source_line')];r,_,ds=build(xs,[200,300],10);self.assertIsNone(r);self.assertEqual(ds[0]['reason'],'prose_or_unknown_leaf_cannot_be_frozen')
 def test_footnote_text_never_freezes_with_rule(self):
  xs=[leaf(0,20,'source_line'),leaf(1,45)];self.assertIsNone(propose({'0','1'},xs,[200,300])[0])
 def test_unknown_role_refuses(self):
  xs=[leaf(0,20,'unknown'),leaf(1,45)];self.assertIsNone(propose({'0','1'},xs,[200,300])[0])
 def test_foreign_text_inside_region_refuses(self):
  xs=[leaf(0,20),leaf(1,80),leaf('caption',50,'source_line',25,10,5)];g,t=propose({'0','1'},xs,[200,300]);self.assertIsNone(g);self.assertEqual(t['reason'],'foreign_leaf_intersects_region')
 def test_foreign_native_interval_refuses_even_outside_box(self):
  xs=[leaf(0,20,indexes=[1]),leaf(1,45,indexes=[3]),leaf('foreign',20,'source_line',60,20,10,[2])];g,t=propose({'0','1'},xs,[200,300]);self.assertIsNone(g);self.assertEqual(t['reason'],'foreign_native_character_interval')
 def test_whole_page_or_tall_region_refuses(self):
  xs=[leaf(0,5,w=90,h=180),leaf(1,100,w=90,h=180)];self.assertIsNone(propose({'0','1'},xs,[200,300])[0])
 def test_offpage_region_refuses(self):
  xs=[leaf(0,-1),leaf(1,24)];self.assertIsNone(propose({'0','1'},xs,[200,300])[0])
 def test_duplicate_native_ownership_refuses(self):
  xs=[leaf(0,20),leaf(1,45)];xs[1]['unit_ids']=xs[0]['unit_ids'];self.assertIsNone(propose({'0','1'},xs,[200,300])[0])
 def test_singleton_is_not_grouped(self):
  xs=[leaf(0,20)];self.assertIsNone(propose({'0'},xs,[200,300])[0])
 def test_existing_safe_graphics_order_unchanged(self):
  xs=[leaf(0,20),leaf(1,70)];before=build_tree(xs,10);r,ls,ds=build(xs,[200,300],10);self.assertEqual(r['tree'],before['tree']);self.assertEqual(ls,xs);self.assertEqual(ds,[])
 def test_two_graphic_rows_keep_distinct_regions_and_body(self):
  xs=self.fixture()+[leaf('next'+str(i),20+i*25,y=90) for i in range(3)];r,ls,ds=build(xs,[200,300],10);self.assertIsNotNone(r);self.assertEqual(sum(bool(v.get('source_leaf_ids')) for v in ls),2)
 def test_no_identifier_keyword_dependence(self):
  xs=self.fixture();r,_,_=build(xs,[200,300],10)
  for i,x in enumerate(xs):x['id']='different-'+str(i)
  s,_,_=build(xs,[200,300],10);self.assertEqual(r['source_unit_bijection'],s['source_unit_bijection'])

class ImagePriorControls(unittest.TestCase):
 def fixture(self):
  xs=[leaf(0,20,w=85,h=20),leaf(1,20,y=50,w=85,h=20),leaf('label',25,'source_line',42,60,6,[1,2])]
  prior=dict(label='image',score=.9,box=[18,18,108,72]);return xs,prior
 def check(self,xs,p,others=()):
  from atomic_native_regions import propose_image_prior
  return propose_image_prior(p,[p]+list(others),xs,[200,300])
 def test_closed_graphic_region_retains_text_spatially(self):
  xs,p=self.fixture();g,t=self.check(xs,p);self.assertIsNotNone(g);self.assertTrue(t['accepted']);self.assertEqual(t['text_leaves_kept_spatially'],1);self.assertFalse(t['internal_order_inferred'])
 def test_model_image_label_does_not_override_prose_only(self):
  xs,p=self.fixture()
  for x in xs:x['role']='source_line'
  self.assertEqual(self.check(xs,p)[1]['reason'],'no_native_graphic_support')
 def test_small_rule_does_not_capture_large_prose_region(self):
  xs,p=self.fixture()
  for x in xs[:2]:x['box'][3]=x['box'][1]+1
  self.assertEqual(self.check(xs,p)[1]['reason'],'graphic_support_not_dominant')
 def test_straddling_caption_or_prose_refuses(self):
  xs,p=self.fixture();xs[-1]['box'][2]=120;self.assertEqual(self.check(xs,p)[1]['reason'],'source_leaf_crosses_prior_boundary')
 def test_conflicting_high_confidence_prior_refuses(self):
  xs,p=self.fixture();other=p|dict(label='table');self.assertEqual(self.check(xs,p,[other])[1]['reason'],'conflicting_prior_regions')
 def test_low_confidence_refuses(self):
  xs,p=self.fixture();p['score']=.5;self.assertEqual(self.check(xs,p)[1]['reason'],'no_independent_image_prior')
 def test_formula_is_not_image_authority(self):
  xs,p=self.fixture();p['label']='formula';self.assertEqual(self.check(xs,p)[1]['reason'],'no_independent_image_prior')
 def test_native_interval_foreign_body_refuses(self):
  xs,p=self.fixture();xs[-1]['native_indexes']=[1,3];xs.append(leaf('body',20,'source_line',90,50,10,[2]));self.assertEqual(self.check(xs,p)[1]['reason'],'foreign_native_character_interval')
 def test_overlapping_graphic_boxes_do_not_double_count_coverage(self):
  from atomic_native_regions import rectangle_union_area
  self.assertEqual(rectangle_union_area([[0,0,10,10],[5,0,15,10]]),150)
 def test_accepted_prior_preserves_all_original_leaf_units(self):
  xs,p=self.fixture();r,ls,ds=build(xs,[200,300],10,image_priors=[p]);self.assertIsNotNone(r);self.assertTrue(r['original_leaf_bijection']);self.assertTrue(r['source_unit_bijection']);self.assertEqual(set(ls[0]['unit_ids']),{u for x in xs for u in x['unit_ids']})

 def test_trailing_footnote_inside_oversized_image_prior_refuses(self):
  xs,p=self.fixture();xs[-1]['box']=[25,72,85,78];p['box'][3]=80;self.assertEqual(self.check(xs,p)[1]['reason'],'text_not_bracketed_by_native_graphic_rows')
 def test_enclosed_known_body_prior_refuses(self):
  xs,p=self.fixture();body=dict(label='text',score=.95,box=xs[-1]['box']);self.assertEqual(self.check(xs,p,[body])[1]['reason'],'independent_prose_or_caption_evidence')
 def test_enclosed_known_footnote_prior_refuses(self):
  xs,p=self.fixture();body=dict(label='footnote',score=.95,box=xs[-1]['box']);self.assertEqual(self.check(xs,p,[body])[1]['reason'],'independent_prose_or_caption_evidence')
 def test_enclosed_caption_prior_refuses(self):
  xs,p=self.fixture();body=dict(label='figure_title',score=.95,box=xs[-1]['box']);self.assertEqual(self.check(xs,p,[body])[1]['reason'],'independent_prose_or_caption_evidence')
 def test_nonfinite_prior_refuses(self):
  xs,p=self.fixture();p['box'][0]=float('nan');self.assertEqual(self.check(xs,p)[1]['reason'],'invalid_prior_geometry')
 def test_nonfinite_source_refuses(self):
  xs,p=self.fixture();xs[0]['box'][0]=float('inf');self.assertEqual(self.check(xs,p)[1]['reason'],'invalid_source_geometry')
 def test_duplicate_native_character_refuses(self):
  xs,p=self.fixture();xs[0]['native_indexes']=[1]
  with self.assertRaises(ValueError):build(xs,[200,300],10,image_priors=[p])
 def test_multiline_internal_body_band_refuses(self):
  xs,p=self.fixture();xs[0]['box']=[20,20,105,60];xs[1]['box']=[20,78,105,100];xs[-1]['box']=[25,61,85,77];p['box'][3]=102
  self.assertEqual(self.check(xs,p)[1]['reason'],'internal_text_gap_too_tall')
 def test_multiple_text_strips_refuse(self):
  xs,p=self.fixture();xs[0]['box']=[20,20,105,40];xs[1]['box']=[20,50,105,70];xs[-1]['box']=[25,42,85,48];xs.extend([leaf('third',20,y=80,w=85,h=20),leaf('label2',25,'source_line',72,60,6,[4,5])]);p['box'][3]=102
  self.assertEqual(self.check(xs,p)[1]['reason'],'internal_text_band_too_tall')
 def test_nested_group_replaces_current_members_once(self):
  xs=[leaf(0,20),leaf(1,45),leaf(2,70)];g,_=propose({'0','1'},xs,[200,300]);second,_=propose({g['id'],'2'},[g,xs[2]],[200,300]);self.assertEqual(set(second['source_leaf_ids']),{'0','1','2'});self.assertEqual(set(second['member_leaf_ids']),{g['id'],'2'})

class NativeSupportControls(unittest.TestCase):
 def check(self,sparse):
  import tempfile,numpy as np
  from PIL import Image
  from atomic_native_regions import verify_native_graphic_support
  with tempfile.TemporaryDirectory() as d:
   image=np.zeros((20,20,4),np.uint8);image[:,:,3]=255
   if sparse:image[1:19,1:19,3]=0
   Image.fromarray(image).save(pathlib.Path(d)/'unit.png')
   return verify_native_graphic_support([dict(source_leaf_ids=['a','b'],unit_ids=['u'])],dict(units=[dict(id='u',glyphs=[])]),dict(results=[dict(id='u',file='unit.png',asset_pixel_box=[0,0,20,20])]),d)[0]
 def test_dense_native_support_passes(self):self.assertTrue(self.check(False)['accepted'])
 def test_sparse_frame_cannot_claim_box_area_as_support(self):self.assertFalse(self.check(True)['accepted'])

if __name__=='__main__':unittest.main()
