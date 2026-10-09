"""Small original mechanism/negative controls, no private document contents."""
import collections,sys,tempfile,pathlib,subprocess,json,unittest
from config import Config
from prototype import native_inventory,plan,mapped_unicode
import pypdfium2 as pdfium

class RepresentationTests(unittest.TestCase):
 def test_mapping_unknown(self):
  for cp,error in [(0,0),(2,0),(0xe100,0),(0xfffd,0),(65,1)]:self.assertFalse(mapped_unicode(cp,error))
  self.assertTrue(mapped_unicode(65,0))
 def test_original_control(self):
  with tempfile.TemporaryDirectory() as d:
   pdf=pathlib.Path(d)/'original.pdf';subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('create_control.py')),str(pdf)],check=True)
   doc=pdfium.PdfDocument(pdf);page=doc[0];trace=[];objects,handles,glyphs,body,limits=native_inventory(page,Config(),trace)
   backgrounds=[o for o in objects if o['kind']=='background'];self.assertEqual(len(backgrounds),1)
   paths=[o for o in objects if o['type']==2 and o['kind']!='background'];self.assertGreaterEqual(len(paths),7)
   self.assertTrue(all(o.get('stroke') for o in paths))
   items,bg,expected,hard=plan(objects,glyphs,*page.get_size(),body,Config(),trace)
   emitted=[a for item in items for a in item['atom_ids']];self.assertEqual(collections.Counter(expected),collections.Counter(emitted))
   self.assertNotIn(backgrounds[0]['id'],emitted)
   self.assertFalse(any(backgrounds[0]['id'] in item.get('objects',[]) for item in items))
   self.assertTrue(any(backgrounds[0]['id'] in item.get('bg_ids',[]) for item in items))
   self.assertNotEqual(collections.Counter(expected),collections.Counter(emitted[:-1]))
   self.assertNotEqual(collections.Counter(expected),collections.Counter(emitted+[emitted[0]]))
   self.assertNotEqual(emitted,list(reversed(emitted)))
   self.assertTrue(all(a['interval'][1]==b['interval'][0] for a,b in zip(items,items[1:])))

if __name__=='__main__':unittest.main()
