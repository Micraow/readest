import contextlib,copy,hashlib,io,json,pathlib,tempfile,unittest
import fitz
from prepare import compile_source
class SourceUnits(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.pdf=self.root/'source.pdf'
  doc=fitz.open();p=doc.new_page(width=220,height=100);p.insert_text((15,30),'Alpha beta x + y',fontsize=12);doc.save(self.pdf)
  self.oracle={'schemaVersion':'oracle-source-units/1','source':{'sha256':hashlib.sha256(self.pdf.read_bytes()).hexdigest()},'bodyFontPt':12,'rasterScale':4,'scopeNote':'Synthetic fixture','sections':[{'id':'test','page':1,'nodes':[{'id':'body','role':'body','lines':[{'refs':[[0,0]],'window':[0,14,215,38],'baseline':30,'groups':[{'chars':[11,15],'role':'inline-math','label':'x plus y'}]}]}]}]}
 def tearDown(self):self.tmp.cleanup()
 def run_compile(self,o=None):
  with contextlib.redirect_stdout(io.StringIO()):return compile_source(self.pdf,o or self.oracle,self.root/'out')
 def test_disjoint_source_ink_and_group(self):
  r=self.run_compile();self.assertEqual(r['audit']['sourceInk'],r['audit']['renderedInk']);self.assertEqual(r['audit']['duplicateInk'],[]);self.assertEqual(len(r['sections'][0]['nodes'][0]['units']),3);self.assertEqual(r['sections'][0]['nodes'][0]['units'][-1]['nativeText'],'x + y')
 def test_immutable_source_hash(self):
  self.oracle['source']['sha256']='0'*64
  with self.assertRaisesRegex(AssertionError,'source hash'):self.run_compile()
 def test_duplicate_source_ownership_rejected(self):
  lines=self.oracle['sections'][0]['nodes'][0]['lines'];lines.append(copy.deepcopy(lines[0]))
  with self.assertRaisesRegex(AssertionError,'duplicate native char'):self.run_compile()
 def test_clipped_source_edge_rejected(self):
  self.oracle['sections'][0]['nodes'][0]['lines'][0]['window'][1]=26
  with self.assertRaisesRegex(AssertionError,'line edge'):self.run_compile()
if __name__=='__main__':unittest.main()
