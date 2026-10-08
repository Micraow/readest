"""Static HTML is shared by the browser fixture and offline CSS snapshots."""
import argparse,html,json,pathlib
E=html.escape
CSS='''*{box-sizing:border-box}body{margin:0;background:#e7ecef;color:#17212a;font-family:Arial,sans-serif}main{width:min(390px,100%);margin:0 auto;padding:14px;background:white;min-height:100vh}h1{font-size:19px;margin:3px 0 8px}h2{font-size:13px;line-height:1.4;margin:20px 0 10px;color:#426073}.notice,.note{overflow-wrap:anywhere;font:12px/1.45 Arial,sans-serif;color:#596571}.notice{background:#f1f5f7;padding:8px;border-left:3px solid #648298}.toolbar{display:flex;gap:8px;position:sticky;top:0;background:#fff;padding:8px 0;z-index:2}.toolbar button,dialog button{padding:7px 10px;border:1px solid #bac5cc;border-radius:5px;background:#fff;color:#263c4e}.reading{font-size:20px;line-height:1.5}.flow{margin:0 0 .9em;line-height:1.5}.unit{display:inline-block;position:relative;text-decoration:none;color:inherit;outline-offset:2px}.unit img{width:100%;height:100%;display:block}.word-gap{display:inline-block;width:.27em}.unit:hover{background:#edf4fa;outline:1px solid #648298}.protected{overflow-x:auto;overflow-y:hidden;max-width:100%;border:1px solid #e1e5e8;margin:8px 0 4px;padding:4px}.protected .unit{display:block;max-width:none}.protected img{max-width:none}.object-note{font:11px/1.4 Arial,sans-serif;margin:0 0 10px;color:#65717b}.caption{font-size:1em}.source-link{font:12px Arial,sans-serif;color:#416b88}details{font:12px/1.5 Arial,sans-serif;margin:16px 0}pre{white-space:pre-wrap;word-break:break-word;user-select:text}.excerpt{border-top:1px solid #dce3e8;margin-top:18px}dialog{padding:12px;border:1px solid #789;width:min(95vw,950px);max-height:94vh}dialog::backdrop{background:#14233488}.source-scroll{max-height:76vh;overflow:auto;background:#ddd;margin-top:8px}.source-plane{position:relative;width:100%;min-width:320px}.source-plane>img{width:100%;height:auto;display:block}.highlight{position:absolute;border:2px solid #df641f;background:#ffb80018;pointer-events:none}.object-preview img{display:block;max-width:100%;height:auto;margin:8px auto}.object-preview{font:12px/1.4 Arial,sans-serif}.source-status{font:12px/1.4 Arial,sans-serif;overflow-wrap:anywhere} .legend{font:11px/1.4 Arial,sans-serif;color:#677;}'''

def unit_html(u):
    style=f'width:{u["widthEm"]:.8f}em;height:{u["heightEm"]:.8f}em;vertical-align:{-u["descentEm"]:.8f}em'
    attrs=f'data-unit="{E(u["id"])}" data-role="{E(u["role"])}" data-page="{u["source"]["page"]}" data-bbox="{E(json.dumps(u["source"]["bbox"]))}"'
    return f'<a href="#source" class="unit" {attrs} style="{style}" title="{E(u["label"])}; view original position"><img src="{u["image"]}" alt="Original source {E(u["role"])}: {E(u["label"])}"></a>'

def render(data):
    body='''<main><h1>原字形重排实验</h1><p class="notice">人工参考结构输入。段落、读序及行内数学分组已由人工给定；本轮只验证渲染，自动结构恢复仍未解决。</p><div class="toolbar"><button data-font="20" aria-pressed="true">20 px</button><button data-font="28" aria-pressed="false">28 px</button><button id="show-original">查看原页</button></div><p class="legend">正文词块真实换行，科学符号保留原像素。点击任何词块可核对原页位置。</p><div id="reading" class="reading">'''
    for sec in data['sections']:
        body+=f'<section id="{E(sec["id"])}" class="excerpt"><h2>{E(sec["label"])}</h2>'
        for nd in sec['nodes']:
            if nd['role'] in ('equation','table'):
                body+=f'<div class="protected" data-node="{E(nd["id"])}" role="group" aria-label="Protected original {nd["role"]}">'+unit_html(nd['units'][0])+'</div><p class="object-note">完整原始对象。宽于阅读区时可左右滑动；点击可查看原页完整对象。</p>'
            else:
                body+=f'<p class="flow {nd["role"]}" data-node="{E(nd["id"])}">'
                for i,u in enumerate(nd['units']):
                    body+=unit_html(u)
                    body+='<br data-source-hyphen="retained">' if u.get('breakAfter') else (' ' if i<len(nd['units'])-1 else '')
                body+='</p>'
        body+='</section>'
    native='\n\n'.join(' '.join(u.get('nativeText','[protected source object]') for nd in sec['nodes'] for u in nd['units']) for sec in data['sections'])
    body+='</div><p class="note">已知缺陷：原文 Sim- / ilarly 的断词连字符与一次强制换行被保留，未删除像素；其他正文词块可正常重排。</p><details id="aux-text"><summary>辅助原生文本：可选择复制，科学语义未核验</summary><p>单独提供原生提取文本。上下标会被压平，可能残留连字，整块公式与表格未转写。不能视为可靠数学或无障碍层；上方视觉正文暂不可选择。</p><pre>'+E(native)+'</pre></details><p class="note">Source SHA-256: '+E(data['source']['sha256'])+'</p></main><dialog id="source-dialog"><button id="close-source">关闭</button> <button id="zoom-source">100% / 200% 放大</button><p id="source-status" class="source-status"></p><div class="object-preview" hidden><p>完整对象缩略预览（原始像素，保持比例）；下方显示其原页位置。</p><img alt="完整原始对象"></div><div class="source-scroll"><div class="source-plane"><img id="source-image" alt="Original PDF page"><div class="highlight"></div></div></div></dialog>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Oracle source reflow experiment</title><style>'+CSS+'</style>'+body+'<script src="fixture.js"></script><script src="interaction.js"></script></html>'
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--dir',default='.');a=ap.parse_args();d=pathlib.Path(a.dir);data=json.loads((d/'fixture.js').read_text().removeprefix('window.ORACLE_FIXTURE=').rstrip(';\n'));(d/'index.html').write_text(render(data))
