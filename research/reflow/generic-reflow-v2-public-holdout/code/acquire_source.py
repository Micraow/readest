"""Reproduce the registered public fixture, without embedding the paper in Git."""
import argparse,hashlib,json,pathlib,urllib.request
from pypdf import PdfReader,PdfWriter
URL='https://papers.nips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf'
FULL_SHA256='d87d482d5ae7960e2e43d7dd6d21377e60e73e8fce1bf2a01aff7aca8a08c537'
PAGE_SHA256='03423c222b2255bd6cd84b5abc551523fb4aeb11d300c877697ce321315ee771'
p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--source-pdf',help='Use an already obtained source instead of downloading it again');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
if a.source_pdf:data=pathlib.Path(a.source_pdf).read_bytes()
else:
 with urllib.request.urlopen(URL,timeout=45) as response:data=response.read(10*1024*1024+1)
if len(data)>10*1024*1024 or hashlib.sha256(data).hexdigest()!=FULL_SHA256:raise RuntimeError('Source hash/size differs from the registered paper; do not substitute silently')
full=out/'full-source-private.pdf';full.write_bytes(data);reader=PdfReader(full)
if len(reader.pages)!=11:raise RuntimeError('Unexpected source page count')
writer=PdfWriter();writer.add_page(reader.pages[3]);page=out/'H7-source-page-private.pdf'
with page.open('wb') as file:writer.write(file)
actual=hashlib.sha256(page.read_bytes()).hexdigest()
if actual!=PAGE_SHA256:raise RuntimeError('Derived fixture differs; check the recorded pypdf/runtime version before evaluating')
report={'source_url':URL,'full_document_sha256':FULL_SHA256,'fixture_sha256':actual,'full_document_pages':11,'original_pdf_page_index':3,'fixture_pdf_page_index':0,'evaluation_performed':False};(out/'acquisition.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
