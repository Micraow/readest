import unittest
from bounded_inline import propose,InlineConfig
from apply_region_priors import table_evidence,PriorConfig
from diagnose_native_regions import make_lines

def g(i,x,y,text='x',size=10,known=True,baseline=None):return dict(id='g'+str(i),source_index=i,object_id='p'+str(i),char=text,box=[x,y,x+2,y+2],baseline=y+2 if baseline is None else baseline,size=size,unicode_known=known,native_object_ink_observed=True)
def u(i,glyphs,objects=(),kind='native_word'):
 b=[min(g['box'][0] for g in glyphs),min(g['box'][1] for g in glyphs),max(g['box'][2] for g in glyphs),max(g['box'][3] for g in glyphs)] if glyphs else [0,5,100,5.5]
 return dict(id='u'+str(i),kind=kind,box=b,glyphs=glyphs,objects=list(objects),text=''.join(g['char'] for g in glyphs),baseline=glyphs[0]['baseline'] if glyphs else 5.5)
class NativeStructureTests(unittest.TestCase):
 def test_fraction_does_not_take_next_line_numerator(self):
  gs=[g(0,2,0,size=7),g(1,2,8,size=7),g(2,2,13,size=7)];us=[u(0,[gs[0]]),u(1,[gs[1]],['p9'],'island'),u(2,[gs[2]])];objs=[dict(id='p9',box=[1,5,5,5.5],horizontal_stroke=True)]
  group,trace=propose({'u1'},us,gs,objs,10,InlineConfig(math_neighbor_gap_em=0,short_identifier_characters=0))
  self.assertIsNotNone(group);self.assertEqual(set(group['former_units']),{'u0','u1'});self.assertNotIn('g2',[g['id'] for g in group['glyphs']])
 def test_thin_image_rule_and_repeated_cells_support_table(self):
  us=[u(i,[g(i,x,y,text='1')]) for i,(x,y) in enumerate([(10,20),(70,20),(10,40),(70,40),(10,60),(70,60)])];us.append(u(9,[],['p9'],'island'));objs=[dict(id='p9',type=3,box=[0,5,100,5.5])]
  self.assertTrue(table_evidence(us,objs,[0,0,100,70],10,PriorConfig())['pass_native_structure'])
 def test_underlined_single_column_prose_is_not_table(self):
  us=[u(i,[g(i,10,y,text='a')]) for i,y in enumerate([20,40,60])];us.append(u(9,[],['p9'],'island'));objs=[dict(id='p9',type=3,box=[0,5,100,5.5])]
  self.assertFalse(table_evidence(us,objs,[0,0,100,70],10,PriorConfig())['pass_native_structure'])
 def test_unknown_symbol_bridge_is_not_false_column(self):
  a=g(0,10,50,baseline=58);a['box'][2]=15;b=g(1,33,50,baseline=58);b['box'][2]=42;c=g(2,18,50,known=False,baseline=50);c['box'][2]=30
  plan=dict(units=[u(0,[a]),u(1,[b]),u(2,[c])],page_size=[100,200]);leaves,result=make_lines(plan,10)
  self.assertEqual(len(leaves),1);self.assertEqual(set(leaves[0]['unit_ids']),{'u0','u1','u2'})
if __name__=='__main__':unittest.main()
