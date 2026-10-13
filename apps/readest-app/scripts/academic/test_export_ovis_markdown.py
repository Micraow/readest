"""Synthetic raw-output export tests; no research inputs or model run required."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import fitz

SCRIPT = pathlib.Path(__file__).with_name('export-ovis-result.py')
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('exporter', SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RawExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.pdf = self.root / 'arbitrary renamed source.pdf'
        with fitz.open() as document:
            for index in range(4):
                page = document.new_page(width=400, height=600)
                page.insert_text((30, 30), f'Synthetic page {index + 1}')
                page.draw_rect(fitz.Rect(40, 120, 160, 240), color=(1, 0, 0))
                page.draw_rect(fitz.Rect(220, 120, 340, 240), color=(0, 0, 1))
            document.save(self.pdf)
        self.markdown = self.root / 'unrelated-output-name.md'
        self.identity = {
            'modelSha256': 'a' * 64,
            'projectorSha256': 'b' * 64,
            'promptSha256': 'c' * 64,
            'runtimeRevision': 'd' * 40,
            'configuration': {'temperature': 0, 'local': True},
        }
        self.raw = (
            '# Arbitrary heading\n\n'
            'A statement $^{7}$ and `$^{7}$`.\n\n'
            'Panel Alpha\n\n<img src="images/bbox_100_200_400_400.jpg" />\n\n'
            'Panel Beta\n\n<img src="images/bbox_550_200_850_400.jpg" />\n\n'
            'Figure 31: Related panels $^{7}$.\n\n'
            '$$\nx_{i}^{2} = \\frac{a}{b} \\tag{52}\n\n+y_i\n$$\n\n'
            '<table><tr><td>$a_b$</td><td>Raw O0 text</td></tr></table>\n\n'
            '$^{7}$ A preserved note.\n\nFinal sentence.'
        )
        self.markdown.write_text(self.raw, encoding='utf-8')

    def export(self, **kwargs):
        return exporter.export_markdown(
            self.pdf, 3, self.markdown, self.identity, self.root / 'assets', **kwargs
        )

    def test_arbitrary_page_preserves_math_figures_notes_and_receipts(self):
        bundle, receipt = self.export()
        self.assertEqual(bundle['pageCount'], 4)
        self.assertEqual(bundle['identity'], self.identity)
        page = bundle['pages'][0]
        self.assertEqual(page['page'], 3)
        self.assertEqual((page['width'], page['height']), (400, 600))
        figures = [block for block in page['blocks'] if block['kind'] == 'visual']
        self.assertEqual(len(figures), 1)
        self.assertIn('Figure 31:', figures[0]['caption'])
        self.assertTrue(any(block.get('markdown') == 'Panel Alpha' for block in page['blocks']))
        self.assertIn('Panel Beta', figures[0]['caption'])
        notes = [block for block in page['blocks'] if block['kind'] == 'footnote']
        self.assertEqual(len(notes), 1)
        self.assertIn(f"[7](#{notes[0]['id']})", figures[0]['caption'])
        self.assertIn('[↩](#ovis-', notes[0]['markdown'])
        texts = [block['markdown'] for block in page['blocks'] if block['kind'] == 'markdown']
        self.assertIn('$$\nx_{i}^{2} = \\frac{a}{b} \\tag{52}\n\n+y_i\n$$', texts)
        self.assertIn('<table><tr><td>$a_b$</td><td>Raw O0 text</td></tr></table>', texts)
        self.assertTrue(any('`$^{7}$`' in text for text in texts))
        self.assertEqual(receipt['source']['pdfSha256'], sha(self.pdf))
        self.assertEqual(receipt['source']['markdownSha256'], sha(self.markdown))
        self.assertEqual(receipt['source']['page'], 3)
        self.assertEqual(receipt['source']['binding'], 'caller-declared')
        self.assertFalse(receipt['verification']['nativeMathChecked'])
        self.assertFalse(receipt['verification']['ocrAccuracyChecked'])
        self.assertEqual(len(receipt['crops']), 1)
        crop = receipt['crops'][0]
        self.assertEqual(crop['blockId'], figures[0]['id'])
        self.assertEqual(crop['box'], figures[0]['box'])
        self.assertEqual(len(crop['modelBoxes']), 2)
        self.assertEqual(crop['sha256'], sha(self.root / crop['asset']))
        box = figures[0]['box']
        clip = fitz.Rect(box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
        with fitz.open(self.pdf) as document:
            expected = document[2].get_pixmap(dpi=crop['dpi'], clip=clip, alpha=False).tobytes('png')
        self.assertEqual(crop['sha256'], hashlib.sha256(expected).hexdigest())
        self.assertNotIn(str(self.root), json.dumps(bundle))
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_names_content_labels_and_page_numbers_are_not_cases(self):
        first, _ = self.export()
        self.markdown.write_text(self.raw.replace('Alpha', 'Jupiter').replace('Beta', 'Saturn').replace('31:', '906:'))
        self.pdf.rename(self.root / 'no-case-name.pdf')
        self.pdf = self.root / 'no-case-name.pdf'
        second, _ = exporter.export_markdown(self.pdf, 4, self.markdown, self.identity, self.root / 'other-assets')
        figure = next(block for block in second['pages'][0]['blocks'] if block['kind'] == 'visual')
        old = next(block for block in first['pages'][0]['blocks'] if block['kind'] == 'visual')
        self.assertEqual(figure['box'], old['box'])
        self.assertTrue(any(block.get('markdown') == 'Panel Jupiter' for block in second['pages'][0]['blocks']))
        self.assertIn('Saturn', figure['caption'])
        self.assertIn('Figure 906:', figure['caption'])
        self.assertEqual(second['pages'][0]['page'], 4)

    def test_unclaimed_image_has_its_own_crop(self):
        self.markdown.write_text('<img src="images/bbox_110_210_420_450.jpg" />')
        bundle, receipt = self.export()
        self.assertEqual(bundle['pages'][0]['blocks'][0]['box'], {'x': 44, 'y': 126, 'width': 124, 'height': 144})
        self.assertEqual(len(receipt['crops']), 1)

    def test_invalid_pages_do_not_use_python_negative_indexing(self):
        for page in [0, -1, 5, True, 1.5]:
            with self.subTest(page=page), self.assertRaisesRegex(ValueError, 'page'):
                exporter.export_markdown(self.pdf, page, self.markdown, self.identity, self.root / 'assets')

    def test_hash_mismatches_are_rejected_before_assets(self):
        for keyword in ['expected_pdf_sha256', 'expected_markdown_sha256']:
            with self.subTest(keyword=keyword), self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.export(**{keyword: '0' * 64})
        self.assertFalse((self.root / 'assets').exists())
        self.export(expected_pdf_sha256=sha(self.pdf), expected_markdown_sha256=sha(self.markdown))

    def test_missing_invalid_and_full_page_geometry_is_rejected(self):
        for markup in [
            '<img src="images/picture.jpg" />',
            '![Figure](unknown.png)',
            '<img src="images/bbox_0_0_1001_200.jpg" />',
            '<img src="images/bbox_20_30_20_80.jpg" />',
            '<img src="images/bbox_100_100_90_200.jpg" />',
            '<img src="images/bbox_-1_10_200_300.jpg" />',
            '<img src="images/bbox_0_0_1000_1000.jpg" />',
            '<img src="images/bbox_0_0_400_1000.jpg" />\n\n<img src="images/bbox_600_0_1000_1000.jpg" />\n\nFigure 2: Full union.',
        ]:
            with self.subTest(markup=markup):
                self.markdown.write_text(markup)
                with self.assertRaisesRegex(ValueError, 'geometry|bounds|whole.page'):
                    self.export()
        self.assertFalse((self.root / 'assets').exists())

    def test_code_is_not_an_image_or_a_footnote_definition(self):
        code = '```md\n\n<img src="unknown.png" />\n\n$^{7}$ literal\n\n```'
        self.markdown.write_text('Call $^{7}$.\n\n' + code + '\n\n$^{7}$ Actual note.')
        bundle, _ = self.export()
        blocks = bundle['pages'][0]['blocks']
        self.assertEqual(sum(block['kind'] == 'footnote' for block in blocks), 1)
        self.assertTrue(any(block.get('markdown') == code for block in blocks))

    def test_tilde_and_long_fences_keep_literal_content(self):
        for fence in ['~~~', '````']:
            with self.subTest(fence=fence):
                code = fence + 'md\n\n$^{8}$ literal\n\n```\n\n<img src="unknown.png" />\n' + fence
                self.markdown.write_text('Call $^{8}$.\n\n' + code + '\n\n$^{8}$ Actual note.')
                bundle, _ = self.export()
                blocks = bundle['pages'][0]['blocks']
                self.assertEqual(sum(block['kind'] == 'footnote' for block in blocks), 1)
                self.assertTrue(any(block.get('markdown') == code for block in blocks))

    def test_short_body_before_figure_is_not_hidden_as_a_label(self):
        self.markdown.write_text('Important preliminary observation\n\n<img src="images/bbox_100_200_400_400.jpg" />\n\nFigure 12: A chart.')
        bundle, _ = self.export()
        blocks = bundle['pages'][0]['blocks']
        self.assertEqual(blocks[0]['kind'], 'markdown')
        self.assertEqual(blocks[0]['markdown'], 'Important preliminary observation')
        self.assertEqual(blocks[1]['kind'], 'visual')
        self.assertNotIn('Important preliminary observation', blocks[1]['caption'])

    def test_html_and_indented_code_do_not_create_images_or_notes(self):
        for code in [
            '<pre>\n\n$^{8}$ literal\n\n<img src="unknown.png" />\n\n</pre>',
            '<code>$^{8}$ literal <img src="unknown.png" /></code>',
            '    <img src="images/bbox_100_200_400_400.jpg" />',
            '\t<img src="images/bbox_100_200_400_400.jpg" />',
            '    $^{8}$ literal',
        ]:
            with self.subTest(code=code):
                self.markdown.write_text('Call $^{8}$.\n\n' + code + '\n\n$^{8}$ Actual note.')
                bundle, receipt = self.export()
                blocks = bundle['pages'][0]['blocks']
                self.assertEqual(sum(block['kind'] == 'footnote' for block in blocks), 1)
                self.assertEqual(receipt['crops'], [])
                self.assertTrue(any(block.get('markdown') == code for block in blocks))

    def test_note_call_only_in_code_does_not_move_unreferenced_note(self):
        for code in ['<code>$^{8}$</code>', '    $^{8}$', '<pre>\n\n$^{8}$\n\n</pre>']:
            with self.subTest(code=code):
                self.markdown.write_text(code + '\n\n$^{8}$ Unreferenced note.')
                bundle, _ = self.export()
                self.assertTrue(all(block['kind'] == 'markdown' for block in bundle['pages'][0]['blocks']))

    def test_literal_code_delimiters_cannot_swallow_later_figures(self):
        for code in ['The delimiter is `$$`.', 'The tag is `<table>`.',
                     '<code>$$</code>', '<pre>\n```\n</pre>', '<pre>\n<table>\n</pre>']:
            with self.subTest(code=code):
                self.markdown.write_text(code + '\n\n<img src="images/bbox_100_200_400_400.jpg" />\n\nFigure 29: Chart.')
                bundle, receipt = self.export()
                blocks = bundle['pages'][0]['blocks']
                self.assertEqual(blocks[0]['markdown'], code)
                self.assertEqual(blocks[1]['kind'], 'visual')
                self.assertEqual(len(receipt['crops']), 1)

    def test_literal_open_html_inside_markdown_code_cannot_split_math(self):
        formula = '$$\nx+y\n\n=z\n$$'
        for code in ['Use `<code>` here.', 'Use ``<pre> ` literal`` here.',
                     '```html\n<pre>\n```', '~~~html\n<code>\n~~~', '    <pre>']:
            with self.subTest(code=code):
                self.markdown.write_text(code + '\n\n' + formula)
                bundle, _ = self.export()
                texts = [block['markdown'] for block in bundle['pages'][0]['blocks']]
                self.assertEqual(texts, [code, formula])

    def test_ambiguous_or_unreferenced_note_definitions_stay_in_body(self):
        raw = 'Call $^{2}$.\n\n$^{2}$ One.\n\n$^{2}$ Two.\n\n$^{9}$ Not referenced.'
        self.markdown.write_text(raw)
        bundle, _ = self.export()
        blocks = bundle['pages'][0]['blocks']
        self.assertTrue(all(block['kind'] == 'markdown' for block in blocks))
        self.assertEqual('\n\n'.join(block['markdown'] for block in blocks), raw)

    def test_note_calls_in_figure_labels_are_linked(self):
        self.markdown.write_text('<img src="images/bbox_100_200_400_400.jpg" />\n\nPanel $^{5}$\n\n<img src="images/bbox_550_200_850_400.jpg" />\n\nFigure 22: A chart.\n\n$^{5}$ Label note.')
        bundle, _ = self.export()
        blocks = bundle['pages'][0]['blocks']
        note = next(block for block in blocks if block['kind'] == 'footnote')
        self.assertIn(f"[5](#{note['id']})", blocks[0]['caption'])
        self.assertIn(f"[↩](#{blocks[0]['id']})", note['markdown'])

    def test_rotated_pdf_is_rejected_without_crop_artifacts(self):
        rotated = self.root / 'rotated.pdf'
        with fitz.open(self.pdf) as document:
            document[2].set_rotation(90)
            document.save(rotated)
        self.pdf = rotated
        with self.assertRaisesRegex(ValueError, 'unrotated'):
            self.export()
        self.assertFalse((self.root / 'assets').exists())

    def test_invalid_identity_and_empty_output_are_rejected(self):
        for identity in [{}, {**self.identity, 'modelSha256': 'invalid'}, {**self.identity, 'configuration': {'nested': {}}}]:
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, 'identity'):
                exporter.export_markdown(self.pdf, 3, self.markdown, identity, self.root / 'assets')
        self.markdown.write_text('  \n\n')
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.export()

    def assert_linked_crop_is_rejected(self, hardlink=False):
        self.markdown.write_text('<img src="images/bbox_100_200_400_400.jpg" />')
        assets = self.root / 'assets'
        assets.mkdir()
        target = assets / f'ovis-{sha(self.pdf)[:12]}-p3-b0.png'
        if hardlink:
            os.link(self.pdf, target)
        else:
            target.symlink_to(self.pdf)
        before = self.pdf.read_bytes()
        try:
            with self.assertRaisesRegex(ValueError, 'overwrite|linked|source'):
                self.export()
        finally:
            self.assertEqual(self.pdf.read_bytes(), before)

    def test_crop_cannot_follow_a_symlink_to_pdf(self):
        self.assert_linked_crop_is_rejected()

    def test_crop_cannot_overwrite_a_hardlinked_pdf(self):
        self.assert_linked_crop_is_rejected(hardlink=True)

    def test_crop_cannot_overwrite_raw_markdown(self):
        assets = self.root / 'assets'
        assets.mkdir()
        self.markdown = assets / f'ovis-{sha(self.pdf)[:12]}-p3-b0.png'
        self.markdown.write_text('<img src="images/bbox_100_200_400_400.jpg" />')
        before = self.markdown.read_bytes()
        try:
            with self.assertRaisesRegex(ValueError, 'overwrite|source'):
                self.export()
        finally:
            self.assertEqual(self.markdown.read_bytes(), before)

    def test_cli_emits_bundle_and_auditable_sidecar(self):
        identity = self.root / 'identity.json'
        identity.write_text(json.dumps(self.identity))
        output = self.root / 'page.ovis.json'
        result = subprocess.run([
            sys.executable, str(SCRIPT), '--pdf', str(self.pdf), '--page', '3',
            '--markdown', str(self.markdown), '--identity', str(identity), '--output', str(output),
            '--expected-pdf-sha256', sha(self.pdf), '--expected-markdown-sha256', sha(self.markdown),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(output.with_suffix('.provenance.json').read_text())
        self.assertEqual(receipt['bundleSha256'], sha(output))
        self.assertEqual(receipt['source']['identitySha256'], sha(identity))
        self.assertEqual(receipt['identity'], self.identity)
        self.assertEqual(json.loads(output.read_text())['pages'][0]['page'], 3)
        self.assertNotIn('native-math.json', [path.name for path in self.root.iterdir()])

    def test_reviewed_mode_keeps_table_and_native_formula_receipts(self):
        reviewed = self.root / 'reviewed'
        reviewed.mkdir()
        table = '<table><tr><td>Reviewed table</td><td>$x_2$</td></tr></table>'
        data = {
            'blocks.json': {'blocks': [
                {'id': 'b0', 'kind': 'table', 'markdown': table},
                {'id': 'b1', 'kind': 'text', 'markdown': '![Source equation](assets/math-7.png)'},
                {'id': 'b2', 'kind': 'text', 'markdown': '(17)'},
            ], 'notes': []},
            'native-math.json': {'pdf_sha256': sha(self.pdf), 'page_number': 3,
                                 'summary': {'checked': 1}},
            'receipt.json': {'figure_groups': [], 'source_formula_replacements': [
                {'source_crop': {'path': 'assets/math-7.png', 'bbox': [30, 300, 200, 330], 'sha256': 'e' * 64}},
            ], 'table_patch': {'reviewed': True, 'source_markdown_sha256': 'f' * 64}},
        }
        for name, value in data.items():
            (reviewed / name).write_text(json.dumps(value))
        before = {path.name: sha(path) for path in reviewed.iterdir()}
        identity = self.root / 'identity.json'
        identity.write_text(json.dumps(self.identity))
        output = self.root / 'reviewed.ovis.json'
        result = subprocess.run([
            sys.executable, str(SCRIPT), '--pdf', str(self.pdf), '--page', '3',
            '--result-dir', str(reviewed), '--identity', str(identity), '--output', str(output),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        blocks = json.loads(output.read_text())['pages'][0]['blocks']
        self.assertEqual(blocks[0]['markdown'], table)
        self.assertEqual(blocks[1]['role'], 'equation')
        self.assertEqual(blocks[1]['box'], {'x': 30, 'y': 300, 'width': 170, 'height': 30})
        self.assertEqual(blocks[2]['markdown'], '(17)')
        self.assertEqual(before, {path.name: sha(path) for path in reviewed.iterdir()})
        self.assertFalse(output.with_suffix('.provenance.json').exists())


if __name__ == '__main__':
    unittest.main()
