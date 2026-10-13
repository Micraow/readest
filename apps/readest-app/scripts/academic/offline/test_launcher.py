"""Synthetic launcher regressions: no model execution or network."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', pathlib.Path(__file__).with_name('launch.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        for name in ('bin', 'models', 'python', 'scripts'):
            (self.root / name).mkdir()
        self.file = self.root / 'models' / 'example.gguf'
        self.file.write_bytes(b'synthetic, not a model')
        self.entry = {'path': 'models/example.gguf', 'bytes': self.file.stat().st_size,
                      'sha256': hashlib.sha256(self.file.read_bytes()).hexdigest()}
        self.manifest()
        self.patcher = patch.object(launcher, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def manifest(self):
        (self.root / 'SHA256-MANIFEST.json').write_text(json.dumps({'files': [self.entry]}))

    def test_complete(self):
        self.assertEqual(launcher.check_integrity(), 1)

    def test_changed_same_length(self):
        self.file.write_bytes(b'x' * self.entry['bytes'])
        with self.assertRaises(ValueError): launcher.check_integrity()

    def test_missing(self):
        self.file.unlink()
        with self.assertRaises(ValueError): launcher.check_integrity()

    def test_extra_runtime(self):
        (self.root / 'bin' / 'unlisted.so').write_bytes(b'extra')
        with self.assertRaises(ValueError): launcher.check_integrity()

    def test_symbolic_file(self):
        self.file.unlink()
        self.file.symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError): launcher.check_integrity()

    def test_parent_traversal(self):
        self.entry['path'] = '../example.gguf'
        self.manifest()
        with self.assertRaises(ValueError): launcher.check_integrity()

    def test_absolute_path(self):
        self.entry['path'] = '/example.gguf'
        self.manifest()
        with self.assertRaises(ValueError): launcher.check_integrity()

class LaunchTests(unittest.TestCase):
    def common(self, args, memory=10000):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch('sys.argv', ['run.sh'] + args))
        stack.enter_context(patch.object(launcher.platform, 'system', return_value='Linux'))
        stack.enter_context(patch.object(launcher.platform, 'machine', return_value='x86_64'))
        stack.enter_context(patch.object(launcher.platform, 'libc_ver', return_value=('glibc','2.38')))
        stack.enter_context(patch.object(launcher, 'check_integrity', return_value=1))
        stack.enter_context(patch.object(launcher, 'memory_available_mib', return_value=memory))
        child = stack.enter_context(patch.object(launcher.subprocess, 'run', return_value=types.SimpleNamespace(stdout='version',stderr='')))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return stack, child

    def test_check_does_not_load_model(self):
        stack, child = self.common(['--check'], 1)
        load = stack.enter_context(patch.object(launcher.importlib.util, 'spec_from_file_location', side_effect=AssertionError('model startup')))
        self.assertEqual(launcher.main(), 0)
        child.assert_called_once()
        self.assertEqual(child.call_args.args[0][-1], '--version')
        self.assertEqual(child.call_args.kwargs['cwd'], launcher.ROOT / 'bin')
        load.assert_not_called()

    def test_default_refuses_low_memory(self):
        stack, _ = self.common(['a.pdf','new-output'], 6143)
        load = stack.enter_context(patch.object(launcher.importlib.util, 'spec_from_file_location', side_effect=AssertionError('must not load')))
        with self.assertRaisesRegex(ValueError,'6144'): launcher.main()
        load.assert_not_called()

    def test_low_profile_refuses_low_memory(self):
        self.common(['--low-memory','a.pdf','new-output'], 3071)
        with self.assertRaisesRegex(ValueError,'3072'): launcher.main()

    def test_invalid_threads(self):
        _, child = self.common(['--check','--threads','9'])
        with self.assertRaises(ValueError): launcher.main()
        child.assert_not_called()

    def test_old_glibc(self):
        _, child = self.common(['--check'])
        with patch.object(launcher.platform, 'libc_ver', return_value=('glibc','2.37')):
            with self.assertRaises(ValueError): launcher.main()
        child.assert_not_called()

    def test_unsupported_arch(self):
        _, child = self.common(['--check'])
        with patch.object(launcher.platform, 'machine', return_value='aarch64'):
            with self.assertRaises(ValueError): launcher.main()
        child.assert_not_called()

    def test_fixed_default_and_low_profile_arguments(self):
        for low in (False, True):
            with self.subTest(low=low):
                stack, _ = self.common((['--low-memory'] if low else []) + ['a b.pdf','new output'])
                actual = {}
                fake = types.SimpleNamespace(parser=lambda:types.SimpleNamespace(parse_args=lambda a:actual.setdefault('args',a)),cancel=lambda *a:None,run=lambda a:{'coverage':{'coveredPages':[1]}})
                stack.enter_context(patch.object(launcher.importlib.util,'spec_from_file_location',return_value=types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m:None))))
                stack.enter_context(patch.object(launcher.importlib.util,'module_from_spec',return_value=fake))
                stack.enter_context(patch.object(launcher.signal,'signal'))
                self.assertEqual(launcher.main(),0)
                args=actual['args']
                def value(flag):return args[args.index(flag)+1]
                self.assertEqual(value('--image-max-tokens'),'1024' if low else '2048')
                self.assertEqual(value('--max-rss-mib'),'2048' if low else '4096')
                self.assertEqual(value('--flash-attn'),'on')
                self.assertEqual(value('--pdf'),str(pathlib.Path('a b.pdf').absolute()))
                self.assertEqual(value('--model'),str(launcher.ROOT/'models/OvisOCR2-Q3_K_M.gguf'))
                stack.close()

if __name__=='__main__':unittest.main()
