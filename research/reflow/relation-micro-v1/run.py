"""Original synthetic relation probe, with oracle boxes; not a PDF reflow system."""
import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[n]='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import pathlib,json,hashlib,time,resource,math
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
import numpy as np
B=pathlib.Path(__file__).resolve().parent;CFG=json.loads((B/'FREEZE.json').read_text())
NAMES=['qx','qy','qw','qh','fx','fy','fw','fh','signed_dx','abs_dx','signed_dy','abs_dy','horizontal_gap','vertical_gap','log_distance','y_overlap','x_overlap','top_gap','bottom_gap','center_gap','left_gap','right_gap','q_inside_formula_x','q_inside_formula_y']
def page(family,seed):
 r=np.random.default_rng(seed);W,H=600.,820.;cols=2 if family.startswith('double') or family=='narrow-staggered' else 1
 margin=r.uniform(35,65);gutter=r.uniform(14,28) if family=='narrow-staggered' else r.uniform(28,48);cw=(W-2*margin-gutter*(cols-1))/cols;fs=[];qs=[]
 for col in range(cols):
  left=margin+col*(cw+gutter);right=left+cw
  for row in range(5):
   font=r.uniform(8,12);height=font*r.choice([1.,1.,2.,3.]);width=r.uniform(.32,.76)*cw
   if family=='wide-multiline':height=font*r.choice([3.,4.,5.]);width=r.uniform(.6,.85)*cw
   y=90+row*123+r.uniform(-12,12)+(20*col if family=='narrow-staggered' else 0);x=left+r.uniform(.03,.11)*cw;fid=int(r.integers(1,2**31));fs.append({'id':fid,'box':[x,y,x+width,y+height]})
   side='left' if family=='single-left' or (family=='double-alternate' and row%2) else 'right'
   if family=='wide-multiline':side='left' if row%2 else 'right'
   qw=r.uniform(9,17);qh=font*r.uniform(.85,1.05);qx=left-qw-3 if side=='left' else right-qw;align=r.choice([0,.5,1.],p=[.15,.7,.15])
   if family=='wide-multiline':align=1.
   if family=='narrow-staggered':align=0.
   qy=y+align*(height-qh)+r.uniform(-1.5,1.5);qs.append({'box':[qx,qy,qx+qw,qy+qh],'parent':fid})
 qs.extend([{'box':[294.,780.,306.,788.],'parent':None},{'box':[margin,28.,margin+12,36.],'parent':None}])
 if r.random()<.5:
  x=r.uniform(margin,W-margin-12);y=r.choice([160.,280.,410.,530.,660.])+r.uniform(-12,12);qs.append({'box':[x,y,x+12,y+9],'parent':None})
 r.shuffle(fs);r.shuffle(qs);return {'family':family,'seed':seed,'width':W,'height':H,'formulas':fs,'queries':qs}
def features(q,f,W,H):
 x0,y0,x1,y1=q;u0,v0,u1,v1=f;qh=y1-y0;dx=((x0+x1)-(u0+u1))/2/W;dy=((y0+y1)-(v0+v1))/2/H;gx=max(u0-x1,x0-u1,0)/qh;gy=max(v0-y1,y0-v1,0)/qh
 return [x0/W,y0/H,(x1-x0)/W,qh/H,u0/W,v0/H,(u1-u0)/W,(v1-v0)/H,dx,abs(dx),dy,abs(dy),math.log1p(gx),math.log1p(gy),math.log1p(math.hypot(gx,gy)),max(0,min(y1,v1)-max(y0,v0))/qh,max(0,min(x1,u1)-max(x0,u0))/(x1-x0),abs(y0-v0)/H,abs(y1-v1)/H,abs(dy),abs(x0-u0)/W,abs(x1-u1)/W,float(u0<=x0<=u1),float(v0<=y0<=v1)]
def matrix(pages):
 X=[];Y=[];groups=[]
 for pi,p in enumerate(pages):
  for qi,q in enumerate(p['queries']):
   start=len(X)
   for f in p['formulas']:X.append(features(q['box'],f['box'],p['width'],p['height']));Y.append(q['parent']==f['id'])
   groups.append({'page':pi,'query':qi,'family':p['family'],'start':start,'end':len(X),'true_index':next((j for j,f in enumerate(p['formulas']) if f['id']==q['parent']),None)})
 return np.array(X),np.array(Y,dtype=float),groups
def sigmoid(z):return 1/(1+np.exp(-np.clip(z,-30,30)))
def choices(scores,groups):
 result=[]
 for g in groups:
  a=scores[g['start']:g['end']];order=np.argsort(a)[::-1];top=int(order[0]);second=float(a[order[1]]) if len(a)>1 else 0.;result.append({**g,'chosen':top,'score':float(a[top]),'margin':float(a[top]-second)})
 return result
def evaluate(rows,t,m):
 accepted=[r for r in rows if r['score']>=t and r['margin']>=m];correct=sum(r['true_index'] is not None and r['chosen']==r['true_index'] for r in accepted);true=sum(r['true_index'] is not None for r in rows);wrong=len(accepted)-correct;pages=sorted(set(r['page'] for r in rows));exact=[]
 for p in pages:exact.append(all((r['score']>=t and r['margin']>=m and r['chosen']==r['true_index']) if r['true_index'] is not None else not(r['score']>=t and r['margin']>=m) for r in rows if r['page']==p))
 return {'queries':len(rows),'true_links':true,'accepted':len(accepted),'correct_accepted':correct,'wrong_accepted':wrong,'wrong_rate_among_accepted':wrong/len(accepted) if accepted else None,'true_link_coverage':correct/true,'rejection_rate':1-len(accepted)/len(rows),'exact_pages':sum(exact),'total_pages':len(pages),'candidate_recall':1.}
def calibrate(rows):
 best=None
 for t in [.5,.6,.7,.8,.9,.95,.98,.99]:
  for m in [0,.05,.1,.2,.3]:
   e=evaluate(rows,t,m)
   if e['accepted']>=100 and e['wrong_rate_among_accepted']<=.01:
    rank=(e['correct_accepted'],-e['wrong_accepted'],t,m)
    if best is None or rank>best[0]:best=(rank,t,m,e)
 return {'threshold':best[1],'margin':best[2],'metrics':best[3]} if best else {'threshold':2.,'margin':1.,'metrics':evaluate(rows,2,1),'reason':'No calibration setting met risk/support constraints'}
def run():
 start=time.perf_counter()
 if (B/'RUN-STARTED.json').exists():raise SystemExit('One frozen run already started')
 (B/'RUN-STARTED.json').write_text(json.dumps({'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'freeze_sha256':hashlib.sha256((B/'FREEZE.json').read_bytes()).hexdigest(),'epoch':time.time()}));data={}
 for part,s in CFG['partitions'].items():data[part]=[page(f,s['seed']+i*1000+j) for i,f in enumerate(s['families']) for j in range(s['pages_per_family'])]
 (B/'DATA.json').write_text(json.dumps(data,separators=(',',':')));X,Y,G=matrix(data['train']);mu=X.mean(0);sd=X.std(0);sd[sd<1e-8]=1.;A=np.column_stack([(X-mu)/sd,np.ones(len(X))]);theta=np.zeros(A.shape[1]);pos=Y.sum();weights=np.where(Y>0,len(Y)/(2*pos),len(Y)/(2*(len(Y)-pos)));ts=time.perf_counter()
 for _ in range(CFG['model']['iterations']):
  grad=A.T@((sigmoid(A@theta)-Y)*weights)/len(Y);grad[:-1]+=CFG['model']['l2']*theta[:-1];theta-=CFG['model']['learning_rate']*grad
 train_seconds=time.perf_counter()-ts;(B/'MODEL.json').write_text(json.dumps({'feature_names':NAMES,'weights':theta.tolist(),'mean':mu.tolist(),'std':sd.tolist(),'learned_parameters':len(theta)},indent=2));thresholds={};results={};timing={}
 for part in ['calibration','test_in_family','test_unseen_family']:
  ts=time.perf_counter();xx,yy,gg=matrix(data[part]);zz=np.column_stack([(xx-mu)/sd,np.ones(len(xx))]);sp=sigmoid(zz@theta);seconds=time.perf_counter()-ts;base=np.exp(-np.expm1(xx[:,14])/4.);result={}
  for name,scores in [('learned',sp),('nearest_rectangle',base)]:
   rows=choices(scores,gg)
   if part=='calibration':thresholds[name]=calibrate(rows)
   cal=thresholds[name];res=evaluate(rows,cal['threshold'],cal['margin']);res['forced_owner_accuracy_on_true_links']=sum(r['chosen']==r['true_index'] for r in rows if r['true_index'] is not None)/sum(r['true_index'] is not None for r in rows);res['per_family']={f:evaluate([r for r in rows if r['family']==f],cal['threshold'],cal['margin']) for f in CFG['partitions'][part]['families']};result[name]=res;(B/(part+'-'+name+'-predictions.json')).write_text(json.dumps(rows,separators=(',',':')))
  results[part]=result;timing[part]={'feature_and_model_seconds':seconds,'mean_seconds_per_page':seconds/len(data[part])}
 out={'train_pages':len(data['train']),'train_pairs':len(Y),'train_positive_pairs':int(pos),'train_seconds':train_seconds,'thresholds':thresholds,'results':results,'timing':timing,'learned_parameters':len(theta),'float32_runtime_bytes':4*(len(theta)+len(mu)+len(sd)),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'wall_seconds':time.perf_counter()-start,'data_sha256':hashlib.sha256((B/'DATA.json').read_bytes()).hexdigest(),'limitations':CFG['scope']};a=results['test_unseen_family']['learned'];b=results['test_unseen_family']['nearest_rectangle'];out['predefined_success_gate_passed']=a['true_link_coverage']-b['true_link_coverage']>=.05 and a['wrong_rate_among_accepted'] is not None and a['wrong_rate_among_accepted']<=.01 and a['true_link_coverage']>=.5 and timing['test_unseen_family']['mean_seconds_per_page']<.05 and out['float32_runtime_bytes']<10240;(B/'RESULT.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['results','thresholds']},indent=2))
if __name__=='__main__':run()
