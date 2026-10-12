import importlib.util,json,pathlib,tempfile,unittest,hashlib
import fitz
spec=importlib.util.spec_from_file_location('export_ovis_result',pathlib.Path(__file__).with_name('export-ovis-result.py'))
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
class ExportTests(unittest.TestCase):
 def make(self,directory):
  root=pathlib.Path(directory);pdf=fitz.open();pdf.new_page(width=300,height=500);pdf.save(root/'source.pdf');pdf.close()
  digest=hashlib.sha256((root/'source.pdf').read_bytes()).hexdigest()
  (root/'native-math.json').write_text(json.dumps({'pdf_sha256':digest,'page_number':1}))
  (root/'blocks.json').write_text(json.dumps({'blocks':[{'id':'b0','kind':'text','markdown':'Some text $^{1}$ and `$^{1}$`.'},{'id':'b1','kind':'figure','asset':'assets/group.png','caption':'Figure 1. Two panels.','labels':['Panel A','Panel B']},{'id':'b2','kind':'text','markdown':'![Source equation](assets/math-1.png)'},{'id':'b3','kind':'text','markdown':'(7)'}],'notes':[{'id':'b4','marker':'1','content':'Source note.'}]}))
  (root/'receipt.json').write_text(json.dumps({'figure_groups':[{'asset':'assets/group.png','bbox':[10,20,290,180]}],'source_formula_replacements':[{'source_crop':{'path':'assets/math-1.png','bbox':[10,200,200,220]}}]}))
  return root
 def test_content_and_only_local_geometry_are_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=self.make(d);bundle=exporter.export_result(root/'source.pdf',1,root,{'modelSha256':'a'*64})
   blocks=bundle['pages'][0]['blocks'];self.assertEqual(bundle['pageCount'],1);self.assertEqual(len(blocks),5)
   self.assertIn('[1](#ovis-',blocks[0]['markdown']);self.assertIn('`$^{1}$`',blocks[0]['markdown'])
   self.assertEqual(blocks[1]['box'],{'x':10,'y':20,'width':280,'height':160});self.assertIn('Panel A',blocks[1]['caption'])
   self.assertEqual(blocks[2]['role'],'equation');self.assertEqual(blocks[3]['markdown'],'(7)');self.assertEqual(blocks[4]['marker'],'1');self.assertIn('[↩](#ovis-',blocks[4]['markdown'])
   self.assertNotIn('data:image',json.dumps(bundle));self.assertNotIn(str(root),json.dumps(bundle))
 def test_wrong_source_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=self.make(d);(root/'source.pdf').write_bytes((root/'source.pdf').read_bytes()+b'changed')
   with self.assertRaisesRegex(ValueError,'does not match'):exporter.export_result(root/'source.pdf',1,root,{})
 def test_wrong_page_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=self.make(d)
   with self.assertRaisesRegex(ValueError,'does not match'):exporter.export_result(root/'source.pdf',2,root,{})
if __name__=='__main__':unittest.main()
