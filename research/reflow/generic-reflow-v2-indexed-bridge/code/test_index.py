import importlib.util,pathlib,random,sys,unittest,math
from bridge import bridge,BridgeConfig
p=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-paragraph-vector/code/bridge.py';spec=importlib.util.spec_from_file_location('brute_native_bridge',p);old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
def fixture(points):
 gs=[{'id':f'g{i}','origin':x,'baseline':y} for i,(x,y) in enumerate(points)];us=[{'id':f'w{i}','kind':'native_word','glyphs':[g]} for i,g in enumerate(gs)];return {'glyphs':gs,'units':us}
def events(points):return [{'id':i,'transform':[2,0,0,2,0,0],'x':x,'y':y,'resource':'native','state':{'clips':[],'blend':'source-over','filter':'none'},'pattern':False,'missingFile':False,'activeSMask':False,'textRenderingMode':0} for i,(x,y) in enumerate(points)]
class Controls(unittest.TestCase):
 def test_boundary_and_duplicates(self):
  pts=[(-.002,0),(0,0),(.002,0),(.002,0),(.0040001,0)];q=[(x,y) for x,y in pts]+[(.0000001,0),(-.0039999,0)];p=fixture(pts);e=events(q);self.assertEqual(bridge(p,e),old.bridge(p,e))
 def test_seeded_perturbations(self):
  rng=random.Random(7041)
  for _ in range(50):
   ps=[(rng.uniform(-100,100),rng.uniform(-100,100)) for _ in range(80)];qs=[(x+rng.uniform(-.003,.003),y+rng.uniform(-.003,.003)) for x,y in ps];p=fixture(ps);e=events(qs);self.assertEqual(bridge(p,e),old.bridge(p,e))
 def test_zero_tolerance(self):
  p=fixture([(1,2),(1,2.1)]);e=events([(1,2),(1,2.1000001)]);self.assertEqual(bridge(p,e,BridgeConfig(maximum_origin_error_pdf_points=0)),old.bridge(p,e,old.BridgeConfig(maximum_origin_error_pdf_points=0)))
 def test_nonfinite_stays_unmatched(self):
  p=fixture([(float('nan'),2),(1,float('inf')),(1,2)]);e=events([(1,2),(float('nan'),2)]);self.assertEqual(bridge(p,e),old.bridge(p,e))
 def test_exact_bucket_edges_and_next_floats(self):
  for n in range(-250,251):
   x=n*.002
   for y in [x-.002,x+.002]:
    for q in [y,math.nextafter(y,-math.inf),math.nextafter(y,math.inf)]:
     p=fixture([(x,x)]);e=events([(q,q)]);self.assertEqual(bridge(p,e),old.bridge(p,e))
 def test_extreme_coordinate_safe_fallback(self):
  p=fixture([(1e308,1e308),(1e18,-1e18)]);e=events([(1e308,1e308),(1e18,-1e18)]);self.assertEqual(bridge(p,e),old.bridge(p,e))
if __name__=='__main__':unittest.main()
