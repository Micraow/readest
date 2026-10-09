"""Authored geometry controls; no real-paper source strings or fonts."""
import copy,math,unittest
from geometry_evidence import local_anchor_ids,formula_evidence,label_extension_ok
from direction_groups import group
from diagnose_native_regions import make_lines

def unit(uid,x,y,size=10,text='abcd',known=True,angle=0,object_id=None,start=0):
    gs=[]
    for i,c in enumerate(text):
        gs.append({'id':f'g{start+i}','source_index':start+i,'object_id':object_id or uid,'char':c,'unicode_known':known,'native_object_ink_observed':True,'size':size,'baseline':y,'origin':x+i*.6*size,'box':[x+i*.6*size,y-.7*size,x+(i+.5)*.6*size,y],'native_angle_radians':angle})
    return {'id':uid,'kind':'native_word','box':[x,y-.7*size,gs[-1]['box'][2],y],'baseline':y,'glyphs':gs}
def plan(us):return {'units':us,'glyphs':[g for u in us for g in u['glyphs']],'patches':{},'page_size':[600,800],'objects':[]}
class Controls(unittest.TestCase):
    def test_small_metadata_row(self):
        us=[unit('a',20,100,7),unit('b',40,100,7,start=4),unit('large',20,140,10,start=8)]
        ids,_=local_anchor_ids(us,10);self.assertTrue({'a','b'}<=ids)
    def test_adjacent_superscript_is_not_line(self):
        us=[unit('base',20,100,12,text='X'),unit('script',30,94,7,text='abcd',start=1)]
        ids,_=local_anchor_ids(us,12);self.assertNotIn('script',ids)
    def test_isolated_small_glyph_abstains(self):
        ids,_=local_anchor_ids([unit('a',20,100,6,text='x')],12);self.assertFalse(ids)
    def test_unknown_full_size_can_anchor(self):
        leaves,d=make_lines(plan([unit('a',20,100,10,known=False)]),10);self.assertFalse(d['unresolved_small_units']);self.assertEqual(len(leaves),1)
    def test_unknown_thin_accent_is_not_independent_anchor(self):
        u=unit('a',20,100,10,text='? ',known=False);u['glyphs']=u['glyphs'][:1];u['glyphs'][0]['box']=[20,88,24,89];u['box']=[20,88,24,89]
        _,d=make_lines(plan([u]),10);self.assertEqual(d['unresolved_small_units'],['a'])
    def formula(self):
        a=unit('tall',20,100,10,text='?',known=False);a['glyphs'][0]['box']=[20,82,24,105];a['box']=[20,82,24,105]
        b=unit('main',25,100,10,text='abcde',known=False,start=1);c=unit('script',29,95,6,text='ij',known=False,start=6)
        return [a,b,c]
    def test_unknown_formula_positive_geometry(self):self.assertTrue(formula_evidence(self.formula(),[],10)['pass_native_structure'])
    def test_prose_with_one_citation_rejected(self):
        us=[unit('p',20,100,10,text='a'*35),unit('s',220,95,6,text='1',start=35)];self.assertFalse(formula_evidence(us,[],10)['pass_native_structure'])
    def test_filled_fraction_bar_is_geometric_evidence(self):
        us=[unit('a',20,100,text='a'),unit('b',20,94,6,text='mn',start=1),{'id':'bar','kind':'island','box':[20,96,32,96.3],'glyphs':[],'objects':['p9']}]
        ev=formula_evidence(us,[{'id':'p9','type':2,'box':[20,96,32,96.3]}],10);self.assertTrue(ev['pass_native_structure'])
    def test_unknown_prose_not_auto_formula(self):self.assertFalse(formula_evidence([unit('p',20,100,10,known=False)],[],10)['pass_native_structure'])
    def test_far_equation_label(self):
        a=unit('a',20,100,text='abc');n=unit('n',80,100,text='(2)',start=3);ok,_=label_extension_ok([a,n],[18,88,45,102],[a,n],10);self.assertTrue(ok)
    def test_label_unknown_unicode_rejected(self):
        a=unit('a',20,100);n=unit('n',80,100,text='(2)',known=False,start=4);self.assertFalse(label_extension_ok([a,n],[18,88,45,102],[a,n],10)[0])
    def test_label_intervening_prose_rejected(self):
        a=unit('a',20,100,text='abc');n=unit('n',100,100,text='(2)',start=3);b=unit('b',55,100,text='abc',start=6);self.assertFalse(label_extension_ok([a,n],[18,88,45,102],[a,n,b],10)[0])
    def test_label_between_two_rows_rejected(self):
        a=unit('a',20,96,text='abc');b=unit('b',20,104,text='abc',start=3);n=unit('n',100,100,text='(2)',start=6);self.assertFalse(label_extension_ok([a,b,n],[18,85,45,108],[a,b,n],10)[0])
    def test_rotation_preserved_as_closed_unit(self):
        us=[unit('a',20,100,angle=math.pi/2,object_id='p0'),unit('b',20,120,angle=math.pi/2,object_id='p0',start=4)];result,t=group(plan(us));self.assertEqual(len(result['units']),1);self.assertTrue(t[0]['accepted']);self.assertEqual(len(result['units'][0]['glyphs']),8)
    def test_mixed_direction_abstains(self):
        us=[unit('a',20,100,angle=math.pi/2,object_id='p0'),unit('b',20,120,angle=0,object_id='p0',start=4)];result,t=group(plan(us));self.assertEqual(len(result['units']),2);self.assertFalse(t[0]['accepted'])
    def test_rotated_interval_foreign_content_abstains(self):
        us=[unit('a',20,100,text='aa',angle=math.pi/2,object_id='p0'),unit('foreign',100,100,text='x',start=2),unit('b',20,120,text='bb',angle=math.pi/2,object_id='p0',start=3)];_,t=group(plan(us));self.assertFalse(t[0]['accepted'])
if __name__=='__main__':unittest.main()
