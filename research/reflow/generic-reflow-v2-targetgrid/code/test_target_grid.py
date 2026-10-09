import unittest
from dataclasses import replace
from target_grid import TargetConfig,choose_grid,cache_key,AssetCache,ownership_proof
class SamplingTests(unittest.TestCase):
 def test_28px_dpr2_has_enough_samples(self):
  r=choose_grid(28,2,9.96);self.assertEqual(r['grid'],6.);self.assertGreaterEqual(r['samples_per_device_pixel'],1.)
 def test_zoom_increases_grid(self):self.assertGreater(choose_grid(20,1,10,3)['grid'],choose_grid(20,1,10)['grid'])
 def test_excessive_or_invalid_request_rejects(self):
  for args in [(100,4,8,1),(20,0,10,1),(20,1,10,5)]:
   with self.assertRaises(ValueError):choose_grid(*args)
 def test_cache_key_distinguishes_grid_source_plan_and_units(self):
  base=cache_key('a','b',['u1'],2,'r','white');self.assertNotEqual(base,cache_key('a','b',['u1'],6,'r','white'));self.assertNotEqual(base,cache_key('a','c',['u1'],2,'r','white'));self.assertNotEqual(base,cache_key('c','b',['u1'],2,'r','white'));self.assertNotEqual(base,cache_key('a','b',['u2'],2,'r','white'))
 def test_lru_eviction_honors_decoded_bytes(self):
  c=AssetCache(replace(TargetConfig(),maximum_cache_encoded_bytes=100,maximum_cache_decoded_bytes=20));c.put('a',b'a',10);c.put('b',b'b',10);self.assertEqual(c.get('a'),b'a');c.put('c',b'c',10);self.assertIsNone(c.get('b'));self.assertEqual(c.decoded_bytes,20)
 def test_renderer_policy_change_invalidates_key(self):self.assertNotEqual(cache_key("a","b",["u"],6,"old","white"),cache_key("a","b",["u"],6,"new","white"))
 def test_shared_object_is_not_closed(self):
  a=dict(id="g1",object_id="p1",char="a",box=[0,0,1,1]);b={**a,"id":"g2","char":"b"};r=ownership_proof([dict(id="u1",glyphs=[a]),dict(id="u2",glyphs=[b])],[a,b],{"p1"});self.assertEqual(r["p1"],{"u1","u2"})
 def test_unmapped_native_record_blocks_closed_set(self):
  a=dict(id="g1",object_id="p1",char="a",box=[0,0,1,1]);b={**a,"id":"g2"}
  with self.assertRaises(ValueError):ownership_proof([dict(id="u1",glyphs=[a])],[a,b],{"p1"})
 def test_oversize_is_not_cached(self):
  c=AssetCache(replace(TargetConfig(),maximum_cache_encoded_bytes=2));self.assertFalse(c.put('a',b'123',1));self.assertIsNone(c.get('a'))
if __name__=='__main__':unittest.main()
