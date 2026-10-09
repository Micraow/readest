"""Config-driven, limited direct Paddle Inference adapter; no new model.

Compatibility reference: PaddleX 3.7.2 (Apache-2.0), common/vision processors,
object_detection processors and paddle_static runner. This original adapter
supports only the tested simple detector recipe and fails on other recipes.
"""
from dataclasses import dataclass,asdict
import argparse,hashlib,json,os,pathlib,socket,time
@dataclass(frozen=True)
class DirectPriorConfig:
    render_scale:float=4.
    threads:int=1
    optimization_level:int=3
    large_image_role:str='image'
    landscape_image_area_limit:float=.82
    portrait_image_area_limit:float=.93
    def json(self):return asdict(self)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def setup(out,cfg):
    cache=out/'runtime-cache';cache.mkdir(exist_ok=True)
    for k,v in {'PADDLE_PDX_CACHE_HOME':str(cache),'MPLCONFIGDIR':str(cache/'matplotlib'),'XDG_CACHE_HOME':str(cache),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':str(cfg.threads),'OMP_NUM_THREADS':str(cfg.threads),'MKL_NUM_THREADS':str(cfg.threads),'OPENBLAS_NUM_THREADS':str(cfg.threads)}.items():os.environ[k]=v
    def deny(*a,**k):raise RuntimeError('Networking is disabled in local layout inference')
    socket.socket.connect=deny;socket.create_connection=deny

def preprocess(rgb,recipe):
    import cv2,numpy as np
    if [x['type'] for x in recipe]!=['Resize','NormalizeImage','Permute']:raise ValueError('unsupported preprocessing recipe')
    resize,norm,_=recipe
    if resize.get('keep_ratio',False) or resize.get('interp',2)!=2 or norm.get('norm_type') not in (None,'none','mean_std'):raise ValueError('unsupported resize/normalization mode')
    height,width=resize['target_size'];oldheight,oldwidth=rgb.shape[:2];image=cv2.resize(rgb,(width,height),interpolation=cv2.INTER_CUBIC).astype(np.float32);factor=1/255. if norm.get('is_scale',True) else 1.
    means=norm.get('mean',[.485,.456,.406]);stds=norm.get('std',[.229,.224,.225])
    if len(means)!=3 or len(stds)!=3 or any(s<=0 for s in stds):raise ValueError('invalid channel normalization')
    for i in range(3):image[:,:,i]*=factor/stds[i];image[:,:,i]+=-means[i]/stds[i]
    return {'image':np.ascontiguousarray(image.transpose(2,0,1)[None]),'scale_factor':np.asarray([[height/oldheight,width/oldwidth]],dtype=np.float32)}

def postprocess(raw,model,size,cfg=DirectPriorConfig()):
    import numpy as np
    if raw.ndim!=2 or raw.shape[1]!=6:raise ValueError('unsupported detector output shape')
    if any(model.get(k) for k in ['layout_nms','layout_unclip_ratio','layout_merge_bboxes_mode']):raise ValueError('unsupported optional postprocessor')
    threshold=model.get('draw_threshold',.5)
    if not isinstance(threshold,float):raise ValueError('unsupported category-specific thresholds')
    labels=model['label_list'];width,height=size;boxes=raw[(raw[:,1]>threshold)&(raw[:,0]>-1)];trace={'threshold':threshold,'post_threshold_count':len(boxes),'upstream_compatibility_rules':cfg.json(),'large_image_filtered':0}
    if len(boxes)>1 and cfg.large_image_role in labels:
        role=labels.index(cfg.large_image_role);limit=cfg.landscape_image_area_limit if width>height else cfg.portrait_image_area_limit;keep=[]
        for box in boxes:
            x1,y1,x2,y2=box[2:];area=(min(width,x2)-max(0,x1))*(min(height,y2)-max(0,y1));keep.append(box[0]!=role or area<=limit*width*height)
        if any(keep):trace['large_image_filtered']=int(len(boxes)-sum(keep));boxes=boxes[keep]
    result=[]
    for box in boxes:
        cid=int(box[0]);x1,y1,x2,y2=box[2:];x1=max(0,x1);y1=max(0,y1);x2=min(width,x2);y2=min(height,y2)
        if x2<=x1 or y2<=y1:continue
        if not 0<=cid<len(labels):raise ValueError('class ID outside configured label vocabulary')
        result.append({'cls_id':cid,'label':labels[cid],'score':float(box[1]),'coordinate':[float(max(0,x1)),float(max(0,y1)),float(min(width,x2)),float(min(height,y2))]})
    return result,trace

def predict(pdf,out,model_dir,cfg=DirectPriorConfig()):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);model_dir=pathlib.Path(model_dir);start=time.perf_counter();cpu=time.process_time();setup(out,cfg);stages=[]
    def mark(name,t,c):stages.append({'name':name,'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c})
    t=time.perf_counter();c=time.process_time();import cv2,numpy as np,yaml,pypdfium2 as pdfium;from paddle import inference;mark('imports',t,c)
    model=yaml.safe_load((model_dir/'inference.yml').read_text());t=time.perf_counter();c=time.process_time();config=inference.Config(str(model_dir/'inference.json'),str(model_dir/'inference.pdiparams'));config.disable_gpu();config.disable_mkldnn();config.set_cpu_math_library_num_threads(cfg.threads);config.enable_new_ir(True);config.enable_new_executor();config.set_optimization_level(cfg.optimization_level);config.enable_memory_optim();config.disable_glog_info();predictor=inference.create_predictor(config);mark('create_predictor',t,c)
    t=time.perf_counter();c=time.process_time();doc=pdfium.PdfDocument(pdf);page=doc[0];bm=page.render(scale=cfg.render_scale,draw_annots=False,may_draw_forms=False);image=bm.to_pil().convert('RGB');size=image.size;image.save(out/'native-model-input.png');rgb=np.asarray(image);bm.close();page.close();doc.close();mark('page_render_and_png',t,c)
    t=time.perf_counter();c=time.process_time();inputs=preprocess(rgb,model['Preprocess']);names=predictor.get_input_names()
    if set(names)!=set(inputs):raise RuntimeError('unsupported predictor input names')
    for name,array in inputs.items():handle=predictor.get_input_handle(name);handle.reshape(array.shape);handle.copy_from_cpu(array)
    predictor.run();outputs={name:predictor.get_output_handle(name).copy_to_cpu() for name in predictor.get_output_names()};raw=[a for a in outputs.values() if a.ndim==2 and a.shape[1]==6]
    if len(raw)!=1:raise RuntimeError('ambiguous detector raw output')
    boxes,trace=postprocess(raw[0],model,size,cfg);mark('preprocess_infer_postprocess',t,c);result={'res':{'input_path':str(out/'native-model-input.png'),'page_index':None,'boxes':boxes}};(out/'prediction-private.json').write_text(json.dumps(result));(out/'postprocess-trace-private.json').write_text(json.dumps(trace,indent=2));np.savez(out/'inference-tensors-private.npz',**{('input_'+n):a for n,a in inputs.items()},**{('output_'+n):a for n,a in outputs.items()})
    costs={'model':'PP-DocLayout-S','mode':'offline direct CPU; existing weak prior only','config':cfg.json(),'native_model_input_size':list(size),'native_input_png_sha256':sha(out/'native-model-input.png'),'model_file_hashes':{p.name:sha(p) for p in model_dir.iterdir() if p.is_file()},'input_names':names,'output_shapes':{n:list(a.shape) for n,a in outputs.items()},'stages':stages,'whole_process_body_wall_seconds':time.perf_counter()-start,'whole_process_body_cpu_seconds':time.process_time()-cpu,'prediction_count':len(boxes),'equivalence_verified':False,'whole_cold_page_cost':False};(out/'model-costs.json').write_text(json.dumps(costs,indent=2));return costs
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('model_dir');a=p.parse_args();print(json.dumps(predict(a.pdf,a.out,a.model_dir)))
