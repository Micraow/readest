import json as standard,pathlib,sys,types,unittest
from compact_wire import install,report
class ScopeTests(unittest.TestCase):
 def test_standard_module_unchanged(self):
  original=standard.dumps;owned=types.ModuleType('wire_owned_control');owned.__file__=__file__;owned.json=standard;other=types.ModuleType('wire_outside_control');other.__file__='/outside/research-tree/control.py';other.json=standard;sys.modules[owned.__name__]=owned;sys.modules[other.__name__]=other
  try:
   changes=install(pathlib.Path(__file__).parent);self.assertIs(standard.dumps,original);self.assertIs(other.json,standard);self.assertIsNot(owned.json,standard);self.assertEqual(owned.json.loads(owned.json.dumps({'a':[1,2]},indent=8)),{'a':[1,2]});self.assertEqual(report(changes)['standard_json_module_modified'],False)
  finally:sys.modules.pop(owned.__name__);sys.modules.pop(other.__name__)
if __name__=='__main__':unittest.main()
