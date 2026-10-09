"""Sampling policy and byte-bounded asset cache, independent of document identity."""
import collections,hashlib,json,math,pathlib
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class TargetConfig:
    raster_grids:tuple[float,...]=(2.,3.,4.,6.,8.)
    maximum_reference_pixels:int=32_000_000
    maximum_object_crop_pixels:int=4_000_000
    maximum_unit_mask_pixels:int=8_000_000
    maximum_requested_units:int=8
    maximum_enlargement:float=4.
    maximum_cache_encoded_bytes:int=8*1024*1024
    maximum_cache_decoded_bytes:int=32*1024*1024
    maximum_cache_entries:int=64
    def json(self):return asdict(self)

def choose_grid(font_css_px,dpr,body_pdf_points,enlargement=1.,cfg=TargetConfig()):
    values=[font_css_px,dpr,body_pdf_points,enlargement]
    if any(not math.isfinite(x) or x<=0 for x in values):raise ValueError('positive finite geometry required')
    if enlargement>cfg.maximum_enlargement:raise ValueError('local enlargement exceeds configured limit')
    required=font_css_px*dpr*enlargement/body_pdf_points
    grid=next((s for s in cfg.raster_grids if s>=required),None)
    if grid is None:raise ValueError('requested density exceeds native-grid budget')
    return dict(grid=grid,required_samples_per_pdf_point=required,samples_per_device_pixel=grid/required,reason='smallest configured native grid satisfying target CSS size, DPR and enlargement',cfg=cfg.json())

def cache_key(source_sha,plan_sha,unit_ids,grid,renderer_version,backdrop_policy):
    fields=dict(source_sha=source_sha,plan_sha=plan_sha,units=sorted(unit_ids),grid=grid,renderer=renderer_version,backdrop=backdrop_policy)
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class AssetCache:
    """In-memory bytes only; caller owns persisted evidence, not an unbounded cache."""
    def __init__(self,cfg=TargetConfig()):self.cfg=cfg;self.entries=collections.OrderedDict();self.encoded_bytes=0;self.decoded_bytes=0;self.trace=[]
    def get(self,key):
        if key not in self.entries:self.trace.append(dict(action='miss',key=key));return None
        self.entries.move_to_end(key);self.trace.append(dict(action='hit',key=key));return self.entries[key][0]
    def put(self,key,payload:bytes,decoded_bytes:int):
        if decoded_bytes<0:raise ValueError('decoded byte count must be nonnegative')
        n=len(payload)
        if n>self.cfg.maximum_cache_encoded_bytes or decoded_bytes>self.cfg.maximum_cache_decoded_bytes:self.trace.append(dict(action='not_cached_oversize',key=key,encoded_bytes=n,decoded_bytes=decoded_bytes));return False
        if key in self.entries:
            p,d=self.entries.pop(key);self.encoded_bytes-=len(p);self.decoded_bytes-=d
        while self.entries and (self.encoded_bytes+n>self.cfg.maximum_cache_encoded_bytes or self.decoded_bytes+decoded_bytes>self.cfg.maximum_cache_decoded_bytes or len(self.entries)>=self.cfg.maximum_cache_entries):
            k,(p,d)=self.entries.popitem(last=False);self.encoded_bytes-=len(p);self.decoded_bytes-=d;self.trace.append(dict(action='eviction',key=k))
        self.entries[key]=(payload,decoded_bytes);self.encoded_bytes+=n;self.decoded_bytes+=decoded_bytes;self.trace.append(dict(action='store',key=key,encoded_bytes=n,decoded_bytes=decoded_bytes));return True


def renderer_identity(pdfium_version):
    here=pathlib.Path(__file__).resolve().parent;root=here.parents[1]
    sources=[here/name for name in ['render_request.py','native_target_layer.py','target_grid.py']]
    sources += [root/'generic-reflow-v2-localcanvas/code/render_native_localcanvas.py',root/'generic-reflow-v2-inkownership/code/ink_ownership.py',root/'generic-reflow-v2-inkownership/code/ink_config.py']
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sources)).hexdigest()
    return 'PDFium:'+pdfium_version+';native-asset-adapter:'+digest

def ownership_proof(units,glyphs,target_objects):
    owners={g['id']:u['id'] for u in units for g in u['glyphs']};object_owners=collections.defaultdict(set);unmapped=[]
    for g in glyphs:
        if g['object_id'] not in target_objects or g['char'].isspace() or g['box'][2]<=g['box'][0] or g['box'][3]<=g['box'][1]:continue
        if g['id'] not in owners:unmapped.append(g['id'])
        else:object_owners[g['object_id']].add(owners[g['id']])
    if unmapped:raise ValueError('potential painted native records have no owner: '+','.join(unmapped))
    return dict(object_owners)
