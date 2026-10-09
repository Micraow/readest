"""Finite local miss/hit/eviction probe; initial page preprocessing excluded."""
import argparse,hashlib,json,pathlib,time
from dataclasses import replace
from asset_service import NativeAssetService
from target_grid import TargetConfig
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--plan',required=True);p.add_argument('--unit',action='append',required=True);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);body=json.loads((pathlib.Path(a.plan)/'ownership-summary.json').read_text())['body_font'];service=NativeAssetService(a.pdf,a.plan,out/'assets',replace(TargetConfig(),maximum_cache_entries=1));payloads=[]
    for font,dpr in [(28,2),(28,2),(body*2,1)]:
        payload,r=service.request(a.unit,font,dpr);payloads.append(payload)
        if payload is None:break
    result=dict(scope='native requested-unit cache service after existing page preprocessing, not full page or UI',requests=service.requests,cache_trace=service.cache.trace,repeat_high_grid_payload_identical=len(payloads)>1 and payloads[0]==payloads[1],final_cached_entries=len(service.cache.entries),all_requests_succeeded=len(payloads)==3 and all(p is not None for p in payloads),semantic_selection_certified=False,interactive_zoom_tested=False)
    (out/'pipeline-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
