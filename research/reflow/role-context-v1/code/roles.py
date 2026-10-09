"""Generic geometric label evidence; no paper names or formula content templates."""
import re
def external_label_supported(token,box,core,font,edges):
    external_gap=max(box[0]-core[2],core[0]-box[2])
    delimited=bool(re.fullmatch(r'\s*(?:\([0-9]+[a-z]?\)|\[[0-9]+[a-z]?\])\s*',token))
    edge_distance=min(abs(box[0]-edges[0]),abs(box[2]-edges[1])) if edges is not None else float('inf')
    return (delimited and external_gap>=.5*font) or (not delimited and external_gap>=1.5*font and edge_distance<=2*font)
