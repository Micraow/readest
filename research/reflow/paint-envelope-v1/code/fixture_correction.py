"""Fixture-only correction: legacy insert_text encoded Unicode radical as a dot.
The frozen envelope algorithm is unchanged. New validation input uses TextWriter.
"""
import pathlib,json,hashlib,time
import fitz
from envelope import inspect
B=pathlib.Path(__file__).resolve().parents[1]
if (B/'FIXTURE-CORRECTION.json').exists():raise SystemExit('Fixture correction already run')
freeze={'epoch':time.time(),'reason':'Visual QA showed original Symbol insert_text fixture painted a dot, not a radical; original result retained and not counted as radical validation.','envelope_sha256':hashlib.sha256((B/'code/envelope.py').read_bytes()).hexdigest(),'new_generator':'TextWriter with Symbol Unicode glyph','scales':[1.25,4.]};(B/'FIXTURE-CORRECTION-FREEZE.json').write_text(json.dumps(freeze,indent=2))
d=fitz.open();p=d.new_page(width=200,height=120);writer=fitz.TextWriter(p.rect);writer.append((30,70),'√',font=fitz.Font('symb'),fontsize=55);writer.write_text(p);assert p.get_text().strip()=='√';d.save(B/'inputs/verified-radical.pdf');rows=[]
for scale in [1.25,4.]:
 pix,r=inspect(p,scale);pix.save(str(B/'evidence'/f'verified-radical-{scale}.png'));rows.append({k:v for k,v in r.items() if k!='paints'})
(B/'FIXTURE-CORRECTION.json').write_text(json.dumps({'freeze':freeze,'rows':rows},indent=2));print(json.dumps(rows,indent=2))
