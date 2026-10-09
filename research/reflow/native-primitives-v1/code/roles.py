"""General compact equation-identifier schema and source-core relation evidence."""
import re
ID=r'(?:(?:[A-Za-z]\.)?[0-9]+(?:\.[0-9]+)*[a-z]?|[IVXivx]+|[*†‡])'
TAG=re.compile(r'\s*(?:\('+ID+r'\)|\['+ID+r'\])\s*')
BARE=re.compile(r'\s*[0-9]+[a-z]?\s*')
def label_candidate(token):return bool(TAG.fullmatch(token) or BARE.fullmatch(token))
def external_label_supported(token,box,core,font,edges):
 external_gap=max(box[0]-core[2],core[0]-box[2]);delimited=bool(TAG.fullmatch(token));edge_distance=min(abs(box[0]-edges[0]),abs(box[2]-edges[1])) if edges is not None else float('inf')
 return (delimited and external_gap>=.5*font) or (not delimited and external_gap>=1.5*font and edge_distance<=2*font)
