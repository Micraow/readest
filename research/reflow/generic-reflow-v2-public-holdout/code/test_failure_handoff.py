"""Authored subprocess controls. No model, renderer, network or private fixture."""
import json,pathlib,subprocess,sys,tempfile,unittest
RUN=pathlib.Path(__file__).with_name('run_once.py')
class Controls(unittest.TestCase):
 def run_request(self,fail,gates=False):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);python=root/'layout-evaluation/venv/bin/python';python.parent.mkdir(parents=True);python.symlink_to(sys.executable)
   worker=root/'readest-research-checkpoint/research/reflow/generic-reflow-v2-integrated-paper-1/code/run_cold_page.py';worker.parent.mkdir(parents=True)
   worker.write_text("import pathlib,sys,json\np=pathlib.Path(sys.argv[3])/'native';p.mkdir(parents=True)\n"+("(p/'failure-gates.json').write_text(json.dumps(dict(source_replay_exact=False,region_order_resolved=False)))\n" if gates else '')+f'sys.exit({2 if fail else 0})\n')
   pdf=root/'source.pdf';pdf.write_bytes(b'%PDF-1.4\n% authored inert control\n');out=root/'result'
   result=subprocess.run([sys.executable,str(RUN),str(root),str(pdf),str(out)],capture_output=True,text=True,timeout=10);self.assertEqual(result.returncode,0,result.stderr)
   execution=json.loads((out/'execution.json').read_text());self.assertEqual(execution['execution_pass'],not fail)
   if not fail:self.assertFalse((out/'source-fallback-private.json').exists());return
   fallback=json.loads((out/'source-fallback-private.json').read_text());self.assertEqual(fallback['schema'],'readest-reflow-failure-v1');self.assertTrue(fallback['source_pdf'].startswith('data:application/pdf;base64,JVBER'));self.assertTrue(json.loads((out/'fallback-status.json').read_text())['source_fallback_generated'])
   if gates:self.assertIn('source_replay_exact',fallback['reason']);self.assertIn('region_order_resolved',fallback['reason'])
 def test_both_native_failures_are_explicit(self):self.run_request(True,True)
 def test_unclassified_failure_retains_source(self):self.run_request(True)
 def test_success_does_not_create_failure_bundle(self):self.run_request(False)
if __name__=='__main__':unittest.main()
