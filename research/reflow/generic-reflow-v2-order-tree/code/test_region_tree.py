import unittest
from region_tree import build_tree,AmbiguousOrder

def b(uid,x,y,w=100,h=30):return dict(id=uid,box=[x,y,x+w,y+h],provenance='authored rectangular mechanism case')
class ContractTests(unittest.TestCase):
 def test_two_columns_finish_left_first(self):
  blocks=[b('L1',10,10),b('R1',150,10),b('L2',10,60),b('R2',150,60)]
  self.assertEqual(build_tree(blocks)['sequence'],['L1','L2','R1','R2'])
 def test_spanning_title_then_columns(self):
  blocks=[b('title',10,0,240,25),b('L1',10,45),b('R1',150,45),b('L2',10,90),b('R2',150,90)]
  self.assertEqual(build_tree(blocks)['sequence'],['title','L1','L2','R1','R2'])
 def test_small_title_gap_does_not_split_larger_paragraph_gap_first(self):
  blocks=[b('title',10,0,240,25),b('L1',10,32),b('R1',150,32),b('L2',10,110),b('R2',150,110)]
  self.assertEqual(build_tree(blocks)['sequence'],['title','L1','L2','R1','R2'])
 def test_middle_span_breaks_column_bands(self):
  blocks=[b('L1',10,10),b('R1',150,10),b('figure',10,65,240,70),b('L2',10,160),b('R2',150,160)]
  self.assertEqual(build_tree(blocks)['sequence'],['L1','R1','figure','L2','R2'])
 def test_embedded_figure_keeps_own_column(self):
  blocks=[b('L1',10,10),b('figure',10,60,100,70),b('L2',10,155),b('R1',150,10,100,80),b('R2',150,120,100,70)]
  self.assertEqual(build_tree(blocks)['sequence'],['L1','figure','L2','R1','R2'])
 def test_crossing_float_must_abstain(self):
  with self.assertRaises(AmbiguousOrder):build_tree([b('L',10,10,100,150),b('R',150,10,100,150),b('float',80,70,100,50)])
 def test_duplicate_leaf_rejects(self):
  with self.assertRaises(ValueError):build_tree([b('same',10,10),b('same',150,10)])
 def test_node_descendants_are_contiguous(self):
  r=build_tree([b('L1',10,10),b('R1',150,10),b('L2',10,60),b('R2',150,60)]);self.assertEqual(r['tree']['output_interval'],[0,4]);self.assertEqual([x['output_interval'] for x in r['tree']['children']],[[0,2],[2,4]])
if __name__=='__main__':unittest.main()
