"""Run only the authored control in a permitted browser environment.

No private source path or network URL is accepted. Do not disable a rejected
browser sandbox or move private PDFs into public CI to run these checks.
"""
import json,pathlib,subprocess,sys
from browser_audit import audit
code=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(code/'create_control.py'),str(out/'original-control.pdf')],check=True)
subprocess.run([sys.executable,str(code/'prototype.py'),str(out/'original-control.pdf'),str(out/'rendered')],check=True)
a=json.loads((out/'rendered/audit.json').read_text());assert not a['hard_failures'],a['hard_failures']
audit(out/'rendered',widths=(320,390,430))
b=json.loads((out/'rendered/browser-private.json').read_text())
assert len(b['settings'])==6
for r in b['settings']:
 assert r['sequence_matches_plan'] and r['ownership_matches_plan']
 assert r['scrollWidth']<=r['clientWidth']
 assert float(r['fontSize'].removesuffix('px'))==r['size']
 assert len(r['backgrounds'])==1
 assert 'shaded panel' in r['selected_text'] and 'Table borders' in r['selected_text']
for width in (320,390,430):
 small,large=[r for r in b['settings'] if r['width']==width]
 assert large['backgrounds'][0]['height']>small['backgrounds'][0]['height']
assert b['local_zoom']['class_toggled']
assert b['local_zoom']['after_width']>b['local_zoom']['before_width']
assert b['local_zoom']['scroll_width']>b['local_zoom']['viewport_width']
print('Original control: actual Chromium sequence, selection, resizing, width and local-zoom checks passed. Not real-PDF semantic acceptance.')
