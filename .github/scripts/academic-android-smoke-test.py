#!/usr/bin/env python3
"""Lightweight guard tests; no Android SDK, emulator, network, or private PDF."""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load('academic-android-smoke')
ui = load('academic-android-smoke-ui')


class ArtifactGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'artifact.zip'

    def make_zip(self, entries):
        with zipfile.ZipFile(self.path, 'w') as archive:
            for name, data in entries:
                archive.writestr(name, data)

    def test_allowlisted_entry(self):
        self.make_zip([('apk.part00', b'ok')])
        self.assertEqual(smoke.zip_entries(self.path, {'apk.part00': 2}), {'apk.part00': b'ok'})

    def test_traversal_and_extra_files_rejected(self):
        for name in ['../apk.part00', '/apk.part00', 'private-key.p12']:
            with self.subTest(name=name):
                self.make_zip([(name, b'x')])
                with self.assertRaises(RuntimeError):
                    smoke.zip_entries(self.path, {'apk.part00': 2})

    def test_duplicate_entries_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.make_zip([('apk.part00', b'x'), ('apk.part00', b'y')])
        with self.assertRaises(RuntimeError):
            smoke.zip_entries(self.path, {'apk.part00': 2})

    def test_oversize_entry_rejected(self):
        self.make_zip([('apk.part00', b'xxx')])
        with self.assertRaises(RuntimeError):
            smoke.zip_entries(self.path, {'apk.part00': 2})

    def test_symlink_rejected(self):
        entry = zipfile.ZipInfo('apk.part00')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_zip([(entry, b'key')])
        with self.assertRaises(RuntimeError):
            smoke.zip_entries(self.path, {'apk.part00': 10})

    def manifests(self):
        return ({'sourceCommit': smoke.SOURCE, 'fileName': 'Readest-Academic-arm64-unsigned.apk',
                 'fileBytes': smoke.APK_BYTES, 'fileSha256': smoke.APK_SHA,
                 'parts': [dict(name=n, bytes=b, sha256=h) for n,b,h in smoke.PARTS]},
                {'sourceCommit': smoke.SOURCE, 'sourceTree': smoke.TREE, 'apkBytes': smoke.APK_BYTES,
                 'apkSha256': smoke.APK_SHA, 'sourceIntegrity': {'passed': True},
                 'apkValidation': {'passed': True, 'native': {'abis': ['arm64-v8a']}},
                 'applicationId': smoke.APP_ID, 'javaJniNamespace': 'com.bilingify.readest', 'installable': False})

    def test_valid_manifest_contract(self):
        smoke.validate_manifests(*self.manifests())

    def test_provenance_mismatch_rejected(self):
        for key, value in [('sourceCommit', 'other'), ('sourceTree', 'other'), ('installable', True),
                           ('applicationId', 'com.bilingify.readest'), ('sourceIntegrity', {'passed': False}),
                           ('apkValidation', {'passed': True, 'native': {'abis': ['x86_64']}})]:
            with self.subTest(key=key):
                transfer, provenance = self.manifests()
                provenance[key] = value
                with self.assertRaises(RuntimeError):
                    smoke.validate_manifests(transfer, provenance)

    def test_part_order_is_pinned(self):
        transfer, provenance = self.manifests()
        transfer['parts'].reverse()
        with self.assertRaises(RuntimeError):
            smoke.validate_manifests(transfer, provenance)

    def test_signature_exclusion_does_not_hide_other_payload_changes(self):
        original = Path(self.tmp.name) / 'original.apk'
        original.write_bytes(b'')
        with zipfile.ZipFile(original, 'w') as archive:
            archive.writestr('classes.dex', b'original')
        self.make_zip([('classes.dex', b'original'), ('META-INF/CERT.RSA', b'temporary signature')])
        self.assertEqual(smoke.payload(original), smoke.payload(self.path))
        self.make_zip([('classes.dex', b'changed'), ('META-INF/CERT.RSA', b'temporary signature')])
        self.assertNotEqual(smoke.payload(original), smoke.payload(self.path))


class ImageAndUIGuards(unittest.TestCase):
    def metadata(self):
        return f'''<sdk><license id="android-sdk-license">test terms\n</license>
        <remotePackage path="{smoke.IMAGE}"><revision><major>16</major></revision>
        <uses-license ref="android-sdk-license"/><archives><archive><complete>
        <size>{smoke.IMAGE_BYTES}</size><checksum>{smoke.IMAGE_SHA1}</checksum>
        <url>x86_64-30_r16.zip</url></complete></archive></archives></remotePackage></sdk>'''

    def test_exact_official_image_metadata(self):
        info = smoke.image_metadata(self.metadata())
        self.assertEqual(info['compressedBytes'], 1438186618)
        self.assertEqual(info['licenseText'], 'test terms\n')

    def test_changed_image_or_size_rejected(self):
        for old,new in [('1438186618', '1610612737'), ('<major>16', '<major>17'),
                        (smoke.IMAGE_SHA1, 'bad'), ('x86_64-30_r16.zip', '../other.zip')]:
            with self.subTest(old=old), self.assertRaises(RuntimeError):
                smoke.image_metadata(self.metadata().replace(old, new))

    def node(self, **kwargs):
        import xml.etree.ElementTree as ET
        return ET.Element('node', {'package': smoke.APP_ID, 'bounds': '[10,20][110,120]',
                                  'enabled': 'true', 'text': 'Import Books', **kwargs})

    def test_selector_requires_expected_package_and_visible_bounds(self):
        self.assertTrue(ui.matches(self.node(), ['Import Books'], {smoke.APP_ID}))
        self.assertFalse(ui.matches(self.node(package='com.android.permissioncontroller'), ['Import Books'], {smoke.APP_ID}))
        self.assertFalse(ui.matches(self.node(bounds='[0,0][0,0]'), ['Import Books'], {smoke.APP_ID}))
        self.assertFalse(ui.matches(self.node(bounds='[0,0][9999,9999]'), ['Import Books'], {smoke.APP_ID}))

    def test_no_substring_dialog_approval(self):
        self.assertFalse(ui.matches(self.node(text='Import Books and grant all permissions'), ['Import Books'], {smoke.APP_ID}))

    def test_workflow_is_bounded_and_deliberate(self):
        workflow = Path(__file__).parents[1].joinpath('workflows/academic-android-smoke.yml').read_text()
        self.assertIn('[smoke-academic-android]', workflow)
        self.assertIn('timeout-minutes: 20', workflow)
        self.assertIn('runs-on: ubuntu-24.04', workflow)
        self.assertIn('actions: read', workflow)
        self.assertNotIn('matrix:', workflow)
        self.assertNotIn('sudo ', workflow)
        self.assertNotIn('yes |', workflow)
        self.assertNotIn('secrets.', workflow)
        self.assertIn('path: smoke-evidence/', workflow)


if __name__ == '__main__':
    unittest.main()
