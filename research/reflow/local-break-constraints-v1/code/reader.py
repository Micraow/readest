"""Shared-atlas source-word renderer; source page is optional comparison only."""
import base64,html,io,json,math,pathlib,collections
from PIL import Image
E=html.escape
CSS='''*{box-sizing:border-box}body{margin:0;background:#eef1f4;color:#173047;font-family:Arial,sans-serif}.shell{width:var(--reader-width,390px);max-width:100%;margin:auto;background:white;min-height:100vh;padding:14px}header{position:sticky;top:0;background:#fffffff5;z-index:2;padding:8px 0;border-bottom:1px solid #d4dce4}h1{font-size:17px;margin:0 0 8px}button,select{font:13px Arial;padding:6px 8px;background:white;border:1px solid #93a7b8;border-radius:5px;color:#173047}.notice{font:12px/1.5 Arial;color:#506170}.reading{font-size:var(--reader-font,20px);font-family:serif;line-height:1.5;color:#111}.flow{margin:0 0 .8em;line-height:1.5}.heading{font-weight:bold;margin-top:1em}.unit{display:inline-block;position:relative;vertical-align:baseline;text-decoration:none;color:inherit}.unit .texture{position:absolute;top:0;display:block;background-repeat:no-repeat}.unit:focus-visible{outline:2px solid #176bc0}.object,.wide-local{max-width:100%;overflow-x:auto;overflow-y:hidden;margin:8px 0}.object .unit,.wide-local .unit{display:block;flex:none}.equation-row{display:flex;align-items:center;gap:.5em;max-width:100%;margin:.8em 0}.equation-row .object{flex:1;min-width:0;margin:0}.equation-number{flex:none}.note-label{font:11px Arial;color:#647686;margin:5px 0}.page-separator{font:12px Arial;color:#647686;margin:20px 0 8px}.source-definitions{position:absolute;width:0;height:0;overflow:hidden}dialog{width:min(95vw,1100px);height:90vh;border:1px solid #789;border-radius:8px;padding:12px}dialog::backdrop{background:#203244aa}.source-scroll{height:calc(100% - 55px);overflow:auto;background:#dce4eb}.source-plane{position:relative;width:100%;min-width:320px}.source-plane img{display:block;width:100%}.mark{position:absolute;border:2px solid #176bc0;pointer-events:none}.source-status{font:12px Arial}.auxiliary{margin-top:1.2em;border-top:1px solid #bdcbd5}.rejected{font:14px/1.5 Arial;padding:12px;background:#fff1da}.atlas{display:none}'''
def uri(im):
 b=io.BytesIO();im.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
def pack(atoms):
 width=max(2048,max([a['rgba'].width+8 for a in atoms] or [0]));x=y=4;rowh=0
 for a in atoms:
  im=a['rgba']
  if x+im.width+4>width:x=4;y+=rowh+8;rowh=0
  a['atlas_box']=[x,y,im.width,im.height];x+=im.width+8;rowh=max(rowh,im.height)
 atlas=Image.new('RGBA',(width,y+rowh+4),(255,255,255,0))
 for a in atoms:atlas.paste(a['rgba'],tuple(a['atlas_box'][:2]));a['atlas_size']=[atlas.width,atlas.height]
 return atlas

def unit(a,key):
 x,y,w,h=a['atlas_box'];attrs=f'data-unit="{E(key+"-"+a["id"])}" data-page="{E(key)}" data-source-box="{E(json.dumps(a["source_box"]))}"';style=f'width:{a["advance_em"]:.7f}em;height:{a["height_em"]:.7f}em;vertical-align:{-a["descent_em"]:.7f}em';svgstyle=f'left:{a["left_em"]:.7f}em;width:{a["image_width_em"]:.7f}em;height:{a["height_em"]:.7f}em;background-size:{a["atlas_size"][0]/4/a["font_reference"]:.7f}em {a["atlas_size"][1]/4/a["font_reference"]:.7f}em;background-position:{-x/4/a["font_reference"]:.7f}em {-y/4/a["font_reference"]:.7f}em'
 return f'<a href="#source" class="unit" {attrs} style="{style}" aria-label="查看这个原字形片段的出处"><span class="texture texture-{E(key)}" style="{svgstyle}"></span></a>'
def events(atoms,state):
 W=state['size'][0]/4;H=state['size'][1]/4;cols=state['columns'];spans={};items=[];numbers={a['number']:a['formula_dummy']+len(state['words']) for a in state['associations']};consumed=set();groupnumbers=collections.defaultdict(list)
 for a in atoms:
  for w in a['number_words']:
   for formula in atoms:
    if numbers[w] in formula.get('dummy_ids',[]):groupnumbers[formula['id']].append(a);consumed.add(a['id'])
 for a in atoms:
  if a['id'] in consumed:continue
  b=a['source_box'];lane=0 if cols['count']==1 else (-1 if -1 in a['lanes'] or b[0]<cols['cut']-.15*W and b[2]>cols['cut']+.15*W else int((b[0]+b[2])/2>=cols['cut']));role=a['parent_role'];aux=role in {'header','footer','number','footnote','aside_text','header_image','footer_image'} or (len(a['words'])==1 and a['native_text'].strip().isdigit() and b[1]>.9*H and .3*W<(b[0]+b[2])/2<.7*W)
  item={'atom':a,'lane':lane,'aux':aux,'number_atoms':groupnumbers[a['id']]};items.append(item)
  if lane==-1 and not aux:spans.setdefault(a['parent'],[]).append(b)
 bands=[(min(b[1] for b in bs),max(b[3] for b in bs)) for bs in spans.values()];bands.sort()
 for e in items:
  a=e['atom'];y=a['sort_y'];e['order']=(1 if e['aux'] else 0,sum(end<=a['source_box'][1] for start,end in bands),2 if e['lane']==-1 else 0,e['lane'],y,a['source_box'][0])
 return sorted(items,key=lambda e:e['order'])

def render(pages,width=390,font=20,interactive=True):
 defs=[];parts=[];sources={};layout=[];deferred_aux=[]
 for p in pages:
  key=p['key'];state=p['state'];atoms=p['atoms'];atlas=p.get('atlas') or pack(atoms);p['atlas']=atlas;defs.append('.texture-'+key+'{background-image:url("'+uri(atlas)+'")}');source=Image.fromarray(state['rgb']);sources[key]={'image':uri(source),'width':source.width/4,'height':source.height/4};openflow=None;last=None;auxshown=False
  for event in events(atoms,state):
   a=event['atom']
   if event['aux']:deferred_aux.append((key,a));continue
   u=unit(a,key);protected=a['role']=='object' or a['display_math'] or a['parent_role'] in {'image','chart','table','algorithm','graphic'};wide=a['advance_em']*font>width-28;whole=area_fraction(a['source_box'],state['size'])>.8 and (not state['words'] or a['parent_role'] not in {'image','table','chart','algorithm'})
   if whole:
    if openflow:parts.append('</div>');openflow=None
    parts.append('<p class="rejected">本页局部依赖范围过大，未达到正文重排要求。原版可从对照入口查看。</p>');layout.append({'id':a['id'],'status':'primary_reading_rejected','source_ink':a['source_ink']});continue
   if event['aux'] and not auxshown:
    if openflow:parts.append('</div>');openflow=None
    parts.append('<p class="note-label auxiliary">页边信息与脚注</p>');auxshown=True
   if protected or wide:
    if openflow:parts.append('</div>');openflow=None
    if event['number_atoms']:
     parts.append('<div class="equation-row"><div class="object">'+u+'</div><div class="equation-number">'+''.join(unit(n,key) for n in event['number_atoms'])+'</div></div>')
     for number in event['number_atoms']:layout.append({'key':key,'id':number['id'],'status':'shown_equation_identifier','source_ink':number['source_ink']})
    else:parts.append('<div class="'+('object' if protected else 'wide-local')+'">'+u+'</div>')
    parts.append('<p class="note-label">局部原字形，宽对象可左右查看</p>');last=None
   else:
    pid=a['parent']
    continuity=last is not None and abs(last['font_reference']-a['font_reference'])<.05*a['font_reference'] and (abs(last['sort_y']-a['sort_y'])<.2*a['font_reference'] or (set(last['native_blocks'])&set(a['native_blocks']) and 0<a['sort_y']-last['sort_y']<1.8*a['font_reference']))
    if openflow!=pid and not continuity:
     if openflow:parts.append('</div>')
     parts.append('<div class="flow '+('heading' if a['parent_role'] in {'paragraph_title','doc_title'} else '')+'" data-parent="'+E(key+'-'+pid)+'">');openflow=pid;last=None
    if last:
     # Keep uncertain source hyphens visible, without forcing their old line break.
     same_row=abs(a['sort_y']-last['sort_y'])<.2*a['font_reference'];gap=a['source_box'][0]-last['source_box'][2];join=same_row and gap<.12*a['font_reference'] or last['native_text'].endswith('-');cjk=last['native_text'] and a['native_text'] and any('\u3400'<=c<='\u9fff' for c in last['native_text'][-1:]+a['native_text'][:1]);parts.append('<wbr>' if join or cjk else ' ')
    parts.append(u);last=a
   layout.append({'id':a['id'],'parent':a['parent'],'advance_em':a['advance_em'],'wide':wide,'protected':protected,'source_ink':a['source_ink'],'status':'shown'})
  if openflow:parts.append('</div>')
 if deferred_aux:
  parts.append('<section class="auxiliary"><p class="note-label">页边信息与脚注</p>');previous=None
  for key,a in deferred_aux:
   parent=(key,a['parent'])
   if previous!=parent:
    if previous:parts.append('</div>')
    parts.append('<div class="flow">');previous=parent
   else:parts.append(' ')
   parts.append(unit(a,key));layout.append({'id':a['id'],'status':'shown_auxiliary','source_ink':a['source_ink']})
  if previous:parts.append('</div>')
  parts.append('</section>')
 payload=json.dumps(sources,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c');toolbar='<header><h1>原字形流式试读</h1><button data-font="20">20 px</button> <button data-font="28">28 px</button> <select id="width" aria-label="阅读宽度"><option>320</option><option selected>390</option><option>430</option></select> <button id="original">原页对照</button></header><p class="notice">实验候选：正文按可用宽度换行；数学和图表只保留必要局部。关系与完整性仍需核对。图像文字的选择、搜索与无障碍尚未实现。</p>' if interactive else ''
 doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'none\'; object-src \'none\'; base-uri \'none\'"><style>'+CSS+'</style><body style="--reader-width:'+str(width)+'px;--reader-font:'+str(font)+'px"><style>'+''.join(defs)+'</style><main class="shell">'+toolbar+'<div class="reading">'+''.join(parts)+'</div></main>'
 if interactive:doc+='<dialog id="source"><button id="close">返回阅读</button> <button id="zoom">放大/适应</button><p class="source-status"></p><div class="source-scroll"><div class="source-plane"><img alt="原页对照"><div class="mark"></div></div></div></dialog><script id="source-data" type="application/json">'+payload+'</script><script>'+JS+'</script>'
 return doc+'</body></html>',layout

def area_fraction(b,size):return (b[2]-b[0])*(b[3]-b[1])/(size[0]*size[1]/16)
JS='''const q=s=>document.querySelector(s),sources=JSON.parse(q('#source-data').textContent),dialog=q('#source');let opener=null,current=Object.keys(sources)[0];function show(key,box,button){current=key;opener=button;const p=sources[key];q('.source-plane img').src=p.image;q('.source-plane').style.width='100%';const mark=q('.mark');mark.hidden=!box;if(box)Object.assign(mark.style,{left:100*box[0]/p.width+'%',top:100*box[1]/p.height+'%',width:100*(box[2]-box[0])/p.width+'%',height:100*(box[3]-box[1])/p.height+'%'});q('.source-status').textContent='原页 '+key+'，蓝框为当前片段';dialog.showModal();}document.querySelectorAll('[data-unit]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();show(a.dataset.page,JSON.parse(a.dataset.sourceBox),a);}));function localOverflow(){document.querySelectorAll('[data-overflow-wrapper]').forEach(w=>{const a=w.firstElementChild;w.replaceWith(a);});document.querySelectorAll('.flow > .unit').forEach(a=>{if(a.getBoundingClientRect().width>a.parentElement.clientWidth+.5){const wrapper=document.createElement('div');wrapper.className='wide-local';wrapper.dataset.overflowWrapper='true';a.replaceWith(wrapper);wrapper.append(a);}});}document.querySelectorAll('[data-font]').forEach(b=>b.addEventListener('click',()=>{document.body.style.setProperty('--reader-font',b.dataset.font+'px');localOverflow();}));q('#width').addEventListener('change',e=>{document.body.style.setProperty('--reader-width',e.target.value+'px');localOverflow();});window.addEventListener('resize',localOverflow);localOverflow();q('#original').addEventListener('click',e=>show(current,null,e.currentTarget));q('#close').addEventListener('click',()=>dialog.close());q('#zoom').addEventListener('click',()=>q('.source-plane').style.width=q('.source-plane').style.width==='200%'?'100%':'200%');dialog.addEventListener('close',()=>opener?.focus());window.localBreakReaderReady=true;'''
