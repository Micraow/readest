"""Original synthetic PDFs and fake local children; no models or network needed."""
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import fitz

SCRIPT = pathlib.Path(__file__).with_name('run-ovis-pdf.py')

FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, signal, subprocess, sys, time
args = sys.argv[1:]
def arg(flag): return args[args.index(flag) + 1]
mode = pathlib.Path(arg('--file')).read_text().strip()
page_dir = pathlib.Path(arg('--image')).parent
page = int(page_dir.name.split('-')[-1])
(page_dir / 'child.json').write_text(json.dumps({'pid': os.getpid(), 'args': args,
    'cwd': str(pathlib.Path.cwd()),
    'page': page, 'llamaEnv': [k for k in os.environ if k.startswith('LLAMA_ARG_')],
    'threadEnv': {k: os.environ[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}}))
if mode == 'sleep':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    (page_dir / 'grandchild.pid').write_text(str(grandchild.pid))
    time.sleep(60)
if mode == 'rss':
    memory = bytearray(80 * 1024 * 1024)
    time.sleep(60)
if mode == 'mutate': pathlib.Path(arg('--model')).write_bytes(b'changed')
if mode == 'mutate-identity': (page_dir.parent.parent / 'identity.json').write_text('{}')
if mode == 'mutate-previous' and page == 2: (page_dir.parent / 'page-000001/raw.md').write_text('Changed')
if mode == 'block-publication': (page_dir.parent.parent / '.publication').touch(exist_ok=True)
if mode == 'descendants': subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
if mode == 'nonzero':
    sys.stdout.buffer.write(b'Partial text\\n')
    sys.exit(7)
if mode == 'empty': sys.exit(0)
if mode == 'invalid-utf8':
    sys.stdout.buffer.write(b'\\xff')
    sys.exit(0)
# The long first page is deliberately slower; a parallel runner could reorder it.
time.sleep(0.04 if page == 1 else 0)
sys.stdout.buffer.write(('Page %d: exact raw bytes.\\r\\n\\n$ x + y $\\n' % page).encode())
# Performance output does not authenticate a finish reason or emitted-token count.
sys.stderr.write('llama_perf_context_print: eval time = 4 ms / 1 runs\\n')
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux /proc process-group accounting')
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.pdf = self.root / 'synthetic.pdf'
        with fitz.open() as pdf:
            for index in range(3):
                page = pdf.new_page(width=240 + index * 10, height=360)
                page.insert_text((20, 30), f'Original synthetic page {index + 1}')
            pdf.save(self.pdf)
        self.cli = self.root / 'fake-cli'
        self.cli.write_text(FAKE)
        self.cli.chmod(0o700)
        self.model, self.mmproj, self.prompt = [self.root / name for name in ('model', 'mmproj', 'prompt')]
        self.model.write_bytes(b'synthetic model')
        self.mmproj.write_bytes(b'synthetic projector')
        self.prompt.write_text('normal')
        self.output = self.root / 'output'

    def command(self, *extra):
        return [sys.executable, str(SCRIPT), '--pdf', str(self.pdf), '--cli', str(self.cli),
                '--model', str(self.model), '--mmproj', str(self.mmproj), '--prompt', str(self.prompt),
                '--runtime-revision', 'd' * 40, '--output-dir', str(self.output),
                '--page-timeout-seconds', '5', '--kill-grace-seconds', '0.1', *extra]

    def run_cli(self, mode='normal', *extra):
        self.prompt.write_text(mode)
        return subprocess.run(self.command(*extra), capture_output=True, text=True, timeout=15)

    def receipt(self):
        return json.loads((self.output / 'run.json').read_text())

    def assert_failed(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.output / 'result').exists())
        self.assertIn(self.receipt()['status'], ('failed', 'cancelled'))

    def test_complete_order_exact_raw_bytes_and_truthful_finish(self):
        environment = dict(os.environ, LLAMA_ARG_THREADS='99', LLAMA_ARG_MODEL_URL='https://invalid.example')
        result = subprocess.run(self.command('--flash-attn', 'on'), capture_output=True, text=True, env=environment, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        final = self.output / 'result'
        bundle = json.loads((final / 'bundle.json').read_text())
        receipt = json.loads((final / 'run.json').read_text())
        self.assertEqual([page['page'] for page in bundle['pages']], [1, 2, 3])
        self.assertEqual(receipt['status'], 'process-completed')
        self.assertEqual(receipt['nativeFinishReason'], 'unknown')
        self.assertEqual(receipt['generationCompleteness'], 'unknown')
        self.assertTrue(receipt['coverage']['complete'])
        self.assertEqual(receipt['bundleSha256'], sha(final / 'bundle.json'))
        self.assertEqual(receipt['identity'], bundle['identity'])
        self.assertEqual(receipt['identity']['configuration']['flashAttention'], 'on')
        self.assertEqual(self.receipt()['status'], 'publication-ready')
        self.assertEqual(self.receipt()['terminalReceipt'], 'result/run.json')
        self.assertFalse(receipt['offline']['osNetworkIsolationVerified'])
        self.assertNotIn('generatedTokens', json.dumps(receipt))
        for number in range(1, 4):
            page_dir = self.output / 'pages' / f'page-{number:06d}'
            raw = page_dir / 'raw.md'
            self.assertEqual(raw.read_bytes(), f'Page {number}: exact raw bytes.\r\n\n$ x + y $\n'.encode())
            execution = json.loads((page_dir / 'execution.json').read_text())
            provenance = json.loads((page_dir / 'bundle.provenance.json').read_text())
            self.assertEqual(execution['nativeFinishReason'], 'unknown')
            self.assertEqual(execution['source']['page'], number)
            self.assertEqual(execution['source']['pdfSha256'], sha(self.pdf))
            self.assertEqual(execution['rawSha256'], sha(raw))
            self.assertEqual(provenance['source']['markdownSha256'], sha(raw))
            child = json.loads((page_dir / 'child.json').read_text())
            self.assertEqual(child['page'], number)
            self.assertEqual(child['cwd'], str(self.cli.resolve().parent))
            for flag in ('--model', '--mmproj', '--file', '--image'):
                self.assertTrue(pathlib.Path(child['args'][child['args'].index(flag) + 1]).is_absolute())
            self.assertEqual(child['llamaEnv'], [])
            self.assertEqual(set(child['threadEnv'].values()), {'2'})
            self.assertIn('--offline', child['args'])
            self.assertEqual(child['args'][child['args'].index('--threads') + 1], '2')
            self.assertEqual(child['args'][child['args'].index('--gpu-layers') + 1], '0')
            self.assertIn('--no-mmproj-offload', child['args'])
            self.assertEqual(child['args'][child['args'].index('--flash-attn') + 1], 'on')

    def test_cli_resets_inherited_ignored_sigchld_before_spawning(self):
        result = subprocess.run(
            self.command(), capture_output=True, text=True, timeout=15,
            preexec_fn=lambda: signal.signal(signal.SIGCHLD, signal.SIG_IGN))
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / 'result/run.json').read_text())
        self.assertEqual(receipt['status'], 'process-completed')

    def test_empty_nonzero_and_invalid_utf8_never_publish(self):
        for mode in ('empty', 'nonzero', 'invalid-utf8'):
            with self.subTest(mode=mode):
                self.output = self.root / mode
                self.assert_failed(self.run_cli(mode))
                self.assertEqual(len(list((self.output / 'pages').glob('page-*'))), 1)

    def test_timeout_kills_and_reaps(self):
        result = self.run_cli('sleep', '--page-timeout-seconds', '0.25')
        self.assert_failed(result)
        execution = json.loads((self.output / 'pages/page-000001/execution.json').read_text())
        self.assertEqual(execution['status'], 'timeout')
        self.assertTrue(execution['childReaped'])
        self.assertTrue(execution['processGroupStopped'])

    def test_rss_limit(self):
        result = self.run_cli('rss', '--max-rss-mib', '40')
        self.assert_failed(result)
        execution = json.loads((self.output / 'pages/page-000001/execution.json').read_text())
        self.assertEqual(execution['status'], 'rss-limit')
        self.assertGreater(execution['peakSampledGroupRssBytes'], 40 * 1024 * 1024)

    def test_parent_signals_stop_child_group(self):
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signum=signum):
                self.output = self.root / f'cancel-{signum}'
                self.prompt.write_text('sleep')
                process = subprocess.Popen(self.command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                marker = self.output / 'pages/page-000001/grandchild.pid'
                deadline = time.monotonic() + 8
                while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                if not marker.exists():
                    process.kill()
                    out, err = process.communicate()
                    self.fail(out + err)
                process.send_signal(signum)
                out, err = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 128 + signum, out + err)
                self.assertEqual(self.receipt()['status'], 'cancelled')
                self.assertFalse((self.output / 'result').exists())
                execution = json.loads((marker.parent / 'execution.json').read_text())
                self.assertTrue(execution['childReaped'])
                self.assertTrue(execution['processGroupStopped'])
                child_pid = json.loads((marker.parent / 'child.json').read_text())['pid']
                self.assertFalse(pathlib.Path(f'/proc/{child_pid}').exists())

    def test_existing_directory_and_input_collision_are_untouched(self):
        self.output.mkdir()
        sentinel = self.output / 'sentinel'
        sentinel.write_text('keep')
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        before = self.pdf.read_bytes()
        self.output = self.pdf
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.pdf.read_bytes(), before)

    def test_identity_change_fails_without_publication(self):
        self.assert_failed(self.run_cli('mutate'))
        self.assertIn('identity changed', self.receipt()['error'].lower())

    def test_identity_file_change_fails_without_publication(self):
        self.assert_failed(self.run_cli('mutate-identity'))
        self.assertIn('identity changed', self.receipt()['error'].lower())

    def test_completed_page_tampering_fails_without_publication(self):
        self.assert_failed(self.run_cli('mutate-previous'))
        self.assertIn('artifact identity changed', self.receipt()['error'].lower())

    def test_unicode_and_space_paths(self):
        self.output = self.root / '精确 raw output'
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / 'result/bundle.json').is_file())

    def test_live_descendants_are_stopped_and_fail_the_run(self):
        self.assert_failed(self.run_cli('descendants'))
        execution = json.loads((self.output / 'pages/page-000001/execution.json').read_text())
        self.assertEqual(execution['status'], 'unexpected-descendants')
        self.assertTrue(execution['liveDescendantsAfterChildExit'])
        self.assertTrue(execution['processGroupStopped'])

    def test_publication_preparation_failure_leaves_no_final_bundle(self):
        self.assert_failed(self.run_cli('block-publication'))
        self.assertEqual(self.receipt()['coverage']['coveredPages'], [1, 2, 3])

    def test_rotated_encrypted_and_empty_pdfs_rejected_preflight(self):
        original = self.pdf.read_bytes()
        for mode in ('rotation', 'encryption', 'empty-password-encryption', 'empty'):
            with self.subTest(mode=mode):
                self.output = self.root / f'bad-{mode}'
                if mode == 'empty':
                    self.pdf.write_bytes(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF')
                else:
                    with fitz.open(stream=original, filetype='pdf') as document:
                        if mode == 'rotation':
                            document[1].set_rotation(90)
                            data = document.tobytes()
                        else:
                            data = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,
                                                    user_pw='' if mode == 'empty-password-encryption' else 'synthetic',
                                                    owner_pw='synthetic-owner')
                    self.pdf.write_bytes(data)
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertFalse(self.output.exists())

    def test_empty_prompt_and_invalid_revision_rejected(self):
        self.assertNotEqual(self.run_cli('').returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertNotEqual(self.run_cli('normal', '--runtime-revision', 'not-a-revision').returncode, 0)
        self.assertFalse(self.output.exists())


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux waitid ownership')
class ProcessIdentityTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('ovis_runner_ownership', SCRIPT)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)

    def test_loader_working_directory_is_not_the_writable_page_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            runtime = root / 'fixed runtime'
            page = root / 'writable page'
            runtime.mkdir()
            page.mkdir()
            # A harmless file named like a ggml backend. The synthetic child
            # observes the loader search location; it never loads this file.
            (page / 'libggml-poison-test.so').write_bytes(b'not a shared library')
            cli = runtime / 'synthetic-cli'
            cli.write_text(
                '#!' + sys.executable + '\n'
                'import json, pathlib\n'
                'print(json.dumps({"cwd": str(pathlib.Path.cwd()), '
                '"backends": [p.name for p in pathlib.Path.cwd().glob("libggml-*.so")]}))\n')
            cli.chmod(0o700)
            self.runner.infer(
                [str(cli)], page,
                SimpleNamespace(threads=1, page_timeout_seconds=3, max_rss_mib=100,
                                kill_grace_seconds=0.05),
                time.monotonic() + 5, {}, {})
            observed = json.loads((page / 'raw.md').read_text())
            self.assertEqual(observed['cwd'], str(runtime.resolve()))
            self.assertEqual(observed['backends'], [])

    def test_relative_executable_is_rejected_before_spawn(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(self.runner.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'absolute executable'):
                self.runner.infer(
                    ['relative-cli'], pathlib.Path(temporary),
                    SimpleNamespace(threads=1), time.monotonic() + 5, {}, {})
            spawn.assert_not_called()

    def test_group_leader_is_not_reaped_before_last_group_signal(self):
        child = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
        original = self.runner.signal_group
        signals = []
        try:
            deadline = time.monotonic() + 5
            while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)

            def require_owned_leader(group, signum):
                self.assertEqual(group, child.pid)
                self.assertIsNone(child.returncode, 'Group leader was reaped before a group signal')
                self.assertIsNotNone(os.waitid(os.P_PID, child.pid,
                                              os.WEXITED | os.WNOHANG | os.WNOWAIT))
                signals.append(signum)
                return original(group, signum)

            with patch.object(self.runner, 'signal_group', require_owned_leader):
                self.assertTrue(self.runner.stop_group(child, 0.05))
            self.assertEqual(signals, [signal.SIGTERM, signal.SIGKILL])
            self.assertEqual(child.returncode, 0)
        finally:
            child.wait(timeout=5)

    def test_inference_does_not_poll_reap_before_cleanup(self):
        parent = self
        children = []
        base = subprocess.Popen

        class OwnedChild(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                children.append(self)

            def poll(self):
                parent.fail('Inference must observe exit without poll() reaping its leader')

        try:
            with tempfile.TemporaryDirectory() as temporary, patch.object(self.runner.subprocess, 'Popen', OwnedChild):
                receipt = self.runner.infer(
                    [sys.executable, '-c', 'print("Original synthetic output")'],
                    pathlib.Path(temporary),
                    SimpleNamespace(threads=1, page_timeout_seconds=3, max_rss_mib=100,
                                    kill_grace_seconds=0.05),
                    time.monotonic() + 5, {}, {})
                self.assertEqual(receipt['status'], 'process-completed')
                self.assertTrue(receipt['childReaped'])
                self.assertTrue(receipt['processGroupStopped'])
        finally:
            for child in children:
                child.wait(timeout=5)

    def test_lost_child_ownership_keeps_a_truthful_raw_receipt(self):
        base = subprocess.Popen

        class ExternallyReapedChild(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                os.waitpid(self.pid, 0)  # Popen has no exit status from this other reaper.

        with tempfile.TemporaryDirectory() as temporary:
            page = pathlib.Path(temporary)
            with patch.object(self.runner.subprocess, 'Popen', ExternallyReapedChild), \
                    patch.object(self.runner, 'signal_group') as group_signal:
                with self.assertRaises(Exception):
                    self.runner.infer(
                        [sys.executable, '-c', 'print("Preserved synthetic raw")'], page,
                        SimpleNamespace(threads=1, page_timeout_seconds=3, max_rss_mib=100,
                                        kill_grace_seconds=0.05),
                        time.monotonic() + 5, {}, {})
                group_signal.assert_not_called()
            receipt = json.loads((page / 'execution.json').read_text())
            self.assertEqual(receipt['status'], 'ownership-lost')
            self.assertIsNone(receipt['exitCode'])
            self.assertFalse(receipt['processGroupStopped'])
            self.assertEqual(receipt['rawSha256'], sha(page / 'raw.md'))
            self.assertEqual((page / 'raw.md').read_text(), 'Preserved synthetic raw\n')


if __name__ == '__main__':
    unittest.main()
