"""Original geometry/font/context features. No token identities or generated text."""
import json,pathlib,re,math,collections
import fitz,numpy as np
B=pathlib.Path(__file__).resolve().parents[1]
LABELS=['text','formula','number','header','footer','footnote','paragraph_title','doc_title','figure_title','table_title','image','table','reference']
ROLES={1:3,2:2,3:1,4:0,5:2,6:2,7:3,8:3,9:3,10:0,11:3}
FEATURE_NAMES=['x','y','w','h','log_chars','font_relative','font_spread','math_font','digit_fraction','alpha_fraction','operator_fraction','bracket_fraction','space_fraction','log_words','log_aspect','edge_y','up_gap','down_gap','same_row_gap','same_row_alpha','numeric_identifier','native_line_fraction']+['pp_'+s for s in LABELS]
def inside(x,y,b):return b[0]<=x<=b[2] and b[1]<=y<=b[3]
def page_features(row):
 name=row['file_name'][:-4];folder=B/'data'/name;page=fitz.open(folder/'source.pdf')[0];w,h=page.rect.width,page.rect.height;raw=page.get_text('rawdict');lines=[]
 for bi,block in enumerate(raw['blocks']):
  for li,line in enumerate(block.get('lines',[])):
   gs=[];text=''
   for span in line['spans']:
    for ci,g in enumerate(span['chars']):
     text+=g['c']
     if not g['c'].strip():continue
     box=fitz.Rect(g['bbox'])*page.rotation_matrix;gs.append({'c':g['c'],'x':(box.x0+box.x1)/2/w,'y':(box.y0+box.y1)/2/h,'font':span['font'],'size':span['size']})
   if not gs:continue
   box=fitz.Rect(line['bbox'])*page.rotation_matrix;lines.append({'id':f'{bi}:{li}','bbox':[box.x0/w,box.y0/h,box.x1/w,box.y1/h],'glyphs':gs,'text':text})
 body=float(np.median([g['size'] for l in lines for g in l['glyphs']])) if lines else 1
 predictions=json.loads((folder/'detector.json').read_text())['res']['boxes'];annotations=json.loads((folder/'annotations.json').read_text())['annotations'];anns=[{'role':ROLES[a['category_id']],'box':[a['bbox'][0]/row['width'],a['bbox'][1]/row['height'],(a['bbox'][0]+a['bbox'][2])/row['width'],(a['bbox'][1]+a['bbox'][3])/row['height']],'id':a['id'],'category':a['category_id']} for a in annotations]
 dw,dh=page.rect.width*4,page.rect.height*4;features=[];targets=[];base=[];counts=[];support=collections.Counter();ground=collections.Counter();unknown=0
 for line in lines:
  gs=line['glyphs'];n=len(gs);text=line['text'];a,y,c,d=line['bbox'];sizes=[g['size'] for g in gs];maths=sum(bool(re.search('CMMI|CMSY|CMEX|Math|Symbol|STIX',g['font'],re.I)) for g in gs)/n;digits=sum(g['c'].isdigit() for g in gs)/n;alpha=sum(g['c'].isalpha() for g in gs)/n;ops=sum(g['c'] in '=+−×·∑∫<>≤≥' for g in gs)/n;brackets=sum(g['c'] in '()[]{}' for g in gs)/n;nums=bool(re.fullmatch(r'\(?\d+(?:\.\d+)*(?:[a-z])?\)?',text.strip()));up=down=20.;samegap=20.;samealpha=0
  for other in lines:
   if other is line:continue
   A,Y,C,D=other['bbox'];xo=min(c,C)-max(a,A);yo=min(d,D)-max(y,Y);og=other['glyphs'];na=sum(g['c'].isalpha() for g in og)
   if xo>0 and na>=10:
    if D<=y:up=min(up,(y-D)*h/body)
    if Y>=d:down=min(down,(Y-d)*h/body)
   if yo>.5*min(d-y,D-Y) and na>=3:
    gap=max(a-C,A-c,0)*w/body
    if gap<samegap:samegap=gap;samealpha=na
  det={k:0. for k in LABELS}
  for p in predictions:
   if p['label'] not in det:continue
   box=[p['coordinate'][0]/dw,p['coordinate'][1]/dh,p['coordinate'][2]/dw,p['coordinate'][3]/dh];fraction=sum(inside(g['x'],g['y'],box) for g in gs)/n;det[p['label']]=max(det[p['label']],p['score']*fraction)
  # Fixed geometry/PP-label comparator. Page-edge numbers need a detached source gap.
  nearest=min(up,down);same_prose=samegap<=6 and samealpha>=3
  if max(det['header'],det['footer'],det['footnote'])>=.5 or nums and (y<.1 or d>.9) and nearest>1.5:baseline=2
  elif max(det['paragraph_title'],det['doc_title'],det['figure_title'],det['table_title'],det['image'],det['table'])>=.6:baseline=3
  elif det['formula']>=.5 and (maths>.4 or alpha<.35 or ops>.1) and not same_prose:baseline=1
  elif det['text']>=.6 or det['reference']>=.6 or same_prose and det['formula']>=.5:baseline=0
  else:baseline=-1
  feature=[(a+c)/2,(y+d)/2,c-a,d-y,math.log1p(n)/5,np.median(sizes)/body,np.std(sizes)/body,maths,digits,alpha,ops,brackets,text.count(' ')/max(1,len(text)),math.log1p(len(text.split()))/4,math.log(max(1e-3,(c-a)/(d-y)))/5,min(y,1-d),min(up,20)/20,min(down,20)/20,min(samegap,20)/20,min(samealpha,80)/80,float(nums),n/max(1,sum(len(z['glyphs']) for z in lines))]+[det[k] for k in LABELS]
  glyphroles=[]
  for g in gs:
   matches=[an for an in anns if inside(g['x'],g['y'],an['box'])];roles={an['role'] for an in matches}
   for an in matches:support[an['id']]+=1
   role=next(iter(roles)) if len(roles)==1 else -1;glyphroles.append(role)
   if role>=0:ground[role]+=1
   else:unknown+=1
  counter=collections.Counter(glyphroles);target,count=counter.most_common(1)[0];target=target if target>=0 and count/n>=.9 else -1
  features.append(feature);targets.append(target);base.append(baseline);counts.append({'source_line':line['id'],'glyphs':n,'glyph_role_counts':dict(counter)})
 # Annotation objects without native character support stay in the denominator.
 objects=[{'id':a['id'],'role':a['role'],'category':a['category'],'native_glyph_support':support[a['id']]} for a in anns]
 return np.array(features,np.float64).reshape((-1,len(FEATURE_NAMES))),np.array(targets),np.array(base),{'rows':counts,'objects':objects,'all_native_glyphs':sum(ground.values())+unknown,'unknown_role_glyphs':unknown,'body_font_size_points':body}
