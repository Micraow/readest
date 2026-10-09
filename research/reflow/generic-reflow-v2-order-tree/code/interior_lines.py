"""Conservative displaced-baseline association shared by source-line planners."""

def union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]

def associate_interior_lines(lines,body,cfg):
    """Join a displaced native baseline only with a unique enclosing source line.

    Uses geometry and strictly nested native intervals, never symbol/font names.
    Ambiguous hosts remain separate and the order tree can still refuse them.
    """
    def indexes(line):
        return [g['source_index'] for u in line['units'] for g in u['glyphs'] if g.get('native_object_ink_observed',True)]
    proposals=[];trace=[]
    for line in lines:
        ix=indexes(line);b=line['box'];hosts=[]
        if not ix or b[2]-b[0]>cfg.inline_max_width_em*body or b[3]-b[1]>cfg.inline_max_height_em*body:continue
        for host in lines:
            if host is line:continue
            hi=indexes(host);hb=host['box']
            if hi and min(hi)<min(ix) and max(ix)<max(hi) and hb[0]<=b[0] and b[2]<=hb[2] and min(b[3],hb[3])>max(b[1],hb[1]):hosts.append(host)
        if hosts:
            trace.append(dict(rule='strict_native_interval_interior_line',units=[u['id'] for u in line['units']],host_candidates=[[u['id'] for u in h['units']] for h in hosts],accepted=len(hosts)==1))
        if len(hosts)==1:proposals.append((line,hosts[0]))
    # Avoid cascading associations whose destination would itself disappear.
    sources={id(line) for line,host in proposals};removed=set()
    for line,host in proposals:
        if id(host) in sources:continue
        host['units'].extend(line['units']);host['box']=union([host['box'],line['box']]);removed.add(id(line))
    return [line for line in lines if id(line) not in removed],trace

def associate_bridged_lines(lines,body,cfg):
    """A bounded native interval may bridge two fragments of one baseline.

    Requires a unique left/right pair, source-index order, disjoint horizontal
    boxes and vertical overlap. Conflicting proposals remain unresolved.
    """
    def interval(line):
        ix=[g['source_index'] for u in line['units'] for g in u['glyphs'] if g.get('native_object_ink_observed',True)]
        return (min(ix),max(ix)) if ix else None
    intervals={id(line):interval(line) for line in lines};proposals=[];trace=[]
    def overlaps(a,b):return min(a[3],b[3])>max(a[1],b[1])
    for middle in lines:
        b=middle['box'];mi=intervals[id(middle)]
        if not mi or b[2]-b[0]>cfg.inline_max_width_em*body or b[3]-b[1]>cfg.inline_max_height_em*body:continue
        left=[];right=[]
        for other in lines:
            oi=intervals[id(other)];ob=other['box']
            if other is middle or not oi or not overlaps(b,ob):continue
            if 0<=b[0]-ob[2]<=cfg.horizontal_chunk_gap_em*body and oi[1]<mi[0]:left.append(other)
            if 0<=ob[0]-b[2]<=cfg.horizontal_chunk_gap_em*body and mi[1]<oi[0]:right.append(other)
        pairs=[(l,r) for l in left for r in right if abs(l['baseline']-r['baseline'])<=cfg.baseline_tolerance_em*body]
        if pairs:
            trace.append(dict(rule='unique_native_interval_line_bridge',units=[u['id'] for u in middle['units']],candidate_pairs=len(pairs),accepted=False))
            if len(pairs)==1:proposals.append((middle,*pairs[0],trace[-1]))
    counts={}
    for middle,left,right,t in proposals:
        for line in [middle,left,right]:counts[id(line)]=counts.get(id(line),0)+1
    removed=set()
    for middle,left,right,t in proposals:
        if any(counts[id(line)]>1 for line in [middle,left,right]):continue
        left['units'].extend(middle['units']+right['units']);left['box']=union([left['box'],middle['box'],right['box']]);removed.update([id(middle),id(right)]);t['accepted']=True
    return [line for line in lines if id(line) not in removed],trace
