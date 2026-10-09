"""Adapter over frozen composition, with only the validated stencil event fix."""
import pathlib,sys,importlib.util
root,work,pdf,page,key,harness=sys.argv[1:];W=pathlib.Path(root);B=pathlib.Path(work)
sys.path.insert(0,str(W/'stroke-object-batch-v1/code'));import compose,helpers
s=importlib.util.spec_from_file_location('stencil_envelope',W/'stencil-paint-v1/code/envelope.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
compose.B=B;helpers.B=B;helpers.H=pathlib.Path(harness);compose.inspect=m.inspect
# The source remains local; one symlink avoids a second copy of the PDF.
link=B/'inputs'/(key+'.pdf')
if not link.exists():link.symlink_to(pathlib.Path(pdf).resolve())
compose.main({'key':key,'page_1based':int(page)})
