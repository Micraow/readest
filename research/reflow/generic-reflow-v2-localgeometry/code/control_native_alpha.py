"""Original small native PDF; full-grid alpha must pass exact native replay."""
import argparse,json,pathlib,sys
from reportlab.pdfgen import canvas
from global_alpha import extract
from masked_native_replay import run as replay
p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);pdf=out/'authored-control.pdf';c=canvas.Canvas(str(pdf),pagesize=(300,240),pageCompression=0)
c.setFont('Helvetica',13);c.drawString(23.17,210.39,'Native curve ( control )');c.setFont('Helvetica',7);c.drawString(24.23,184.87,'small separate metadata row');c.setFont('Helvetica',12);c.drawString(24.73,150.13,'X');c.setFont('Helvetica',6);c.drawString(34.08,155.33,'abcd');c.saveState();c.translate(13.47,24.89);c.rotate(90);c.setFont('Helvetica',8);c.drawString(0,0,'rotated original run');c.restoreState();c.save()
r=extract(pdf,out/'native');rr=replay(pdf,out/'native');result={'ownership_unique':r['all_object_pixels_uniquely_assigned'],'global_native_replay_exact':rr['ownership_and_replay_pass'],'changed_pixels':rr['changed_pixels'],'native_alpha_renders':r['native_renders'],'original_fixture_only':True};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert result['ownership_unique'] and result['global_native_replay_exact']
