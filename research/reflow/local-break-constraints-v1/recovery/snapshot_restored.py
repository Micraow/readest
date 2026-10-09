"""Rehydrate exact generated HTML for the unchanged local CSS QA renderer."""
import pathlib,json,re,base64,subprocess,sys,tempfile,time,os
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';key,family,arm=sys.argv[1:4];width,font=map(int,sys.argv[4:6]);root=B/'evidence'/(key.split('-')[0]+'-assets');p=B/'output'/(key+'-'+family)/(arm+f'-{width}-{font}.html');text=p.read_text();text=re.sub(r'asset://([a-f0-9]+)\.png',lambda m:'data:image/png;base64,'+base64.b64encode((root/(m.group(1)+'.png')).read_bytes()).decode(),text);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
with tempfile.NamedTemporaryFile(mode='w',suffix='.html',dir=W/'readest-recovery') as f:
 f.write(text);f.flush();subprocess.run([str(W/'layout-evaluation/venv/bin/python'),str(B/'code/snapshots.py'),f.name,str(B/'evidence'/(key+'-'+('E' if family=='E' else arm))),'--width',str(width),'--font',str(font)],check=True,timeout=60)
