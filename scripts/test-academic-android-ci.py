#!/usr/bin/env python3
"""Check parallel-install identity and artifact validation with synthetic inputs."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

spec = importlib.util.spec_from_file_location("academic_android", Path(__file__).with_name("academic-android-ci.py"))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


def elf(alignment=16384):
    data = bytearray(128)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", data, 18, 183)  # AArch64
    struct.pack_into("<Q", data, 32, 64)  # program header offset
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0, 0, 128, 128, alignment)
    return bytes(data)


class AndroidTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        self.base = (self.repo / ci.ANDROID / "app/src/main/AndroidManifest.xml").read_text()

    def test_rotated_signing_identity_can_coexist_with_previous_academic_install(self):
        self.assertEqual(ci.APP_ID, "com.bilingify.readest.academic.v2")
        self.assertEqual(ci.LABEL, "Readest 学术测试版 2")
        gradle = (self.repo / ci.ANDROID / "app/build.gradle.kts").read_text()
        self.assertIn('applicationId = if (academicBuild) "' + ci.APP_ID + '"', gradle)
        self.assertIn("val academicRevision = 14", gradle)
        self.assertNotEqual(ci.APP_ID, "com.bilingify.readest.academic")

    def test_parallel_manifest_preserves_imports_without_claiming_production_links(self):
        derived = ci.academic_manifest(self.base)
        root = ET.fromstring(derived)
        app = root.find("application")
        self.assertEqual(app.get(ci.A + "label"), ci.LABEL)
        self.assertEqual(app.get(ci.A + "extractNativeLibs"), "true")
        self.assertEqual(app.find("activity").get(ci.A + "name"), ci.NAMESPACE + ".MainActivity")
        self.assertEqual({node.get(ci.A + "scheme") for node in root.iter("data") if node.get(ci.A + "scheme")}, {"file", "content"})
        self.assertIn("application/pdf", derived)
        self.assertIn("android.intent.action.SEND", derived)
        self.assertIn("android.intent.category.LAUNCHER", derived)
        self.assertIn("${applicationId}.fileprovider", derived)
        self.assertNotIn("REQUEST_INSTALL_PACKAGES", derived)
        self.assertIn('android:scheme="readest"', self.base)

    def test_resolved_manifest_rejects_identity_and_provider_collisions(self):
        root = ET.fromstring(ci.academic_manifest(self.base).replace("${applicationId}", ci.APP_ID))
        root.set("package", ci.APP_ID)
        self.assertEqual(ci.manifest_errors(root), [])
        root.find("application/provider").set(ci.A + "authorities", ci.NAMESPACE + ".fileprovider")
        self.assertTrue(any("provider" in error for error in ci.manifest_errors(root)))
        root.set("package", ci.NAMESPACE)
        root.find("application").set(ci.A + "debuggable", "true")
        self.assertTrue(any("package" in error for error in ci.manifest_errors(root)))
        self.assertTrue(any("debuggable" in error for error in ci.manifest_errors(root)))

    def test_preflight_environment_lookup_stays_inside_its_temporary_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "source-app"
            android = app / "src-tauri/gen/android"
            (android / "app/src/main/res").mkdir(parents=True)
            (android / "app/src/academic").mkdir()
            (app / ".env").write_text("SENTRY_DSN=\n")
            (android / "build.gradle.kts").write_text("// generated root build\n")
            (android / "gradle.properties").write_text("org.gradle.workers.max=2\n")
            (android / "app/build.gradle.kts").write_text(
                (self.repo / ci.ANDROID / "app/build.gradle.kts").read_text())
            (android / "app/src/academic/AndroidManifest.xml").write_text(ci.academic_manifest(self.base))
            observed = []

            def gradle(args, **kwargs):
                probe = Path(args[args.index("-p") + 1])
                environment = (probe / "../../../.env").resolve()
                self.assertEqual(environment, probe.parents[2] / ".env")
                self.assertEqual(environment.read_text(), "SENTRY_DSN=\n")
                self.assertNotEqual(environment.parent, Path("/"))
                observed.append(probe)
                merged = probe / "app/build/intermediates/merged_manifests/release/AndroidManifest.xml"
                merged.parent.mkdir(parents=True)
                root = ET.fromstring(ci.academic_manifest(self.base).replace("${applicationId}", ci.APP_ID))
                root.set("package", ci.APP_ID)
                merged.write_text(ET.tostring(root, encoding="unicode"))

            with patch.object(ci, "APP", app), patch.object(ci, "ANDROID", android), \
                    patch.object(ci.subprocess, "run", side_effect=gradle), patch("builtins.print"):
                ci.preflight()
            self.assertEqual(len(observed), 1)
            self.assertFalse(observed[0].exists())

    def test_native_libraries_require_arm64_and_16k_load_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "test.apk"
            for path, library, expected in [
                ("lib/arm64-v8a/libapp.so", elf(), []),
                ("lib/arm64-v8a/libapp.so", elf(4096), ["16 KiB"]),
                ("lib/x86_64/libapp.so", elf(), ["arm64-v8a"]),
            ]:
                with zipfile.ZipFile(apk, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                    bundle.writestr(path, library)
                result = ci.inspect_native(apk)
                if expected:
                    self.assertTrue(any(expected[0] in error for error in result["errors"]))
                else:
                    self.assertEqual(result["errors"], [])
                    self.assertEqual(result["libraries"][0]["loadAlignments"], [16384])

    def test_transfer_round_trip_keeps_candidate_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = root / ci.APP / "src/services/academic/layout.ts"
            layout.parent.mkdir(parents=True)
            layout.write_text("export const PARSER_VERSION = 'academic-test';\n")
            apk = root / ci.ANDROID / "app/build/outputs/apk/universal/release/app-universal-release-unsigned.apk"
            apk.parent.mkdir(parents=True)
            payload = bytes(range(256)) * 10
            apk.write_bytes(payload)
            for name in ["Cargo.lock", "pnpm-lock.yaml"]:
                (root / name).write_text(name)
            source = {"passed": False, "diff": "unexpected tracked source change", "status": "M source"}
            validation = {"passed": False, "errors": ["synthetic identity mismatch"]}
            with patch.object(Path, "cwd", return_value=root), \
                    patch.object(ci, "inspect_apk", return_value=validation), \
                    patch.object(ci.shared, "inspect_source", return_value=source), \
                    patch.object(ci, "command", return_value="synthetic provenance"), \
                    patch.object(ci, "PART_SIZE", 1024), patch("builtins.print"):
                ci.export_artifact()
                with self.assertRaisesRegex(RuntimeError, "quarantined"):
                    ci.verify_candidate()
            out = root / ci.OUTPUT
            transfer = json.loads((out / "transfer.json").read_text())
            restored = b"".join((out / part["name"]).read_bytes() for part in transfer["parts"])
            self.assertEqual(restored, payload)
            self.assertEqual(transfer["fileSha256"], ci.digest(apk))
            self.assertGreater(len(transfer["parts"]), 1)
            for part in transfer["parts"]:
                self.assertEqual(part["sha256"], ci.digest(out / part["name"]))
            provenance = json.loads((out / "provenance.json").read_text())
            self.assertEqual(provenance["sourceIntegrity"], source)
            self.assertEqual(provenance["apkValidation"], validation)
            self.assertFalse(provenance["installable"])


if __name__ == "__main__":
    unittest.main()
