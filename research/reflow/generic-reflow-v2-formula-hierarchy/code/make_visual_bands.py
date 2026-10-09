"""Private inspection images only; these are never the reading representation."""
import argparse,json,pathlib
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('render');p.add_argument('out');a=p.parse_args();folder=pathlib.Path(a.render);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);r=json.loads((folder/'render-summary.json').read_text());images=[Image.open(f).convert('RGB') for f in sorted(folder.glob('block-*.png'))];full=Image.new('RGB',(max(im.width for im in images),sum(im.height for im in images)),'white');y=0
for im in images:full.paste(im,(0,y));y+=im.height
# Preserve native DPR for the private full image; review bands use CSS dimensions.
full.save(out/'full-native.png');css=full.resize((390,round(full.height/r['dpr'])),Image.Resampling.LANCZOS) if r['dpr']!=1 else full;css.save(out/'full.png');band=1400
for i,y in enumerate(range(0,css.height,band)):css.crop((0,y,css.width,min(y+band,css.height))).save(out/('band-%02d.png'%i))
print(json.dumps({'height_css':css.height,'bands':(css.height+band-1)//band,'private_review_only':True}))
