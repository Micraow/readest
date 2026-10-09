"""Native paint/glyph reflow representation probe. Original research code.

PDFium via pypdfium2; no detector, OCR, font-name keyword or source-document rule.
Private extraction and HTML outputs must remain outside the public repository.
"""
from __future__ import annotations
import argparse, collections, ctypes, hashlib, html, json, math, pathlib, resource, statistics, time, unicodedata
from dataclasses import asdict
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from config import Config

def set_active(obj,active):
    if not raw.FPDFPageObj_SetIsActive(obj,bool(active)):raise RuntimeError('Native object activation failed')

def addr(obj): return ctypes.cast(getattr(obj, 'raw', obj), ctypes.c_void_p).value

def box_union(boxes):
    boxes=list(boxes)
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def area(b): return max(0,b[2]-b[0])*max(0,b[3]-b[1])
def center(b): return [(b[0]+b[2])/2,(b[1]+b[3])/2]
def inside(b,p): return b[0]<=p[0]<=b[2] and b[1]<=p[1]<=b[3]
def dist(a,b): return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))
def pad(b,p):return [b[0]-p,b[1]-p,b[2]+p,b[3]+p]
def reason(out,subject,rule,accepted,**measured):out.append(dict(subject=subject,rule=rule,accepted=accepted,measured=measured))
def mapped_unicode(cp,error):
    return bool(cp and cp<=0x10ffff and not error and unicodedata.category(chr(cp)) not in {'Co','Cs','Cn','Cc'} and chr(cp)!='\ufffd')

class Union:
    def __init__(self,n):self.p=list(range(n))
    def find(self,a):
        while self.p[a]!=a:self.p[a]=self.p[self.p[a]];a=self.p[a]
        return a
    def join(self,a,b):self.p[self.find(b)]=self.find(a)

def components(items,padding):
    """Spatial sweep avoids unbounded all-pairs object overlap work."""
    uf=Union(len(items));active=[]
    for i in sorted(range(len(items)),key=lambda i:items[i]['box'][0]):
        a=items[i]['box'];active=[j for j in active if items[j]['box'][2]+padding>=a[0]]
        for j in active:
            if dist(a,items[j]['box'])<=padding:uf.join(i,j)
        active.append(i)
    groups=collections.defaultdict(list)
    for i,item in enumerate(items):groups[uf.find(i)].append(item)
    return list(groups.values())

def native_inventory(page,cfg,trace):
    W,H=page.get_size();tp=page.get_textpage(); objects=[];handles={}; pointer={}
    def topbox(b):return [b[0],H-b[3],b[2],H-b[1]]
    # This first prototype deliberately refuses form descendants rather than using
    # uncomposed form-space coordinates as page-space truth.
    for seq,obj in enumerate(page.get_objects(max_depth=1)):
        oid=f'p{seq}'; handles[oid]=obj;pointer[addr(obj)]=oid
        info=dict(id=oid,seq=seq,type=obj.type,box=topbox(obj.get_bounds()),kind='foreground',level=obj.level)
        if obj.type==raw.FPDF_PAGEOBJ_PATH:
            fill,stroke=ctypes.c_int(),ctypes.c_int();raw.FPDFPath_GetDrawMode(obj,fill,stroke)
            rgba=[ctypes.c_uint() for _ in range(4)];raw.FPDFPageObj_GetFillColor(obj,*rgba)
            info.update(fill=fill.value,stroke=bool(stroke.value),rgba=[v.value for v in rgba])
            pts=[];straight=True
            for k in range(raw.FPDFPath_CountSegments(obj)):
                seg=raw.FPDFPath_GetPathSegment(obj,k);x,y=ctypes.c_float(),ctypes.c_float();raw.FPDFPathSegment_GetPoint(seg,x,y)
                pts.append((x.value,y.value));straight &= raw.FPDFPathSegment_GetType(seg) in {raw.FPDF_SEGMENT_MOVETO,raw.FPDF_SEGMENT_LINETO}
            unique=set(pts);xs={round(x,cfg.rectangle_precision_digits) for x,y in unique};ys={round(y,cfg.rectangle_precision_digits) for x,y in unique}
            closed=bool(pts) and bool(raw.FPDFPathSegment_GetClose(raw.FPDFPath_GetPathSegment(obj,len(pts)-1)))
            cycle=pts[:-1] if len(pts)>1 and pts[0]==pts[-1] else pts
            edges=list(zip(cycle,cycle[1:]+cycle[:1]))
            orthogonal=all((abs(a[0]-b[0])<=cfg.geometry_epsilon) != (abs(a[1]-b[1])<=cfg.geometry_epsilon) for a,b in edges)
            matrix=raw.FS_MATRIX();raw.FPDFPageObj_GetMatrix(obj,matrix)
            axis_aligned=abs(matrix.b)<=cfg.geometry_epsilon and abs(matrix.c)<=cfg.geometry_epsilon
            clip=raw.FPDFPageObj_GetClipPath(obj);clip_count=raw.FPDFClipPath_CountPaths(clip)
            # In the pinned PDFium implementation -1 with a valid object means the clip has no reference.
            info['horizontal_stroke']=bool(stroke.value) and len(pts)>=2 and max(y for x,y in pts)-min(y for x,y in pts)<=cfg.geometry_epsilon
            info.update(clip_path_count=clip_count,transparency=bool(raw.FPDFPageObj_HasTransparency(obj)),closed=closed,axis_aligned=axis_aligned)
            info['simple_rect']=straight and closed and orthogonal and axis_aligned and len(xs)==2 and len(ys)==2 and len(unique)==4
        if obj.type==raw.FPDF_PAGEOBJ_TEXT: info['render_mode']=raw.FPDFTextObj_GetTextRenderMode(obj)
        objects.append(info)
    glyphs=[];generated=0;invisible=0;unmapped_objects=0
    omap={o['id']:o for o in objects}
    for i in range(tp.count_chars()):
        cp=raw.FPDFText_GetUnicode(tp,i);oid=pointer.get(addr(raw.FPDFText_GetTextObject(tp,i)));gen=raw.FPDFText_IsGenerated(tp,i)
        if gen:generated+=1;continue
        if not oid:unmapped_objects+=1;continue
        if omap[oid].get('render_mode')==3:invisible+=1;continue
        x,y=ctypes.c_double(),ctypes.c_double();raw.FPDFText_GetCharOrigin(tp,i,x,y)
        matrix=raw.FS_MATRIX();raw.FPDFText_GetMatrix(tp,i,matrix)
        effective_size=raw.FPDFText_GetFontSize(tp,i)*math.hypot(matrix.c,matrix.d)
        b=topbox(tp.get_charbox(i));ch=chr(cp) if 0<cp<=0x10ffff else '\ufffd';err=raw.FPDFText_HasUnicodeMapError(tp,i)
        glyphs.append(dict(id=f'g{i}',source_index=i,object_id=oid,char=ch,box=b,baseline=H-y.value,origin=x.value,size=effective_size,unicode_known=mapped_unicode(cp,err),map_error=err))
    visible=[g for g in glyphs if not g['char'].isspace() and area(g['box'])>0]
    body=statistics.median([g['size'] for g in visible if g['size']>=cfg.minimum_font_pt]) if visible else cfg.fallback_body_font_pt
    for obj in objects:
        if obj['type']!=raw.FPDF_PAGEOBJ_PATH:continue
        contained=[g for g in visible if inside(obj['box'],center(g['box']))]
        earlier=bool(contained) and all(obj['seq']<omap[g['object_id']]['seq'] for g in contained)
        yes=bool(obj.get('simple_rect') and obj['fill'] and not obj['stroke'] and not obj['transparency'] and obj['clip_path_count']==-1 and obj['rgba'][3]>=cfg.background_opacity_min and len(contained)>=cfg.background_min_glyphs and area(obj['box'])>=cfg.background_min_area_em2*body**2 and earlier)
        reason(trace,obj['id'],'background_simple_opaque_rectangle',yes,simple_rect=obj.get('simple_rect'),fill=obj['fill'],stroke=obj['stroke'],enclosed_glyphs=len(contained),earlier_than_text=earlier,area_em2=area(obj['box'])/body**2)
        if yes:obj['kind']='background';obj['enclosed_glyphs']=[g['id'] for g in contained]
    geometry_groups=collections.defaultdict(list)
    for g in visible: geometry_groups[(g['object_id'],tuple(round(x,cfg.coordinate_precision_digits) for x in g['box']),round(g['origin'],cfg.coordinate_precision_digits),round(g['baseline'],cfg.coordinate_precision_digits))].append(g['id'])
    aliases=[ids for ids in geometry_groups.values() if len(ids)>1]
    for ids in aliases: reason(trace,ids[0],'shared_ink_candidate',True,character_ids=ids,identity_certified=False)
    return objects,handles,glyphs,body,dict(shared_ink_candidate_groups=len(aliases),annotations=raw.FPDFPage_GetAnnotCount(page),clip_text_objects=sum(o.get('render_mode',0)>=4 for o in objects),generated_nonpaint_chars=generated,invisible_text_chars=invisible,unmapped_text_object_chars=unmapped_objects,forms=sum(o['type']==raw.FPDF_PAGEOBJ_FORM for o in objects))

def line_words(glyphs,body,cfg,trace):
    lines=[]
    for g in sorted(glyphs,key=lambda g:(g['baseline'],g['origin'])):
        candidates=[line for line in lines[-cfg.line_cluster_lookback:] if abs(line['baseline']-g['baseline'])<=cfg.baseline_tolerance_em*body]
        reason(trace,g['id'],'baseline_cluster',bool(candidates),baseline=g['baseline'],tolerance_em=cfg.baseline_tolerance_em,candidate_count=len(candidates))
        if candidates: line=min(candidates,key=lambda l:abs(l['baseline']-g['baseline']));line['glyphs'].append(g)
        else:lines.append(dict(baseline=g['baseline'],glyphs=[g]))
    out=[]
    for line in lines:
        words=[];current=[];last=None
        for g in sorted(line['glyphs'],key=lambda g:g['origin']):
            if g['char'].isspace():
                if current:words.append(current);current=[]
                last=None;continue
            east=unicodedata.east_asian_width(g['char']) in 'WF'
            split=last is not None and (g['origin']-last['box'][2]>cfg.word_gap_em*body or east or unicodedata.east_asian_width(last['char']) in 'WF')
            reason(trace,g['id'],'word_boundary',bool(split),gap_em=(g['origin']-last['box'][2])/body if last else None,east_asian_character=east,threshold_em=cfg.word_gap_em)
            if current and split:words.append(current);current=[]
            current.append(g);last=g
        if current:words.append(current)
        chunks=[];chunk=[]
        for gs in words:
            w=dict(id='w'+gs[0]['id'][1:],glyphs=gs,box=box_union(g['box'] for g in gs),text=''.join(g['char'] for g in gs),baseline=line['baseline'])
            if chunk and w['box'][0]-chunk[-1]['box'][2]>cfg.column_gap_em*body:chunks.append(chunk);chunk=[]
            chunk.append(w)
        if chunk:chunks.append(chunk)
        for chunk in chunks:
            first=chunk[0];marker=len(chunk)>1 and len(first['text'])==1 and not first['text'].isalnum() and unicodedata.category(first['text'])!='Sm' and first['box'][2]-first['box'][0]<=cfg.list_marker_max_width_em*body
            out.append(dict(id='l'+first['id'][1:],words=chunk,box=box_union(w['box'] for w in chunk),baseline=line['baseline'],kind='line',list_start=marker,content_start=chunk[1]['box'][0] if marker else first['box'][0]))
    return out

def spatial_order(items,body,cfg,trace):
    if len(items)<2:return items
    # Prefer a complete vertical gutter; otherwise isolate horizontal bands and recurse.
    for axis,min_gap in [(0,cfg.column_gap_em*body),(1,cfg.paragraph_gap_em*body)]:
        ordered=sorted(items,key=lambda q:q['box'][axis]);cuts=[];end=ordered[0]['box'][axis+2]
        for n,q in enumerate(ordered[1:],1):
            gap=q['box'][axis]-end
            if gap>min_gap:cuts.append((gap,n))
            end=max(end,q['box'][axis+2])
        if cuts:
            gap,n=max(cuts)
            reason(trace,ordered[0]['id'],'reading_order_whitespace_cut',True,axis=axis,gap=gap,threshold=min_gap,left_count=n,right_count=len(ordered)-n)
            return spatial_order(ordered[:n],body,cfg,trace)+spatial_order(ordered[n:],body,cfg,trace)
    return sorted(items,key=lambda q:(q['box'][1],q['box'][0]))

def plan(objects,glyphs,W,H,body,cfg,trace,fraction_support_selector=None):
    backgrounds=[o for o in objects if o['kind']=='background'];nontext=[o for o in objects if o['type']!=raw.FPDF_PAGEOBJ_TEXT and o['kind']!='background']
    visible=[g for g in glyphs if not g['char'].isspace() and area(g['box'])>0]
    # Foreground objects join foreground only. Never feed a background into this union.
    groups=components(nontext,cfg.foreground_join_em*body);islands=[];consumed=set();aux=[]
    content_bounds=box_union(g['box'] for g in visible) if visible else [0,0,W,H]
    for group in groups:
        b=box_union(o['box'] for o in group);near=[g for g in visible if inside(pad(b,cfg.attachment_distance_em*body),center(g['box']))]
        fraction=False
        if all(o['type']==raw.FPDF_PAGEOBJ_PATH and o.get('horizontal_stroke') for o in group) and b[2]-b[0]>=cfg.fraction_rule_min_width_em*body:
            nearby=[g for g in visible if b[0]<=center(g['box'])[0]<=b[2] and dist(b,g['box'])<=cfg.fraction_vertical_reach_em*body]
            above=any(g['box'][3]<b[1] for g in nearby);below=any(g['box'][1]>b[3] for g in nearby)
            fraction=above and below
            if fraction:
                support=[b[0]-cfg.fraction_side_reach_em*body,b[1]-cfg.fraction_vertical_reach_em*body,b[2]+cfg.fraction_side_reach_em*body,b[3]+cfg.fraction_vertical_reach_em*body]
                near=[g for g in visible if inside(support,center(g['box']))]
                if fraction_support_selector is not None:
                    selected=fraction_support_selector(b,visible,cfg.fraction_vertical_reach_em*body,body=body)
                    near=selected if selected is not None else []
                    reason(trace,group[0]['id'],'projected_fraction_support',selected is not None,glyphs=len(near))
            reason(trace,group[0]['id'],'fraction_rule_local_support',fraction,above=above,below=below,glyphs=len(near))
        margin=(b[2]<content_bounds[0] or b[0]>content_bounds[2]) and b[2]-b[0]<cfg.margin_mark_width_em*body
        item=dict(id='o'+group[0]['id'][1:],kind='aux' if margin else 'island',objects=[o['id'] for o in group],fraction_support=fraction,glyphs=[] if margin else near,box=b)
        if near and not margin:item['box']=box_union([b]+[g['box'] for g in near]);consumed.update(g['id'] for g in near)
        (aux if margin else islands).append(item)
        reason(trace,item['id'],'foreground_local_component',True,paint_objects=len(group),attached_glyphs=len(item['glyphs']),margin_mark=margin,background_edges=0)
    # When local components overlap, assign each glyph to exactly one, smallest support.
    candidates=collections.defaultdict(list)
    for item in islands:
        for g in item['glyphs']:candidates[g['id']].append(item)
    for gid,owners in candidates.items():
        best=min(owners,key=lambda o:area(o['box']))
        for owner in owners:
            if owner is not best:owner['glyphs']=[g for g in owner['glyphs'] if g['id']!=gid]
    remaining=[g for g in glyphs if g['id'] not in consumed]
    lines=line_words(remaining,body,cfg,trace)
    for line in lines:
        line['bg_ids']=[bg['id'] for bg in backgrounds if all(inside(bg['box'],center(g['box'])) for w in line['words'] for g in w['glyphs'])]
        line['auxiliary']=line['box'][3]<H*cfg.margin_auxiliary_band_page_ratio or line['box'][1]>H*(1-cfg.margin_auxiliary_band_page_ratio)
    for item in islands:
        item['bg_ids']=[bg['id'] for bg in backgrounds if inside(bg['box'],item['box'][:2]) and inside(bg['box'],item['box'][2:])]
    main=[i for i in lines if not i['auxiliary']]+islands
    ordered=spatial_order(main,body,cfg,trace)
    # Keep page furniture out of body continuations. Preserve it in separate output.
    ordered+=sorted([i for i in lines if i['auxiliary']],key=lambda x:x['box'][1])+aux
    result=[];p=None
    for item in ordered:
        if item['kind']!='line':result.append(item);p=None;continue
        join=False;vertical=None;list_continuation=False;aligned=False
        if p is not None:
            prev=p['lines'][-1];b1=prev['box'];b2=item['box'];vertical=item['baseline']-prev['baseline']
            aligned=abs(b1[0]-b2[0])<cfg.paragraph_indent_em*body
            list_continuation=p['lines'][0]['list_start'] and abs(p['lines'][0]['content_start']-item['content_start'])<=cfg.continuation_alignment_em*body
            join=(0<vertical<(b1[3]-b1[1])+cfg.paragraph_gap_em*body and (aligned or list_continuation) and p['bg_ids']==item['bg_ids'] and not item['auxiliary'] and not item['list_start'])
        reason(trace,item['id'],'paragraph_join',join,previous=result[-1]['id'] if result else None,baseline_delta=vertical,aligned=aligned,list_continuation=list_continuation,list_start=item['list_start'],content_start=item['content_start'])
        if not join:
            p=dict(id='r'+item['id'][1:],kind='text',lines=[],box=item['box'],bg_ids=item['bg_ids'],auxiliary=item['auxiliary']);result.append(p)
        p['lines'].append(item);p['box']=box_union([p['box'],item['box']])
    # Backgrounds decorate a containing logical range. No pixel layer behind text crops.
    for bg in backgrounds:
        owners=[i for i,r in enumerate(result) if bg['id'] in r.get('bg_ids',[])]
        bg['range']=[min(owners),max(owners)+1] if owners else None
        reason(trace,bg['id'],'background_logical_range',bool(owners),owners=len(owners),contiguous=bool(owners) and owners==list(range(min(owners),max(owners)+1)))
    cursor=0
    for item in result:
        if item['kind']=='text':item['glyphs']=[g for line in item['lines'] for w in line['words'] for g in w['glyphs']]
        item['atom_ids']=[g['id'] for g in item.get('glyphs',[])]+item.get('objects',[])
        item['interval']=[cursor,cursor+len(item['atom_ids'])];cursor=item['interval'][1]
    expected=[g['id'] for g in visible]+[o['id'] for o in nontext]
    emitted=[a for item in result for a in item['atom_ids']]
    hard=[]
    if collections.Counter(expected)!=collections.Counter(emitted):hard.append('atom_ownership_mismatch')
    for item in islands:
        cropbox=pad(item['box'],cfg.local_object_padding_em*body)
        owned=set(item['atom_ids'])
        candidates=[g['id'] for g in visible if g['id'] not in owned and dist(cropbox,g['box'])==0]+[o['id'] for o in nontext if o['id'] not in owned and dist(cropbox,o['box'])==0]
        object_ids=set(item['objects'])|{g['object_id'] for g in item['glyphs']}
        shared=[g['id'] for g in visible if g['object_id'] in object_ids and g['id'] not in owned and dist(cropbox,g['box'])==0]
        if shared:hard.append('shared_text_object_ink_in_local_crop:'+item['id'])
        reason(trace,item['id'],'local_crop_ownership',not shared,unowned_bbox_candidates=candidates,shared_native_object_candidates=shared,renderer='native object active isolation')
        prose=sum(g['char'].isalpha() for g in item['glyphs'])
        if prose>cfg.maximum_prose_chars_in_object:hard.append('long_prose_locked:'+item['id'])
        if area(item['box'])>W*H*cfg.maximum_object_area_page_ratio or item['box'][3]-item['box'][1]>H*cfg.maximum_object_height_page_ratio:hard.append('oversized_island:'+item['id'])
    for bg in backgrounds:
        if bg['range'] is None:hard.append('background_without_logical_owner:'+bg['id'])
        else:
            owners=[i for i,r in enumerate(result) if bg['id'] in r.get('bg_ids',[])]
            if owners!=list(range(*bg['range'])):hard.append('background_noncontiguous_owners:'+bg['id'])
    for a in backgrounds:
        for b in backgrounds:
            if a['range'] and b['range'] and a['range'][0]<b['range'][0]<a['range'][1]<b['range'][1]: hard.append('background_crossed_intervals:'+a['id']+':'+b['id'])
    return result,backgrounds,expected,hard

def render(page,objects,handles,items,backgrounds,body,cfg,out):
    # Native source paint is retained locally. Reader only references local islands,
    # never the source page as a reading result.
    source=page.render(scale=cfg.render_scale).to_pil();source.save(out/'source.png')
    for o in backgrounds:set_active(handles[o['id']],False)
    foreground=page.render(scale=cfg.render_scale,fill_color=(0,0,0,0)).to_pil();foreground.save(out/'foreground.png')
    for o in backgrounds:set_active(handles[o['id']],True)
    parts=[];emitted=[];bg_emitted=[];isolation_passes=0
    W,H=page.get_size()
    def isolated(objects_to_keep,b):
        nonlocal isolation_passes
        # Preserve PDFium's paint order and clip state; suppress unrelated native
        # page objects before rasterization, rather than cropping their pixels away.
        left=max(0,b[0]);top=max(0,b[1]);right=min(W,b[2]);bottom=min(H,b[3])
        for oid,handle in handles.items():set_active(handle,oid in objects_to_keep)
        try:
            bitmap=page.render(scale=cfg.render_scale,crop=(left,H-bottom,W-right,top),fill_color=(0,0,0,0),may_draw_forms=False,draw_annots=False)
            image=bitmap.to_pil().copy();bitmap.close();isolation_passes+=1;return image
        finally:
            for handle in handles.values():set_active(handle,True)
    for k,item in enumerate(items):
        for bg in backgrounds:
            if bg['range'] and bg['range'][0]==k:
                rgba=bg['rgba'];parts.append(f'<section class="background" data-atom="{bg["id"]}" style="background:rgb({rgba[0]},{rgba[1]},{rgba[2]})">');bg_emitted.append(bg['id'])
        attrs=f'data-item="{item["id"]}" data-start="{item["interval"][0]}" data-end="{item["interval"][1]}"'
        if item['kind']=='text':
            parts.append(f'<p {attrs} class="{"auxiliary" if item["auxiliary"] else "prose"}">')
            prev=None
            for line in item['lines']:
                for word in line['words']:
                    if prev and not (unicodedata.east_asian_width(prev[-1]) in 'WF' or unicodedata.east_asian_width(word['text'][0]) in 'WF'):parts.append(' ')
                    gs=word['glyphs'];known=all(g['unicode_known'] for g in gs)
                    ids=' '.join(g['id'] for g in gs);emitted.extend(g['id'] for g in gs)
                    if known:parts.append(f'<span data-atoms="{ids}" class="word">{html.escape(word["text"])}</span>')
                    else:
                        b=word['box'];crop=isolated({g['object_id'] for g in gs},b);name=word['id']+'.png';crop.save(out/name)
                        parts.append(f'<img data-atoms="{ids}" src="{name}" class="unknown-glyph" alt="" title="Unicode mapping unavailable" style="width:{(b[2]-b[0])/body}em;height:{(b[3]-b[1])/body}em">')
                    prev=word['text']
            parts.append('</p>')
        else:
            b=pad(item['box'],cfg.local_object_padding_em*body);keep=set(item['objects'])|{g['object_id'] for g in item['glyphs']};crop=isolated(keep,b);name=item['id']+'.png';crop.save(out/name)
            ids=' '.join(item['atom_ids']);emitted.extend(item['atom_ids'])
            # Native text inside local visuals is not overlaid; unknown glyph
            # mappings must not manufacture selectable success.
            parts.append(f'<figure {attrs} class="local-object {item["kind"]}" data-atoms="{ids}"><div class="object-control" role="button" tabindex="0" onclick="this.parentElement.classList.toggle(\'zoomed\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){{event.preventDefault();this.click()}}" aria-label="Toggle local object enlargement"><img src="{name}" alt="Local original PDF object" style="--natural:{(b[2]-b[0])/body}em"></div></figure>')
        for bg in reversed(backgrounds):
            if bg['range'] and bg['range'][1]==k+1:parts.append('</section>')
    doc='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    *{box-sizing:border-box}body{margin:0;padding:12px;font:20px/1.5 sans-serif;color:#171717;background:white}main{max-width:46em;margin:auto}p{margin:0 0 .7em;overflow-wrap:anywhere}.word{white-space:normal}.unknown-glyph{vertical-align:baseline;object-fit:contain}.background{padding:.5em;margin:.5em 0}.auxiliary,.aux{color:#555;font-size:.75em;border-top:1px solid #ddd}.local-object{margin:1em 0;overflow:auto}.local-object .object-control{font:inherit;line-height:normal;border:0;padding:0;display:block;background:none;max-width:100%;cursor:zoom-in}.local-object img{display:block;width:var(--natural);max-width:100%;height:auto}.local-object.zoomed .object-control{max-width:none}.local-object.zoomed img{max-width:none}nav{font:14px sans-serif;position:sticky;top:0;background:#fff;padding:5px;z-index:1}nav button{font:inherit}section{break-inside:auto}
    </style></head><body><nav><button onclick="document.querySelector('main').style.fontSize='20px'">20 px</button> <button onclick="document.querySelector('main').style.fontSize='28px'">28 px</button></nav><main>'''+''.join(parts)+'</main></body></html>'
    (out/'reader.html').write_text(doc)
    return emitted,bg_emitted,isolation_passes

def run(pdfpath,pageindex,out,cfg):
    out.mkdir(parents=True,exist_ok=True);trace=[];st=time.perf_counter();phases={}
    document=pdfium.PdfDocument(pdfpath);page=document[pageindex];W,H=page.get_size()
    objects,handles,glyphs,body,limitations=native_inventory(page,cfg,trace);phases['extract_seconds']=time.perf_counter()-st;tick=time.perf_counter()
    items,bgs,expected,hard=plan(objects,glyphs,W,H,body,cfg,trace);planned_order=[atom for item in items for atom in item['atom_ids']];phases['plan_seconds']=time.perf_counter()-tick;tick=time.perf_counter()
    emitted,bgemit,isolation_passes=render(page,objects,handles,items,bgs,body,cfg,out);phases['render_output_seconds']=time.perf_counter()-tick
    if emitted!=planned_order:hard.append('renderer_sequence_mismatch')
    if expected and collections.Counter(expected)!=collections.Counter(emitted):hard.append('renderer_ownership_mismatch')
    if collections.Counter(bg['id'] for bg in bgs)!=collections.Counter(bgemit):hard.append('background_emission_mismatch')
    if limitations['annotations'] or limitations['clip_text_objects']:hard.append('unsupported_annotations_or_text_clipping')
    if limitations['forms'] or limitations['unmapped_text_object_chars']:hard.append('unsupported_form_or_unmapped_objects')
    audit=dict(schema=1,input_sha256=hashlib.sha256(pathlib.Path(pdfpath).read_bytes()).hexdigest(),pdfium=str(pdfium.PDFIUM_INFO),pypdfium2=str(pdfium.PYPDFIUM_INFO),page_index=pageindex,config=cfg.json(),page_size=[W,H],body_font_median=body,objects=len(objects),native_character_records=len(glyphs),unknown_unicode_glyphs=sum(not g['unicode_known'] for g in glyphs),backgrounds=len(bgs),text_units=sum(i['kind']=='text' for i in items),islands=sum(i['kind']=='island' for i in items),prose_glyphs=sum(len(i['glyphs']) for i in items if i['kind']=='text'),local_visual_glyphs=sum(len(i['glyphs']) for i in items if i['kind']=='island'),expected_atoms=len(expected),emitted_atoms=len(emitted),exact_once=collections.Counter(expected)==collections.Counter(emitted),renderer_sequence_matches_plan=emitted==planned_order,hard_failures=hard,limitations=limitations,phases=phases,hot_pipeline_seconds=time.perf_counter()-st,semantic_unicode_verification='not performed',reading_order_semantic_verification='not performed',visibility_completeness='not established: occlusion, transparency, clipping, annotation appearances not independently audited')
    audit['isolated_native_object_render_passes']=isolation_passes
    audit['process_peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    audit['process_cpu_seconds']=time.process_time()
    audit['inventory_scope']='native character records and top-level paint objects; not final visible ink instances'
    audit['unprotected_math_characters']=sum(unicodedata.category(g['char'])=='Sm' for item in items if item['kind']=='text' for g in item['glyphs'])
    if audit['unprotected_math_characters']: audit['hard_failures'].append('math_geometry_not_preserved')
    (out/'audit.json').write_text(json.dumps(audit,indent=2));(out/'trace.json').write_text(json.dumps(trace,indent=2));(out/'plan-private.json').write_text(json.dumps(dict(objects=objects,items=items,backgrounds=bgs,expected_order=planned_order),ensure_ascii=False,indent=2))
    print(json.dumps(audit))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('output');ap.add_argument('--page',type=int,default=0);args=ap.parse_args();run(args.pdf,args.page,pathlib.Path(args.output),Config())
