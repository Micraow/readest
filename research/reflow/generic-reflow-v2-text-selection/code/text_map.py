"""Unicode agreement eligibility, never a mathematical semantic certificate."""
import collections,math,statistics,unicodedata
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class TextSelectionConfig:
    eligible_native_unit_kind:str='native_word'
    maximum_baseline_delta_em:float=.08
    minimum_size_ratio:float=.86
    maximum_direction_error_radians:float=.00001
    allowed_unicode_categories:tuple[str,...]=('Lu','Ll','Lt','Lm','Lo','Nd','Pc','Pd','Ps','Pe','Pi','Pf','Po','Sc')
    replacement_codepoint:int=0xFFFD
    def json(self):return asdict(self)
def classify_token(token,units,glyphs,events,bridge,cfg=TextSelectionConfig()):
    reasons=[];records=[];pairs=[];members=token.get('members',[])
    if token.get('kind')!='vector':reasons.append('native_image_has_no_verified_text_layer')
    if not members:reasons.append('missing_native_members')
    for member in members:
        unit=units.get(member);converted=bridge.get('converted',{}).get(member)
        if unit is None:reasons.append('missing_native_unit');continue
        if unit['kind']!=cfg.eligible_native_unit_kind:reasons.append('not_ordinary_native_word')
        if converted is None:reasons.append('no_unique_geometry_bridge');continue
        pairs.extend(converted['correspondence']);records.extend(unit['glyphs'])
    for g in records:
        native=glyphs.get(g['id'])
        if native is None or any(native.get(k)!=g.get(k) for k in ['source_index','char','box','unicode_known','map_error']):reasons.append('immutable_source_record_mismatch')
    indices=[g['source_index'] for g in records]
    if any(a>=b for a,b in zip(indices,indices[1:])):reasons.append('nonmonotone_native_character_order')
    source_ids=[g['id'] for g in records];event_ids=[p['native_event'] for p in pairs]
    if not source_ids:reasons.append('no_source_glyphs')
    if len(source_ids)!=len(set(source_ids)) or len(event_ids)!=len(set(event_ids)):reasons.append('duplicate_correspondence')
    if collections.Counter(source_ids)!=collections.Counter(p['source_glyph'] for p in pairs) or collections.Counter(event_ids)!=collections.Counter(token.get('native_event_ids',[])):reasons.append('incomplete_glyph_paint_bijection')
    by_source={p['source_glyph']:p['native_event'] for p in pairs};characters=[]
    for g in records:
        e=events.get(by_source.get(g['id']));char=g['char'];candidate=e.get('unicodeCandidate') if e else None
        if not g.get('unicode_known') or g.get('map_error'):reasons.append('native_unicode_unknown_or_mapping_error')
        if len(char)!=1 or candidate!=char:reasons.append('extractor_unicode_disagreement')
        if len(char)!=1 or ord(char)==cfg.replacement_codepoint or unicodedata.category(char) not in cfg.allowed_unicode_categories:reasons.append('unsupported_unicode_category_or_replacement')
        angle=g.get('native_angle_radians');err=abs(math.remainder(angle,2*math.pi)) if angle is not None and math.isfinite(angle) else math.inf
        if err>cfg.maximum_direction_error_radians:reasons.append('nonhorizontal_or_unknown_native_direction')
        if e:characters.append({'source_glyph':g['id'],'source_index':g['source_index'],'native_event':e['id'],'text':char,'box_pdf':g['box']})
    sizes=[g['size'] for g in records];baselines=[g['baseline'] for g in records]
    if sizes:
        if min(sizes)<=0 or min(sizes)<max(sizes)*cfg.minimum_size_ratio:reasons.append('mixed_or_invalid_glyph_sizes')
        elif max(baselines)-min(baselines)>statistics.median(sizes)*cfg.maximum_baseline_delta_em:reasons.append('multibaseline_script_or_ambiguous_word')
    reasons=sorted(set(reasons));return {'id':token['id'],'eligible':not reasons,'reasons':reasons,'text':''.join(c['text'] for c in characters) if not reasons else None,'characters':characters if not reasons else [],'semantic_unicode_certified':False,'evidence':'exact two-extractor scalar agreement plus existing unique geometry correspondence' if not reasons else 'refused'}
def build(reader,plan,capture,bridge,cfg=TextSelectionConfig()):
    units={u['id']:u for u in plan['units']};glyphs={g['id']:g for g in plan['glyphs']};events={e['id']:e for e in capture};blocks=[];reasons=collections.Counter();accepted=0;refused=0
    for block in reader['blocks']:
        tokens=[]
        for token in block['tokens']:
            row=classify_token(token,units,glyphs,events,bridge,cfg);tokens.append(row);accepted+=row['eligible'];refused+=not row['eligible'];reasons.update(row['reasons'])
        blocks.append({'tokens':tokens,'complete_ordinary_text_eligible':all(t['eligible'] for t in tokens),'space_policy':'one explicit separator for a positive reader token gap; source hyphens retained'})
    return {'config':cfg.json(),'blocks':blocks,'summary':{'eligible_tokens':accepted,'refused_tokens':refused,'refusal_reasons':dict(reasons),'semantic_unicode_certified':False,'browser_selection_verified':False,'copy_across_refused_content_allowed':False}}
