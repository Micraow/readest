"""One frozen real-native-line softmax baseline; no output-driven model search."""
import pathlib,json,time,os,resource,hashlib,collections
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from features import B,page_features,FEATURE_NAMES
if (B/'MODEL-RUN-STARTED.json').exists():raise SystemExit('Frozen fit already started; no rerun')
(B/'MODEL-RUN-STARTED.json').write_text(json.dumps({'epoch':time.time(),'code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}))
start=time.monotonic();pages=[]
for row in json.loads((B/'SELECTION-FREEZE.json').read_text())['pages']:
 t=time.monotonic();X,y,g,meta=page_features(row);pages.append({'source':row,'X':X,'y':y,'baseline':g,'meta':meta,'seconds':time.monotonic()-t});print(json.dumps({'features_page':len(pages),'lines':len(y),'unknown':int((y<0).sum()),'seconds':time.monotonic()-t}),flush=True)
 if time.monotonic()-t>60:raise RuntimeError('Page feature budget exceeded')
train=[p for p in pages if p['source']['split']=='train'];X=np.concatenate([p['X'] for p in train]);y=np.concatenate([p['y'] for p in train]);known=y>=0;X=X[known];y=y[known];mu=X.mean(0);sd=X.std(0);sd[sd<1e-8]=1.;T=np.column_stack([(X-mu)/sd,np.ones(len(X))]);dim=T.shape[1];classes=4;counts=np.bincount(y,minlength=4);assert (counts>0).all();weights=1/counts[y];weights*=len(y)/weights.sum()
def loss(flat):
 W=flat.reshape(dim,classes);scores=T@W;logp=scores-logsumexp(scores,axis=1)[:,None];value=-(weights*logp[np.arange(len(y)),y]).mean()+.005*np.square(W[:-1]).sum();prob=np.exp(logp);prob[np.arange(len(y)),y]-=1;grad=T.T@(prob*weights[:,None])/len(y);grad[:-1]+=.01*W[:-1];return value,grad.ravel()
fit_start=time.monotonic();fit=minimize(loss,np.zeros(dim*classes),jac=True,method='L-BFGS-B',options={'maxiter':150,'ftol':1e-9});W=fit.x.reshape(dim,classes);fit_seconds=time.monotonic()-fit_start
for p in pages:
 t=time.monotonic();scores=np.column_stack([(p['X']-mu)/sd,np.ones(len(p['X']))])@W;p['prob']=np.exp(scores-logsumexp(scores,axis=1)[:,None]);p['pred']=p['prob'].argmax(1);p['confidence']=p['prob'].max(1);p['inference_seconds']=time.monotonic()-t
cal=[p for p in pages if p['source']['split']=='val'];candidates=[]
for threshold in [i/100 for i in range(50,100)]:
 accepted=wrong=0
 for p in cal:
  mask=p['confidence']>=threshold;accepted+=int(mask.sum());wrong+=int((mask&(p['pred']!=p['y'])).sum())
 if accepted>=20 and wrong==0:candidates.append((accepted,threshold))
threshold=sorted(candidates,key=lambda p:(-p[0],p[1]))[0][1] if candidates else 1.1
model={'feature_names':FEATURE_NAMES,'roles':['body','formula','auxiliary','other'],'mean':mu.tolist(),'std':sd.tolist(),'weights':W.tolist(),'threshold':threshold,'parameters':int(W.size),'l2':.01,'fit_success':bool(fit.success),'fit_message':str(fit.message),'iterations':int(fit.nit),'fit_seconds':fit_seconds,'train_lines_with_known_roles':len(y),'training_role_counts':counts.tolist(),'calibration':'zero observed wrong/unverifiable accepted and>=20 lines; otherwise reject all'};(B/'MODEL.json').write_text(json.dumps(model,indent=2))
def wilson(k,n):
 if n==0:return None
 z=1.959963984540054;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return [float(max(0,mid-half)),float(min(1,mid+half))]
def score(p,pred):
 target=p['y'];accepted=pred>=0;known=target>=0;bad=accepted&(pred!=target);correct=accepted&(pred==target);n=len(target);body=correctbody=falsemath=falseaux=falseother=unverifiable=0
 for k,row in enumerate(p['meta']['rows']):
  rs={int(i):v for i,v in row['glyph_role_counts'].items()};body+=rs.get(0,0)
  if pred[k]==0:correctbody+=rs.get(0,0);falsemath+=rs.get(1,0);falseaux+=rs.get(2,0);falseother+=rs.get(3,0);unverifiable+=rs.get(-1,0)
 confusion=np.zeros((5,5),int)
 for t,v in zip(target,pred):confusion[int(t) if t>=0 else 4,int(v) if v>=0 else 4]+=1
 return {'native_lines':n,'known_role_lines':int(known.sum()),'unknown_or_mixed_lines':int((~known).sum()),'accepted_lines':int(accepted.sum()),'correct_accepted_lines':int(correct.sum()),'wrong_or_unverifiable_accepted_lines':int(bad.sum()),'error95_wilson_independent_line_assumption_only':wilson(int(bad.sum()),int(accepted.sum())),'all_gold_body_glyphs':body,'correctly_proposed_body_glyphs_not_reflow':correctbody,'formula_glyphs_falsely_body':falsemath,'auxiliary_glyphs_falsely_body':falseaux,'other_role_glyphs_falsely_body':falseother,'unknown_glyphs_proposed_body':unverifiable,'confusion_true_rows_pred_columns_body_formula_aux_other_unknown':confusion.tolist()}
results=[]
for p in pages:
 prediction=np.where(p['confidence']>=threshold,p['pred'],-1);scores={'geometry':score(p,p['baseline']),'learned_all':score(p,p['pred']),'learned_calibrated':score(p,prediction)};objects=p['meta']['objects'];results.append({'split':p['source']['split'],'collection':p['source']['collection'],'page_hash':p['source']['file_name'][:-4],'doc_name':p['source']['doc_name'],'feature_seconds':p['seconds'],'classifier_inference_seconds':p['inference_seconds'],'all_annotated_objects':len(objects),'annotated_text_formula_aux_objects':sum(o['role'] in [0,1,2] for o in objects),'annotated_text_formula_aux_objects_without_native_glyphs':sum(o['role'] in [0,1,2] and not o['native_glyph_support'] for o in objects),'all_native_glyphs':p['meta']['all_native_glyphs'],'unknown_role_glyphs':p['meta']['unknown_role_glyphs'],'scores':scores})
 # Local audit details retain candidate IDs and confidence; no paper text.
 np.savez_compressed(B/'data'/p['source']['file_name'][:-4]/'role-predictions.npz',features=p['X'],target=p['y'],baseline=p['baseline'],probabilities=p['prob'])
 (B/'data'/p['source']['file_name'][:-4]/'line-reference.json').write_text(json.dumps(p['meta'],indent=2))
summary={}
for split in ['train','val','test']:
 rows=[r for r in results if r['split']==split];summary[split]={'documents':len(rows),'scores':{}}
 for method in ['geometry','learned_all','learned_calibrated']:
  keys=[k for k,v in rows[0]['scores'][method].items() if isinstance(v,int)];s={k:sum(r['scores'][method][k] for r in rows) for k in keys};s['error95_wilson_independent_line_assumption_only']=wilson(s['wrong_or_unverifiable_accepted_lines'],s['accepted_lines']);summary[split]['scores'][method]=s
report={'status':'one frozen role-only fit/evaluation complete','model':{k:v for k,v in model.items() if k not in ['weights','mean','std']},'summary':summary,'pages':results,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':['Line-role assignment is not source-pixel fidelity, reading order, formula-number ownership or actual text reflow.','Human layout labels are operational targets; >=90% glyph agreement does not certify semantic atomicity.','All missing/mixed lines and missing annotated objects are retained in denominators.','Wilson intervals assume independent lines and are descriptive only; lines cluster by document. Twelve held-out source-style documents do not certify a general risk bound.','Official detector upstream training overlap unknown.','No quality-driven parameter correction after locked test.']};(B/'RESULT.json').write_text(json.dumps(report,indent=2));print(json.dumps({'model':report['model'],'summary':summary,'total_seconds':report['total_seconds'],'peak_rss_kib':report['peak_rss_kib']},indent=2))
