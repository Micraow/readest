"""Synthetic PDF font measurements; no paper-specific content or coordinates."""
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock

import fitz

SCRIPT = pathlib.Path(__file__).with_name('export-ovis-result.py')
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('exporter', SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class SourceFontSizeTests(unittest.TestCase):
    def document(self, width=400, height=600):
        document = fitz.open()
        self.addCleanup(document.close)
        document.new_page(width=width, height=height)
        return document

    def test_measures_font_size_not_glyph_height_or_page_size(self):
        for font in ['helv', 'tiro', 'cour']:
            for size in [6.5, 10, 18]:
                for width, height in [(300, 500), (800, 1000)]:
                    with self.subTest(font=font, size=size, page=(width, height)):
                        document = self.document(width, height)
                        page = document[0]
                        page.insert_text((40, 80), 'x + y = z', fontsize=size, fontname=font)
                        self.assertAlmostEqual(
                            exporter.measure_source_font_size(page, [30, 40, 250, 100]), size,
                            places=4,
                        )

    def test_uniform_source_scaling_preserves_crop_to_font_ratio(self):
        original = self.document()
        original[0].insert_text((40, 80), 'a + b = c', fontsize=11)
        bounds = fitz.Rect(35, 65, 105, 85)
        for scale in [0.5, 1, 2.25]:
            with self.subTest(scale=scale):
                scaled = self.document(400 * scale, 600 * scale)
                scaled[0].show_pdf_page(scaled[0].rect, original, 0)
                crop = bounds * fitz.Matrix(scale, scale)
                size = exporter.measure_source_font_size(scaled[0], crop)
                self.assertAlmostEqual(size, 11 * scale, places=4)
                # The reader's crop.width * readerFontSize / sourceFontSize
                # stays the same when the source PDF itself is enlarged.
                for reader_size in [12, 16, 24]:
                    self.assertAlmostEqual(crop.width * reader_size / size,
                                           bounds.width * reader_size / 11, places=4)

    def test_nonuniform_source_transforms_do_not_claim_a_scalar_font_size(self):
        original = self.document()
        original[0].insert_text((40, 80), 'x+y=z', fontsize=12)
        for x_scale, y_scale in [(2, 1), (1, 2), (0.5, 1.5)]:
            with self.subTest(x_scale=x_scale, y_scale=y_scale):
                transformed = self.document(400 * x_scale, 600 * y_scale)
                transformed[0].show_pdf_page(transformed[0].rect, original, 0,
                                             keep_proportion=False)
                self.assertIsNone(exporter.measure_source_font_size(
                    transformed[0], transformed[0].rect,
                ))

    def test_fonts_with_normalized_boxes_keep_uniform_but_not_nonuniform_scales(self):
        # This built-in font has ascender - descender < 1 em. PyMuPDF repairs
        # its bbox to one em even under nonuniform transformations; do not use
        # the repaired height as independent proof of the scalar font size.
        for embedded in [False, True]:
            original = self.document()
            name = 'zadb'
            if embedded:
                name = 'synthetic'
                original[0].insert_font(fontname=name, fontbuffer=fitz.Font('zadb').buffer)
            text = '✁✂✃✄✆' if embedded else 'a+b=c'
            original[0].insert_text((40, 80), text, fontsize=12, fontname=name)
            for x_scale, y_scale in [(1, 1), (0.5, 0.5), (2, 2), (2, 1), (1, 2)]:
                with self.subTest(embedded=embedded, x_scale=x_scale, y_scale=y_scale):
                    transformed = self.document(400 * x_scale, 600 * y_scale)
                    transformed[0].show_pdf_page(transformed[0].rect, original, 0,
                                                 keep_proportion=False)
                    measured = exporter.measure_source_font_size(transformed[0], transformed[0].rect)
                    if x_scale == y_scale:
                        self.assertAlmostEqual(measured, 12 * x_scale, places=4)
                    else:
                        self.assertIsNone(measured)

    def test_missing_or_conflicting_native_scale_evidence_is_not_guessed(self):
        document = self.document()
        document[0].insert_text((40, 80), 'x+y=z', fontsize=12)
        original_trace = document[0].get_texttrace()
        for trace in [[], original_trace + [{**original_trace[0], 'size': 18}]]:
            with self.subTest(trace=bool(trace)):
                page = Mock(wraps=document[0])
                page.get_texttrace.return_value = trace
                self.assertIsNone(exporter.measure_source_font_size(page, document[0].rect))

    def test_unmapped_unicode_cannot_hide_a_conflicting_scale_at_the_same_origin(self):
        document = self.document()
        document[0].insert_text((40, 80), 'x+y=z', fontsize=12)
        trace = document[0].get_texttrace()
        unmapped = {**trace[0], 'chars': tuple(
            (0xfffd, glyph, origin, box) for _, glyph, origin, box in trace[0]['chars']
        )}
        page = Mock(wraps=document[0])
        page.get_texttrace.return_value = trace + [{**unmapped, 'size': 18}]
        self.assertIsNone(exporter.measure_source_font_size(page, document[0].rect))
        # Without a character match, alignment remains conservatively unknown.
        page.get_texttrace.return_value = [unmapped]
        self.assertIsNone(exporter.measure_source_font_size(page, document[0].rect))

    def test_characters_not_spans_or_whitespace_weight_the_median(self):
        document = self.document()
        page = document[0]
        # The main-size letters are split across fonts; scripts contribute one
        # vote per character, never one vote per span or glyph area.
        page.insert_text((40, 90), 'a+b', fontsize=10, fontname='tiro')
        page.insert_text((65, 90), '=cd', fontsize=10, fontname='helv')
        page.insert_text((48, 83), '12', fontsize=6)
        page.insert_text((73, 95), '34', fontsize=6)
        page.insert_text((100, 90), ' ' * 30, fontsize=20)
        self.assertEqual(exporter.measure_source_font_size(page, [20, 50, 300, 110]), 10)

    def test_tight_crop_uses_character_positions_and_excludes_nearby_text(self):
        document = self.document()
        page = document[0]
        page.insert_text((40, 80), 'x+y=z', fontsize=10)
        page.insert_text((100, 80), 'Nearby heading outside the crop', fontsize=24)
        page.insert_text((40, 60), 'Above the crop', fontsize=20)
        # This ink crop is shorter than the native font's line-height bbox.
        self.assertEqual(exporter.measure_source_font_size(page, [39, 74, 75, 81]), 10)

    def test_only_in_crop_characters_count_from_an_intersecting_span(self):
        document = self.document()
        page = document[0]
        page.insert_text((40, 80), 'a+b=c', fontsize=10)
        page.insert_text((75, 80), 'Small neighboring text outside', fontsize=6)
        # Exactly the first smaller glyph is inside; the rest share its span.
        self.assertEqual(exporter.measure_source_font_size(page, [30, 50, 78, 100]), 10)

    def test_does_not_invent_an_average_between_distinct_middle_sizes(self):
        document = self.document()
        page = document[0]
        page.insert_text((40, 80), 'ab', fontsize=8)
        page.insert_text((60, 80), 'cd', fontsize=14)
        self.assertIsNone(exporter.measure_source_font_size(page, [30, 50, 150, 100]))

    def test_script_majority_and_larger_symbols_are_ambiguous(self):
        for main, scripts, large in [('x=y', '12345678', ''), ('x+y=z', '', '()'),
                                     ('x', '12345678', ''), ('x+y=z', '', '(')]:
            with self.subTest(main=main, scripts=scripts, large=large):
                document = self.document()
                page = document[0]
                page.insert_text((40, 80), main, fontsize=12)
                if scripts:
                    page.insert_text((50, 86), scripts, fontsize=8)
                if large:
                    page.insert_text((100, 88), large, fontsize=24)
                # Geometry alone cannot identify a minority larger character
                # as a primary letter or an enlarged mathematical symbol.
                self.assertIsNone(exporter.measure_source_font_size(page, [20, 40, 180, 110]))

    def test_empty_raster_only_and_invisible_text_have_no_measurement(self):
        document = self.document()
        page = document[0]
        self.assertIsNone(exporter.measure_source_font_size(page, page.rect))
        source = self.document()
        source[0].insert_text((40, 80), 'Raster equation', fontsize=10)
        page.insert_image(page.rect, pixmap=source[0].get_pixmap())
        page.insert_text((40, 80), 'Hidden OCR text', fontsize=18, render_mode=3)
        page.insert_text((40, 100), 'Transparent text', fontsize=20, fill_opacity=0)
        self.assertIsNone(exporter.measure_source_font_size(page, page.rect))

    def test_invalid_sizes_and_synthetic_characters_are_not_evidence(self):
        for size in [0, -1, float('nan'), float('inf')]:
            with self.subTest(size=size):
                page = Mock()
                page.get_text.return_value = {'blocks': [{'lines': [{'spans': [{
                    'size': size, 'alpha': 255, 'char_flags': 24,
                    'chars': [{'c': 'x', 'bbox': [1, 1, 2, 2]}],
                }]}]}]}
                self.assertIsNone(exporter.measure_source_font_size(page, [0, 0, 10, 10]))
        page.get_text.return_value['blocks'][0]['lines'][0]['spans'][0] = {
            'size': 10, 'alpha': 255, 'char_flags': 24,
            'chars': [{'c': 'x', 'bbox': [1, 1, 2, 2], 'synthetic': True}],
        }
        self.assertIsNone(exporter.measure_source_font_size(page, [0, 0, 10, 10]))

    def test_missing_native_visibility_metadata_is_not_assumed_visible(self):
        document = self.document()
        document[0].insert_text((40, 80), 'x+y=z', fontsize=10)
        for missing in ['alpha', 'char_flags']:
            with self.subTest(missing=missing):
                native = document[0].get_text('rawdict')
                del native['blocks'][0]['lines'][0]['spans'][0][missing]
                page = Mock(wraps=document[0])
                page.get_text.return_value = native
                self.assertIsNone(exporter.measure_source_font_size(page, [30, 50, 150, 100]))

    def test_unknown_visibility_inside_crop_cannot_bias_other_known_sizes(self):
        for missing in ['alpha', 'char_flags']:
            for unknown_size in [8, 12]:
                with self.subTest(missing=missing, unknown_size=unknown_size):
                    document = self.document()
                    document[0].insert_text((40, 80), 'x+y=z', fontsize=12)
                    document[0].insert_text((100, 86), '123', fontsize=8)
                    native = document[0].get_text('rawdict')
                    for block in native['blocks']:
                        for line in block['lines']:
                            for span in line['spans']:
                                if span['size'] == unknown_size:
                                    del span[missing]
                    page = Mock(wraps=document[0])
                    page.get_text.return_value = native
                    self.assertIsNone(exporter.measure_source_font_size(page, [30, 50, 150, 100]))
                    # Uncertain text beyond the crop cannot invalidate it.
                    if unknown_size == 8:
                        self.assertEqual(exporter.measure_source_font_size(page, [30, 50, 80, 100]), 12)

    def test_definitely_invisible_spans_need_not_prove_the_other_visibility_field(self):
        document = self.document()
        document[0].insert_text((40, 80), 'x+y=z', fontsize=12)
        document[0].insert_text((100, 80), 'Hidden', fontsize=18)
        for known_field in ['alpha', 'char_flags']:
            with self.subTest(known_field=known_field):
                native = document[0].get_text('rawdict')
                for block in native['blocks']:
                    for line in block['lines']:
                        for span in line['spans']:
                            if span['size'] == 18:
                                del span['alpha' if known_field == 'char_flags' else 'char_flags']
                                span[known_field] = 0
                page = Mock(wraps=document[0])
                page.get_text.return_value = native
                self.assertEqual(exporter.measure_source_font_size(page, [30, 50, 250, 100]), 12)

    def test_sub_point_measurements_do_not_bypass_the_reader_scale_floor(self):
        for size in [0.5, 0.999, 1]:
            with self.subTest(size=size):
                document = self.document()
                page = document[0]
                page.insert_text((10, 10), 'x+y=z', fontsize=size)
                measured = exporter.measure_source_font_size(page, page.rect)
                if size < 1:
                    self.assertIsNone(measured)
                else:
                    self.assertEqual(measured, 1)

    def test_reviewed_export_adds_only_equation_measurement_and_keeps_old_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = self.document()
            document[0].insert_text((40, 80), 'x + y = z', fontsize=9)
            document.save(root / 'source.pdf')
            digest = hashlib.sha256((root / 'source.pdf').read_bytes()).hexdigest()
            structure = {'blocks': [
                {'id': 'equation', 'kind': 'text', 'markdown': '![Source equation](assets/math.png)'},
                {'id': 'figure', 'kind': 'figure', 'asset': 'assets/figure.png',
                 'caption': 'Synthetic figure', 'labels': []},
                {'id': 'text', 'kind': 'text', 'markdown': '$x+y=z$'},
            ], 'notes': []}
            receipt = {'figure_groups': [{'asset': 'assets/figure.png', 'bbox': [30, 50, 150, 100]}],
                       'source_formula_replacements': [
                           {'source_crop': {'path': 'assets/math.png', 'bbox': [30, 50, 150, 100]}},
                       ]}
            for name, content in [('blocks.json', structure), ('receipt.json', receipt),
                                  ('native-math.json', {'pdf_sha256': digest, 'page_number': 1})]:
                (root / name).write_text(json.dumps(content))
            legacy = exporter.bundle_from_blocks(digest, 1, 400, 600, 1, structure, receipt, {})
            measured = exporter.export_result(root / 'source.pdf', 1, root, {})
            equation = measured['pages'][0]['blocks'][0]
            self.assertEqual(equation.pop('sourceFontSize'), 9)
            self.assertEqual(measured, legacy)


if __name__ == '__main__':
    unittest.main()
