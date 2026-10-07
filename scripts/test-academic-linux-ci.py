#!/usr/bin/env python3
"""Exercise artifact transfer without compiling or using any user documents."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("academic_ci", Path(__file__).with_name("academic-linux-ci.py"))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class ArtifactTests(unittest.TestCase):
    def test_export_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "target/debug/readest"
            binary.parent.mkdir(parents=True)
            original = bytes(range(256)) * 100
            binary.write_bytes(original)
            binary.chmod(0o755)
            cef = root / "cef"
            (cef / "locales").mkdir(parents=True)
            for name in ci.RUNTIME + ["locales/en-US.pak"]:
                (cef / name).write_bytes(name.encode())
            for name in ["LICENSE", "Cargo.cef.lock", "pnpm-lock.yaml"]:
                (root / name).write_text(name)

            def command(*args, **kwargs):
                if args[:2] == ("git", "status"):
                    return ""
                if args[0] == "ldd":
                    return "libcef.so => verified"
                return "synthetic-provenance"

            env = {"CEF_PATH": str(cef), "GITHUB_REPOSITORY": "example/test", "GITHUB_RUN_ID": "1"}
            with patch.object(Path, "cwd", return_value=root), patch.object(ci, "command", command), \
                    patch.dict(os.environ, env), patch.object(ci, "PART_SIZE", 1024), patch("builtins.print"):
                ci.export_artifact()
            artifact = root / "academic-linux-artifact"
            manifest = json.loads((artifact / "transfer.json").read_text())
            data = b"".join((artifact / part["name"]).read_bytes() for part in manifest["parts"])
            self.assertGreater(len(manifest["parts"]), 1)
            self.assertEqual(hashlib.sha256(data).hexdigest(), manifest["archiveSha256"])
            self.assertEqual(len(data), manifest["archiveBytes"])
            for part in manifest["parts"]:
                self.assertEqual(ci.digest(artifact / part["name"]), part["sha256"])
            archive = root / "restored.tar.gz"
            archive.write_bytes(data)
            with ci.tarfile.open(archive) as bundle:
                self.assertEqual(set(bundle.getnames()), {"readest", "LICENSE", "provenance.json"})
                self.assertEqual(bundle.extractfile("readest").read(), original)
                self.assertEqual(bundle.getmember("readest").mode, 0o755)
                provenance = json.load(bundle.extractfile("provenance.json"))
                self.assertEqual(provenance["binarySha256"], ci.digest(binary))
                self.assertEqual(provenance["cefRuntimeSha256"]["locales/en-US.pak"], ci.digest(cef / "locales/en-US.pak"))

    def test_reject_corrupt_cached_cef(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "readest-cef-cache/cef.tar.bz2"
            archive.parent.mkdir()
            archive.write_bytes(b"corrupt archive")
            with patch.dict(os.environ, {"RUNNER_TEMP": tmp}):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    ci.prepare_cef()


if __name__ == "__main__":
    unittest.main()
