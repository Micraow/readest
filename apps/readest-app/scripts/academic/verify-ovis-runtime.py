#!/usr/bin/env python3
"""Inspect a fixed Linux Ovis resource candidate without loading or running it.

This is a developer packaging check, not a native authorization or launch API.
Pins identify the reviewed development bytes, not a reproducible/portable build.
Even a matching candidate remains Unavailable: see the explicit packaging and
native integration blockers in the report. No downloads or manifest overrides.
"""
import argparse
import errno
import hashlib
import json
import os
import platform
import stat
import sys

PROFILE_ID = 'ovis-linux-x86_64-cpu-v1'
LLAMA_REVISION = '5266f24da75dc449bd56cbed7addb9c8e4a6a73e'
MODEL_REVISION = 'dbd462d4e3fbbb85da78443e7e34e87d688dd8a0'
# Explicit runner settings; not a capability to launch with arbitrary argv.
PROFILE = {
    'threads': 2, 'dpi': 144, 'max_tokens': 4096, 'ctx_size': 8192,
    'image_max_tokens': 2048, 'max_rss_mib': 12288, 'flash_attn': 'off',
    'page_timeout_seconds': 900, 'wall_timeout_seconds': 3600,
    'kill_grace_seconds': 2,
}
# (relative path, exact size, SHA-256, must have an executable mode bit).
# These are code-owned pins. Never accept replacement hashes from the package.
ARTIFACTS = (
    ('scripts/run-ovis-pdf.py', 24672, '038e22ddcdeac9c10cb55fdb68f967b45b70e9b3872121c5b73e2f113bd1ee2d', False),
    ('scripts/export-ovis-result.py', 17842, '474c20552b3e9305fa3cb3c48d88e2f54fe648b64ca5f00d3e9183a26c661185', False),
    ('scripts/merge-ovis-results.py', 15277, '6b4030786512281d41c7d2a10b92481384f12dcc233dabd3d7603e8c28fe071c', False),
    ('scripts/ovis_markdown.py', 9020, '2e5496036eb1aeb6908cb4d3b8d170312cae670b10afcd2f2fbba2957df400e5', False),
    ('bin/libggml-base.so.0.23.0', 895640, '1298455b4fc7aa5375cf3f8f82073e345403f73bd25a4403b404cf145abf9237', False),
    ('bin/libggml-cpu.so.0.23.0', 1416488, '5d1fcce302bd4518815cd75525506c83575b4e8310fb766ed0cea02d575c2127', False),
    ('bin/libggml.so.0.23.0', 55920, '3c8640e33d3a5a9edc44b52ca268f32a185b696baed0773fb03242c447737063', False),
    ('bin/libllama-common.so.0.4.0', 5613704, '512b002435a1beb9e4d86443d5f5e66f311577e86520b3ef3aa5f406dfb6e2e4', False),
    ('bin/libllama.so.0.4.0', 4634368, '86a494b757be4303a07da708f030ad97bcbcadf4b91ef571a3f7976a9f8259f7', False),
    ('bin/libmtmd.so.0.4.0', 1915984, '66b6267b5f0d0eae51c6b1b9ce9678a7a11a906940f2849f187cb4c77f642218', False),
    ('bin/llama-mtmd-cli', 84000, '42921fefd96c11211a08e41c3d3c19a27fc15164aee3e449652c5a73bdb08b13', True),
    ('models/OvisOCR2-Q3_K_M.gguf', 466222464, '7b63233151df58d5513f9010c7beba99349492a9395a21dd6b64d85fb19a9c20', False),
    ('models/mmproj-OvisOCR2-Q8_0.gguf', 115923616, 'af67e31a365f791b416878ea77cbb321c0af6d5c97da0eac4a14ac2dca0701f6', False),
    ('prompt.txt', 514, 'e5de851c39df867918ea32a20830816cbb397b529bed59d21dce1fccdbbd5624', False),
)

# No runtime switch can clear these gates in this inspection-only stage.
BLOCKERS = (
    'controlled-python-pymupdf-runtime-not-packaged',
    'portable-loader-and-cpu-baseline-not-verified',
    'native-confirmation-and-job-entry-not-integrated',
)


def _directory_flags():
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_root(root):
    """Open every component without following links, including root ancestors."""
    raw = os.fspath(root)
    if not raw.startswith('/') or raw.startswith('//') or any(
            part in ('.', '..') for part in raw.split('/')):
        raise ValueError('An absolute, normalized package root is required')
    fd = os.open('/', _directory_flags())
    try:
        for part in filter(None, raw.split('/')):
            following = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = following
        return fd
    except BaseException:
        os.close(fd)
        raise


def _error_code(error):
    if error.errno == errno.ENOENT:
        return 'resource-missing'
    if error.errno in (errno.ELOOP, errno.ENOTDIR):
        return 'unsafe-resource'
    return 'resource-unreadable'


def _inspect_artifact(root_fd, artifact):
    relative, expected_size, expected_hash, executable = artifact
    # Defense in depth for future edits to the code-owned table.
    parts = relative.split('/')
    if not parts or any(part in ('', '.', '..') for part in parts):
        return {'path': relative, 'status': 'invalid-pin'}
    fd = os.dup(root_fd)
    leaf = stream = None
    try:
        for part in parts[:-1]:
            following = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = following
        # O_PATH inspects the leaf without opening a FIFO/device for I/O.
        leaf = os.open(parts[-1], os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        before = os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode):
            status = 'unsafe-resource'
        elif before.st_size != expected_size:
            status = 'size-mismatch'
        elif executable and not before.st_mode & 0o111:
            status = 'not-executable'
        else:
            # Reopen our held regular-file descriptor, not a replaceable name.
            stream = os.open(f'/proc/self/fd/{leaf}', os.O_RDONLY | os.O_CLOEXEC)
            digest, count = hashlib.sha256(), 0
            while chunk := os.read(stream, min(1024 * 1024, expected_size - count + 1)):
                count += len(chunk)
                if count > expected_size:
                    break
                digest.update(chunk)
            after = os.fstat(stream)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if count != expected_size or identity(before) != identity(after):
                status = 'resource-changed'
            elif digest.hexdigest() != expected_hash:
                status = 'hash-mismatch'
            else:
                status = 'verified'
        return {'path': relative, 'status': status}
    except OSError as error:
        return {'path': relative, 'status': _error_code(error)}
    finally:
        if stream is not None:
            os.close(stream)
        if leaf is not None:
            os.close(leaf)
        os.close(fd)


def inspect_runtime(root):
    report = {
        'format': 'readest-ovis-runtime-inspection', 'version': 1,
        'profileId': PROFILE_ID, 'profile': dict(PROFILE),
        'platform': {'system': platform.system(), 'machine': platform.machine()},
        'availability': 'unavailable', 'integrity': 'not-checked',
        'blockers': list(BLOCKERS), 'artifacts': [],
        'identity': {'llamaRevision': LLAMA_REVISION, 'modelRevision': MODEL_REVISION,
                     'provenance': 'reviewed-development-bytes-not-build-attestation'},
    }
    if report['platform'] != {'system': 'Linux', 'machine': 'x86_64'}:
        report['blockers'].insert(0, 'unsupported-platform')
        return report
    try:
        fd = _open_root(root)
    except ValueError:
        report['blockers'].insert(0, 'invalid-package-root')
        return report
    except OSError as error:
        report['blockers'].insert(0, _error_code(error))
        return report
    try:
        report['artifacts'] = [_inspect_artifact(fd, artifact) for artifact in ARTIFACTS]
    finally:
        os.close(fd)
    failures = [item for item in report['artifacts'] if item['status'] != 'verified']
    report['integrity'] = 'failed' if failures else 'verified'
    if failures:
        report['blockers'].insert(0, 'resource-verification-failed')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Absolute fixed-package root to inspect')
    args = parser.parse_args(argv)
    report = inspect_runtime(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # No successful launch/readiness exit code while integration is unavailable.
    return 2


if __name__ == '__main__':
    sys.exit(main())
