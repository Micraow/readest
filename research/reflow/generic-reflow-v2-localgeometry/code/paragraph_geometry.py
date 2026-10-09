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
        pairs=[]
        for a,b in zip(rows,rows[1:]):
            sa,sb=a['native_dominant_font'],b['native_dominant_font'];s=(sa+sb)/2;delta=b['baseline']-a['baseline']
            if max(sa,sb)/min(sa,sb)>cfg.maximum_font_ratio or abs(a['box'][0]-b['box'][0])>cfg.aligned_left_tolerance_em*s or min(a['box'][2]-a['box'][0],b['box'][2]-b['box'][0])<cfg.minimum_row_width_em*s or not cfg.minimum_leading_em*s<=delta<=cfg.maximum_leading_em*s:continue
            pairs.append(delta)
        clusters=[]
        for delta in sorted(pairs):
            found=next((c for c in clusters if abs(statistics.median(c)-delta)<=cfg.leading_cluster_tolerance_em*body),None)
            if found is None:clusters.append([delta])
            else:found.append(delta)
        clusters.sort(key=lambda c:(-len(c),statistics.median(c)))
        if clusters and len(clusters[0])>=cfg.minimum_repeated_pairs:result[path]={'leading_pdf':statistics.median(clusters[0]),'supporting_pairs':len(clusters[0]),'other_pairs':len(pairs)-len(clusters[0]),'source':'repeated aligned native baselines'}
    return result

def can_join(a,b,body,leading,flow,cfg=ParagraphGeometryConfig()):
    if not a or a['path']!=b['path']:return False
    sa,sb=a['native_dominant_font'],b['native_dominant_font']
    if max(sa,sb)/min(sa,sb)>cfg.maximum_font_ratio:return False
    limit=leading[a['path']]['leading_pdf']*cfg.accepted_gap_ratio if a['path'] in leading else flow.maximum_paragraph_baseline_gap_em*body
    return 0<b['baseline']-a['baseline']<=limit and -flow.maximum_first_line_return_em*body<=b['box'][0]-a['box'][0]<=flow.new_paragraph_indent_em*body
