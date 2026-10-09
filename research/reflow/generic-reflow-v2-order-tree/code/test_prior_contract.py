import unittest
from dataclasses import replace
from apply_region_priors import PriorConfig,validate_candidates,table_evidence,prior_provenance
class PriorTests(unittest.TestCase):
 def test_live_provenance_does_not_claim_historical_cache(self):
  p=prior_provenance("live_local_page");self.assertFalse(p["cached_predictions_only"]);self.assertEqual(p["page_pipeline_inference_calls"],1);self.assertEqual(p["adapter_inference_calls"],0)
 def test_unknown_provenance_rejects(self):
  with self.assertRaises(ValueError):prior_provenance("unknown")
 def test_disabled_prior_adds_no_region(self):
  accepted,trace=validate_candidates([dict(label='table',score=.99,box=[0,0,100,100])],replace(PriorConfig(),enabled=False));self.assertEqual(accepted,[])
 def test_missing_prior_adds_no_region(self):self.assertEqual(validate_candidates([])[0],[])
 def test_low_confidence_is_ignored(self):self.assertEqual(validate_candidates([dict(label='table',score=.5,box=[0,0,100,100])])[0],[])
 def test_conflicting_overlap_rejects_both(self):
  cs=[dict(label='table',score=.9,box=[0,0,100,100]),dict(label='chart',score=.9,box=[10,10,90,90])];self.assertEqual(validate_candidates(cs)[0],[])
 def test_text_without_table_structure_rejects(self):self.assertFalse(table_evidence([],[],[0,0,100,100],10,PriorConfig())['pass_native_structure'])
if __name__=='__main__':unittest.main()
