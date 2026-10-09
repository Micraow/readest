"""Private visual QA from already measured native plan/capture/target assets."""
import argparse,json,pathlib,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('plan');p.add_argument('capture_reader');p.add_argument('local_images');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();plan=pathlib.Path(a.plan).resolve()/'fractions';previous=pathlib.Path(a.capture_reader).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False);P=root/'readest-research-checkpoint/research/reflow/generic-reflow-v2-paragraph-vector/code';runtime=root/'generic-reflow-v2-glyph-resources-local/runtime';capture=previous/'capture';bridge=previous/'bridge-private.json';rows=[]
def stage(name,cmd):
 start=time.perf_counter()
 with (out/(name+'.stdout')).open('w') as so,(out/(name+'.stderr')).open('w') as se:r=subprocess.run([str(x) for x in cmd],stdout=so,stderr=se)
 rows.append({'name':name,'wall_seconds':time.perf_counter()-start,'exit_code':r.returncode});(out/'stages.json').write_text(json.dumps(rows,indent=2))
 if r.returncode:raise RuntimeError(name)
py=sys.executable
stage('prepare',[py,P/'prepare_reader.py',plan,capture,bridge,out/'prepared'])
stage('target_assets',[py,P/'update_local_images.py',out/'prepared/reader-data-private.json',a.local_images,out/'updated/reader-data-private.json'])
stage('components',[py,P/'refine_vector_components.py',out/'updated/reader-data-private.json',plan/'plan-private.json',plan/'tree-reader-assets-private.json',bridge,out/'components/reader-data-private.json'])
data=out/'final/reader-data-private.json';stage('flow',[py,P/'flow_refinements.py',out/'components/reader-data-private.json',plan/'plan-private.json',data,'--events',capture/'events-private.json','--bridge',bridge])
for font,dpr in [(28,2),(20,1)]:stage('render_'+str(font),['node',P/'render_reader.mjs',runtime,data,out/('reader-'+str(font)),font,dpr])
stage('geometry',['node',P/'audit_geometry.mjs',runtime,data,out/'geometry-audit-private.json'])
stage('preview',[py,P/'make_preview.py',data,out/'research-preview-private.html'])
(out/'warm-qa-result.json').write_text(json.dumps({'complete':True,'native_plan_and_glyph_resources_reused':True,'target_assets_reused':True,'blind':False,'cold_whole_page_cost':False,'visual_review_pass':False},indent=2))
