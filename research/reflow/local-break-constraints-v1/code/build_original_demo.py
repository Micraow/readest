import pathlib,json,sys,time
import fitz
from atoms import build,materialize
from reader import render
B=pathlib.Path(__file__).resolve().parents[1];pages=[];metrics=[]
for i,(name,det) in enumerate([('geometry','geometry-raster-detector'),('cjk','cjk-detector'),('ligature','ligature-detector')],1):
 state=build(fitz.open(B/'controls'/(name+'.pdf'))[0],json.loads((B/'controls'/(det+'.json')).read_text())['res']['boxes']);atoms,measurement=materialize(state,'A');pages.append({'key':'Original-'+name,'page_label':i,'state':state,'atoms':atoms});metrics.append(measurement)
html,layout=render(pages);(B/'output/original-demo.html').write_text(html);(B/'output/original-demo-metrics.json').write_text(json.dumps({'scope':'Original development controls, not held-out paper quality','pages':metrics,'source_atoms':sum(len(p['atoms']) for p in pages),'html_unit_links':html.count('data-unit='),'displayed_source_ink':sum(x['source_ink'] for x in layout if x['status'].startswith('shown')),'source_ink':sum(p['source_ink'] for p in metrics)},indent=2));print((B/'output/original-demo-metrics.json').read_text())
