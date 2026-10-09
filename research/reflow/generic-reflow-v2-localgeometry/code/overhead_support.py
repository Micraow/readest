"""Opt-in geometry proposal for an already joined shoulder/overhead-paint unit.

Preserves the horizontal placement of native content beneath an attached stroke.
It does not recognize a Unicode symbol or assign mathematical meaning. A bounded
native-interval closure and exact replay are required before accepting any seed.
"""
def seeds(units,objects):
    objects={o['id']:o for o in objects};out=[]
    for unit in units:
        if unit.get('kind')!='inline_native_group' or not unit.get('glyphs'):continue
        for oid in unit.get('objects',[]):
            paint=objects[oid]
            if not paint.get('horizontal_stroke'):continue
            b=paint['box']
            # The existing owner must contain a real glyph crossing the left
            # end and extending downward. Plain underlines have no such anchor.
            shoulders=[g for g in unit['glyphs'] if g['box'][0]<b[0]<g['box'][2] and g['box'][1]<=b[3] and g['box'][3]>b[3]]
            if not shoulders:continue
            bottom=max(g['box'][3] for g in shoulders);neighbors=[]
            for other in units:
                if other['id']==unit['id'] or other.get('kind')!='native_word':continue
                inside=[g for g in other['glyphs'] if b[0]<=(g['box'][0]+g['box'][2])/2<=b[2] and b[3]<=g['box'][1] and g['box'][3]<=bottom]
                if inside:neighbors.append(other['id'])
            if neighbors:out.append(set([unit['id'],*neighbors]))
    return out
