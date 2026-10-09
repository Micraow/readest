"""A repeated column edge can support a bounded source first-line return."""
import importlib.util,pathlib,statistics,sys
from dataclasses import dataclass,asdict
P=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-localgeometry/code/paragraph_geometry.py';spec=importlib.util.spec_from_file_location('previous_paragraph_geometry',P);old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
@dataclass(frozen=True)
class FirstLineConfig:
    edge_cluster_tolerance_em:float=.3
    minimum_repeated_edge_rows:int=3
    maximum_first_line_indent_em:float=3.
    minimum_first_line_width_em:float=8.
    def json(self):return asdict(self)
RETURN_TRACE=[]
annotate=old.annotate

def estimate(items,body,cfg=FirstLineConfig()):
    leading=old.estimate(items,body)
    for path,row in leading.items():
        lines=[x for x in items if x['kind']=='line' and x['path']==path and x['box'][2]-x['box'][0]>=cfg.minimum_first_line_width_em*x['native_dominant_font']];clusters=[]
        for line in sorted(lines,key=lambda x:x['box'][0]):
            c=next((c for c in clusters if abs(statistics.median(x['box'][0] for x in c)-line['box'][0])<=cfg.edge_cluster_tolerance_em*body),None)
            if c is None:clusters.append([line])
            else:c.append(line)
        clusters.sort(key=lambda c:(-len(c),statistics.median(x['box'][0] for x in c)))
        if clusters and len(clusters[0])>=cfg.minimum_repeated_edge_rows:row.update(column_edge_pdf=statistics.median(x['box'][0] for x in clusters[0]),column_edge_support=len(clusters[0]))
    return leading

def can_join(a,b,body,leading,flow,cfg=FirstLineConfig()):
    if old.can_join(a,b,body,leading,flow):return True
    if not a or a['path']!=b['path'] or a['path'] not in leading:return False
    ev=leading[a['path']];edge=ev.get('column_edge_pdf');s=a['native_dominant_font'];ratio=max(s,b['native_dominant_font'])/min(s,b['native_dominant_font']);delta=b['baseline']-a['baseline'];indent=a['box'][0]-edge if edge is not None else 0
    accepted=bool(edge is not None and flow.new_paragraph_indent_em*body<indent<=cfg.maximum_first_line_indent_em*body and abs(b['box'][0]-edge)<=cfg.edge_cluster_tolerance_em*body and a['box'][2]-a['box'][0]>=cfg.minimum_first_line_width_em*s and ratio<=old.ParagraphGeometryConfig().maximum_font_ratio and 0<delta<=ev['leading_pdf']*old.ParagraphGeometryConfig().accepted_gap_ratio)
    # This trace is carried in structured source items during the builder run.
    b['first_line_return_evidence']={'previous':a.get('id'),'next':b.get('id'),'accepted':accepted,'column_edge_pdf':edge,'previous_indent_pdf':indent,'native_leading_pdf':ev['leading_pdf'],'baseline_gap_pdf':delta,'config':cfg.json()}
    RETURN_TRACE.append(b['first_line_return_evidence'])
    return accepted
