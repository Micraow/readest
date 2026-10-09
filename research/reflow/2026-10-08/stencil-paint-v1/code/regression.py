"""One seen-page regression with only the missing paint event added."""
import pathlib,sys,json,importlib.util
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent
sys.path.insert(0,str(W/'stroke-object-batch-v1/code'));import compose,helpers
spec=importlib.util.spec_from_file_location('stencil_envelope',B/'code/envelope.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
compose.inspect=module.inspect;compose.B=B;helpers.B=B
page=next(x for x in json.loads((W/'stroke-object-batch-v1/INPUT-FREEZE.json').read_text())['inputs'] if x['key']=='BatchNorm-v1-p03')
compose.main(page)
