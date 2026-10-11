"""Only authored blank PDFs; originals/candidate assets never enter this suite."""
import hashlib,json,pathlib,tempfile,unittest
from pypdf import PdfWriter
from build_paper_session import build
from serve_paper_session import frozen_routes

class Builder(unittest.TestCase):
 def test_all_original_pages_and_routes_are_pinned(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);pdf=p/'synthetic.pdf';writer=PdfWriter();writer.add_blank_page(width=100,height=150);writer.add_blank_page(width=120,height=140);writer.write(pdf)
   config=p/'config.json';config.write_text(json.dumps(dict(documents=[dict(id='synthetic',title='Synthetic',pdf=str(pdf),sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),page_count=2)])))
   receipt=build(config,p/'out');self.assertEqual(receipt['papers'][0]['rendered_original_pages'],2);self.assertFalse(receipt['browser_verified'])
   routes=frozen_routes(p/'out');self.assertIn('/document/synthetic/page-001.png',routes);self.assertNotIn('/config.json',routes);self.assertNotIn('/document/synthetic/page-002.png',routes)
   manifest=json.loads(routes['/session-manifest.json'][0]);self.assertEqual([x['index'] for x in manifest['documents'][0]['pages']],[0,1]);self.assertTrue(all(x['reflow'] is None for x in manifest['documents'][0]['pages']))
   image=p/'out/synthetic/page-000.png';image.write_bytes(image.read_bytes()+b'changed')
   with self.assertRaisesRegex(ValueError,'pin differs'):frozen_routes(p/'out')
 def test_wrong_source_hash_or_count_never_claims_a_complete_document(self):
  for mode in ('hash','count'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
    p=pathlib.Path(t);pdf=p/'authored.pdf';w=PdfWriter();w.add_blank_page(width=100,height=120);w.write(pdf)
    c=p/'config.json';c.write_text(json.dumps(dict(documents=[dict(id='authored',title='Authored',pdf=str(pdf),sha256='0'*64 if mode=='hash' else hashlib.sha256(pdf.read_bytes()).hexdigest(),page_count=2 if mode=='count' else 1)])))
    with self.assertRaises(ValueError):build(c,p/'out')
    self.assertFalse((p/'out/BUILD-RECEIPT.json').exists())
if __name__=='__main__':unittest.main()
