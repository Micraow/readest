"""Generate an empty, offline, unlinked Readest public research entry. No fixture data."""
import argparse,base64,hashlib,json,pathlib,re,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[4]
CODE=pathlib.Path(__file__).parent
p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args()
with tempfile.TemporaryDirectory() as tmp:
    folder=pathlib.Path(tmp);manifest=folder/'empty.json';manifest.write_text('[]')
    subprocess.run([sys.executable,str(ROOT/'research/reflow/generic-reflow-v2-trial-reader/code/package_trial.py'),str(manifest),str(folder/'empty.html')],check=True,capture_output=True)
    content=(folder/'empty.html').read_text()
validator=(CODE/'bundle_contract.mjs').read_text().replace('export ','')
importer=(CODE/'import_ui.mjs').read_text()
content=content.replace('</script></html>','\n'+validator+'\n'+importer+'</script></html>')
content=content.replace('两页已预计算样本。','仅接收本地预计算研究 JSON，不接收任意 PDF，也不运行提取或模型。')
content=content.replace('此文件尚未集成 Readest。所有资源均在本文件内，无外部请求。','这是独立研究入口，未接入常规阅读模式。导入数据仅在本页内存使用，关闭页面即释放；不上传、不写入书库。')
content=content.replace('<header><h1>','<header><p><label>导入本地研究数据 <input id="research-bundle" type="file" accept=".json,application/json"></label></p><h1>')
script=re.search(r'<script type="module">(.*?)</script>',content,re.S).group(1)
digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
csp="default-src 'none'; script-src 'sha256-"+digest+"'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
content=content.replace('<meta charset="utf-8">','<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="'+csp+'">')
out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(content)
print(json.dumps({'output':str(out),'bytes':out.stat().st_size,'embedded_pages':0,'network_policy':'deny','browser_verified':False}))
