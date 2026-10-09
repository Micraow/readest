"""Infer repeated native line leading per geometric column, not from font size."""
import collections,statistics
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class ParagraphGeometryConfig:
    maximum_font_ratio:float=1.12
    aligned_left_tolerance_em:float=.3
    minimum_row_width_em:float=8.
    minimum_leading_em:float=.7
    maximum_leading_em:float=3.
    leading_cluster_tolerance_em:float=.12
    minimum_repeated_pairs:int=2
    accepted_gap_ratio:float=1.2
    def json(self):return asdict(self)
def annotate(items,units,body):
    for item in items:
        sizes=[round(g['size'],3) for uid in item['source_unit_ids'] for g in units[uid]['glyphs'] if g.get('native_object_ink_observed',True) and g['size']>0];item['native_dominant_font']=collections.Counter(sizes).most_common(1)[0][0] if sizes else body

def estimate(items,body,cfg=ParagraphGeometryConfig()):
    bypath=collections.defaultdict(list);result={}
    for it in items:
        if it['kind']=='line':bypath[it['path']].append(it)
    for path,rows in bypath.items():
        pairs=[];pair_records=[]
        for a,b in zip(rows,rows[1:]):
            sa,sb=a['native_dominant_font'],b['native_dominant_font'];s=(sa+sb)/2;delta=b['baseline']-a['baseline']
            if max(sa,sb)/min(sa,sb)>cfg.maximum_font_ratio or abs(a['box'][0]-b['box'][0])>cfg.aligned_left_tolerance_em*s or min(a['box'][2]-a['box'][0],b['box'][2]-b['box'][0])<cfg.minimum_row_width_em*s or not cfg.minimum_leading_em*s<=delta<=cfg.maximum_leading_em*s:continue
            pairs.append(delta);pair_records.append((delta,a,b))
        clusters=[]
        for delta in sorted(pairs):
            found=next((c for c in clusters if abs(statistics.median(c)-delta)<=cfg.leading_cluster_tolerance_em*body),None)
            if found is None:clusters.append([delta])
            else:found.append(delta)
        clusters.sort(key=lambda c:(-len(c),statistics.median(c)))
        if clusters and len(clusters[0])>=cfg.minimum_repeated_pairs:result[path]={'leading_pdf':statistics.median(clusters[0]),'supporting_pairs':len(clusters[0]),'other_pairs':len(pairs)-len(clusters[0]),'source':'repeated aligned native baselines'}
        if path in result:
            accepted=[(a,b) for delta,a,b in pair_records if abs(delta-result[path]['leading_pdf'])<=cfg.leading_cluster_tolerance_em*body]
            clearances=[b['box'][1]-a['box'][3] for a,b in accepted if 0<=b['box'][1]-a['box'][3]<=body]
            if len(clearances)>=cfg.minimum_repeated_pairs:
                result[path].update(native_ink_clearance_pdf=statistics.median(clearances),clearance_supporting_pairs=len(clearances),native_line_ink_height_pdf=statistics.median(x['box'][3]-x['box'][1] for pair in accepted for x in pair))
    return result

def can_join(a,b,body,leading,flow,cfg=ParagraphGeometryConfig()):
    if not a or a['path']!=b['path']:return False
    sa,sb=a['native_dominant_font'],b['native_dominant_font']
    if max(sa,sb)/min(sa,sb)>cfg.maximum_font_ratio:return False
    limit=leading[a['path']]['leading_pdf']*cfg.accepted_gap_ratio if a['path'] in leading else flow.maximum_paragraph_baseline_gap_em*body
    delta=b['baseline']-a['baseline'];aligned=-flow.maximum_first_line_return_em*body<=b['box'][0]-a['box'][0]<=flow.new_paragraph_indent_em*body
    if not aligned or delta<=0:return False
    if delta<=limit:return True
    # A tall inline native object can increase baseline spacing without adding
    # paragraph whitespace. Require repeated same-column ink-clearance evidence;
    # do not increase the frozen baseline-gap ratio to fit an individual page.
    evidence=leading.get(a['path'],{});clearance=b['box'][1]-a['box'][3]
    tall=max(a['box'][3]-a['box'][1],b['box'][3]-b['box'][1])>evidence.get('native_line_ink_height_pdf',float('inf'))+cfg.leading_cluster_tolerance_em*body
    accepted=bool(tall and 'native_ink_clearance_pdf' in evidence and 0<=clearance<=evidence['native_ink_clearance_pdf']*cfg.accepted_gap_ratio and delta<=flow.maximum_paragraph_baseline_gap_em*body)
    if accepted:b['ink_clearance_join_evidence']={'baseline_gap_pdf':delta,'ink_clearance_pdf':clearance,'reference_clearance_pdf':evidence['native_ink_clearance_pdf'],'supporting_pairs':evidence['clearance_supporting_pairs']}
    return accepted
