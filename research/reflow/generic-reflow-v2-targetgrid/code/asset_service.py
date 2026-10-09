"""Local diagnostic cache service. No network, UI, or inferred copy strings."""
import hashlib,io,json,pathlib,time,zipfile
from PIL import Image
import pypdfium2 as pdfium
from target_grid import TargetConfig,AssetCache,cache_key,choose_grid,renderer_identity
from render_request import run

class NativeAssetService:
    def __init__(self,pdf,plan_folder,evidence_root,cfg=TargetConfig()):self.pdf=pathlib.Path(pdf);self.folder=pathlib.Path(plan_folder);self.out=pathlib.Path(evidence_root);self.cfg=cfg;self.cache=AssetCache(cfg);self.requests=[]
    def request(self,unit_ids,font_css_px,dpr,enlargement=1.):
        start=time.perf_counter();cpu=time.process_time();pdfsha=hashlib.sha256(self.pdf.read_bytes()).hexdigest();plansha=hashlib.sha256((self.folder/'plan-private.json').read_bytes()+(self.folder/'ownership-summary.json').read_bytes()).hexdigest();base=json.loads((self.folder/'ownership-summary.json').read_text());grid=choose_grid(font_css_px,dpr,base['body_font'],enlargement,self.cfg)['grid'];key=cache_key(pdfsha,plansha,unit_ids,grid,renderer_identity(str(pdfium.PDFIUM_INFO)),'source_flat_backdrop');payload=self.cache.get(key);hit=payload is not None;result=None
        if not hit:
            dest=self.out/(str(len(self.requests))+'-'+key[:12])
            if dest.exists():raise ValueError('refuse to overwrite an existing request evidence directory')
            result=run(self.pdf,self.folder,dest,unit_ids,font_css_px,dpr,enlargement,self.cfg)
            if not result['target_grid_accepted']:
                report=dict(cache_hit=False,failure=result['failure'],wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu);self.requests.append(report);return None,report
            assets=json.loads((dest/'native-unit-assets-private.json').read_text());buffer=io.BytesIO();decoded=0
            with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as z:
                z.writestr('assets.json',json.dumps(assets))
                for asset in assets['results']:
                    if asset.get('empty'):continue
                    p=dest/asset['file'];z.writestr(asset['file'],p.read_bytes());im=Image.open(p);decoded+=im.width*im.height*4
            payload=buffer.getvalue();self.cache.put(key,payload,decoded)
        report=dict(cache_hit=hit,key=key,grid=grid,payload_bytes=len(payload),cache_encoded_bytes=self.cache.encoded_bytes,cache_decoded_bytes=self.cache.decoded_bytes,wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,includes='source/plan fingerprinting, cache lookup; on miss native mask/reference/render/encode and pack/store',native_preprocessing_reused='existing source ownership plan; no new layout-model invocation',failure=None)
        self.requests.append(report);return payload,report
