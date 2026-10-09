"""Narrow 2-D 4/8-connected component adapter, using installed OpenCV SAUF."""
from dataclasses import dataclass,asdict
import cv2,numpy as np
@dataclass(frozen=True)
class ComponentBackendConfig:
    maximum_pixels:int=32_000_000
    cpu_threads:int=1
    algorithm:str='SAUF'
    output_dtype:str='int32'
    def json(self):return asdict(self)
class Labels(np.ndarray):
    """Component bounds travel with this array, not in a mutable global cache."""
    def __array_finalize__(self,parent):
        self.component_slices=getattr(parent,'component_slices',None);self.component_identity=getattr(parent,'component_identity',None)

def label(input,structure=None,cfg=ComponentBackendConfig()):
    a=np.asarray(input)
    if a.ndim!=2 or a.size>cfg.maximum_pixels:raise ValueError('only bounded 2-D masks are supported')
    cross=np.asarray([[0,1,0],[1,1,1],[0,1,0]],dtype=bool);s=cross if structure is None else np.asarray(structure,dtype=bool)
    if s.shape!=(3,3):raise ValueError('unsupported component structure')
    if np.array_equal(s,np.ones((3,3),bool)):connectivity=8
    elif np.array_equal(s,cross):connectivity=4
    else:raise ValueError('only standard 4/8 connectivity is supported')
    cv2.setNumThreads(cfg.cpu_threads)
    if not a.size:
        result=np.zeros(a.shape,np.int32).view(Labels);result.component_slices=[];result.component_identity=(result.__array_interface__['data'][0],result.shape,result.strides);result.setflags(write=False);return result,0
    count,array,stats,_=cv2.connectedComponentsWithStatsWithAlgorithm(np.ascontiguousarray(a!=0,dtype=np.uint8),connectivity,cv2.CV_32S,cv2.CCL_SAUF)
    array.setflags(write=False);result=array.view(Labels);result.component_identity=(result.__array_interface__['data'][0],result.shape,result.strides);result.component_slices=[(slice(int(y),int(y+h)),slice(int(x),int(x+w))) for x,y,w,h,_ in stats[1:]];return result,int(count)-1

def find_objects(array,max_label=0):
    if not isinstance(array,Labels) or array.component_slices is None or array.component_identity!=(array.__array_interface__['data'][0],array.shape,array.strides):raise ValueError('only the unchanged paired label result is supported')
    if not array.size and not max_label:raise ValueError('zero-size labels have no maximum')
    if max_label and max_label<len(array.component_slices):return array.component_slices[:max_label]
    return list(array.component_slices)+[None]*max(0,max_label-len(array.component_slices))
