import unittest
from analyze import coordinates, extract
from request import FIELDS, multipart


class StructureEvidenceTests(unittest.TestCase):
    def test_coordinates_remain_separate_across_pages(self):
        boxes = coordinates('1,10,20,30,4;2,15,18,25,4')
        self.assertEqual([b['page'] for b in boxes], [1, 2])
        self.assertEqual(len(boxes), 2)

    def test_invalid_coordinates_fail_closed(self):
        for raw in ('0,1,1,1,1', '1,nan,1,1,1', '1,1,1,-1,1', '1,1,1,1'):
            with self.assertRaises(ValueError):
                coordinates(raw)

    def test_caption_relation_does_not_invent_caption_box(self):
        _, nodes, relations = extract('''<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div>
          <p coords="1,1,1,30,5">before <ref type="figure" target="#fig_1">Fig. 1</ref></p>
          <figure xml:id="fig_1" coords="1,1,9,30,20"><figDesc>caption</figDesc></figure>
          <p coords="1,1,31,30,5;2,1,1,30,5">continued text</p>
          <formula coords="2,1,7,30,5">a b 2</formula>
          <ref target="#missing">[9]</ref>
        </div></body></text></TEI>''')
        caption = next(n for n in nodes if n['tag'] == 'figDesc')
        self.assertEqual(caption['coords'], [])
        self.assertTrue(caption['figureEnvelopeForReviewOnly'])
        self.assertTrue(any(r['relation'] == 'caption-of' for r in relations))
        self.assertTrue(any(r.get('resolved') is False for r in relations))
        self.assertTrue(any(r.get('resolved') is True for r in relations))
        formula = next(n for n in nodes if n['tag'] == 'formula')
        self.assertEqual(formula['text'], 'a b 2')
        self.assertNotIn('latex', formula)

    def test_request_no_consolidation_no_page_cropping(self):
        fields = dict(FIELDS)
        for name in ('consolidateHeader', 'consolidateCitations', 'consolidateFunders'):
            self.assertEqual(fields[name], '0')
        self.assertNotIn('start', fields)
        self.assertNotIn('end', fields)
        boundary, body = multipart(b'%PDF-test', 'public.pdf')
        self.assertIn(b'%PDF-test', body)
        self.assertTrue(body.endswith(('--' + boundary + '--\r\n').encode()))


if __name__ == '__main__':
    unittest.main()
