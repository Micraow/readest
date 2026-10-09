"""Original mechanism-only controls; never a holdout score."""
import unittest
from dataclasses import replace
import numpy as np
from ink_config import InkConfig,LocalGroupConfig,ReaderLayoutConfig
from ink_ownership import partition_alpha
from coalesce_local_intervals import propose
from reader_spacing import separators

def glyph(i,x,y=0,text='x',size=10):
    return dict(id=f'g{i}',source_index=i,object_id='p0',box=[x,y,x+1,y+1],baseline=y+1,char=text,size=size,unicode_known=True)

def unit(i,x,text='x'):
    g=glyph(i,x,text=text)
    return dict(id=f'w{i}',kind='native_word',box=g['box'],glyphs=[g],baseline=g['baseline'],text=text)

class OwnershipTests(unittest.TestCase):
    def test_faint_pixel_is_not_dropped(self):
        a=np.zeros((3,5,4),np.uint8);a[1,1]=[31,44,59,1];g=glyph(0,1)
        pieces,q,r=partition_alpha(a,[0,0,5,3],[g],{'g0':'w0'},InkConfig(render_scale=1))
        self.assertTrue(r['all_ink_uniquely_assigned']);self.assertEqual(r['native_ink_pixels'],1);self.assertTrue(np.array_equal(pieces['w0'][1,1],a[1,1]))
    def test_unknown_owner_retains_quarantine(self):
        a=np.zeros((3,5,4),np.uint8);a[1,1]=[31,44,59,255]
        pieces,q,r=partition_alpha(a,[0,0,5,3],[],{},InkConfig(render_scale=1))
        self.assertEqual(r['unassigned_ink_pixels'],1);self.assertTrue(r['conservation_with_quarantine']);self.assertFalse(r['all_ink_uniquely_assigned'])
    def test_disjoint_shared_native_object(self):
        a=np.zeros((3,7,4),np.uint8);a[0,0]=[0,0,0,255];a[0,5]=[0,0,0,127]
        gs=[glyph(0,0),glyph(1,5)];p,q,r=partition_alpha(a,[0,0,7,3],gs,{'g0':'w0','g1':'w1'},InkConfig(render_scale=1,glyph_support_fringe_pixels=0))
        self.assertTrue(r['all_ink_uniquely_assigned']);self.assertEqual(sum(np.count_nonzero(v[:,:,3]) for v in p.values()),2)
    def test_touching_multiple_owner_component_stays_unresolved(self):
        a=np.zeros((2,5,4),np.uint8);a[0,:,3]=255
        gs=[glyph(0,0),glyph(1,4)];p,q,r=partition_alpha(a,[0,0,5,2],gs,{'g0':'w0','g1':'w1'},InkConfig(render_scale=1,glyph_support_fringe_pixels=1))
        self.assertFalse(r['all_ink_uniquely_assigned']);self.assertTrue(r['conservation_with_quarantine']);self.assertGreater(r['unassigned_ink_pixels'],0)

class LocalIntervalTests(unittest.TestCase):
    def test_contiguous_bounded_closure(self):
        us=[unit(0,0),unit(1,3),unit(2,6)]
        group,trace=propose({'w0','w2'},us,[g for u in us for g in u['glyphs']],[],10,LocalGroupConfig())
        self.assertIsNotNone(group);self.assertEqual(group['source_interval'],[0,3]);self.assertEqual(set(group['former_units']),{'w0','w1','w2'})
    def test_intervening_distant_body_rejected(self):
        us=[unit(0,0),unit(1,1000),unit(2,6)]
        group,trace=propose({'w0','w2'},us,[g for u in us for g in u['glyphs']],[],10,LocalGroupConfig())
        self.assertIsNone(group);self.assertEqual(trace[-1]['rule'],'bounded_local_group')
    def test_character_budget_is_hard(self):
        us=[unit(i,i) for i in range(7)]
        group,trace=propose({'w0','w6'},us,[g for u in us for g in u['glyphs']],[],10,replace(LocalGroupConfig(),max_visible_characters=4))
        self.assertIsNone(group)

class SpacingTests(unittest.TestCase):
    def test_source_gap_not_fallback_font_space(self):
        us=[unit(0,0),unit(2,6)];a={u['id']:{'asset_pixel_box':[u['box'][0]*2,0,u['box'][2]*2,2]} for u in us};gs=[us[0]['glyphs'][0],glyph(1,3,text=' '),us[1]['glyphs'][0]]
        r=separators(['w0','w2'],{u['id']:u for u in us},a,gs,10,2)[0]
        self.assertEqual(r['gap_em'],.5);self.assertEqual(r['semantic_space'],'native_whitespace')
    def test_unspaced_cjk_wrap_has_no_inserted_space(self):
        us=[unit(0,0,'甲'),unit(1,0,'乙')];us[1]['baseline']=15
        a={u['id']:{'asset_pixel_box':[0,0,2,2]} for u in us}
        r=separators(['w0','w1'],{u['id']:u for u in us},a,[g for u in us for g in u['glyphs']],10,2)[0]
        self.assertEqual(r['gap_em'],0);self.assertEqual(r['semantic_space'],'no_certified_whitespace')
    def test_large_geometric_gap_does_not_become_huge_blank(self):
        us=[unit(0,0),unit(1,90)];a={u['id']:{'asset_pixel_box':[u['box'][0]*2,0,u['box'][2]*2,2]} for u in us}
        r=separators(['w0','w1'],{u['id']:u for u in us},a,[g for u in us for g in u['glyphs']],10,2)[0]
        self.assertEqual(r['gap_em'],ReaderLayoutConfig().fallback_word_gap_em)
if __name__=='__main__':unittest.main()
