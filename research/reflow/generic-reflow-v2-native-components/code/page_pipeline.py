"""Fresh native pipeline with opt-in compact evidence encoding only."""
import argparse,importlib.util,json,pathlib,sys
from safe_wire import install,report
from backend_loader import load_backend
backend_report=load_backend()
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];path=ROOT/'generic-reflow-v2-integrated-paper-1/code/page_pipeline.py';spec=importlib.util.spec_from_file_location('compact_integrated_native',path);original=importlib.util.module_from_spec(spec);sys.modules[spec.name]=original;spec.loader.exec_module(original);changes=install(ROOT)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir',required=True);a=p.parse_args();original.pe.RETURN_TRACE.clear();result=original.legacy.flow.run(a.pdf,a.out,a.model_dir,native_renderer=original.render_units);out=pathlib.Path(a.out);(out/'first-line-return-private.json').write_text(json.dumps(original.pe.RETURN_TRACE,indent=2));result.update(candidate='native-components',blind_acceptance=False);(out/'pipeline-result.json').write_text(json.dumps(result,indent=2));(out/'compact-wire-report.json').write_text(json.dumps(report(changes),indent=2));(out/'component-backend.json').write_text(json.dumps(backend_report|{'scipy_imported_in_native_process':any(n=='scipy' or n.startswith('scipy.') for n in sys.modules)},indent=2));print(json.dumps(result))
