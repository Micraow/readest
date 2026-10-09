"""Experimental initial support proposal: nearest projected vertical components.

This diagnostic does not alter native ownership. No strings or font families are
consulted; source pixels must be re-partitioned and replay-verified before use.
"""
def propose_support(box,glyphs,reach,body=None):
    # Same 3-em maximum as the existing bounded native fraction stage.
    # Long separators must not capture the rows above and below them.
    if body is not None and box[2]-box[0]>3.0*body:return None
    candidates=[g for g in glyphs if not g['char'].isspace() and box[0]<=(g['box'][0]+g['box'][2])/2<=box[2] and g['box'][1]<=box[3]+reach and g['box'][3]>=box[1]-reach]
    components=[]
    for g in sorted(candidates,key=lambda g:(g['box'][1],g['box'][3])):
        if not components or g['box'][1]>components[-1]['bottom']:
            components.append(dict(top=g['box'][1],bottom=g['box'][3],glyphs=[g]))
        else:
            components[-1]['bottom']=max(components[-1]['bottom'],g['box'][3]);components[-1]['glyphs'].append(g)
    above=[c for c in components if c['bottom']<box[1]]
    below=[c for c in components if c['top']>box[3]]
    crossing=[c for c in components if c['top']<=box[3] and c['bottom']>=box[1]]
    selected=[]
    if above:selected.append(max(above,key=lambda c:c['bottom']))
    if crossing:selected.extend(crossing)
    elif below:selected.append(min(below,key=lambda c:c['top']))
    # Both sides of the paint must retain native glyph support.
    gs=[g for c in selected for g in c['glyphs']]
    if not any(g['box'][3]<box[1] for g in gs) or not any(g['box'][1]>box[3] for g in gs):return None
    return gs
