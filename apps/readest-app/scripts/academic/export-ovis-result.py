"""Export a local, reviewed Ovis page into Readest's result-import contract.

Consumes block/provenance JSON produced by an Ovis adapter, not weights or images.
PyMuPDF is used only to verify the PDF identity and page dimensions.
"""
import argparse
import hashlib
import json
import pathlib
import re


def rect(bounds):
    x, y, right, bottom = bounds
    return {'x': x, 'y': y, 'width': right-x, 'height': bottom-y}


def export_result(pdf_path, page_number, result_dir, identity):
    import fitz
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    structure = json.loads((result_dir/'blocks.json').read_text())
    receipt = json.loads((result_dir/'receipt.json').read_text())
    math = json.loads((result_dir/'native-math.json').read_text())
    if math['pdf_sha256'] != sha or math['page_number'] != page_number:
        raise ValueError('Source PDF/page does not match the processed result')
    with fitz.open(pdf_path) as pdf:
        page = pdf[page_number-1]
        if page.rotation:
            raise ValueError('This exporter currently supports unrotated PDF pages only')
        width, height, count = page.rect.width, page.rect.height, len(pdf)
    prefix = f'ovis-{sha[:12]}-p{page_number}-'
    note_ids = {note['marker']: prefix+note['id'] for note in structure['notes']}
    first_calls = {}
    marker = re.compile(r'\$\s*\^\{(\d+|\\dagger|\\ddagger|\*)\}\s*\$')
    def references(text, block_id):
        # Do not interpret note-like text inside Markdown code spans/fences.
        protected = [(m.start(),m.end()) for m in re.finditer(r'(`+)([\s\S]*?)\1', text)]
        def replace(match):
            label=match.group(1)
            if label not in note_ids or any(a<=match.start()<b for a,b in protected):return match.group()
            first_calls.setdefault(label,block_id)
            display=label.replace('\\dagger','†').replace('\\ddagger','‡')
            return f'[{display}](#{note_ids[label]})'
        return marker.sub(replace,text)
    figures={item['asset']:item for item in receipt['figure_groups']}
    formulas={pathlib.Path(item['source_crop']['path']).name:item for item in receipt['source_formula_replacements']}
    blocks=[]
    for block in structure['blocks']:
        block_id=prefix+block['id']
        if block['kind']=='figure':
            caption=references(block['caption'],block_id)
            if block['labels']:
                caption+='\n\n<details><summary>Recognized figure labels</summary>\n\n'+'\n\n'.join(block['labels'])+'\n\n</details>'
            blocks.append({'id':block_id,'kind':'visual','role':'figure','box':rect(figures[block['asset']]['bbox']),'caption':caption})
        elif block['kind']=='image':
            left,top,right,bottom=block['bbox']
            blocks.append({'id':block_id,'kind':'visual','role':'figure','box':rect([left*width/1000,top*height/1000,right*width/1000,bottom*height/1000])})
        else:
            match=re.fullmatch(r'!\[Source equation\]\(assets/([a-z0-9-]+\.png)\)',block['markdown'])
            if match and match.group(1) in formulas:
                blocks.append({'id':block_id,'kind':'visual','role':'equation','box':rect(formulas[match.group(1)]['source_crop']['bbox'])})
            else:
                blocks.append({'id':block_id,'kind':'markdown','markdown':references(block['markdown'],block_id)})
    for note in structure['notes']:
        text=note['content'];label=note['marker']
        if label in first_calls:text+=f'\n\n[↩](#{first_calls[label]})'
        blocks.append({'id':note_ids[label],'kind':'footnote','marker':label.replace('\\dagger','†').replace('\\ddagger','‡'),'markdown':text})
    return {'format':'readest-ovis-reflow','version':1,'pdfSha256':sha,'pageCount':count,'identity':identity,'pages':[{'page':page_number,'width':width,'height':height,'blocks':blocks}]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=pathlib.Path,required=True)
    parser.add_argument('--page',type=int,required=True)
    parser.add_argument('--result-dir',type=pathlib.Path,required=True)
    parser.add_argument('--identity',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args()
    bundle=export_result(args.pdf,args.page,args.result_dir,json.loads(args.identity.read_text()))
    args.output.write_text(json.dumps(bundle,ensure_ascii=False,indent=2))
    print(json.dumps({'output_bytes':args.output.stat().st_size,'pdf_sha256':bundle['pdfSha256'],'covered_pages':[page['page'] for page in bundle['pages']],'blocks':sum(len(page['blocks']) for page in bundle['pages'])}))
