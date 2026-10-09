"""Safe-cut reading tree over pre-associated blocks; role priors stay separate."""
from dataclasses import dataclass,asdict
from collections import Counter

@dataclass(frozen=True)
class OrderConfig:
    minimum_column_gap_em: float = 1.5
    minimum_band_gap_em: float = 0.6
    same_row_overlap_tolerance_em: float = 0.15
    maximum_depth: int = 32
    def json(self):return asdict(self)

class AmbiguousOrder(ValueError):pass

def bounds(blocks):return [min(b['box'][0] for b in blocks),min(b['box'][1] for b in blocks),max(b['box'][2] for b in blocks),max(b['box'][3] for b in blocks)]

def gaps(blocks,axis,minimum):
    intervals=sorted((b['box'][axis],b['box'][axis+2]) for b in blocks);right=intervals[0][1];out=[]
    for left,end in intervals[1:]:
        if left-right>=minimum:out.append((right,left))
        right=max(right,end)
    return out

def flatten(node):
    if node['kind']=='leaf':return [node['id']]
    return [uid for child in node['children'] for uid in flatten(child)]

def build_tree(blocks,body=10,cfg=OrderConfig()):
    ids=[b['id'] for b in blocks]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate input leaf identity')
    if not blocks:raise ValueError('empty region')
    trace=[]
    def rec(bs,depth=0):
        if depth>cfg.maximum_depth:raise AmbiguousOrder('reading tree depth budget')
        if len(bs)==1:return dict(kind='leaf',**bs[0])
        for axis,minimum,kind in [(0,cfg.minimum_column_gap_em*body,'columns'),(1,cfg.minimum_band_gap_em*body,'bands')]:
            found=gaps(bs,axis,minimum)
            if found:
                # All true empty strips are boundaries, not threshold-tuned winners.
                selected=found if axis==0 else found[:1]
                # A top spanning block can hide a valid gutter below it. Split
                # one horizontal barrier, then retry columns; splitting every
                # paragraph gap now would interleave subsequent column rows.
                cuts=[(a+b)/2 for a,b in selected];groups=[[] for _ in range(len(cuts)+1)]
                for block in bs:
                    bucket=sum(block['box'][axis]>=c for c in cuts);groups[bucket].append(block)
                trace.append(dict(rule='empty_projection_cut',axis=axis,kind=kind,gaps=selected,other_candidate_gaps=found,leaf_ids=[b['id'] for b in bs]))
                return dict(kind=kind,box=bounds(bs),children=[rec(g,depth+1) for g in groups if g])
        ordered=sorted(bs,key=lambda b:(b['box'][1],b['box'][0]));tolerance=cfg.same_row_overlap_tolerance_em*body
        conflicts=[]
        for i,a in enumerate(ordered):
            for b in ordered[i+1:]:
                if min(a['box'][3],b['box'][3])-max(a['box'][1],b['box'][1])>tolerance:conflicts.append([a['id'],b['id']])
        if conflicts:
            trace.append(dict(rule='no_safe_cut_with_overlapping_blocks',accepted=False,conflicts=conflicts));raise AmbiguousOrder({'reason':'no safe region cut','conflicts':conflicts,'trace':trace})
        trace.append(dict(rule='single_column_vertical_sequence',accepted=True,leaf_ids=[b['id'] for b in ordered]))
        return dict(kind='column',box=bounds(bs),children=[rec([b],depth+1) for b in ordered])
    tree=rec(blocks);sequence=flatten(tree)
    if Counter(sequence)!=Counter(ids):raise AssertionError('tree leaf conservation')
    cursor=0
    def annotate(node):
        nonlocal cursor
        start=cursor
        if node['kind']=='leaf':cursor+=1
        else:
            for child in node['children']:annotate(child)
        node['output_interval']=[start,cursor]
    annotate(tree)
    return dict(config=cfg.json(),tree=tree,sequence=sequence,trace=trace,leaf_bijection=True,semantic_order_verified=False)
