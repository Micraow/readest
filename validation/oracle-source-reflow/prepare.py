"""Compile document-neutral oracle source units. No role inference or OCR."""
import argparse,base64,collections,hashlib,io,json,math,pathlib
import fitz
from PIL import Image


def sha(b):return hashlib.sha256(b).hexdigest()
def png_data(im):
    f=io.BytesIO();im.save(f,format='PNG');return 'data:image/png;base64,'+base64.b64encode(f.getvalue()).decode()
def ink_box(im):
    return im.convert('L').point(lambda x:255 if x<245 else 0).getbbox()
def nink(im):return sum(x<245 for x in im.convert('L').getdata())
def pbox(b,s):return [round(x*s) for x in b]
def overlap(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])


def compile_source(pdf,oracle,out):
    data=pathlib.Path(pdf).read_bytes();assert sha(data)==oracle['source']['sha256'],'source hash mismatch'
    doc=fitz.open(stream=data,filetype='pdf');s=oracle['rasterScale'];font=oracle['bodyFontPt']
    result={'schemaVersion':oracle['schemaVersion'],'source':oracle['source'],'bodyFontPt':font,'sections':[], 'pages':{},'exceptions':[], 'scopeNote':oracle['scopeNote']}
    page_images={};raw={};crops=collections.defaultdict(list);owned_ids=set();audits=[]
    for pn in sorted({x['page'] for x in oracle['sections']}):
        page=doc[pn-1];pix=page.get_pixmap(matrix=fitz.Matrix(s,s),alpha=False)
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);page_images[pn]=im;raw[pn]=page.get_text('rawdict')
        result['pages'][str(pn)]={'width':page.rect.width,'height':page.rect.height,'image':png_data(im)}
    def tile(pn,box,base,ids,uid,role,label,join=None):
        pb=pbox(box,s);im=page_images[pn];part=im.crop(pb);tight=ink_box(part);assert tight,('empty unit',uid)
        # Retain exactly the source pixel rectangle; no synthesis, glyph replacement or masking.
        tight=[max(0,tight[0]-1),max(0,tight[1]-1),min(part.width,tight[2]+1),min(part.height,tight[3]+1)]
        rb=[pb[0]+tight[0],pb[1]+tight[1],pb[0]+tight[2],pb[1]+tight[3]]
        crop=im.crop(rb);crops[pn].append((rb,uid,role))
        for x in ids:assert x not in owned_ids,('duplicate native char',x);owned_ids.add(x)
        box=[x/s for x in rb]
        return {'id':uid,'role':role,'label':label,'source':{'sha256':oracle['source']['sha256'],'page':pn,'bbox':box,'partition': [x/s for x in pb], 'charIds':ids},'baseline':base,'widthEm':(box[2]-box[0])/font,'heightEm':(box[3]-box[1])/font,'descentEm':(box[3]-base)/font if base else 0,'image':png_data(crop),'inkPixels':nink(crop),'pixelSha256':sha(crop.tobytes()),'join':join}
    for sec in oracle['sections']:
        pn=sec['page'];dst={k:v for k,v in sec.items() if k!='nodes'};dst['nodes']=[]
        for node in sec['nodes']:
            nd={k:v for k,v in node.items() if k not in ('lines','window')};nd['units']=[]
            if 'window' in node:
                # Protected block remains a whole source object, including original number.
                nd['units'].append(tile(pn,node['window'],None,[],node['id']+'-whole',node['role'],node['label']))
                audits.append({'id':node['id'],'sourceInk':nd['units'][0]['inkPixels'],'ownedInk':nd['units'][0]['inkPixels'],'suppressedInk':0,'kind':'protected-whole'})
            else:
                for li,line in enumerate(node['lines']):
                    chars=[]
                    for bi,lix in line['refs']:
                        if chars:chars.append({'c':' ','bbox':[chars[-1]['bbox'][2],line['baseline'],chars[-1]['bbox'][2],line['baseline']],'id':None})
                        for si,sp in enumerate(raw[pn]['blocks'][bi]['lines'][lix]['spans']):
                            for ci,c in enumerate(sp['chars']):chars.append(dict(c,id=f'{pn}:{bi}:{lix}:{si}:{ci}'))
                    groups=line.get('groups',[]);starts={g['chars'][0]:g for g in groups};taken=set();units=[];i=0
                    while i<len(chars):
                        if chars[i]['c'].isspace():i+=1;continue
                        if i in starts:
                            g=starts[i];end=g['chars'][1]+1
                            assert not taken.intersection(range(i,end));taken.update(range(i,end))
                        else:
                            end=i+1
                            while end<len(chars) and not chars[end]['c'].isspace() and end not in starts:end+=1
                            g={'role':'word','label':''.join(c['c'] for c in chars[i:end])}
                        cs=chars[i:end];xs=[c['bbox'][0] for c in cs if not c['c'].isspace()];xe=[c['bbox'][2] for c in cs if not c['c'].isspace()]
                        units.append({'g':g,'chars':cs,'x0':min(xs),'x1':max(xe),'text':''.join(c['c'] for c in cs)});i=end
                    x0,y0,x1,y1=line['window'];cuts=[round(x0*s)]
                    # Search for a fully white pixel column in each native whitespace gap.
                    # If no gap exists, fail closed: the oracle must group those characters.
                    for a,b in zip(units,units[1:]):
                        lo=math.floor(a['x1']*s);hi=math.ceil(b['x0']*s);mid=(lo+hi)/2
                        candidates=range(max(cuts[-1]+1,lo-2),hi+3)
                        blank=[x for x in candidates if nink(page_images[pn].crop((x,round(y0*s),x+1,round(y1*s))))==0]
                        assert blank,('no safe vertical cut',node['id'],li,a['text'],b['text'],lo,hi)
                        cuts.append(min(blank,key=lambda x:abs(x-mid)))
                    cuts.append(round(x1*s));visible=suppressed=0
                    for ui,u in enumerate(units):
                        box=[cuts[ui]/s,y0,cuts[ui+1]/s,y1];g=u['g'];uid=f'{node["id"]}-l{li}-u{ui}'
                        unit=tile(pn,box,line['baseline'],[c['id'] for c in u['chars'] if c.get('id') and not c['c'].isspace()],uid,g['role'],g['label'],g.get('join'))
                        unit['nativeText']=u['text']
                        if g.get('breakAfter'):unit['breakAfter']=True
                        if g.get('normalizationException'):result['exceptions'].append({'id':uid,'source':unit['source'],'kind':g['normalizationException'],'pixelsRemoved':0,'rendering':'Preserve source hyphen and force line break here. This one line boundary is not reflowed.'})
                        if g['role']=='discretionary-hyphen':result['exceptions'].append(unit);suppressed+=unit['inkPixels']
                        else:nd['units'].append(unit);visible+=unit['inkPixels']
                    region=page_images[pn].crop(pbox(line['window'],s));source_count=nink(region)
                    assert visible+suppressed==source_count,('source ink lost or duplicated',node['id'],li,source_count,visible,suppressed)
                    # Any dark pixel on horizontal region edges is an unresolved clipping risk.
                    assert nink(region.crop((0,0,region.width,1)))==0 and nink(region.crop((0,region.height-1,region.width,region.height)))==0,('ink at line edge',node['id'],li)
                    audits.append({'id':f'{node["id"]}-l{li}','sourceInk':source_count,'ownedInk':visible,'suppressedInk':suppressed,'kind':'disjoint-word-partition'})
                # One explicitly labelled cross-line word join; no heuristic dehyphenation.
                merged=[]
                for u in nd['units']:
                    if u['join'] and merged and merged[-1].get('join')==u['join']:
                        old=merged[-1];old.setdefault('fragments',[{k:v for k,v in old.items() if k!='fragments'}]).append(u);old['widthEm']+=u['widthEm'];old['nativeText']+=u['nativeText'];old['label']=old['nativeText']
                    else:merged.append(u)
                nd['units']=merged
            dst['nodes'].append(nd)
        result['sections'].append(dst)
    # Rectangular source crop overlap audit detects any duplicate ink, not just duplicate IDs.
    duplicates=[]
    for pn,rows in crops.items():
        for i,(a,aid,ar) in enumerate(rows):
            for b,bid,br in rows[i+1:]:
                if overlap(a,b):
                    inter=(max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]));n=nink(page_images[pn].crop(inter))
                    if n:duplicates.append({'a':aid,'b':bid,'ink':n})
    assert not duplicates,duplicates
    result['audit']={'scope':'Selected gold source windows only, not page or document coverage','nativeVisibleChars':len(owned_ids),'sourceInk':sum(a['sourceInk'] for a in audits),'renderedInk':sum(a['ownedInk'] for a in audits),'suppressedInk':sum(a['suppressedInk'] for a in audits),'duplicateInk':duplicates,'lines':audits,'scientificSemanticAudit':'Requires independent visual inspection; counts do not establish correct group ownership.'}
    pathlib.Path(out).mkdir(exist_ok=True,parents=True)
    pathlib.Path(out,'fixture.js').write_text('window.ORACLE_FIXTURE='+json.dumps(result,separators=(',',':'))+';\n')
    pathlib.Path(out,'audit.json').write_text(json.dumps(result['audit'],indent=2))
    print(json.dumps({k:v for k,v in result['audit'].items() if k!='lines'},indent=2))
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('--oracle',default='oracle.json');ap.add_argument('--out',default='.');a=ap.parse_args()
    compile_source(a.pdf,json.loads(pathlib.Path(a.oracle).read_text()),a.out)
