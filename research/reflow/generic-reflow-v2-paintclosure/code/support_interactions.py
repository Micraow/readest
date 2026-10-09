"""Cross-native-object paint-support interactions; no RGB error threshold.

At one declared native sampling grid, intersect each unit's actual nonzero
support. Edges mean possible composition dependence, not duplicate semantic
atoms. Connected sets may merge only under a separate bounded interval guard.
"""
import argparse,collections,json,math,pathlib
import numpy as np
from PIL import Image

def scan(folder,out=None):
    folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());summary=json.loads((folder/'ownership-summary.json').read_text());scale=summary['config']['render_scale'];W,H=plan['page_size'];coverage=np.zeros((math.ceil(H*scale),math.ceil(W*scale)),np.int32);unitids=[u['id'] for u in plan['units']];pairs=collections.Counter();seen=0
    for number,uid in enumerate(unitids,1):
        for p in plan['patches'].get(uid,[]):
            l,t,r,b=p['pixel_box'];mask=np.array(Image.open(folder/p['file']))[:,:,3]>0;view=coverage[t:b,l:r];other=view[mask];hits=other[(other>0)&(other!=number)]
            ids,counts=np.unique(hits,return_counts=True)
            for idx,count in zip(ids,counts):pairs[tuple(sorted((unitids[idx-1],uid)))]+=int(count)
            view[mask&(view==0)]=number;seen+=int(mask.sum())
    edges=[dict(owners=list(pair),interacting_support_pixels=count) for pair,count in pairs.items()];result=dict(scope='native text-alpha support intersections across different owners at the tested grid; foreground path/image support still separate',render_scale=scale,unit_count=len(unitids),support_pixel_occurrences=seen,edges=edges,interacting_pairs=len(edges),native_renders=0)
    path=pathlib.Path(out) if out else folder/'cross-object-support-private.json';path.write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();print(json.dumps(scan(a.folder)))
