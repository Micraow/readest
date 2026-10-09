"""Non-content seen-reader provenance and independent composite equality audit.

Native images are compared to independently rendered, accepted member assets.
This proves local source pixel placement, not mixed-engine/browser equivalence.
"""
import argparse,base64,collections,hashlib,io,json,pathlib
import numpy as np
from PIL import Image

def audit(folder,original_plan):
 folder=pathlib.Path(folder);read=lambda p:json.loads((folder/p).read_text())
 assert (folder/'native/fractions/plan-private.json').read_bytes()==pathlib.Path(original_plan).read_bytes(),'native source plan changed'
 data=read('final/reader-data-private.json');plan=read('native/fractions/plan-private.json');assets=read('native/fractions/native-unit-assets-private.json');bridge=read('bridge-private.json');target=read('local-images/local-images-private.json');capture=read('capture/result.json');events={e['id']:e for e in read('capture/events-private.json')};resources=read('capture/resources-private.json');order=read('native/order/order-tree-private.json')
 tokens=[t for b in data['blocks'] for t in b['tokens']];units={u['id']:u for u in plan['units']};expected=collections.Counter(u['id'] for u in assets['results'] if not u.get('empty'));members=collections.Counter(u for t in tokens for u in t['members'])
 assert members==expected and all(v==1 for v in members.values()),'source unit membership changed'
 glyphs=collections.Counter(g['id'] for u in plan['units'] for g in u['glyphs']);emitted=collections.Counter(g['id'] for t in tokens for u in t['members'] for g in units[u]['glyphs'])
 assert emitted==glyphs and all(v==1 for v in emitted.values()),'native glyph membership changed'
 vectors=[t for t in tokens if t['kind']=='vector'];images=[t for t in tokens if t['kind']=='native_image'];paints=collections.Counter(i for t in vectors for i in t['native_event_ids']);wanted=collections.Counter(i for t in vectors for u in t['members'] for i in bridge['converted'][u]['native_event_ids'])
 assert paints==wanted and all(v==1 for v in paints.values()),'vector paint membership changed'
 assert set(map(str,paints))==set(data['events']),'orphan or omitted vector resource'
 for i in paints:
  a=events[i];b=data['events'][str(i)]
  assert all(a[k]==b[k] for k in ['x','y','fontSize'])
  assert b['source_paint_id']==[a['opIdx'],a['glyphOrdinal']]
  assert data['resources'][b['resource']]==resources[a['resource']]
  assert data['affine_programs'][b['program']]==a['state']['affine']
  assert data['states'][b['state']]=={k:a['state'][k] for k in ['fillStyle','alpha','blend','filter']}
 assert target['all_accepted'] and not assets['unsupported_source_support_units']
 composite_pixels=0
 for t in images:
  parts=[target['assets'][u] for u in t['members']];l,y,r,b=t['asset_pixel_box'];actual=np.asarray(Image.open(io.BytesIO(base64.b64decode(t['data_uri'].split(',',1)[1]))).convert('RGBA'));expected_pixels=np.zeros((b-y,r-l,4),np.uint8);expected_pixels[:,:,:3]=parts[0]['background'];coverage=np.zeros(expected_pixels.shape[:2],np.uint8)
  for p in parts:
   assert p['grid']==t['asset_scale'] and p['background']==parts[0]['background']
   image=np.asarray(Image.open(p['absolute_file']).convert('RGBA'));x0,y0,x1,y1=p['asset_pixel_box'];mask=image[:,:,3]>0;counts=coverage[y0-y:y1-y,x0-l:x1-l];assert not np.any(counts[mask]) and np.all(image[:,:,3][mask]==255),'overlap or fractional native support';expected_pixels[y0-y:y1-y,x0-l:x1-l][mask]=image[mask];counts[mask]=1
  assert np.array_equal(actual,expected_pixels),'native image composition changed source pixels or positions'
  composite_pixels+=int(np.count_nonzero(coverage))
 source=read('native/fractions/masked-native-replay.json');assert source['ownership_and_replay_pass'];assert capture['observerDifference']['pixels']==0 and capture['serializedClipReplayDifference']['pixels']==0
 assert order['original_leaf_bijection'] and order['source_unit_bijection'] and order['native_character_bijection'];assert not order['native_index_boundary_conflicts']
 return dict(scope='seen cached-plan diagnostic; no blind or cold-request claim',blocks=len(data['blocks']),source_units=sum(members.values()),native_glyphs=sum(glyphs.values()),source_plan_byte_identical=True,source_unit_bijection=True,native_glyph_bijection=True,vector_paints=sum(paints.values()),vector_paint_bijection=True,native_vector_geometry_resources_and_state_unchanged=True,native_image_tokens=len(images),independent_native_composite_pixel_equality=True,composite_supported_pixels=composite_pixels,unsupported_source_units=0,target_requests_accepted=True,source_replay_exact=True,observer_pixel_difference=0,serialized_clip_replay_pixel_difference=0,native_clip_replay_pixel_difference=capture['nativeClipReplayDifference']['pixels'],native_character_bijection=True,native_interval_conflicts=0,reader_sha256=hashlib.sha256((folder/'final/reader-data-private.json').read_bytes()).hexdigest(),mixed_engine_pixel_ownership_proven=False,browser_verified=False,reading_acceptance=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('original_plan');p.add_argument('out');a=p.parse_args();result=audit(a.reader,a.original_plan);pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
