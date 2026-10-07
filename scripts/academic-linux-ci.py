#!/usr/bin/env python3
"""Prepare the pinned CEF SDK and export a native build for desktop acceptance.

The artifact contains only the unstripped app ELF and public provenance. Reuse
CEF locally only after matching every runtime-file hash in that provenance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

CEF_ARCHIVE = "cef_binary_151.3.24+g2384915+chromium-151.0.7922.174_linux64_minimal.tar.bz2"
CEF_SHA256 = "db53c43fdace8b7ee4af0f005120116d6973aa9d8eb7702c0617badf9be8684e"
CEF_SHA1 = "b1e99d3e3ff4213f99f7cda0211db89454398811"
RUNTIME = [
    "libcef.so", "libEGL.so", "libGLESv2.so", "libvk_swiftshader.so",
    "libvulkan.so.1", "vk_swiftshader_icd.json", "chrome-sandbox",
    "chrome_100_percent.pak", "chrome_200_percent.pak", "resources.pak",
    "icudtl.dat", "v8_context_snapshot.bin", "CREDITS.html", "LICENSE.txt",
]
PART_SIZE = 16 * 1024 * 1024


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def prepare_cef():
    cache = Path(os.environ["RUNNER_TEMP"]) / "readest-cef-cache"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "cef.tar.bz2"
    if not archive.exists():
        url = "https://cef-builds.spotifycdn.com/" + CEF_ARCHIVE.replace("+", "%2B")
        temporary = archive.with_suffix(".download")
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.rename(archive)
    if digest(archive) != CEF_SHA256:
        raise RuntimeError("Pinned CEF archive checksum mismatch")
    destination = Path(os.environ["CEF_PATH"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A fresh job extracts from the verified archive, never a stale SDK cache.
    if destination.exists():
        raise RuntimeError("CEF destination already exists")
    with tarfile.open(archive) as bundle:
        bundle.extractall(destination.parent, filter="data")
    extracted = destination.parent / CEF_ARCHIVE.removesuffix(".tar.bz2")
    (extracted / "Release").rename(destination)
    for resource in (extracted / "Resources").iterdir():
        resource.rename(destination / resource.name)
    for name in ["include", "cmake", "libcef_dll", "CMakeLists.txt", "CREDITS.html", "LICENSE.txt"]:
        (extracted / name).rename(destination / name)
    (destination / "archive.json").write_text(json.dumps({
        "type": "minimal", "name": CEF_ARCHIVE, "sha1": CEF_SHA1,
    }) + "\n")
    print(f"Verified and prepared CEF {CEF_SHA256}")


def export_artifact():
    repo = Path.cwd()
    binary = repo / "target/debug/readest"
    cef = Path(os.environ["CEF_PATH"])
    artifact = repo / "academic-linux-artifact"
    artifact.mkdir(exist_ok=False)
    runtime_files = [cef / name for name in RUNTIME] + sorted((cef / "locales").glob("*.pak"))
    if len(runtime_files) <= len(RUNTIME):
        raise RuntimeError("CEF locales missing")
    runtime_hashes = {str(path.relative_to(cef)): digest(path) for path in runtime_files}
    linkage_env = os.environ.copy()
    linkage_env["LD_LIBRARY_PATH"] = str(cef)
    linkage = command("ldd", str(binary), env=linkage_env)
    if "not found" in linkage:
        raise RuntimeError(linkage)
    source = command("git", "rev-parse", "HEAD")
    # Lockfile swapping and the production build must not alter tracked source.
    if command("git", "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Build changed tracked source")
    provenance = {
        "sourceCommit": source,
        "sourceTree": command("git", "rev-parse", "HEAD^{tree}"),
        "parserVersion": command("node", "--input-type=module", "-e",
            "import fs from 'node:fs'; const t=fs.readFileSync('apps/readest-app/src/services/academic/layout.ts','utf8'); console.log(t.match(/PARSER_VERSION = ['\"]([^'\"]+)/)[1]);"),
        "profile": "debug native / production frontend / no bundle",
        "nativeAcceptance": "pending: validate downloaded bytes in the desktop app",
        "binarySha256": digest(binary), "binaryBytes": binary.stat().st_size,
        "cefArchive": CEF_ARCHIVE, "cefArchiveSha256": CEF_SHA256,
        "cefRuntimeSha256": runtime_hashes,
        "lockfiles": {name: digest(repo / name) for name in ["Cargo.cef.lock", "pnpm-lock.yaml"]},
        "tools": {name: command(name, "--version") for name in ["rustc", "cargo", "node", "pnpm"]},
        "runnerOs": Path("/etc/os-release").read_text(),
        "packages": command("dpkg-query", "-W", "-f=${Package} ${Version}\n"),
        "ldd": linkage,
        "runUrl": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
    }
    metadata = artifact / "provenance.json"
    metadata.write_text(json.dumps(provenance, indent=2) + "\n")
    compressed = artifact / "native.tar.gz"
    with tarfile.open(compressed, "w:gz") as bundle:
        bundle.add(binary, arcname="readest")
        bundle.add(metadata, arcname="provenance.json")
        bundle.add(repo / "LICENSE", arcname="LICENSE")
    parts = []
    with compressed.open("rb") as stream:
        while data := stream.read(PART_SIZE):
            if len(parts) >= 8:
                raise RuntimeError("Native archive exceeds the bounded 128 MiB transfer budget")
            part = artifact / f"native.part{len(parts):02}"
            part.write_bytes(data)
            parts.append({"name": part.name, "bytes": len(data), "sha256": digest(part)})
    manifest = {"sourceCommit": source, "archiveSha256": digest(compressed),
                "archiveBytes": compressed.stat().st_size, "parts": parts}
    (artifact / "transfer.json").write_text(json.dumps(manifest, indent=2) + "\n")
    compressed.unlink()  # The checksummed parts are the transferred archive.
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["prepare-cef", "export-artifact"])
    args = parser.parse_args()
    {"prepare-cef": prepare_cef, "export-artifact": export_artifact}[args.step]()
