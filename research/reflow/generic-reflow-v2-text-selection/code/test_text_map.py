"""Original known-text positives and intentionally wrong Unicode/geometry negatives."""
import copy,json,pathlib,sys
from text_map import classify_token
cases=[]
def sample(text='Readable',size=10):
 gs=[{'id':'g'+str(i),'source_index':i,'char':c,'box':[i*size*.5,0,(i+1)*size*.5,size],'baseline':size,'size':size,'unicode_known':True,'map_error':False,'native_angle_radians':0} for i,c in enumerate(text)];es={i:{'id':i,'unicodeCandidate':c} for i,c in enumerate(text)};unit={'kind':'native_word','glyphs':gs};token={'id':'w','members':['w'],'kind':'vector','native_event_ids':list(es)};bridge={'converted':{'w':{'correspondence':[{'source_glyph':g['id'],'native_event':i} for i,g in enumerate(gs)]}}};return [token,{'w':unit},{g['id']:copy.deepcopy(g) for g in gs},es,bridge]
def case(name,edit,expected,reason=None,text='Readable',size=10):
 a=sample(text,size);edit(a);r=classify_token(*a);assert r['eligible']==expected,(name,r)
 if reason:assert reason in r['reasons'],(name,r)
 if expected:assert r['text']==text and not r['semantic_unicode_certified']
 cases.append({'name':name,'passed':True,'eligible':r['eligible'],'reasons':r['reasons']})
case('known Latin',lambda a:None,True)
case('small multi-character metadata',lambda a:None,True,text='metadata',size=4)
case('native Chinese characters',lambda a:None,True,text='普通正文')
case('literal source hyphen',lambda a:None,True,text='hyphen-')
case('parenthesized retained source hyphen',lambda a:None,True,text='(ab-')
case('punctuation',lambda a:None,True,text='(2),')
case('wrong matching-length Unicode',lambda a:a[3][1].update(unicodeCandidate='X'),False,'extractor_unicode_disagreement')
case('unknown native Unicode',lambda a:(a[1]['w']['glyphs'][0].update(unicode_known=False),a[2]['g0'].update(unicode_known=False)),False,'native_unicode_unknown_or_mapping_error')
case('equal private use is not enough',lambda a:None,False,'unsupported_unicode_category_or_replacement',text='\ue043')
case('equal replacement is not enough',lambda a:None,False,'unsupported_unicode_category_or_replacement',text='\ufffd')
case('control scalar',lambda a:None,False,'unsupported_unicode_category_or_replacement',text='\x01')
case('math operator',lambda a:None,False,'unsupported_unicode_category_or_replacement',text='=')
case('superscript Unicode number',lambda a:None,False,'unsupported_unicode_category_or_replacement',text='²')
case('native ligature disagreement',lambda a:a[3][0].update(unicodeCandidate='fi'),False,'extractor_unicode_disagreement',text='ﬁ')
case('small script',lambda a:a[1]['w']['glyphs'][1].update(size=6),False,'mixed_or_invalid_glyph_sizes')
case('multi baseline',lambda a:a[1]['w']['glyphs'][1].update(baseline=13),False,'multibaseline_script_or_ambiguous_word')
case('rotation',lambda a:a[1]['w']['glyphs'][1].update(native_angle_radians=1.57079632679),False,'nonhorizontal_or_unknown_native_direction')
case('incomplete paint',lambda a:a[0]['native_event_ids'].pop(),False,'incomplete_glyph_paint_bijection')
case('duplicate event',lambda a:a[4]['converted']['w']['correspondence'][1].update(native_event=0),False,'duplicate_correspondence')
case('immutable mapping corruption',lambda a:a[1]['w']['glyphs'][0].update(char='X'),False,'immutable_source_record_mismatch')
case('image formula',lambda a:a[0].update(kind='native_image'),False,'native_image_has_no_verified_text_layer')
case('nonword native group',lambda a:a[1]['w'].update(kind='inline_native_group'),False,'not_ordinary_native_word')
case('changed logical character order',lambda a:a[1]['w']['glyphs'].reverse(),False,'nonmonotone_native_character_order')
for field in ['size','baseline']:
    for value in [float('nan'),float('inf'),None]:
        case(f'invalid {field} {value}',lambda a,f=field,v=value:(a[1]['w']['glyphs'][0].update({f:v}),a[2]['g0'].update({f:v})),False,'nonfinite_or_missing_native_metrics')
case('nonfinite glyph box',lambda a:(a[1]['w']['glyphs'][0].update(box=[0,0,float('inf'),10]),a[2]['g0'].update(box=[0,0,float('inf'),10])),False,'invalid_or_missing_glyph_geometry')
case('unknown null character',lambda a:(a[1]['w']['glyphs'][0].update(char=None),a[2]['g0'].update(char=None)),False,'extractor_unicode_disagreement')
case('changed source metric',lambda a:a[1]['w']['glyphs'][0].update(baseline=10.001),False,'immutable_source_record_mismatch')
case('Arabic needs directional proof',lambda a:None,False,'unsupported_bidirectional_text',text='كتاب')
case('Hebrew needs directional proof',lambda a:None,False,'unsupported_bidirectional_text',text='שלום')
case('Arabic directional number',lambda a:None,False,'unsupported_bidirectional_text',text='١')
p=pathlib.Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False);(p/'result.json').write_text(json.dumps({'cases':cases,'all_passed':True,'semantic_certification_claimed':False},indent=2));print(json.dumps({'cases':len(cases),'all_passed':True}))
