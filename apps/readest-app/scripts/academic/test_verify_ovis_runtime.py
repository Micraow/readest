"""Synthetic read-only resource checks; never load a model or start inference."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch


HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location('ovis_runtime_check', HERE / 'verify-ovis-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_PATH'), 'Linux descriptor inspection')
class RuntimeInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.file = self.root / 'bin' / 'synthetic'
        self.file.parent.mkdir()
        self.file.write_bytes(b'fixed bytes')
        self.artifact = ('bin/synthetic', 11, hashlib.sha256(b'fixed bytes').hexdigest(), False)

    def inspect(self, artifact=None):
        fd = runtime._open_root(self.root)
        try:
            return runtime._inspect_artifact(fd, artifact or self.artifact)['status']
        finally:
            os.close(fd)

    def report(self):
        with patch.object(runtime, 'ARTIFACTS', (self.artifact,)), \
                patch.object(runtime.platform, 'system', return_value='Linux'), \
                patch.object(runtime.platform, 'machine', return_value='x86_64'):
            return runtime.inspect_runtime(str(self.root))

    def test_matching_candidate_stays_unavailable_with_specific_blockers(self):
        before = self.file.read_bytes()
        result = self.report()
        self.assertEqual(result['integrity'], 'verified')
        self.assertEqual(result['availability'], 'unavailable')
        self.assertEqual(result['blockers'], list(runtime.BLOCKERS))
        self.assertEqual(self.file.read_bytes(), before)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_same_size_modified_bytes(self):
        self.file.write_bytes(b'wrong bytes')
        self.assertEqual(self.inspect(), 'hash-mismatch')

    def test_wrong_size(self):
        self.file.write_bytes(b'short')
        self.assertEqual(self.inspect(), 'size-mismatch')

    def test_missing_artifact(self):
        self.file.unlink()
        self.assertEqual(self.inspect(), 'resource-missing')
        self.assertEqual(self.report()['integrity'], 'failed')

    def test_leaf_symlink_never_followed(self):
        target = self.root / 'target'
        self.file.rename(target)
        self.file.symlink_to(target)
        self.assertEqual(self.inspect(), 'unsafe-resource')

    def test_dangling_leaf_symlink(self):
        self.file.unlink()
        self.file.symlink_to(self.root / 'absent')
        self.assertEqual(self.inspect(), 'unsafe-resource')

    def test_parent_symlink_never_followed(self):
        self.file.parent.rename(self.root / 'actual')
        (self.root / 'bin').symlink_to(self.root / 'actual', target_is_directory=True)
        self.assertEqual(self.inspect(), 'unsafe-resource')

    def test_root_symlink_never_followed(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.file.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            runtime._open_root(alias)

    def test_directory_and_fifo_rejected_without_reading(self):
        self.file.unlink()
        for create in (self.file.mkdir, lambda: os.mkfifo(self.file)):
            create()
            with patch.object(runtime.os, 'read', side_effect=AssertionError('Must not read')):
                self.assertEqual(self.inspect(), 'unsafe-resource')
            if self.file.is_dir():
                self.file.rmdir()
            else:
                self.file.unlink()

    def test_executable_mode_required_only_for_cli(self):
        self.file.chmod(0o600)
        executable = (*self.artifact[:3], True)
        self.assertEqual(self.inspect(executable), 'not-executable')
        self.assertEqual(self.inspect(), 'verified')
        self.file.chmod(0o700)
        self.assertEqual(self.inspect(executable), 'verified')

    def test_invalid_relative_pin(self):
        for name in ('../outside', '/outside', 'bin/../synthetic', 'bin//synthetic'):
            with self.subTest(name=name):
                self.assertEqual(self.inspect((name, *self.artifact[1:])), 'invalid-pin')

    def test_unsupported_platform_does_not_open_package(self):
        for system, machine in [('Windows', 'AMD64'), ('Darwin', 'arm64'), ('Linux', 'aarch64')]:
            with self.subTest(system=system, machine=machine), \
                    patch.object(runtime.platform, 'system', return_value=system), \
                    patch.object(runtime.platform, 'machine', return_value=machine), \
                    patch.object(runtime, '_open_root', side_effect=AssertionError('Must not open')):
                result = runtime.inspect_runtime(str(self.root))
                self.assertEqual(result['blockers'][0], 'unsupported-platform')
                self.assertEqual(result['integrity'], 'not-checked')

    def test_invalid_and_missing_roots_have_stable_codes(self):
        for name in ('relative', '/tmp/../other', '//ambiguous'):
            with self.subTest(name=name):
                self.assertEqual(runtime.inspect_runtime(name)['blockers'][0], 'invalid-package-root')
        self.assertEqual(runtime.inspect_runtime(str(self.root / 'absent'))['blockers'][0],
                         'resource-missing')

    def test_changed_while_reading_is_rejected(self):
        read = os.read
        changed = False

        def change(fd, count):
            nonlocal changed
            result = read(fd, count)
            if not changed:
                changed = True
                self.file.write_bytes(b'newer bytes')
            return result

        with patch.object(runtime.os, 'read', side_effect=change):
            self.assertEqual(self.inspect(), 'resource-changed')

    def test_cli_cannot_signal_readiness_even_when_integrity_matches(self):
        with patch.object(runtime, 'inspect_runtime', return_value=self.report()):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(runtime.main(['--root', str(self.root)]), 2)
            self.assertEqual(json.loads(out.getvalue())['availability'], 'unavailable')

    def test_source_pins_and_fixed_profile_match_current_runner(self):
        runner_spec = importlib.util.spec_from_file_location('runner', HERE / 'run-ovis-pdf.py')
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)
        args = runner.parser().parse_args([
            '--pdf', 'a', '--cli', 'b', '--model', 'c', '--mmproj', 'd', '--prompt', 'e',
            '--output-dir', 'f', '--runtime-revision', runtime.LLAMA_REVISION])
        for name, value in runtime.PROFILE.items():
            self.assertEqual(getattr(args, name), value, name)
        for relative, size, expected, _ in runtime.ARTIFACTS:
            if relative.startswith('scripts/'):
                source = HERE / relative.split('/', 1)[1]
                self.assertEqual(source.stat().st_size, size)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main()
