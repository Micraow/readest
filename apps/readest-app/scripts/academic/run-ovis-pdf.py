#!/usr/bin/env python3
"""Run a supplied local llama-mtmd-cli sequentially on every page of a PDF.

Linux-only process-group supervision; requires PyMuPDF and the adjacent Ovis
exporter/merger. No downloads, OCR corrections, or whole-page reflow fallbacks.
All output must go into a NEW directory. Import result/bundle.json only after
the final result directory is published. Failed runs retain diagnostic files.

--offline is application-level only, NOT an OS network sandbox. If OS isolation
is needed, launch this entire runner inside an already configured sandbox.
Use a trusted local CLI which stays in its process group. Its stdout is treated
as exact UTF-8 model output. Exit zero cannot authenticate EOS or completeness.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import time

VERSION = 'ovis-pdf-runner-1'
HERE = pathlib.Path(__file__).resolve().parent
CANCEL_SIGNAL = None


class RunStopped(RuntimeError):
    pass


def cancel(signum, _frame):
    # Do not throw asynchronously between Popen and registration of its child.
    global CANCEL_SIGNAL
    CANCEL_SIGNAL = CANCEL_SIGNAL or signum


def checkpoint(deadline=None):
    if CANCEL_SIGNAL:
        raise RunStopped('Run cancelled by parent signal')
    if deadline is not None and time.monotonic() >= deadline:
        raise RunStopped('Run wall-clock limit reached')


def digest(path, deadline=None, check_signals=True):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            if check_signals:
                checkpoint(deadline)
            value.update(chunk)
    return value.hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def write_new(path, value):
    data = value if isinstance(value, bytes) else json_bytes(value)
    with path.open('xb') as stream:
        stream.write(data)


def update_receipt(path, value):
    # This path belongs to our newly created private output directory only.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.receipt-', delete=False) as stream:
        temporary = pathlib.Path(stream.name)
        stream.write(json_bytes(value))
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_group(group):
    """Sample live group RSS, including descendants, not the runner itself."""
    members, rss = [], 0
    for path in pathlib.Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == group:
                members.append((int(path.name), fields[0]))
                rss += max(0, int(fields[21])) * os.sysconf('SC_PAGE_SIZE')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return members, rss


def signal_group(group, signum):
    try:
        os.killpg(group, signum)
    except ProcessLookupError:
        pass


def reap_group(group):
    # After the direct child is waited, Linux's subreaper adoption allows us to
    # collect its exited descendants rather than leave zombies to PID 1.
    while True:
        try:
            pid, _ = os.waitpid(-group, os.WNOHANG)
        except ChildProcessError:
            return
        if not pid:
            return


def observe_child_exit(child):
    """Observe exit without releasing our group leader's PID to the kernel."""
    while True:
        try:
            return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except InterruptedError:
            continue


def owns_child(child):
    # Ignored SIGCHLD can auto-reap a child despite WNOWAIT. Imported callers
    # must also have the default disposition and no concurrent child reaper.
    if child.returncode is not None or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        return False
    try:
        observe_child_exit(child)
        return True
    except ChildProcessError:
        return False


def stop_group(child, grace):
    # The group leader must remain our unreaped child through the final signal.
    # Otherwise PID/PGID reuse could redirect killpg to an unrelated new group.
    if not owns_child(child):
        return False
    signal_group(child.pid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        # Do not poll()/wait()/reap_group here: any may release the leader.
        if all(state == 'Z' for _, state in process_group(child.pid)[0]):
            break
        time.sleep(0.025)
    if not owns_child(child):
        return False
    signal_group(child.pid, signal.SIGKILL)
    child.wait()  # Always reap the direct child, including after parent SIGINT.
    deadline = time.monotonic() + max(grace, 1)
    while True:
        reap_group(child.pid)
        if not process_group(child.pid)[0]:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.025)


def child_environment(threads):
    # No inherited CLI defaults, URLs, startup hooks, credentials, or proxies.
    # Dynamic-library loading must work through the local executable's rpath.
    return {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'HOME': '/', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
            'OMP_NUM_THREADS': str(threads), 'OPENBLAS_NUM_THREADS': str(threads),
            'MKL_NUM_THREADS': str(threads)}


def infer(command, page_dir, args, deadline, source, identity):
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise ValueError('Inference requires default SIGCHLD and exclusive child ownership')
    receipt = {'format': 'readest-ovis-page-execution', 'version': 1,
               'source': source, 'identity': identity, 'status': 'starting',
               'nativeFinishReason': 'unknown', 'generationCompleteness': 'unknown',
               'peakSampledGroupRssBytes': 0, 'rssScope': 'live-process-group-sampled',
               'rssSampleIntervalSeconds': 0.025, 'childReaped': False,
               'processGroupStopped': False}
    started, child = time.monotonic(), None
    raw_path, stderr_path = page_dir / 'raw.md', page_dir / 'stderr.log'
    try:
        checkpoint(deadline)
        with raw_path.open('xb') as out, stderr_path.open('xb') as err:
            child = subprocess.Popen(command, cwd=page_dir, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, env=child_environment(args.threads),
                                     start_new_session=True)
            receipt['pid'] = child.pid
            receipt['status'] = 'running'
            while True:
                _, rss = process_group(child.pid)
                receipt['peakSampledGroupRssBytes'] = max(receipt['peakSampledGroupRssBytes'], rss)
                if CANCEL_SIGNAL:
                    receipt['status'] = 'cancelled'
                elif time.monotonic() >= min(deadline, started + args.page_timeout_seconds):
                    receipt['status'] = 'timeout'
                elif rss > args.max_rss_mib * 1024 * 1024:
                    receipt['status'] = 'rss-limit'
                elif (exit_info := observe_child_exit(child)) is not None:
                    receipt['status'] = ('process-completed'
                                         if exit_info.si_code == os.CLD_EXITED and exit_info.si_status == 0
                                         else 'nonzero-exit')
                    break
                else:
                    time.sleep(0.025)
                    continue
                break
    except ChildProcessError as error:
        receipt['status'] = 'ownership-lost'
        raise RunStopped('Child ownership was lost; refusing process-group signals') from error
    finally:
        if child is not None:
            owned = owns_child(child)
            if not owned:
                receipt['status'] = 'ownership-lost'
            elif observe_child_exit(child) is not None:
                remaining = [pid for pid, state in process_group(child.pid)[0] if state != 'Z']
                receipt['liveDescendantsAfterChildExit'] = remaining
                if remaining and receipt['status'] == 'process-completed':
                    receipt['status'] = 'unexpected-descendants'
            receipt['processGroupStopped'] = stop_group(child, args.kill_grace_seconds) if owned else False
            receipt['childReaped'] = owned and child.returncode is not None
            receipt['exitCode'] = child.returncode if owned else None
        receipt['elapsedSeconds'] = round(time.monotonic() - started, 6)
        # Preserve and hash raw bytes even for failed/cancelled children. The
        # cancellation-aware source hasher must not prevent this terminal audit.
        for key, path in (('rawSha256', raw_path), ('stderrSha256', stderr_path)):
            if path.exists():
                receipt[key] = digest(path, check_signals=False)
        write_new(page_dir / 'execution.json', receipt)
    if receipt['status'] != 'process-completed' or not receipt['processGroupStopped']:
        raise RunStopped('Page process did not complete cleanly: ' + receipt['status'])
    checkpoint(deadline)
    return receipt


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    for name in ('pdf', 'cli', 'model', 'mmproj', 'prompt', 'output-dir'):
        result.add_argument('--' + name, required=True, type=pathlib.Path)
    result.add_argument('--runtime-revision', required=True, help='Declared local source commit (40 lowercase hex)')
    result.add_argument('--flash-attn', choices=('on', 'off', 'auto'), default='off')
    for name, default in [('threads', 2), ('dpi', 144), ('max-tokens', 4096),
                          ('ctx-size', 8192), ('image-max-tokens', 2048), ('max-rss-mib', 12288)]:
        result.add_argument('--' + name, type=int, default=default)
    for name, default in [('page-timeout-seconds', 900), ('wall-timeout-seconds', 3600),
                          ('kill-grace-seconds', 2)]:
        result.add_argument('--' + name, type=float, default=default)
    return result


def preflight(args):
    import fitz
    if not sys.platform.startswith('linux') or not pathlib.Path('/proc/self/stat').is_file():
        raise ValueError('This runner currently requires Linux /proc process-group supervision')
    if not re.fullmatch('[a-f0-9]{40}', args.runtime_revision):
        raise ValueError('runtime-revision must be a complete 40-character lowercase commit hash')
    for key in ('threads', 'dpi', 'max_tokens', 'ctx_size', 'image_max_tokens', 'max_rss_mib',
                'page_timeout_seconds', 'wall_timeout_seconds', 'kill_grace_seconds'):
        value = getattr(args, key)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(key + ' must be positive and finite')
    if args.max_tokens >= args.ctx_size:
        raise ValueError('max-tokens must be smaller than ctx-size, leaving room for image and prompt')
    if args.dpi > 600 or args.threads > 64 or args.kill_grace_seconds > 30:
        raise ValueError('DPI <= 600, threads <= 64, and kill grace <= 30 seconds are required')
    output = args.output_dir.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output directory already exists; no existing output is overwritten')
    if not output.parent.is_dir():
        raise ValueError('Output parent directory must already exist')
    if ',' in str(output):
        raise ValueError('Output path cannot contain commas: the CLI treats --image as a comma-separated list')
    sources = {name: getattr(args, name).resolve(strict=True)
               for name in ('pdf', 'cli', 'model', 'mmproj', 'prompt')}
    sources.update({name: HERE / filename for name, filename in (
        ('runner', 'run-ovis-pdf.py'), ('exporter', 'export-ovis-result.py'),
        ('merger', 'merge-ovis-results.py'), ('adapter', 'ovis_markdown.py'))})
    if any(not path.is_file() for path in sources.values()):
        raise ValueError('All inputs must be existing local regular files')
    if not os.access(sources['cli'], os.X_OK):
        raise ValueError('CLI must be an existing local executable')
    if sources['prompt'].stat().st_size > 1024 * 1024:
        raise ValueError('Prompt exceeds the one-MiB safety limit')
    prompt = sources['prompt'].read_bytes()
    if not prompt.decode('utf-8').strip() or b'\x00' in prompt:
        raise ValueError('Prompt must be nonempty UTF-8 without NUL bytes')
    if sources['pdf'].stat().st_size > 512 * 1024 * 1024:
        raise ValueError('PDF exceeds the 512-MiB in-memory safety limit')
    with fitz.open(sources['pdf']) as pdf:
        if not pdf.is_pdf:
            raise ValueError('Input must be a PDF document')
        if pdf.needs_pass or pdf.is_encrypted or (pdf.metadata or {}).get('encryption'):
            raise ValueError('Encrypted PDFs are not supported')
        if len(pdf) == 0:
            raise ValueError('Empty PDFs are not supported')
        for page in pdf:
            if page.rotation:
                raise ValueError('Rotated PDF pages are not supported')
            width, height = page.rect.width, page.rect.height
            if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                raise ValueError('Invalid PDF page dimensions')
            if math.ceil(width * args.dpi / 72) * math.ceil(height * args.dpi / 72) > 24_000_000:
                raise ValueError('Rendered page exceeds the 24-million-pixel safety limit; reduce --dpi')
        page_count = len(pdf)
    return output, sources, page_count


def verify_sources(sources, hashes, deadline):
    for name, path in sources.items():
        if digest(path, deadline) != hashes[name]:
            raise ValueError('Input/producer identity changed: ' + name)


def run(args):
    import fitz
    output, sources, page_count = preflight(args)
    started = time.monotonic()
    deadline = started + args.wall_timeout_seconds
    hashes = {name: digest(path, deadline) for name, path in sources.items()}
    # PR_SET_CHILD_SUBREAPER is local process lifecycle bookkeeping, not a
    # security setting. It lets us wait for orphaned same-group descendants.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Could not enable child reaping')
    config = {
        'runner': VERSION, 'threads': args.threads, 'threadsBatch': args.threads,
        'OMP_NUM_THREADS': str(args.threads), 'OPENBLAS_NUM_THREADS': str(args.threads),
        'MKL_NUM_THREADS': str(args.threads),
        'dpi': args.dpi, 'maxTokens': args.max_tokens, 'contextSize': args.ctx_size,
        'imageMaxTokens': args.image_max_tokens, 'gpuLayers': 0, 'mmprojOffload': False,
        'seed': 0, 'temperature': 0, 'batchSize': 512, 'ubatchSize': 128,
        'flashAttention': args.flash_attn, 'warmup': False, 'escape': False, 'offline': True,
        'pageTimeoutSeconds': args.page_timeout_seconds, 'wallTimeoutSeconds': args.wall_timeout_seconds,
        'maxRssMiB': args.max_rss_mib, 'killGraceSeconds': args.kill_grace_seconds,
        'renderMaxPixels': 24_000_000, 'pythonVersion': sys.version.split()[0],
        'pymupdfVersion': fitz.VersionBind,
        'otherCliDefaults': 'bound-to-cli-sha256',
        **{name + 'Sha256': hashes[name] for name in ('cli', 'runner', 'exporter', 'merger', 'adapter')},
    }
    identity = {'modelSha256': hashes['model'], 'projectorSha256': hashes['mmproj'],
                'promptSha256': hashes['prompt'], 'runtimeRevision': args.runtime_revision,
                'configuration': config}
    receipt = {
        'format': 'readest-ovis-pdf-execution', 'version': 1, 'status': 'running',
        'source': {'pdfSha256': hashes['pdf'], 'pageCount': page_count}, 'identity': identity,
        'pageArtifacts': {},
        'nativeFinishReason': 'unknown', 'generationCompleteness': 'unknown',
        'coverage': {'pageCount': page_count, 'coveredPages': [],
                     'missingPages': list(range(1, page_count + 1)), 'complete': False},
        'offline': {'cliOfflineFlag': True, 'localFilesOnly': True,
                    'automaticDownloads': False, 'osNetworkIsolationVerified': False},
        'verification': {'nativeFinishAuthenticated': False, 'ocrAccuracyChecked': False,
                         'runtimeRevisionAuthenticated': False, 'wholePageFallback': False},
        'limits': {'rssScope': 'live-process-group-sampled', 'rssSampleIntervalSeconds': 0.025,
                   'runnerRssIncluded': False, 'rssIsHardKernelLimit': False},
        'limitations': [
            'Exit zero establishes process completion only; EOG, max tokens, antiprompt and internal SIGINT are indistinguishable.',
            'Complete page coverage does not establish complete or correct model generation.',
            'Runtime revision is supplied by the operator; byte hashes do not authenticate the build or model.',
            'CLI --offline is not OS network isolation; use a separately configured sandbox if required.',
            'RSS is a sampled process-group guard, not a hard kernel bound; rendering and hashing use the parent process.',
            'Wall limits are checked between Python operations and during inference; termination adds the configured grace.',
        ],
    }
    # mkdir fails atomically even if another caller created it since preflight.
    output.mkdir(mode=0o700)
    try:
        update_receipt(output / 'run.json', receipt)
        write_new(output / 'identity.json', identity)
        identity_hash = digest(output / 'identity.json', deadline)
        exporter = load_module('_readest_runner_exporter', 'export-ovis-result.py')
        merger = load_module('_readest_runner_merger', 'merge-ovis-results.py')
        exporter.validate_identity(identity)
        (output / 'pages').mkdir()
        bundles = []
        for page_number in range(1, page_count + 1):
            checkpoint(deadline)
            verify_sources(sources, hashes, deadline)
            if digest(output / 'identity.json', deadline) != identity_hash:
                raise ValueError('Input/producer identity changed: identity.json')
            page_dir = output / 'pages' / f'page-{page_number:06d}'
            page_dir.mkdir()
            raster = page_dir / 'render.png'
            with fitz.open(sources['pdf']) as pdf:
                write_new(raster, pdf[page_number - 1].get_pixmap(dpi=args.dpi, alpha=False).tobytes('png'))
            raster_hash = digest(raster, deadline)
            command = [str(sources['cli']), '--model', str(sources['model']),
                       '--mmproj', str(sources['mmproj']), '--file', str(sources['prompt']),
                       '--image', str(raster), '--offline', '--no-escape',
                       '--threads', str(args.threads), '--threads-batch', str(args.threads),
                       '--ctx-size', str(args.ctx_size), '--n-predict', str(args.max_tokens),
                       '--image-max-tokens', str(args.image_max_tokens), '--gpu-layers', '0',
                       '--no-mmproj-offload', '--seed', '0', '--temp', '0', '--batch-size', '512',
                       '--ubatch-size', '128', '--flash-attn', args.flash_attn, '--no-warmup']
            execution = infer(command, page_dir, args, deadline,
                              {'pdfSha256': hashes['pdf'], 'page': page_number,
                               'renderSha256': raster_hash}, identity)
            verify_sources(sources, hashes, deadline)
            if digest(raster, deadline) != raster_hash:
                raise ValueError('Rendered page identity changed')
            raw_path = page_dir / 'raw.md'
            bundle, provenance = exporter.export_markdown(
                sources['pdf'], page_number, raw_path, identity, page_dir / 'assets',
                hashes['pdf'], execution['rawSha256'], list(sources.values()))
            merger.validate_bundle(bundle)
            provenance['source']['identitySha256'] = identity_hash
            # Preserve existing exporter's conservative caller-declared provenance.
            write_new(page_dir / 'bundle.provenance.json', provenance)
            bundle_path = page_dir / 'bundle.json'
            write_new(bundle_path, bundle)
            bundles.append(bundle_path)
            artifacts = [raster, raw_path, page_dir / 'stderr.log', page_dir / 'execution.json',
                         bundle_path, page_dir / 'bundle.provenance.json',
                         *[page_dir / crop['asset'] for crop in provenance['crops']]]
            receipt['pageArtifacts'].update({str(path.relative_to(output)): digest(path, deadline)
                                             for path in artifacts})
            receipt['coverage']['coveredPages'].append(page_number)
            receipt['coverage']['missingPages'].remove(page_number)
            update_receipt(output / 'run.json', receipt)
        verify_sources(sources, hashes, deadline)
        if digest(output / 'identity.json', deadline) != identity_hash:
            raise ValueError('Input/producer identity changed: identity.json')
        for relative, expected in receipt['pageArtifacts'].items():
            if digest(output / relative, deadline) != expected:
                raise ValueError('Completed page artifact identity changed: ' + relative)
        # Same strict path as merge-ovis-results.py --require-complete, in process.
        bundle, provenance = merger.merge_results(sources['pdf'], bundles, require_complete=True)
        if not merger.identities_equal(bundle['identity'], identity):
            raise ValueError('Merged identity differs from the frozen producer identity')
        receipt['coverage'] = provenance['coverage']
        receipt['status'] = 'process-completed'
        receipt['bundleSha256'] = hashlib.sha256(json_bytes(bundle)).hexdigest()
        receipt['elapsedSeconds'] = round(time.monotonic() - started, 6)
        publication = output / '.publication'
        publication.mkdir()
        write_new(publication / 'bundle.provenance.json', provenance)
        write_new(publication / 'run.json', receipt)
        write_new(publication / 'bundle.json', bundle)
        update_receipt(output / 'run.json', {
            **receipt, 'status': 'publication-ready',
            'terminalReceipt': 'result/run.json',
        })
        checkpoint(deadline)
        # The import bundle and all terminal sidecars become visible together.
        # There is no prior destination: this run owns a newly created directory.
        if (output / 'result').exists() or (output / 'result').is_symlink():
            raise ValueError('Final result destination already exists')
        os.rename(publication, output / 'result')
    except Exception as error:
        receipt['status'] = 'cancelled' if CANCEL_SIGNAL else 'failed'
        receipt['error'] = str(error)
        receipt['elapsedSeconds'] = round(time.monotonic() - started, 6)
        if CANCEL_SIGNAL:
            receipt['signal'] = CANCEL_SIGNAL
        update_receipt(output / 'run.json', receipt)
        raise
    # Terminal success is inside result/run.json. Do not perform fallible writes
    # after its commit that could recast a valid publication as a failed run.
    return receipt


def main():
    args = parser().parse_args()
    signal.signal(signal.SIGINT, cancel)
    signal.signal(signal.SIGTERM, cancel)
    # exec preserves SIG_IGN. Own all waits in this single-process CLI instead
    # of letting an inherited ignored disposition auto-reap group leaders.
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        receipt = run(args)
    except (ValueError, OSError, RuntimeError, UnicodeError, OverflowError) as error:
        print('Ovis PDF run failed: ' + str(error), file=sys.stderr)
        return 128 + CANCEL_SIGNAL if CANCEL_SIGNAL else 1
    print(json.dumps({'status': receipt['status'], 'coveredPages': receipt['coverage']['coveredPages'],
                      'nativeFinishReason': 'unknown', 'generationCompleteness': 'unknown'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
