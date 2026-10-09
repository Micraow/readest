import pathlib,tempfile,unittest
from PIL import Image
from rendered_support import edges
class Controls(unittest.TestCase):
 def check(self,alpha_a,alpha_b,box_b):
  with tempfile.TemporaryDirectory() as d:
   for name,alpha in [('a',alpha_a),('b',alpha_b)]:
    im=Image.new('RGBA',(2,2));im.putdata([(0,0,0,a) for a in alpha]);im.save(pathlib.Path(d)/(name+'.png'))
   return edges(d,[dict(id='a',file='a.png',asset_pixel_box=[0,0,2,2]),dict(id='b',file='b.png',asset_pixel_box=box_b)])
 def test_nonzero_faint_alpha_is_not_dropped(self):self.assertEqual(self.check([1]*4,[1]*4,[1,1,3,3])[0]['pixels'],1)
 def test_disjoint_actual_support_is_not_bbox_overlap(self):self.assertEqual(self.check([255,0,0,0],[0,0,0,255],[0,0,2,2]),[])
 def test_adjacent_boxes_do_not_interact(self):self.assertEqual(self.check([255]*4,[255]*4,[2,0,4,2]),[])
 def test_wrong_asset_dimensions_refuse(self):
  with self.assertRaises(ValueError):self.check([255]*4,[255]*4,[0,0,3,2])
if __name__=='__main__':unittest.main()
