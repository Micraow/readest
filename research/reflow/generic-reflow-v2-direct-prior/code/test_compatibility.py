"""Compare reference operators on authored arrays, not private PDF labels."""
import json,pathlib,sys,tempfile
from direct_prior import preprocess,postprocess,setup,DirectPriorConfig
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);setup(out,DirectPriorConfig())
import cv2,numpy as np
from paddlex.inference.models.object_detection.processors import DetPostProcess,Resize,Normalize,ToCHWImage,ToBatch
recipe=[{'type':'Resize','target_size':[480,480],'keep_ratio':False,'interp':2},{'type':'NormalizeImage','mean':[.485,.456,.406],'std':[.229,.224,.225],'is_scale':True},{'type':'Permute'}];pre=[]
for h,w in [(1,1),(17,31),(480,480),(137,83)]:
 rng=np.random.default_rng(h+w);rgb=rng.integers(0,256,(h,w,3),dtype=np.uint8);datas=[{'img':rgb,'ori_img_size':[w,h]}]
 for op in [Resize(target_size=[480,480],keep_ratio=False,interp='BICUBIC'),Normalize(scale=1/255.,mean=[.485,.456,.406],std=[.229,.224,.225]),ToCHWImage()]:datas=op(datas)
 reference=ToBatch(('img','scale_factors'))(datas);actual=preprocess(rgb,recipe);same=all(np.array_equal(a,b) for a,b in zip(reference,[actual['image'],actual['scale_factor']]));pre.append({'input_size':[w,h],'tensor_exact':same});assert same
labels=['text','image','formula'];model={'draw_threshold':.5,'label_list':labels};post=[]
for shape in [(200,300),(300,200)]:
 rng=np.random.default_rng(sum(shape));raw=np.concatenate([np.column_stack([rng.integers(0,3,200),rng.random(200),rng.uniform(-50,150,(200,2)),rng.uniform(100,350,(200,2))]),np.asarray([[1,.9,0,0,*shape],[0,.5,0,0,10,10],[0,.5000001,-2,-3,20,30],[2,.99,50,50,40,40],[1,.9,0,0,300,200]])]).astype(np.float32);ref=DetPostProcess(labels).apply(raw.copy(),shape,.5,None,None,None);actual,trace=postprocess(raw.copy(),model,shape);same=len(ref)==len(actual) and all(a['cls_id']==b['cls_id'] and a['label']==b['label'] and float(a['score'])==b['score'] and [float(x) for x in a['coordinate']]==b['coordinate'] for a,b in zip(ref,actual));post.append({'input_size':shape,'boxes_exact':same,'output_boxes':len(actual)});assert same
ref=DetPostProcess(labels).apply(np.empty((0,6),np.float32),(200,300),.5,None,None,None);actual,_=postprocess(np.empty((0,6),np.float32),model,(200,300));assert ref==actual==[]
refusals=0
for m in [model|{'layout_nms':True},model|{'draw_threshold':{0:.5}}]:
 try:postprocess(raw,m,(200,300));raise AssertionError('unsupported mode accepted')
 except ValueError:refusals+=1
result={'preprocessing':pre,'postprocessing':post,'empty_output_equivalent':True,'unsupported_modes_refused':refusals,'all_passed':True};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
