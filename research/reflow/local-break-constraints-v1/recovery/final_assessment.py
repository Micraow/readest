"""Validate a manual, evaluation-only paragraph audit of the frozen outputs.

This does not run or modify a reflow arm. Manual labels come from source and
A 390/20 image inspection on 2026-10-09. They are not a browser, independent,
all-size, glyph-perfect, or preregistered paragraph score.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

W = Path(__file__).resolve().parents[1]
B = W / 'local-break-constraints-v1'
O = W / 'readest-recovery'
units = []


def add(doc, refs, result, reason, complete=True):
    units.append({
        'id': f'D{doc}-U{1 + sum(u["document"] == doc for u in units)}',
        'document': doc,
        'reference_regions': [f'D{doc}-P{p}-R{r}' for p, r in refs],
        'complete_source_unit_within_registered_pair': complete,
        'A_390_20_visual_result': result,
        'reason': reason,
        'full_matrix_acceptance': 'not_certified',
    })


flow = 'Visibly rewrapped at the inspected setting without an identified internal sequence or paragraph-boundary defect; not full acceptance.'
add(1, [(1,1),(1,3),(1,5),(1,7),(2,1)], 'fail', 'One continuous derivation around three displayed formulas crosses the page boundary. Source entry is clipped; A has definite multi-line prose-island reordering within the available portion.', False)
add(1, [(2,3)], 'readable_at_inspected_setting', flow)
add(1, [(2,4)], 'readable_at_inspected_setting', flow)
add(1, [(2,5)], 'unknown', 'The visible fragment flows, but the paragraph ends outside the registered pair; complete-unit readability cannot be accepted.', False)

add(2, [(1,4)], 'readable_at_inspected_setting', flow)
add(2, [(1,5)], 'readable_at_inspected_setting', flow)
add(2, [(1,6),(2,2),(2,4)], 'unknown', 'One formula-connected unit with equations 13-16 spans the two source pages. Page-local portions flow, but paired-reader continuation was not tested.')
for r in (6,7,8):
    add(2, [(2,r)], 'readable_at_inspected_setting', flow)
add(2, [(2,10)], 'fail', 'Footnote/rule island interrupts the last ordinary body sentence; the paragraph also continues beyond the registered pair.', False)

add(3, [(1,2)], 'fail', 'Initial source fragment is split into multi-line math/prose islands with interrupted logical order.', False)
add(3, [(1,5)], 'fail', 'Prose wraps, but its end is merged directly into the next independently indented source paragraph.')
add(3, [(1,9),(1,11)], 'fail', 'One paragraph spans equation 14; its continuation is then merged directly into the next source paragraph.')
add(3, [(1,12)], 'fail', 'The paragraph is merged into adjacent source paragraphs, including the following summary.')
add(3, [(1,14),(1,3)], 'fail', 'The left-bottom to right-top continuation is interrupted by the source page number.')
add(3, [(1,7)], 'readable_at_inspected_setting', flow)
add(3, [(2,3),(2,6),(2,8),(2,10)], 'unknown', 'Formula-connected paragraph with equations 15-17. Prose mostly flows, but complete mathematical dependency/readability and horizontal access were not verified; isolated punctuation is visible.')
add(3, [(2,12),(2,2)], 'fail', 'False paragraph gap at the cross-column continuation and loss of separation from the next source paragraph.')
add(3, [(2,5)], 'fail', 'Source paragraph boundaries are lost at both adjacent prose transitions.')
add(3, [(2,13)], 'fail', 'Merged into the preceding paragraph; the exit also lies outside the registered pair.', False)

add(4, [(1,5)], 'fail', 'Inline math islands include ordinary prose from multiple source lines and corrupt its sequence; entry is outside the pair.', False)
add(4, [(1,9)], 'fail', 'Short paragraph is broken around a summation island, reordering ordinary words.')
add(4, [(1,11),(1,8)], 'fail', 'Multi-line prose islands and page header/figure/caption interposition corrupt the column-spanning paragraph.')
add(4, [(1,12),(2,3)], 'fail', 'Inline mathematical islands reorder ordinary words on both pages; source paragraph continuation is not preserved.')
for r in (4,5,6):
    add(4, [(2,r)], 'fail', 'Ordinary prose is retained in multi-line mathematical islands and appears in interrupted or reordered sequence.')
add(4, [(2,7),(2,9)], 'fail', 'Inline islands break prose order, while page number and figure/caption interrupt the column continuation.')

for r in (3,4,7):
    add(5, [(1,r)], 'readable_at_inspected_setting', flow)
add(5, [(1,8)], 'fail', 'Margin revision stroke is inserted inside the paragraph, splitting the sentence.')
for r in (9,10,11,12,13):
    add(5, [(1,r)], 'fail', 'Grey painted background connects the Tips introduction/list into a page-width local island; ordinary body cannot genuinely wrap.')
add(5, [(1,14)], 'readable_at_inspected_setting', flow)
add(5, [(1,15)], 'fail', 'Margin revision stroke is inserted between two parts of the same sentence.')
for r in (3,4,5,8):
    add(5, [(2,r)], 'readable_at_inspected_setting', flow)
add(5, [(2,9)], 'fail', 'Margin revision stroke is inserted in the middle of the paragraph.')
add(5, [(2,10),(2,11)], 'fail', 'Introductory sentence and expression are one unit. Revision stroke and spacing split the expression; its ordinary Text annotation does not make it a separate paragraph.')
add(5, [(2,12)], 'unknown', 'Visible prose flows, but it introduces a calculation outside the registered pair; full unit remains unknown.', False)

for r in (3,5,6,7,8,9,10,11,12,13):
    add(6, [(1,r)], 'fail' if r in (5,6,7) else 'readable_at_inspected_setting', 'Original source-line divisions survive as false paragraph gaps inside one source paragraph.' if r in (5,6,7) else flow)
for r in range(3,15):
    add(6, [(2,r)], 'fail' if r == 10 else 'readable_at_inspected_setting', 'Original source-line division survives as a false paragraph gap inside one source paragraph.' if r == 10 else flow)

inventory = json.loads((B / 'QA-INVENTORY.json').read_text())
raw = {r['id'] for p in inventory['pages'] for r in p['regions'] if r['official_role'] in ('Text','List-item')}
excluded = {'D6-P1-R2': 'Running title, not body', 'D6-P2-R2': 'Running title, not body'}
mapped = [r for u in units for r in u['reference_regions']]
assert len(mapped) == len(set(mapped)), 'Reference assigned more than once'
assert set(mapped) | set(excluded) == raw, (raw - set(mapped) - set(excluded))
assert set(mapped).isdisjoint(excluded)
assert len(raw) == 87 and len(mapped) == 85 and len(units) == 69

freeze = json.loads((B / 'IMPLEMENTATION-FREEZE.json').read_text())
code = []
for relative, expected in freeze['code_sha256'].items():
    actual = hashlib.sha256((W / relative).read_bytes()).hexdigest()
    assert actual == expected, relative
    code.append({'path': relative, 'sha256': actual, 'matches_freeze': True})
inputs = []
seen_inputs = set()
for receipt in json.loads((B / 'INPUT-RECEIPTS.json').read_text()):
    suffix = '.pdf' if receipt['archive'] == 'extra' else '-official.png'
    p = B / 'inputs' / (receipt['key'] + suffix)
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    assert actual == receipt['sha256'], str(p)
    if (receipt['key'], receipt['archive']) in seen_inputs:
        continue
    seen_inputs.add((receipt['key'], receipt['archive']))
    inputs.append({'key': receipt['key'], 'kind': receipt['archive'], 'sha256': actual, 'matches_receipt': True})
assert len(inputs) == 24

missing_b = []
display_coverage = []
for page in inventory['pages']:
    key = page['key']
    for arm in ('A','B'):
        directory = B / 'output' / (key + '-AB')
        atoms = json.loads((directory / (arm + '-atoms.json')).read_text())['atoms']
        html = (directory / (arm + '.html')).read_text()
        displayed = re.findall(r'data-unit="([^"]+)"', html)
        counts = Counter(displayed)
        missing = [a for a in atoms if key + '-' + a['id'] not in counts]
        display_coverage.append({'page': key, 'arm': arm, 'atoms': len(atoms), 'missing_atoms': len(missing), 'duplicate_display_ids': sum(v-1 for v in counts.values() if v>1), 'missing_declared_source_ink': sum(a['source_ink'] for a in missing)})
        if arm == 'B':
            missing_b += [{'page': key, 'atom': a['id'], 'declared_source_ink': a['source_ink']} for a in missing]
assert [(a['page'],a['declared_source_ink']) for a in missing_b] == [('D1-P1',12912),('D3-P2',4188),('D4-P1',3363)]

counts = Counter(u['A_390_20_visual_result'] for u in units)
execution_rows = []
for path in sorted(O.glob('PAIR-*-REPLAY.json')):
    execution_rows.extend(json.loads(path.read_text())['rows'])
assert len(execution_rows) == 36 and all(r['returncode'] == 0 for r in execution_rows)
detector = json.loads((B/'DETECTOR-RESULT.json').read_text())
page_costs = []
for p in detector['pages']:
    groups = [r for r in execution_rows if r['key'] == p['key']]
    summed = sum(r['elapsed_seconds'] for r in groups)
    page_costs.append({'page':p['key'], 'sum_AB_E_CD_group_wall_seconds':summed, 'detector_page_seconds':p['raster_encode_inference_seconds'], 'full_comparison_sum_plus_hot_detector_seconds':summed+p['raster_encode_inference_seconds']})
result = {
    'status': 'negative_frozen_candidate_assessment_complete_at_stated_scope',
    'date_utc': '2026-10-09',
    'source_freeze': '9f6b88cfa9b15169f7d739b10c350efa261e19dd',
    'engine_rerun_or_tuning_in_this_assessment': False,
    'scope': 'Manual source and A 390px/20px self-review of all twelve pages; not independent or browser acceptance. Paragraph grouping was audited after output inspection, so descriptive rather than preregistered.',
    'unit_definition': 'Join source paragraphs across display formulas, columns and the registered adjacent-page boundary; standalone list items count. Retain clipped, failed and unknown units. Exclude only two explicitly identified running titles. Units concern registered source body, not complete documents.',
    'old_scoring_invalid': {'raw_regions':95,'mechanical_candidates':76,'reason':'DocLayNet image_id collision across train/val mixed D3-P2 annotations; invalid counts preserved in historical observation document.'},
    'corrected_denominator': {'raw_Text_List_regions':87,'excluded_nonbody_titles':excluded,'mapped_body_regions':85,'paragraph_or_list_units':69,'unmapped_body_regions':0,'duplicate_region_assignments':0},
    'A_390_20_self_review_counts': dict(counts),
    'overall_success_percentage': None,
    'why_no_acceptance_percentage': 'Single-setting visible readability is not complete mathematical/glyph/browser or six-setting verification. Unknowns stay in the 69-unit denominator. No A/B gain is valid because B omits three complete formula atoms.',
    'by_document': {f'D{d}':dict(Counter(u['A_390_20_visual_result'] for u in units if u['document']==d)) for d in range(1,7)},
    'units': units,
    'visual_coverage': [{'page':p['key'], 'source_pixels_inspected':True, 'A_390_20_inspected':True, 'A_evidence_kind':'WeasyPrint CSS raster' if int(p['key'][1])<3 else 'Source atlas blit at WeasyPrint box coordinates; UI labels/borders omitted', 'other_five_settings_visual_review':'not_done', 'real_page_browser_review':'not_done', 'E_visual_review':'not_done', 'C_D_visual_review':'not_done'} for p in inventory['pages']],
    'B_comparison': {'status':'invalid_for_superiority_claim','missing_formula_atoms':missing_b,'D1_P1_selected_visual_comparison':True,'other_omissions_verified_from_atom_and_HTML_accounting':True},
    'display_accounting_not_semantic_proof': display_coverage,
    'acceptance_gate': {'body_85_percent':'not_established; candidate has definite paragraph/relationship failures', 'gain_over_B_15_percentage_points':'not_evaluable_with_contaminated_B', 'strict_content_and_relation_gate':'failed', 'decision':'do_not_promote'},
    'resource_accounting': {'executed_groups':36, 'all_group_exit_codes_zero':True, 'max_group_wall_seconds':max(r['elapsed_seconds'] for r in execution_rows), 'detector_cold_init_seconds':detector['cold_init_seconds'], 'detector_page_seconds_range':[min(p['raster_encode_inference_seconds'] for p in detector['pages']),max(p['raster_encode_inference_seconds'] for p in detector['pages'])], 'per_page_comparison_costs':page_costs, 'warning':'AB and E each build two alternatives and six sizes; CD builds two baseline alternatives. Group wall time is not per-arm mobile latency. Summed full comparison exceeds 60 seconds on four pages even before cold detector initialization; do not claim that the full experiment fits a 60-second page budget.', 'browser_validation':'Run 37882285419 passed five original-fixture groups only. No real-PDF browser acceptance.', 'storage':'Historical evidence exceeded the planned 200 MiB budget before storage compaction; private backups are additional durable copies, not evidence that the original cap was met.'},
    'integrity': {'engine_files':code,'source_files':inputs},
    'next_generic_architecture': ['Separate painted backgrounds, foreground glyph ink and decorative/revision marks before dependency closure.', 'Require each geometry atom to be emitted exactly once even when semantic association endpoints share a component.', 'Enforce consistency between source logical intervals and actual renderer event order; preserve paragraph and cross-column/page continuations.', 'Keep headers, footnotes, captions and figure labels associated without interposing them inside body sentences.', 'Validate new mechanisms first with original controls, then a newly frozen unseen corpus; do not repair or replace these twelve samples to claim generalization.'],
}
(O/'FINAL-ASSESSMENT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'paragraph_units':len(units),'counts':counts,'frozen_code_files_verified':len(code),'inputs_verified':len(inputs),'B_missing_formulas':len(missing_b)}))
