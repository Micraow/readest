"""Mutation checks on privately acquired reader evidence; no fixture redistribution."""
import argparse,copy,json,pathlib,tempfile
from audit_atomic_reader import audit
p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('original_plan');a=p.parse_args();source=pathlib.Path(a.reader).resolve();data=json.loads((source/'final/reader-data-private.json').read_text());passed=[]
def duplicate_member(d):d['blocks'][0]['tokens'][0]['members']*=2
def duplicate_paint(d):
 t=next(t for b in d['blocks'] for t in b['tokens'] if t['kind']=='vector');t['native_event_ids']*=2
def moved_paint(d):next(iter(d['events'].values()))['x']+=1
def changed_affine(d):d['affine_programs'][0].append({'name':'translate','args':[1,0]})
def changed_native_image_origin(d):
 t=next(t for b in d['blocks'] for t in b['tokens'] if t['kind']=='native_image');t['asset_pixel_box'][0]-=1
for change in [duplicate_member,duplicate_paint,moved_paint,changed_affine,changed_native_image_origin]:
 with tempfile.TemporaryDirectory() as tmp:
  root=pathlib.Path(tmp)
  for name in ['native','local-images','capture','bridge-private.json']:(root/name).symlink_to(source/name)
  (root/'final').mkdir();mutated=copy.deepcopy(data);change(mutated);(root/'final/reader-data-private.json').write_text(json.dumps(mutated))
  try:audit(root,a.original_plan)
  except AssertionError:passed.append(change.__name__)
  else:raise AssertionError('audit accepted mutation: '+change.__name__)
print(json.dumps(dict(mutation_controls=len(passed),rejected=passed,browser_verified=False)))
