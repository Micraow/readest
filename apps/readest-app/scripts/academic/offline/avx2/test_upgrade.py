# SPDX-License-Identifier: AGPL-3.0-or-later
import importlib.util,pathlib,tempfile,json,unittest,hashlib
spec=importlib.util.spec_from_file_location('upgrade',pathlib.Path(__file__).with_name('upgrade.py'));u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class UpgradeTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=pathlib.Path(self.t.name);self.s=self.r/'old';self.s.mkdir();self.d=self.r/'new';self.p=self.r/'payload';self.p.mkdir()
  for name in ['bin','models','python','scripts']:(self.s/name).mkdir()
  for name,data in [('run.sh',b'"$ROOT/launch.py"'),('launch.py',b'pass'),('bin/libggml-cpu.so.0',b'old'),('models/fake',b'model')]:
   (self.s/name).write_bytes(data)
  self.files=[{'path':p.relative_to(self.s).as_posix(),'bytes':p.stat().st_size,'sha256':u.digest(p)} for p in self.s.rglob('*') if p.is_file()]
  (self.s/'SHA256-MANIFEST.json').write_text(json.dumps({'files':self.files}));u.BASE_MANIFEST=u.digest(self.s/'SHA256-MANIFEST.json');(self.p/'libggml-cpu.so.0').write_bytes(b'new');u.BACKEND_SHA=u.digest(self.p/'libggml-cpu.so.0')
 def test_success_preserves_original(self):
  before={p.relative_to(self.s).as_posix():p.read_bytes() for p in self.s.rglob('*') if p.is_file()};u.upgrade(self.s,self.d,self.p)
  self.assertEqual(before,{p.relative_to(self.s).as_posix():p.read_bytes() for p in self.s.rglob('*') if p.is_file()});self.assertEqual((self.d/'bin/libggml-cpu.so.0').read_bytes(),b'new');self.assertIn('cpu_guard.py',(self.d/'run.sh').read_text())
  m=json.loads((self.d/'SHA256-MANIFEST.json').read_text());self.assertTrue(all(u.digest(self.d/e['path'])==e['sha256'] for e in m['files']))
 def test_existing_destination(self):
  self.d.mkdir()
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_nested_destination(self):
  with self.assertRaises(ValueError):u.upgrade(self.s,self.s/'new',self.p)
 def test_changed_source(self):
  (self.s/'models/fake').write_bytes(b'wrong')
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
  self.assertFalse(self.d.exists())
 def test_wrong_manifest(self):
  u.BASE_MANIFEST='x'
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_wrong_backend(self):
  u.BACKEND_SHA='x'
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_extra_runtime(self):
  (self.s/'bin/extra').write_bytes(b'x')
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_symlink_source(self):
  (self.s/'bin/libggml-cpu.so.0').unlink();(self.s/'bin/libggml-cpu.so.0').symlink_to(self.p/'libggml-cpu.so.0')
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_symlink_destination(self):
  self.d.symlink_to(self.r/'absent')
  with self.assertRaises(ValueError):u.upgrade(self.s,self.d,self.p)
 def test_path_traversal(self):
  with self.assertRaises(ValueError):u.safe_file(self.s,'../x')
if __name__=='__main__':unittest.main()
