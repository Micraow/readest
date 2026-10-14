# SPDX-License-Identifier: AGPL-3.0-or-later
"""Synthetic receipts only: no models, documents, or network required."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
import warnings
import subprocess
import sys
import zipfile

SCRIPT = pathlib.Path(__file__).with_name('profile-ovis-run.py')
spec = importlib.util.spec_from_file_location('profile_ovis_run', SCRIPT)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.identity = {'modelSha256': 'a' * 64, 'projectorSha256': 'b' * 64,
                         'promptSha256': 'c' * 64, 'runtimeRevision': 'd' * 40,
                         'configuration': {'threads': 2, 'dpi': 144, 'cliSha256': 'e' * 64}}

    def make_run(self, name='run', elapsed=12, raw=b'Private synthetic OCR\n', stderr=None):
        root = self.root / name
        page = root / 'pages/page-000001'
        page.mkdir(parents=True)
        (root / 'result').mkdir()
        stderr = stderr if stderr is not None else (
            b'0.02.000.000 I mtmd batch encoding done in 2000 ms\n'
            b'llama_perf_context_print: prompt eval time = 3000.00 ms / 20 tokens\n'
            b'llama_perf_context_print:        eval time = 4000.00 ms / 30 runs\n')
        data = {'render.png': b'synthetic raster', 'raw.md': raw, 'stderr.log': stderr}
        execution = {'format': 'readest-ovis-page-execution', 'version': 1,
                     'source': {'pdfSha256': 'f' * 64, 'page': 1, 'renderSha256': sha(data['render.png'])},
                     'identity': copy.deepcopy(self.identity), 'status': 'process-completed',
                     'elapsedSeconds': elapsed - 1, 'rawSha256': sha(raw), 'stderrSha256': sha(stderr),
                     'peakSampledGroupRssBytes': 1024, 'childReaped': True, 'processGroupStopped': True,
                     'exitCode': 0, 'nativeFinishReason': 'unknown', 'generationCompleteness': 'unknown'}
        data['execution.json'] = json.dumps(execution).encode()
        for name, contents in data.items():
            (page / name).write_bytes(contents)
        receipt = {'format': 'readest-ovis-pdf-execution', 'version': 1,
                   'status': 'process-completed', 'elapsedSeconds': elapsed,
                   'source': {'pdfSha256': 'f' * 64, 'pageCount': 1}, 'identity': copy.deepcopy(self.identity),
                   'coverage': {'pageCount': 1, 'coveredPages': [1], 'missingPages': [], 'complete': True},
                   'pageArtifacts': {'pages/page-000001/' + name: sha(contents) for name, contents in data.items()}}
        (root / 'run.json').write_text(json.dumps(dict(receipt, status='publication-ready')))
        (root / 'result/run.json').write_text(json.dumps(receipt))
        return root

    def edit_receipt(self, root, edit):
        path = root / 'result/run.json'
        value = json.loads(path.read_text())
        edit(value)
        path.write_text(json.dumps(value))

    def test_profile_keeps_timing_and_excludes_content(self):
        result = profile.profile_run(self.make_run())
        self.assertEqual(result['timing']['pageProcessSeconds'], 11)
        self.assertEqual(result['timing']['outsidePageProcessesSeconds'], 1)
        self.assertEqual(result['timing']['imageEncodingSeconds'], 2)
        self.assertEqual(result['pages'][0]['nativeTimings']['promptEvalSeconds'], 3)
        self.assertEqual(result['pages'][0]['nativeTimings']['evalSeconds'], 4)
        self.assertNotIn('Private synthetic', json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertFalse(result['verification']['ocrAccuracyChecked'])

    def test_missing_timing_is_unknown_not_zero(self):
        result = profile.profile_run(self.make_run(stderr=b'ordinary warning\n'))
        self.assertIsNone(result['timing']['imageEncodingSeconds'])
        self.assertIsNone(result['pages'][0]['nativeTimings']['evalSeconds'])

    def test_multiple_image_batches_are_summed(self):
        result = profile.parse_timings('mtmd batch encoding done in 250 ms\nmtmd batch encoding done in 750 ms\n')
        self.assertEqual(result['imageEncodingSeconds'], 1)
        self.assertEqual(result['imageEncodingBatches'], 2)

    def test_repeated_context_summaries_are_not_double_counted(self):
        result = profile.parse_timings('llama_perf_context_print: eval time = 1 ms / 1 runs\n' * 2)
        self.assertIsNone(result['evalSeconds'])
        self.assertIn('ambiguous-eval-summary', result['warnings'])

    def test_nonfinite_or_negative_timings_rejected(self):
        for elapsed in (float('nan'), float('inf'), -1, True):
            with self.subTest(elapsed=elapsed):
                root = self.make_run(name=str(elapsed))
                self.edit_receipt(root, lambda r: r.update(elapsedSeconds=elapsed))
                with self.assertRaises(ValueError):
                    profile.profile_run(root)

    def test_changed_artifact_rejected(self):
        root = self.make_run()
        (root / 'pages/page-000001/stderr.log').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'hash'):
            profile.profile_run(root)

    def test_identity_mismatch_rejected(self):
        root = self.make_run()
        self.edit_receipt(root, lambda r: r['identity'].update(modelSha256='9' * 64))
        with self.assertRaisesRegex(ValueError, 'identity'):
            profile.profile_run(root)

    def test_bad_coverage_rejected(self):
        for pages in ([1, 1], [2], [True]):
            root = self.make_run(str(pages))
            self.edit_receipt(root, lambda r: r['coverage'].update(coveredPages=pages))
            with self.assertRaises(ValueError):
                profile.profile_run(root)

    def test_cancelled_run_has_no_speed_ratio(self):
        root = self.make_run()
        self.edit_receipt(root, lambda r: r.update(status='cancelled'))
        a = profile.profile_run(root)
        b = profile.profile_run(self.make_run('candidate'))
        result = profile.compare_runs(a, b)
        self.assertFalse(result['comparable'])
        self.assertIsNone(result['wallSpeedRatio'])

    def test_same_workload_ratio_and_changed_output(self):
        a = profile.profile_run(self.make_run('baseline', elapsed=12))
        b = profile.profile_run(self.make_run('candidate', elapsed=6, raw=b'different output'))
        result = profile.compare_runs(a, b)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['wallSpeedRatio'], 2)
        self.assertEqual(result['changedOutputPages'], [1])
        self.assertFalse(result['ocrAccuracyChecked'])

    def test_configuration_changes_block_comparison(self):
        a = profile.profile_run(self.make_run())
        self.identity['configuration']['threads'] = 8
        b = profile.profile_run(self.make_run('candidate'))
        result = profile.compare_runs(a, b)
        self.assertFalse(result['comparable'])
        self.assertIn('configuration.threads', result['mismatches'])

    def test_model_or_raster_changes_block_comparison(self):
        a = profile.profile_run(self.make_run())
        for section, key in [('identity', 'modelSha256'), ('source', 'pdfSha256')]:
            b = copy.deepcopy(a)
            b[section][key] = '0' * 64
            self.assertFalse(profile.compare_runs(a, b)['comparable'])
        b = copy.deepcopy(a)
        b['pages'][0]['renderSha256'] = '0' * 64
        self.assertFalse(profile.compare_runs(a, b)['comparable'])

    def test_zip_selection_does_not_mix_nested_runs(self):
        outer = self.make_run('outer')
        inner = self.make_run('inner', elapsed=6)
        archive = self.root / 'runs.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for directory, prefix in [(outer, 'results'), (inner, 'results/meta')]:
                for path in directory.rglob('*'):
                    if path.is_file():
                        z.write(path, prefix + '/' + path.relative_to(directory).as_posix())
        with self.assertRaisesRegex(ValueError, 'Multiple'):
            profile.profile_run(archive)
        result = profile.profile_run(archive, 'results/meta')
        self.assertEqual(result['timing']['runWallSeconds'], 6)

    def test_zip_single_root_autodetected(self):
        root = self.make_run()
        archive = self.root / 'run.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for path in root.rglob('*'):
                if path.is_file():
                    z.write(path, 'results/' + path.relative_to(root).as_posix())
        self.assertEqual(profile.profile_run(archive)['timing']['runWallSeconds'], 12)

    def test_zip_traversal_and_duplicate_names_rejected(self):
        for bad_name in ('../run.json', '/run.json', 'a\\run.json'):
            archive = self.root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(bad_name, '{}')
            with self.assertRaises(ValueError):
                profile.profile_run(archive)

    def test_symlink_artifacts_rejected(self):
        root = self.make_run()
        original = root / 'pages/page-000001/raw.md'
        target = self.root / 'outside'
        original.rename(target)
        original.symlink_to(target)
        with self.assertRaises(ValueError):
            profile.profile_run(root)

    def test_inconsistent_stage_time_is_reported_not_subtracted(self):
        result = profile.profile_run(self.make_run(stderr=b'mtmd batch encoding done in 999999 ms\n'))
        self.assertIn('native-stage-exceeds-process-wall', result['pages'][0]['nativeTimings']['warnings'])
        self.assertIsNone(result['timing']['imageEncodingSeconds'])

    def test_unknown_configuration_cannot_be_silently_ignored(self):
        root = self.make_run()
        self.edit_receipt(root, lambda r: r['identity']['configuration'].update(newSetting=1))
        with self.assertRaisesRegex(ValueError, 'Unknown configuration'):
            profile.profile_run(root)

    def test_configuration_cannot_leak_arbitrary_path_or_text(self):
        root = self.make_run()
        self.edit_receipt(root, lambda r: r['identity']['configuration'].update(runner='/private/path'))
        with self.assertRaisesRegex(ValueError, 'Unrecognized configuration value'):
            profile.profile_run(root)

    def test_unrelated_receipt_text_is_not_in_report(self):
        root = self.make_run()
        self.edit_receipt(root, lambda r: (r['source'].update(privateText='sensitive note'),
                                         r['coverage'].update(privateText='sensitive note')))
        self.assertNotIn('sensitive note', json.dumps(profile.profile_run(root)))

    def test_rss_field_cannot_carry_arbitrary_text(self):
        for value in ('private text', {'note': 'private text'}, True, -1):
            with self.subTest(value=value):
                root = self.make_run('rss-' + str(len(list(self.root.iterdir()))))
                page = root / 'pages/page-000001/execution.json'
                execution = json.loads(page.read_text())
                execution['peakSampledGroupRssBytes'] = value
                page.write_text(json.dumps(execution))
                self.edit_receipt(root, lambda r: r['pageArtifacts'].update(
                    {'pages/page-000001/execution.json': sha(page.read_bytes())}))
                with self.assertRaisesRegex(ValueError, 'RSS'):
                    profile.profile_run(root)

    def test_duplicate_zip_member_rejected(self):
        archive = self.root / 'duplicate.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('run.json', '{}')
                z.writestr('run.json', '{}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            profile.profile_run(archive)

    def test_oversized_artifact_rejected_before_read(self):
        root = self.make_run()
        with (root / 'pages/page-000001/raw.md').open('wb') as stream:
            stream.truncate(profile.MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(ValueError, 'bounded'):
            profile.profile_run(root)

    def test_nonpositive_comparison_duration_has_no_ratio(self):
        a = profile.profile_run(self.make_run())
        b = copy.deepcopy(a)
        b['timing']['runWallSeconds'] = 0
        self.assertIsNone(profile.compare_runs(a, b)['wallSpeedRatio'])

    def test_changed_code_hash_is_recorded_not_hidden(self):
        a = profile.profile_run(self.make_run())
        self.identity['configuration']['cliSha256'] = '1' * 64
        b = profile.profile_run(self.make_run('candidate'))
        comparison = profile.compare_runs(a, b)
        self.assertTrue(comparison['comparable'])
        self.assertEqual(comparison['producerCodeChanged'], ['cliSha256'])
        self.assertFalse(comparison['backendLibrariesIdentified'])

    def test_output_path_is_never_overwritten(self):
        root = self.make_run()
        output = self.root / 'profile.json'
        output.write_text('keep me')
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(root), '--output', str(output)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_text(), 'keep me')

    def test_native_image_prefill_batches_are_separate_from_encoding(self):
        timing = profile.parse_timings(
            '0.01.000.000 I mtmd batch encoding done in 1000 ms\n'
            '0.01.400.000 I image decoded (batch 1/2) in 400 ms\n'
            '0.02.000.000 I image decoded (batch 2/2) in 600 ms\n')
        self.assertEqual(timing['imageEncodingSeconds'], 1)
        self.assertEqual(timing['imagePrefillSeconds'], 1)
        self.assertEqual(timing['imagePrefillBatches'], 2)

    def test_image_prefill_is_unknown_when_logging_omits_it(self):
        timing = profile.parse_timings('mtmd batch encoding done in 1000 ms\n')
        self.assertIsNone(timing['imagePrefillSeconds'])
        self.assertEqual(timing['imagePrefillBatches'], 0)

    def test_incomplete_image_prefill_log_is_not_a_full_phase(self):
        timing = profile.parse_timings('image decoded (batch 1/2) in 1000 ms\n')
        self.assertIsNone(timing['imagePrefillSeconds'])
        self.assertIn('incomplete-image-prefill-batches', timing['warnings'])

    def test_multiple_images_have_separate_prefill_batch_sequences(self):
        timing = profile.parse_timings(
            'image decoded (batch 1/1) in 100 ms\n'
            'image decoded (batch 1/2) in 200 ms\n'
            'image decoded (batch 2/2) in 300 ms\n')
        self.assertAlmostEqual(timing['imagePrefillSeconds'], .6)
        self.assertEqual(timing['imagePrefillBatches'], 3)


if __name__ == '__main__':
    unittest.main()
