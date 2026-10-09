import unittest,copy,json,pathlib,tempfile
from bounded_inline import propose,InlineConfig
from apply_region_priors import table_evidence,PriorConfig
from diagnose_native_regions import make_lines

def g(i,x,y,text='x',size=10,known=True,baseline=None):return dict(id='g'+str(i),source_index=i,object_id='p'+str(i),char=text,box=[x,y,x+2,y+2],baseline=y+2 if baseline is None else baseline,size=size,unicode_known=known,native_object_ink_observed=True)
def u(i,glyphs,objects=(),kind='native_word'):
 b=[min(g['box'][0] for g in glyphs),min(g['box'][1] for g in glyphs),max(g['box'][2] for g in glyphs),max(g['box'][3] for g in glyphs)] if glyphs else [0,5,100,5.5]
 return dict(id='u'+str(i),kind=kind,box=b,glyphs=glyphs,objects=list(objects),text=''.join(g['char'] for g in glyphs),baseline=glyphs[0]['baseline'] if glyphs else 5.5)
class NativeStructureTests(unittest.TestCase):
 def test_graphic_only_fraction_seed_refuses_without_mutating(self):
  units=[dict(id='u9',kind='island',box=[1,5,5,5.5],glyphs=[],objects=['p9'])];objects=[dict(id='p9',type=3,box=[1,5,5,5.5],horizontal_stroke=True)];before=copy.deepcopy((units,objects))
  group,trace=propose({'u9'},units,[],objects,10,InlineConfig())
  self.assertIsNone(group);self.assertEqual(trace[-1]['rule'],'native_interval_requires_visible_glyphs');self.assertEqual((units,objects),before)
 def test_empty_seed_refuses(self):
  group,trace=propose(set(),[],[],[],10,InlineConfig());self.assertIsNone(group);self.assertEqual(trace[-1]['rule'],'native_interval_requires_visible_glyphs')
 def test_missing_native_record_refuses(self):
  group,trace=propose({'u0'},[u(0,[g(0,1,1)])],[],[],10,InlineConfig());self.assertIsNone(group)
 def test_empty_native_word_neighbor_is_not_invented(self):
  glyph=g(0,1,1);empty=dict(id='empty',kind='native_word',glyphs=[],objects=[],box=[4,1,5,3]);group,trace=propose({'u0'},[u(0,[glyph]),empty],[glyph],[],10,InlineConfig())
  self.assertIsNotNone(group);self.assertEqual(group['former_units'],['u0']);self.assertTrue(any(t['rule']=='neighbor_requires_native_glyphs' for t in trace))
 def test_fraction_closure_retains_original_graphic_paint(self):
  from close_native_fractions import close
  with tempfile.TemporaryDirectory() as folder:
   source=pathlib.Path(folder)/'source';out=pathlib.Path(folder)/'out';source.mkdir();unit=dict(id='u9',kind='island',box=[1,5,5,5.5],glyphs=[],objects=['p9']);plan=dict(units=[unit],glyphs=[],objects=[dict(id='p9',type=3,box=[1,5,5,5.5])],patches={'u9':[]})
   (source/'plan-private.json').write_text(json.dumps(plan));(source/'ownership-summary.json').write_text('{"body_font":10}');(source/'ownership-records.json').write_text('[]');result=close(source,out);rebuilt=json.loads((out/'plan-private.json').read_text());self.assertEqual(rebuilt['units'],plan['units']);self.assertEqual(rebuilt['objects'],plan['objects']);self.assertEqual(result['new_groups'],0)

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
