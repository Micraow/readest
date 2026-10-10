import copy,unittest
from title_structure import apply_titles
class Controls(unittest.TestCase):
 def fixture(self):
  units=[];leaves=[];blocks=[];assets=[];glyphs=[]
  for row,(x,y) in enumerate([(20,20),(25,32)]):
   ids=[]
   for col in range(2):
    uid=f'w{row}{col}';ids.append(uid);i=row*10+col*2;g=dict(id='g'+str(i),source_index=i,char='A',baseline=y+8,size=10);glyphs.append(g);units.append(dict(id=uid,kind='native_word',glyphs=[g],baseline=y+8));assets.append(dict(id=uid,asset_pixel_box=[x+col*25,y,x+col*25+20,y+10]));
   leaves.append(dict(id='l'+str(row),box=[x,y,x+45,y+10],role='source_line',unit_ids=ids,native_indexes=[row*10,row*10+2],baseline=y+8));blocks.append(dict(kind='paragraph',tokens=[dict(id=u,members=[u],kind='vector',gap_em=0) for u in ids]))
  reader=dict(blocks=blocks,resources=[],events={},states=[],affine_programs=[]);plan=dict(units=units,glyphs=glyphs);asset=dict(results=assets,scale=1);order=dict(sequence=['l0','l1'],tree=dict(kind='rows',children=[dict(kind='leaf',id='l0'),dict(kind='leaf',id='l1')]));priors=[dict(label='paragraph_title',score=.9,box=[20,19,71,43])]
  return [reader,plan,asset,leaves,order,priors,10]
 def check(self,args):return apply_titles(*args)
 def test_complete_title_joins_preserving_input_and_resources(self):
  a=self.fixture();before=copy.deepcopy(a);r,t=self.check(a);self.assertEqual(len(r['blocks']),1);self.assertTrue(t[0]['accepted']);self.assertEqual(a,before);self.assertGreater(r['blocks'][0]['tokens'][1]['gap_em'],0)
 def test_body_text_prior_has_no_authority(self):
  a=self.fixture();a[5][0]['label']='text';r,t=self.check(a);self.assertEqual(r,a[0]);self.assertEqual(t,[])
 def test_low_confidence_title_refuses(self):
  a=self.fixture();a[5][0]['score']=.5;self.assertFalse(self.check(a)[1][0]['accepted'])
 def test_external_body_overlap_prior_refuses(self):
  a=self.fixture();a[5].append(dict(label='text',score=.99,box=[20,19,71,43]));self.assertEqual(self.check(a)[1][0]['reason'],'conflicting_region_prior')
 def test_graphic_leaf_refuses(self):
  a=self.fixture();a[3][1]['role']='protected_local';self.assertEqual(self.check(a)[1][0]['reason'],'partial_or_nontext_title_leaf')
 def test_truncated_prior_beyond_existing_closure_refuses(self):
  a=self.fixture();a[5][0]['box'][2]=50;self.assertEqual(self.check(a)[1][0]['reason'],'partial_or_nontext_title_leaf')
 def test_two_columns_refuse(self):
  a=self.fixture();a[4]['tree']['kind']='columns';self.assertEqual(self.check(a)[1][0]['reason'],'title_crosses_columns')
 def test_tall_line_gap_refuses(self):
  a=self.fixture();a[3][1]['baseline']=60;self.assertEqual(self.check(a)[1][0]['reason'],'title_line_gap_outside_existing_bound')
 def test_font_size_change_refuses(self):
  a=self.fixture();a[1]['units'][-1]['glyphs'][0]['size']=25;self.assertEqual(self.check(a)[1][0]['reason'],'title_font_size_change')
 def test_uncertain_image_token_refuses(self):
  a=self.fixture();a[0]['blocks'][1]['tokens'][0]['kind']='native_image';r,t=self.check(a);self.assertEqual(r,a[0]);self.assertEqual(t[0]['reason'],'uncertain_title_token_keeps_existing_layout')
 def test_external_token_in_block_refuses(self):
  a=self.fixture();a[0]['blocks'][1]['tokens'].append(dict(id='body',members=['body'],kind='vector',gap_em=0));self.assertEqual(self.check(a)[1][0]['reason'],'title_block_contains_external_content')
 def test_foreign_native_interval_refuses(self):
  a=self.fixture();a[3].append(dict(id='body',box=[100,80,140,90],role='source_line',native_indexes=[5]));self.assertEqual(self.check(a)[1][0]['reason'],'foreign_native_source_interval')
 def test_intervening_visible_record_refuses_without_mutation(self):
  a=self.fixture();a[1]['glyphs'].append(dict(id='foreign',source_index=5,char='X'));r,t=self.check(a);self.assertEqual(r,a[0]);self.assertEqual(t[0]['reason'],'visible_native_record_between_title_lines')
 def test_later_boundary_refusal_does_not_partially_mutate_first_gap(self):
  a=self.fixture();reader,plan,asset,leaves,order,priors,body=a
  us=copy.deepcopy(plan['units'][2:]);ats=copy.deepcopy(asset['results'][2:]);leaf=copy.deepcopy(leaves[1]);block=copy.deepcopy(reader['blocks'][1])
  for u,x,t in zip(us,ats,block['tokens']):
   old=u['id'];new=old+'x';u['id']=new;u['baseline']+=12;u['glyphs'][0]['id']+='x';u['glyphs'][0]['source_index']+=10;u['glyphs'][0]['baseline']+=12;x['id']=new;x['asset_pixel_box'][1]+=12;x['asset_pixel_box'][3]+=12;t['id']=new;t['members']=[new]
  leaf.update(id='l2',unit_ids=[u['id'] for u in us],native_indexes=[20,22],baseline=52,box=[25,44,70,54]);plan['units']+=us;plan['glyphs'] += [u['glyphs'][0] for u in us]+[dict(id='between',source_index=15,char='X')];asset['results']+=ats;reader['blocks'].append(block);leaves.append(leaf);order['sequence'].append('l2');order['tree']['children'].append(dict(kind='leaf',id='l2'));priors[0]['box'][3]=55
  r,t=self.check(a);self.assertEqual(r,reader);self.assertEqual(t[0]['reason'],'visible_native_record_between_title_lines')
if __name__=='__main__':unittest.main()
