"""Multi-page assembly contract tests using only original synthetic PDF content."""
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fitz

SCRIPT = pathlib.Path(__file__).with_name('merge-ovis-results.py')
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('merger', SCRIPT)
merger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merger)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.pdf = self.root / 'private source name.pdf'
        self.sizes = [(400, 600), (600, 400), (450, 700), (410, 590)]
        with fitz.open() as document:
            for index, (width, height) in enumerate(self.sizes, 1):
                page = document.new_page(width=width, height=height)
                page.insert_text((30, 30), f'Original synthetic page {index}')
            document.save(self.pdf)
        self.identity = {
            'modelSha256': 'a' * 64, 'projectorSha256': 'b' * 64,
            'promptSha256': 'c' * 64, 'runtimeRevision': 'd' * 40,
            'configuration': {'adapter': 'synthetic-1', 'temperature': 0, 'local': True},
        }
        self.output = self.root / 'document.ovis.json'
        self.sidecar = self.output.with_suffix('.provenance.json')

    def page(self, number):
        width, height = self.sizes[number - 1]
        return {'page': number, 'width': width, 'height': height, 'blocks': [
            {'id': f'p{number}-body', 'kind': 'markdown',
             'markdown': 'A deliberately repeated paragraph. [note](#p4-note)'},
            {'id': f'p{number}-equation', 'kind': 'visual', 'role': 'equation',
             'box': {'x': 40, 'y': 80, 'width': 120, 'height': 20}, 'sourceFontSize': 10.5},
            {'id': f'p{number}-figure', 'kind': 'visual', 'role': 'figure',
             'box': {'x': 40, 'y': 120, 'width': 200, 'height': 140},
             'caption': 'Figure caption [note](#p4-note)'},
            {'id': f'p{number}-note', 'kind': 'footnote', 'marker': '7',
             'markdown': 'Preserved note. [return](#p1-body)'},
        ]}

    def bundle(self, pages):
        return {'format': 'readest-ovis-reflow', 'version': 1,
                'pdfSha256': sha(self.pdf), 'pageCount': 4,
                'identity': copy.deepcopy(self.identity),
                'pages': [self.page(number) for number in pages]}

    def save(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return path

    def inputs(self):
        return [self.save('last-first.json', self.bundle([4, 1])),
                self.save('middle.json', self.bundle([3, 2]))]

    def cli(self, inputs, *extra):
        return subprocess.run([sys.executable, str(SCRIPT), '--pdf', str(self.pdf),
                               *[arg for path in inputs for arg in ['--input', str(path)]],
                               '--output', str(self.output), *extra],
                              capture_output=True, text=True)

    def assert_rejected(self, change, pattern):
        bundle = self.bundle([1])
        change(bundle)
        source = self.save('invalid.json', bundle)
        with self.assertRaisesRegex(ValueError, pattern):
            merger.merge_results(self.pdf, [source])

    def test_sorts_pages_and_retains_blocks_links_crops_and_repeated_text(self):
        sources = self.inputs()
        bundle, manifest = merger.merge_results(self.pdf, sources, require_complete=True)
        self.assertEqual(bundle, self.bundle([1, 2, 3, 4]))
        self.assertEqual(len([p['blocks'][0]['markdown'] for p in bundle['pages']]), 4)
        self.assertEqual(manifest['coverage'], {'pageCount': 4, 'coveredPages': [1, 2, 3, 4],
                                              'missingPages': [], 'complete': True})
        self.assertEqual(manifest['bundleSha256'], hashlib.sha256(merger.json_bytes(bundle)).hexdigest())
        self.assertEqual(manifest['source']['pdfSha256'], sha(self.pdf))
        self.assertEqual(manifest['inputs'], [
            {'input': 1, 'sha256': sha(sources[0]), 'pages': [1, 4]},
            {'input': 2, 'sha256': sha(sources[1]), 'pages': [2, 3]},
        ])
        self.assertEqual(manifest['pages'], [
            {'page': number, 'input': index, 'inputSha256': sha(sources[index - 1])}
            for number, index in [(1, 1), (2, 2), (3, 2), (4, 1)]
        ])
        self.assertEqual(manifest['identity'], self.identity)
        self.assertEqual(manifest['source']['binding'], 'producer-declared')
        self.assertFalse(manifest['verification']['modelRunAuthenticated'])
        self.assertFalse(manifest['verification']['ocrAccuracyChecked'])
        self.assertNotIn(str(self.root), json.dumps(manifest))
        self.assertNotIn(self.pdf.name, json.dumps(manifest))

    def test_partial_reports_exact_missing_pages_and_complete_rejects(self):
        source = self.save('partial.json', self.bundle([4, 2]))
        bundle, manifest = merger.merge_results(self.pdf, [source])
        self.assertEqual([p['page'] for p in bundle['pages']], [2, 4])
        self.assertEqual(manifest['coverage'], {'pageCount': 4, 'coveredPages': [2, 4],
                                              'missingPages': [1, 3], 'complete': False})
        with self.assertRaisesRegex(ValueError, 'Missing.*1.*3'):
            merger.merge_results(self.pdf, [source], require_complete=True)
        result = self.cli([source], '--require-complete')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.sidecar.exists())

    def test_cli_outputs_import_bundle_and_matching_sidecar_and_coverage(self):
        result = self.cli(self.inputs(), '--require-complete')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text()), self.bundle([1, 2, 3, 4]))
        manifest = json.loads(self.sidecar.read_text())
        self.assertEqual(manifest['bundleSha256'], sha(self.output))
        summary = json.loads(result.stdout)
        self.assertEqual(summary['covered_pages'], [1, 2, 3, 4])
        self.assertEqual(summary['missing_pages'], [])
        self.assertTrue(summary['complete'])
        partial = self.cli([self.save('partial.json', self.bundle([3]))])
        self.assertEqual(partial.returncode, 0, partial.stderr)
        self.assertEqual(json.loads(partial.stdout)['missing_pages'], [1, 2, 4])
        self.assertIn('partial', partial.stderr.lower())

    def test_cli_help_describes_repeatable_inputs_and_completion(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--require-complete', result.stdout)
        self.assertIn('--input', result.stdout)
        self.assertIn('repeat', result.stdout.lower())

    def test_renaming_pdf_and_inputs_does_not_change_output_or_receipt(self):
        sources = self.inputs()
        before = merger.merge_results(self.pdf, sources)
        self.pdf = self.pdf.rename(self.root / 'renamed.pdf')
        sources = [path.rename(self.root / f'renamed-{index}.json') for index, path in enumerate(sources)]
        self.assertEqual(before, merger.merge_results(self.pdf, sources))

    def test_input_hashes_bind_bytes_not_parsed_equivalence(self):
        source = self.save('single.json', self.bundle([1]))
        bundle, first = merger.merge_results(self.pdf, [source])
        source.write_text(json.dumps(json.loads(source.read_text()), indent=4))
        other_bundle, second = merger.merge_results(self.pdf, [source])
        self.assertEqual(bundle, other_bundle)
        self.assertNotEqual(first['inputs'][0]['sha256'], second['inputs'][0]['sha256'])

    def test_duplicate_pages_rejected_within_and_across_inputs_even_identical(self):
        for page_lists in [([2, 2],), ([2], [2])]:
            with self.subTest(page_lists=page_lists):
                sources = [self.save(f'input-{index}.json', self.bundle(pages))
                           for index, pages in enumerate(page_lists)]
                with self.assertRaisesRegex(ValueError, '[Dd]uplicate.*page'):
                    merger.merge_results(self.pdf, sources)
        source = self.save('single.json', self.bundle([1]))
        with self.assertRaisesRegex(ValueError, '[Dd]uplicate.*page'):
            merger.merge_results(self.pdf, [source, source])

    def test_duplicate_ids_rejected_within_and_across_pages_and_inputs(self):
        for same_page in [True, False]:
            value = self.bundle([1] if same_page else [1, 2])
            value['pages'][-1]['blocks'][1]['id'] = value['pages'][0]['blocks'][0]['id']
            with self.subTest(same_page=same_page), self.assertRaisesRegex(ValueError, '[Dd]uplicate.*ID'):
                merger.merge_results(self.pdf, [self.save('ids.json', value)])
        first, second = self.bundle([1]), self.bundle([2])
        second['pages'][0]['blocks'][0]['id'] = first['pages'][0]['blocks'][0]['id']
        with self.assertRaisesRegex(ValueError, '[Dd]uplicate.*ID'):
            merger.merge_results(self.pdf, [self.save('first.json', first), self.save('second.json', second)])

    def test_rejects_different_pdf_hash_and_real_page_count(self):
        for key, value in [('pdfSha256', 'e' * 64), ('pageCount', 3), ('pageCount', 5)]:
            with self.subTest(key=key, value=value):
                self.assert_rejected(lambda b: b.update({key: value}), 'PDF|page count')
        sources = self.inputs()
        with fitz.open() as different:
            different.new_page(width=400, height=600)
            different.save(self.root / 'other.pdf')
        with self.assertRaisesRegex(ValueError, 'PDF'):
            merger.merge_results(self.root / 'other.pdf', sources)

    def test_identity_is_complete_and_configuration_type_sensitive(self):
        for key in self.identity:
            second = self.bundle([2])
            second['identity'][key] = ({'local': False} if key == 'configuration' else 'e' * len(self.identity[key]))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, '[Ii]dentity'):
                merger.merge_results(self.pdf, [self.save('first.json', self.bundle([1])), self.save('second.json', second)])
        for replacement in [{'temperature': 0, 'local': 1, 'adapter': 'synthetic-1'},
                            {'temperature': False, 'local': True, 'adapter': 'synthetic-1'}]:
            second = self.bundle([2])
            second['identity']['configuration'] = replacement
            with self.assertRaisesRegex(ValueError, '[Ii]dentity'):
                merger.merge_results(self.pdf, [self.save('first.json', self.bundle([1])), self.save('second.json', second)])
        self.assert_rejected(lambda b: b['identity'].pop('configuration'), '[Ii]dentity')
        for invalid in [None, [], {'nested': {}}, {'bad': float('nan')}, {'bad': float('inf')}]:
            self.assert_rejected(lambda b: b['identity'].update(configuration=invalid), 'identity|configuration|JSON')

    def test_identity_key_order_and_equivalent_json_numbers_can_differ(self):
        second = self.bundle([2])
        second['identity'] = dict(reversed(list(second['identity'].items())))
        second['identity']['configuration'] = {'local': True, 'temperature': 0.0, 'adapter': 'synthetic-1'}
        bundle, _ = merger.merge_results(self.pdf, [self.save('first.json', self.bundle([1])), self.save('second.json', second)])
        self.assertEqual(len(bundle['pages']), 2)

    def test_actual_pdf_geometry_matches_each_page_including_rotation(self):
        self.assert_rejected(lambda b: b['pages'][0].update(width=401), 'geometry|dimensions')
        self.assert_rejected(lambda b: b['pages'][0].update(height=601), 'geometry|dimensions')
        rotated = self.root / 'rotated.pdf'
        with fitz.open(self.pdf) as document:
            document[0].set_rotation(90)
            document.save(rotated)
        self.pdf = rotated
        self.sizes[0] = (600, 400)
        bundle, _ = merger.merge_results(self.pdf, [self.save('rotated.json', self.bundle([1]))])
        self.assertEqual((bundle['pages'][0]['width'], bundle['pages'][0]['height']), (600, 400))

    def test_optional_visual_metadata_is_preserved_for_both_roles(self):
        value = self.bundle([1])
        value['pages'][0]['blocks'][2]['sourceFontSize'] = 1
        value['pages'][0]['blocks'][1]['caption'] = 'Equation caption'
        merged, _ = merger.merge_results(self.pdf, [self.save('metadata.json', value)])
        self.assertEqual(merged, value)
        del value['pages'][0]['blocks'][1]['sourceFontSize']
        merged, _ = merger.merge_results(self.pdf, [self.save('legacy.json', value)])
        self.assertEqual(merged, value)

    def test_invalid_metadata_unknown_fields_and_bad_block_types_are_rejected(self):
        mutations = [
            lambda b: b.update(extra=True),
            lambda b: b['identity'].update(extra=True),
            lambda b: b['pages'][0].update(extra=True),
            lambda b: b['pages'][0]['blocks'][0].update(extra=True),
            lambda b: b['pages'][0]['blocks'][0].update(sourceFontSize=12),
            lambda b: b['pages'][0]['blocks'][1]['box'].update(extra=True),
            lambda b: b['pages'][0]['blocks'][1].update(role='photo'),
            lambda b: b['pages'][0]['blocks'][0].update(kind='paragraph'),
            lambda b: b['pages'][0]['blocks'][0].update(id='  '),
            lambda b: b['pages'][0]['blocks'][0].update(markdown=42),
            lambda b: b['pages'][0]['blocks'][0].update(markdown='\n'),
            lambda b: b['pages'][0]['blocks'][3].update(marker=None),
        ]
        mutations += [lambda b, v=value: b['pages'][0]['blocks'][1].update(sourceFontSize=v)
                      for value in [None, False, '12', 0, 0.5, -3, float('inf'), float('nan')]]
        mutations += [lambda b, v=value: b['pages'][0]['blocks'][2].update(caption=v)
                      for value in [None, False, 12, '', '  ']]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(mutation, '.+')

    def test_nonempty_matches_javascript_trim_for_bom_and_control_characters(self):
        self.assert_rejected(lambda b: b['pages'][0]['blocks'][0].update(markdown='\ufeff'), 'nonempty')
        value = self.bundle([1])
        # ECMAScript trim does not remove these Python-only whitespace values.
        value['pages'][0]['blocks'][0]['markdown'] = '\u0085\u001c'
        merged, _ = merger.merge_results(self.pdf, [self.save('controls.json', value)])
        self.assertEqual(merged, value)

    def test_accepts_real_single_page_exporter_outputs(self):
        markdown = self.root / 'synthetic.md'
        markdown.write_text('A repeated raw paragraph. [next](#unchanged)\n\n'
                            '<img src="images/bbox_100_300_600_600.jpg" />')
        sources, expected = [], []
        for number in [4, 2, 1, 3]:
            exported, _ = merger._exporter.export_markdown(
                self.pdf, number, markdown, self.identity, self.root / f'assets-{number}')
            expected += exported['pages']
            sources.append(self.save(f'exported-{number}.json', exported))
        result = self.cli(sources, '--require-complete')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())['pages'], sorted(expected, key=lambda page: page['page']))

    def test_invalid_page_shape_and_bounds_rejected(self):
        mutations = [lambda b: b.update(pages=[]), lambda b: b.update(pages={}),
                     lambda b: b.update(version=True), lambda b: b.update(pageCount=True),
                     lambda b: b['pages'][0].update(blocks=[])]
        mutations += [lambda b, v=value: b['pages'][0].update(page=v)
                      for value in [0, -1, True, '1', 1.5, 5]]
        mutations += [lambda b, k=key, v=value: b['pages'][0].update({k: v})
                      for key in ['width', 'height'] for value in [0, True, None, float('inf')]]
        mutations += [lambda b, k=key, v=value: b['pages'][0]['blocks'][1]['box'].update({k: v})
                      for key, value in [('x', -1), ('y', -1), ('width', 0), ('height', 0),
                                         ('x', 390), ('y', 590), ('height', float('nan')),
                                         ('width', True), ('x', float('inf'))]]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(mutation, '.+')

    def test_rejects_ambiguous_duplicate_json_keys_and_invalid_json(self):
        source = self.save('bad.json', self.bundle([1]))
        for raw in ['{', 'null', source.read_text().replace('"version": 1', '"version": 2, "version": 1')]:
            source.write_text(raw)
            with self.subTest(raw=raw[:30]), self.assertRaisesRegex(ValueError, 'JSON|bundle'):
                merger.merge_results(self.pdf, [source])
        with self.assertRaisesRegex(ValueError, 'input'):
            merger.merge_results(self.pdf, [])

    def test_cli_rejects_input_output_and_sidecar_aliases_without_changes(self):
        for output_is_sidecar in [False, True]:
            with self.subTest(output_is_sidecar=output_is_sidecar):
                source = self.sidecar if output_is_sidecar else self.output
                source.write_text(json.dumps(self.bundle([1])))
                before = source.read_bytes()
                result = self.cli([source])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(source.read_bytes(), before)
                source.unlink()
        original = self.pdf.read_bytes()
        source = self.save('single.json', self.bundle([1]))
        self.output = self.pdf
        self.assertNotEqual(self.cli([source]).returncode, 0)
        self.assertEqual(self.pdf.read_bytes(), original)

    def test_cli_rejects_symlink_hardlink_and_directory_outputs_before_any_write(self):
        source = self.save('single.json', self.bundle([1]))
        original = source.read_bytes()
        for target in [self.output, self.sidecar]:
            for kind in ['symlink', 'hardlink', 'directory']:
                with self.subTest(target=target.name, kind=kind):
                    if kind == 'symlink':
                        target.symlink_to(source)
                    elif kind == 'hardlink':
                        os.link(source, target)
                    else:
                        target.mkdir()
                    result = self.cli([source])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(source.read_bytes(), original)
                    other = self.sidecar if target == self.output else self.output
                    self.assertFalse(other.exists())
                    target.rmdir() if kind == 'directory' else target.unlink()
        self.output = self.root / 'same.provenance.json'
        result = self.cli([source])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_pair_publication_rolls_back_if_bundle_replace_fails(self):
        sources = self.inputs()
        bundle, manifest = merger.merge_results(self.pdf, sources)
        self.output.write_bytes(b'old bundle')
        self.sidecar.write_bytes(b'old receipt')
        real_replace = os.replace

        def fail_bundle(source, target):
            if pathlib.Path(target) == self.output:
                raise OSError('Synthetic bundle publication failure')
            return real_replace(source, target)

        with mock.patch.object(merger.os, 'replace', side_effect=fail_bundle):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                merger.write_outputs(self.output, bundle, manifest, [self.pdf, *sources])
        self.assertEqual(self.output.read_bytes(), b'old bundle')
        self.assertEqual(self.sidecar.read_bytes(), b'old receipt')
        self.assertFalse(list(self.root.glob('.readest-ovis-*')))
        self.sidecar.unlink()
        with mock.patch.object(merger.os, 'replace', side_effect=fail_bundle):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                merger.write_outputs(self.output, bundle, manifest, [self.pdf, *sources])
        self.assertFalse(self.sidecar.exists())
        self.assertEqual(self.output.read_bytes(), b'old bundle')

    def test_all_serialization_and_staging_finishes_before_publication(self):
        sources = self.inputs()
        bundle, manifest = merger.merge_results(self.pdf, sources)
        self.output.write_bytes(b'old bundle')
        self.sidecar.write_bytes(b'old receipt')
        manifest['unsupported'] = object()
        with self.assertRaises(TypeError):
            merger.write_outputs(self.output, bundle, manifest, [self.pdf, *sources])
        self.assertEqual(self.output.read_bytes(), b'old bundle')
        self.assertEqual(self.sidecar.read_bytes(), b'old receipt')
        del manifest['unsupported']
        real_write = merger.atomic_write
        calls = 0

        def fail_second_stage(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('Synthetic disk full')
            return real_write(*args)

        with mock.patch.object(merger, 'atomic_write', side_effect=fail_second_stage):
            with self.assertRaisesRegex(OSError, 'disk full'):
                merger.write_outputs(self.output, bundle, manifest, [self.pdf, *sources])
        self.assertEqual(self.output.read_bytes(), b'old bundle')
        self.assertEqual(self.sidecar.read_bytes(), b'old receipt')
        self.assertFalse(list(self.root.glob('.readest-ovis-*')))

    def test_failure_does_not_replace_existing_bundle_or_sidecar(self):
        self.output.write_bytes(b'previous bundle')
        self.sidecar.write_bytes(b'previous receipt')
        invalid = self.bundle([1])
        invalid['pages'][0]['blocks'][0]['id'] = ''
        result = self.cli([self.save('good.json', self.bundle([2])), self.save('bad.json', invalid)])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'previous bundle')
        self.assertEqual(self.sidecar.read_bytes(), b'previous receipt')
        self.assertFalse(list(self.root.glob('.readest-ovis-*')))


if __name__ == '__main__':
    unittest.main()
