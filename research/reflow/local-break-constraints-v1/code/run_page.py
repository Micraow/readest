import argparse,pathlib,json,time,sys,resource,os
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
from atoms import build,materialize
from reader import render
import fitz
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('detector');p.add_argument('out');p.add_argument('--key',default='page');a=p.parse_args();B=pathlib.Path(a.out);B.mkdir(parents=True,exist_ok=True);started=time.monotonic();state=build(fitz.open(a.pdf)[0],json.loads(pathlib.Path(a.detector).read_text())['res']['boxes']);allmetrics={}
for arm in ['A','B']:
 atoms,metrics=materialize(state,arm);page={'key':a.key,'state':state,'atoms':atoms};html,layout=render([page]);(B/(arm+'.html')).write_text(html)
 for width in [320,390,430]:
  for font in [20,28]:
   variant,details=render([page],width,font,interactive=False);(B/f'{arm}-{width}-{font}.html').write_text(variant)
 page['atlas'].save(B/(arm+'-atlas.png'));publicatoms=[{k:v for k,v in node.items() if k!='rgba'} for node in atoms];(B/(arm+'-atoms.json')).write_text(json.dumps({'metrics':metrics,'atoms':publicatoms,'layout':layout,'columns':state['columns']},indent=2));allmetrics[arm]=metrics
allmetrics.update(seconds=time.monotonic()-started,peak_self_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Source ownership and renderer preparation, not semantic acceptance');(B/'metrics.json').write_text(json.dumps(allmetrics,indent=2));print(json.dumps(allmetrics,indent=2))
