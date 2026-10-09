"""Geometric separators for tightly cropped native units; no content keywords.

Same-source-line gaps preserve the source's sampled ink-to-ink gap within a
bounded prose range. Cross-line Latin word boundaries use the paragraph's
median source gap. Native whitespace records support semantic spaces; inferred
line joins are marked separately. Logical order is supplied by the planner.
"""
import statistics,unicodedata
from ink_config import ReaderLayoutConfig

def separators(sequence,units,assets,glyphs,body,scale,cfg=ReaderLayoutConfig()):
    records=[];samples=[]
    for left,right in zip(sequence,sequence[1:]):
        a,b=units[left],units[right];ga=a['glyphs'];gb=b['glyphs']
        last=max(g['source_index'] for g in ga);first=min(g['source_index'] for g in gb)
        between=[g for g in glyphs if last<g['source_index']<first]
        native_space=any(g['char'].isspace() for g in between)
        lastchar=max(ga,key=lambda g:g['source_index'])['char'];firstchar=min(gb,key=lambda g:g['source_index'])['char']
        east=unicodedata.east_asian_width(lastchar) in 'WF' or unicodedata.east_asian_width(firstchar) in 'WF'
        same=abs(a.get('baseline',statistics.median(g['baseline'] for g in ga))-b.get('baseline',statistics.median(g['baseline'] for g in gb)))<=cfg.same_baseline_em*body
        delta=(assets[right]['asset_pixel_box'][0]-assets[left]['asset_pixel_box'][2])/scale/body
        visible_between=any(not g['char'].isspace() for g in between)
        # A crossing index interval is not silently described as a semantic space.
        semantic='native_whitespace' if native_space else ('inferred_line_join' if not same and not east and not visible_between else 'no_certified_whitespace')
        usable=same and delta>=0 and delta<=cfg.maximum_preserved_gap_em
        if usable and (native_space or delta>=cfg.minimum_word_gap_em) and not east:samples.append(delta)
        records.append(dict(left=left,right=right,same_source_baseline=same,native_whitespace=native_space,intervening_visible_records=visible_between,source_gap_em=delta,semantic_space=semantic,source_gap_usable=usable,east_asian_boundary=east))
    fallback=statistics.median(samples) if samples else cfg.fallback_word_gap_em
    for rec in records:
        if rec['source_gap_usable']:
            gap=rec['source_gap_em'];reason='same-source-line native ink gap'
        elif rec['east_asian_boundary'] and not rec['native_whitespace']:
            gap=0.;reason='unspaced East Asian line join; no inserted word gap'
        else:
            gap=max(cfg.minimum_word_gap_em,min(cfg.maximum_preserved_gap_em,fallback));reason='paragraph source gap median' if samples else 'typed fallback; no source gap sample'
        rec.update(gap_em=gap,reason=reason)
    return records
