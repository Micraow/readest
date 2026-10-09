"""Optional offline PP-S weak prior; model/runtime costs belong to the page."""
import os,json,pathlib,time,hashlib,socket

def predict(pdf,out,model_dir):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);model_dir=pathlib.Path(model_dir);start=time.perf_counter();cpu=time.process_time()
    cache=out/'runtime-cache';cache.mkdir(exist_ok=True)
    for k,v in {'PADDLE_PDX_CACHE_HOME':str(cache),'MPLCONFIGDIR':str(cache/'matplotlib'),'XDG_CACHE_HOME':str(cache),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():os.environ[k]=v
    def deny(*a,**k):raise RuntimeError('Networking is disabled in local layout inference')
    socket.socket.connect=deny;socket.create_connection=deny
    from paddlex import create_model
    import pypdfium2 as pdfium
    t=time.perf_counter();model=create_model(model_name='PP-DocLayout-S',model_dir=str(model_dir),device='cpu',engine='paddle_static',engine_config={'cpu_threads':1,'run_mode':'paddle'});load=time.perf_counter()-t
    doc=pdfium.PdfDocument(pdf);page=doc[0];bm=page.render(scale=4,draw_annots=False,may_draw_forms=False);im=bm.to_pil().convert('RGB');size=im.size;im.save(out/'native-model-input.png');bm.close();page.close();doc.close();t=time.perf_counter();r=list(model.predict(str(out/'native-model-input.png'),batch_size=1))[0].json
    if isinstance(r,str):r=json.loads(r)
    (out/'prediction-private.json').write_text(json.dumps(r));result=dict(model='PP-DocLayout-S',mode='offline CPU, one thread; weak region prior only',native_model_input_size=list(size),native_input_pdf_renderer='PDFium, annotation-disabled; historical cached predictions used MuPDF',model_file_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model_dir.iterdir() if p.is_file()},import_and_setup_plus_page_wall_seconds=time.perf_counter()-start,import_and_setup_plus_page_cpu_seconds=time.process_time()-cpu,create_model_wall_seconds=load,inference_and_record_wall_seconds=time.perf_counter()-t,prediction_count=len(r['res']['boxes']))
    (out/'model-costs.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('model_dir');a=p.parse_args();print(json.dumps(predict(a.pdf,a.out,a.model_dir)))
