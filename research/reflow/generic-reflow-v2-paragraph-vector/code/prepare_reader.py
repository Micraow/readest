"""Build a native-resource reader payload; no source PDF is emitted publicly."""
import argparse,base64,collections,json,pathlib
from html.parser import HTMLParser
class ReaderParser(HTMLParser):
    def __init__(self):super().__init__();self.blocks=[];self.current=None;self.in_main=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='main':self.in_main=True
        if not self.in_main:return
        if tag in {'p','figure','aside'}:self.current={'kind':{'p':'paragraph','figure':'object','aside':'auxiliary'}[tag],'tokens':[]};self.blocks.append(self.current)
        if tag=='span' and a.get('class')=='token':
            styles=dict(p.split(':',1) for p in a['style'].split(';') if ':' in p)
            self.current['tokens'].append({'id':a['data-unit'],'members':a['data-members'].split(),'width_em':float(styles['width'][:-2]),'height_em':float(styles['height'][:-2]),'vertical_em':float(styles['vertical-align'][:-2]),'gap_em':float(styles['margin-right'][:-2])})
    def handle_endtag(self,tag):
        if tag=='main':self.in_main=False

def prepare(folder,capture,bridgefile,out):
    folder=pathlib.Path(folder);capture=pathlib.Path(capture);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    bridge=json.loads(pathlib.Path(bridgefile).read_text());parser=ReaderParser();parser.feed((folder/'tree-reader.html').read_text());assetdata=json.loads((folder/'tree-reader-assets-private.json').read_text());assets={a['id']:a for a in assetdata['results']};events={e['id']:e for e in json.loads((capture/'events-private.json').read_text())};resources=json.loads((capture/'resources-private.json').read_text());selected={};fallback_units=set();fallback_tokens=[];vector_tokens=[]
    for block in parser.blocks:
        for token in block['tokens']:
            asset=assets[token['id']];token['source_pixel_box']=asset['asset_pixel_box']
            if all(m in bridge['converted'] for m in token['members']):
                ids=sorted(i for m in token['members'] for i in bridge['converted'][m]['native_event_ids']);token.update(kind='vector',native_event_ids=ids);vector_tokens.append(token['id'])
                for i in ids:selected[i]=events[i]
            else:
                token.update(kind='native_image',asset_scale=assetdata['scale'],asset_pixel_box=asset['asset_pixel_box'],data_uri='data:image/png;base64,'+base64.b64encode((folder/asset['file']).read_bytes()).decode());fallback_units.update(token['members']);fallback_tokens.append(token['id'])
    pathkeys=sorted({e['resource'] for e in selected.values()});pathidx={k:i for i,k in enumerate(pathkeys)};programs=[];programids={};states=[];stateids={};nativeevents={}
    for i,e in selected.items():
        program=e['state']['affine'];pk=json.dumps(program,separators=(',',':'));state={k:e['state'][k] for k in ['fillStyle','alpha','blend','filter']};sk=json.dumps(state,separators=(',',':'))
        if pk not in programids:programids[pk]=len(programs);programs.append(program)
        if sk not in stateids:stateids[sk]=len(states);states.append(state)
        nativeevents[i]={'resource':pathidx[e['resource']],'program':programids[pk],'state':stateids[sk],'x':e['x'],'y':e['y'],'fontSize':e['fontSize'],'source_paint_id':[e['opIdx'],e['glyphOrdinal']]}
    result={'schema':1,'body_font_pdf':assetdata['body_font'],'source_capture_scale':assetdata['scale'],'blocks':parser.blocks,'resources':[resources[k] for k in pathkeys],'affine_programs':programs,'states':states,'events':nativeevents,'selection_semantics_certified':False,'mixed_engine_pixel_ownership_proven':False,'local_images_target_grid_verified':False,'native_image_policy':'current low-resolution source-light preview; target-grid update required'}
    (out/'reader-data-private.json').write_text(json.dumps(result,separators=(',',':')));(out/'fallback-requests-private.json').write_text(json.dumps({'units':sorted(fallback_units),'tokens':fallback_tokens},indent=2));summary={'blocks':len(parser.blocks),'paragraphs':sum(b['kind']=='paragraph' for b in parser.blocks),'tokens':len(vector_tokens)+len(fallback_tokens),'vector_tokens':len(vector_tokens),'native_image_tokens':len(fallback_tokens),'fallback_source_units':len(fallback_units),'glyph_events':len(nativeevents),'shared_contours':len(pathkeys),'affine_programs':len(programs),'state_resources':len(states),'payload_bytes':(out/'reader-data-private.json').stat().st_size,'semantic_selection_certified':False};(out/'preparation-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('capture');p.add_argument('bridge');p.add_argument('out');a=p.parse_args();prepare(a.folder,a.capture,a.bridge,a.out)
