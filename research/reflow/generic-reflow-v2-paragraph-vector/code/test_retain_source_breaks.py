import copy,unittest
from test_hyphen_boundaries import fixture
from retain_source_breaks import annotate
class Controls(unittest.TestCase):
 def fixture(self):
  a,b=fixture('ab-','cd');units=[dict(id='left',glyphs=a),dict(id='right',glyphs=b)];plan=dict(units=units,glyphs=a+b);tokens=[dict(id='left',kind='vector',members=['left'],gap_em=0,source_pixel_box=[30,0,55,20]),dict(id='right',kind='vector',members=['right'],gap_em=0,source_pixel_box=[10,24,30,44])];data=dict(body_font_pdf=10,blocks=[dict(kind='paragraph',tokens=tokens)],resources=[],events={});return [data,plan,[],dict(converted={})]
 def test_retains_source_break_without_changing_ink_or_input(self):
  a=self.fixture();before=copy.deepcopy(a);d,t=annotate(*a);self.assertEqual(a,before);self.assertEqual(len(t),1);self.assertTrue(d['blocks'][0]['tokens'][0]['retained_source_break_after']);self.assertEqual(d['resources'],a[0]['resources']);self.assertEqual(d['events'],a[0]['events']);self.assertFalse(t[0]['semantic_selection_certified']);self.assertEqual(t[0]['printed_glyphs_deleted'],0)
 def test_corrobated_unknown_bar_is_preserved_not_certified(self):
  a=self.fixture();g=a[1]['units'][0]['glyphs'][-1];g.update(unicode_known=False,char='\x02',box=[40,6,43,6.3]);a[2]=[dict(id=2,unicodeCandidate='-')];a[3]['converted']={'left':dict(correspondence=[dict(source_glyph=g['id'],native_event=2)])};d,t=annotate(*a);self.assertEqual(len(t),1);self.assertTrue(t[0]['secondary_native_candidate_used']);self.assertFalse(t[0]['semantic_selection_certified'])
 def test_unknown_uncorroborated_terminal_refuses(self):
  a=self.fixture();a[1]['units'][0]['glyphs'][-1].update(unicode_known=False,char='\x02');d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
 def test_uppercase_suffix_stays_refused(self):
  a=self.fixture();a[1]['units'][1]['glyphs'][0]['char']='C';d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
 def test_nonzero_separator_not_silently_changed(self):
  a=self.fixture();a[0]['blocks'][0]['tokens'][0]['gap_em']=.2;d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
 def test_protected_object_not_modified(self):
  a=self.fixture();a[0]['blocks'][0]['kind']='object';d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
 def test_missing_forward_source_box_refuses(self):
  a=self.fixture();a[0]['blocks'][0]['tokens'][1]['source_pixel_box']=[10,0,30,20];d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
 def test_no_cross_paragraph_boundary_added(self):
  a=self.fixture();tokens=a[0]['blocks'][0]['tokens'];a[0]['blocks']=[dict(kind='paragraph',tokens=[tokens[0]]),dict(kind='paragraph',tokens=[tokens[1]])];d,t=annotate(*a);self.assertEqual(d,a[0]);self.assertEqual(t,[])
if __name__=='__main__':unittest.main()
