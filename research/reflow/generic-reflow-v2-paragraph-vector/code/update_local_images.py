"""Use target-sized native local paints without changing logical layout advance."""
import argparse,base64,io,json,pathlib
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('assets');p.add_argument('out');a=p.parse_args();data=json.loads(pathlib.Path(a.reader).read_text());result=json.loads(pathlib.Path(a.assets).read_text());assets=result['assets'];traces=[]
if not result['all_accepted']:raise RuntimeError('all requested native local assets must pass')
for block in data['blocks']:
 for token in block['tokens']:
  if token['kind']!='native_image':continue
  aa=[assets[u] for u in token['members']];grids={x['grid'] for x in aa};colors={tuple(x['background']) for x in aa}
  if len(grids)!=1 or len(colors)!=1:raise RuntimeError('local bundle crosses scale/backdrop states')
  l=min(x['asset_pixel_box'][0] for x in aa);t=min(x['asset_pixel_box'][1] for x in aa);r=max(x['asset_pixel_box'][2] for x in aa);b=max(x['asset_pixel_box'][3] for x in aa);rgba=np.zeros((b-t,r-l,4),np.uint8);rgba[:,:,:3]=next(iter(colors));coverage=np.zeros(rgba.shape[:2],np.uint8)
  for asset in aa:
   im=np.array(Image.open(asset['absolute_file']).convert('RGBA'));x,y=asset['asset_pixel_box'][:2];mask=im[:,:,3]>0;target=rgba[y-t:y-t+im.shape[0],x-l:x-l+im.shape[1]];count=coverage[y-t:y-t+im.shape[0],x-l:x-l+im.shape[1]]
   if np.any(count[mask]) or np.any(im[:,:,3][mask]!=255):raise RuntimeError('new target-grid local bundle overlap or fractional layer')
   target[mask]=im[mask];count[mask]=1
  buffer=io.BytesIO();Image.fromarray(rgba,'RGBA').save(buffer,format='PNG');token.update(data_uri='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),asset_scale=next(iter(grids)),asset_pixel_box=[l,t,r,b]);traces.append({'token':token['id'],'members':token['members'],'grid':token['asset_scale'],'overlapping_support_pixels':0,'fixed_source_layout_box_preserved':True,'bytes':len(buffer.getvalue()),'decoded_bytes':rgba.nbytes})
data.update(local_images_target_grid_verified=True,native_image_policy='source-light native final RGB/support at regenerated target grid; arbitrary backdrop/zoom not certified');out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,separators=(',',':')));(out.parent/'local-image-update-private.json').write_text(json.dumps(traces,indent=2));print(json.dumps({'tokens':len(traces),'png_bytes':sum(x['bytes'] for x in traces),'decoded_bytes':sum(x['decoded_bytes'] for x in traces),'payload_bytes':out.stat().st_size}))
