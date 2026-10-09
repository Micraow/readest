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

