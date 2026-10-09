"""Preserve an explicitly failed request as local source-PDF recovery data."""
import argparse,base64,json,pathlib
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('execution');p.add_argument('out');p.add_argument('--reason',required=True);a=p.parse_args()
pdf=pathlib.Path(a.pdf);execution=json.loads(pathlib.Path(a.execution).read_text())
if execution.get('execution_pass') is not False:raise ValueError('Only an explicitly failed execution may become a failure bundle')
if not 0<len(a.reason)<=2000:raise ValueError('Reason length')
data=pdf.read_bytes()
if not data.startswith(b'%PDF-') or len(data)>10*1024*1024:raise ValueError('Expected bounded source PDF')
bundle=dict(schema='readest-reflow-failure-v1',reason=a.reason,original_filename=pdf.name,source_pdf='data:application/pdf;base64,'+base64.b64encode(data).decode())
text=json.dumps(bundle,ensure_ascii=False)
if len(text.encode())>16*1024*1024:raise ValueError('Bundle byte limit')
out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text)
print(json.dumps(dict(bytes=out.stat().st_size,source_fallback=True,reflow_produced=False,browser_verified=False)))
