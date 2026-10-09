"""Post-run deterministic oracle check, not another model/configuration experiment.
The oracle is authored source-layer identity, independent of connected components.
"""
import pathlib,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fixtures import fixture
from masks import partition
B=pathlib.Path(__file__).resolve().parents[1]
rows=[]
for kind in ['wide_white_background','white_overpaint','late_separate_text']:
 im,boxes,_=fixture(kind);owners,metrics=partition(np.asarray(im),boxes)
 gold=np.zeros((im.height,im.width),np.int32)
 def paint_label(owner,paint):
  layer=Image.new('RGB',im.size,'white');paint(ImageDraw.Draw(layer));gold[np.any(np.asarray(layer)!=255,axis=2)]=owner
 paint_label(1,lambda d:d.line([(45,75),(62,92),(76,42),(135,42)],fill='black',width=5))
 paint_label(2,lambda d:d.text((220,70),'LATER BODY',fill='black'))
 if kind=='white_overpaint':gold[35:56,90:146]=0
 if kind=='late_separate_text':
  gold[120:220,:]=0;paint_label(3,lambda d:d.text((46,160),'AFTER BACKGROUND',fill='black'))
 expected=np.asarray(gold);ink=np.any(np.asarray(im)!=255,axis=2)
 rows.append({'case':kind,'oracle_visible_ink_disagreement':int(((expected>0)!=ink).sum()),'wrong_semantic_owner_pixels':int((owners!=expected).sum()),'hidden_ink_resurrected':int(((owners>0)&~ink).sum()),'refused':metrics['whole_page_refusal']})
result={'scope':'Deterministic post-run oracle verification on the same three accepted original fixtures. No rule changes, new training or generalization claim. Negative fixtures retain their prior refusal results. An initial integer-label raster incorrectly lost antialiased font-edge pixels; oracle corrected to RGB layer masks, with invalid audit preserved.','algorithm_sha256':hashlib.sha256((B/'code/masks.py').read_bytes()).hexdigest(),'rows':rows};(B/'OWNERSHIP-AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
