#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only Ovis receipt timing and conservative same-workload A/B comparison.

Accept a run directory or ZIP without extracting it. Never invoke a runtime,
load models, change a run, or reproduce OCR text in the report. Reports still
contain document fingerprints and should be kept private.
"""
import argparse
import hashlib
import json
import math
import pathlib
import re
import stat
import sys
import zipfile

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 100_000
HASH = re.compile(r'[0-9a-f]{64}')
CONFIG_KEYS = {
    'runner', 'threads', 'threadsBatch', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
    'MKL_NUM_THREADS', 'dpi', 'maxTokens', 'contextSize', 'imageMaxTokens',
    'gpuLayers', 'mmprojOffload', 'seed', 'temperature', 'batchSize', 'ubatchSize',
    'flashAttention', 'warmup', 'escape', 'offline', 'pageTimeoutSeconds',
    'wallTimeoutSeconds', 'maxRssMiB', 'killGraceSeconds', 'renderMaxPixels',
    'pythonVersion', 'pymupdfVersion', 'otherCliDefaults', 'cliWorkingDirectory',
    'cliSha256', 'runnerSha256', 'exporterSha256', 'mergerSha256', 'adapterSha256',
}
NUMBER = r'([0-9]+(?:\.[0-9]+)?)'


def safe_relative(name):
    path = pathlib.PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or '..' in path.parts
            or '.' in name.split('/') or str(path) != name.rstrip('/')):
        raise ValueError('Unsafe relative artifact path')
    return path


def finite_seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Timing must be a finite nonnegative number')
    return value


def validate_configuration(configuration):
    if not isinstance(configuration, dict) or set(configuration) - CONFIG_KEYS:
        raise ValueError('Unknown configuration fields; review before profiling')
    string_patterns = {
        'runner': r'ovis-pdf-runner-[0-9]+',
        'OMP_NUM_THREADS': r'[0-9]+', 'OPENBLAS_NUM_THREADS': r'[0-9]+', 'MKL_NUM_THREADS': r'[0-9]+',
        'pythonVersion': r'[0-9]+(?:\.[A-Za-z0-9]+)+', 'pymupdfVersion': r'[0-9]+(?:\.[A-Za-z0-9]+)+',
        'flashAttention': r'on|off|auto', 'otherCliDefaults': r'bound-to-cli-sha256',
        'cliWorkingDirectory': r'resolved-executable-directory',
    }
    for key, value in configuration.items():
        if key.endswith('Sha256'):
            valid_hash(value)
        elif key in string_patterns:
            if not isinstance(value, str) or not re.fullmatch(string_patterns[key], value):
                raise ValueError('Unrecognized configuration value: ' + key)
        elif type(value) not in (int, float, bool) or not math.isfinite(value):
            raise ValueError('Configuration value must be finite numeric/boolean: ' + key)


def valid_hash(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError('Invalid SHA-256 hash')
    return value


class RunSource:
    """Bounded reads of fixed artifacts. ZIP members are never extracted."""
    def __init__(self, path, prefix=None):
        self.path = pathlib.Path(path)
        self.archive = None
        self.prefix = ''
        if self.path.is_symlink():
            raise ValueError('Symlink input is not supported')
        if self.path.is_dir():
            if prefix:
                raise ValueError('--run-prefix applies only to ZIP inputs')
            return
        if not self.path.is_file():
            raise ValueError('Expected a run directory or ZIP file')
        self.archive = zipfile.ZipFile(self.path)
        try:
            members = self.archive.infolist()
            if len(members) > MAX_ENTRIES:
                raise ValueError('ZIP has too many entries')
            names = set()
            for member in members:
                safe_relative(member.filename)
                if member.filename in names:
                    raise ValueError('Duplicate ZIP member')
                names.add(member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError('ZIP symlinks are not supported')
            roots = sorted({name[:-len('run.json')].rstrip('/') for name in names
                            if name == 'run.json' or name.endswith('/run.json')
                            if name != 'result/run.json' and not name.endswith('/result/run.json')})
            if prefix is not None:
                prefix = prefix.strip('/') if prefix == '' else str(safe_relative(prefix))
                if prefix not in roots:
                    raise ValueError('Selected ZIP prefix does not contain a run receipt')
            elif len(roots) != 1:
                raise ValueError('Multiple or missing runs in ZIP; select one with --run-prefix')
            else:
                prefix = roots[0]
            self.prefix = prefix + '/' if prefix else ''
            self.names = names
        except Exception:
            self.close()
            raise

    def close(self):
        if self.archive is not None:
            self.archive.close()

    def local_path(self, name):
        path = self.path
        for part in safe_relative(name).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError('Symlink artifact is not supported')
        return path

    def exists(self, name):
        if self.archive is not None:
            return self.prefix + name in self.names
        return self.local_path(name).exists()

    def read(self, name, limit=MAX_FILE_BYTES):
        safe_relative(name)
        if self.archive is not None:
            member = self.archive.getinfo(self.prefix + name)
            if member.is_dir() or member.file_size > limit:
                raise ValueError('Artifact is not a bounded regular file')
            stream = self.archive.open(member)
        else:
            path = self.local_path(name)
            if not path.is_file() or path.stat().st_size > limit:
                raise ValueError('Artifact is not a bounded regular file')
            stream = path.open('rb')
        with stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Artifact exceeds read limit')
        return data

    def json(self, name):
        return json.loads(self.read(name, MAX_JSON_BYTES),
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))


def parse_timings(stderr):
    images = [float(value) / 1000 for value in re.findall(
        r'mtmd batch encoding done in ' + NUMBER + r' ms\b', stderr)]
    result = {'imageEncodingSeconds': round(sum(images), 6) if images else None,
              'imageEncodingBatches': len(images), 'warnings': []}
    for label, key in [('load', 'loadSeconds'), ('prompt eval', 'promptEvalSeconds'), ('eval', 'evalSeconds')]:
        values = re.findall(r'llama_perf_context_print:\s+' + label + r' time\s*=\s*' + NUMBER + r' ms\b', stderr)
        result[key] = float(values[0]) / 1000 if len(values) == 1 else None
        if len(values) > 1:
            result['warnings'].append('ambiguous-' + label.replace(' ', '-') + '-summary')
    return result


def profile_run(path, prefix=None):
    source = RunSource(path, prefix)
    try:
        terminal = source.exists('result/run.json')
        receipt = source.json('result/run.json' if terminal else 'run.json')
        if not isinstance(receipt, dict) or receipt.get('format') != 'readest-ovis-pdf-execution' or receipt.get('version') != 1:
            raise ValueError('Unsupported run receipt')
        if receipt['status'] not in ('running', 'failed', 'cancelled', 'publication-ready', 'process-completed'):
            raise ValueError('Unknown run status')
        wall = finite_seconds(receipt['elapsedSeconds'])
        identity = receipt['identity']
        configuration = identity['configuration']
        validate_configuration(configuration)
        if not isinstance(identity['runtimeRevision'], str) or not re.fullmatch(r'[a-f0-9]{40}', identity['runtimeRevision']):
            raise ValueError('Invalid runtime revision')
        for key in ('modelSha256', 'projectorSha256', 'promptSha256'):
            valid_hash(identity[key])
        valid_hash(receipt['source']['pdfSha256'])
        coverage = receipt['coverage']
        count, covered = coverage['pageCount'], coverage['coveredPages']
        if type(count) is not int or not 1 <= count <= MAX_ENTRIES:
            raise ValueError('Invalid page count')
        if (not isinstance(covered, list) or any(type(p) is not int or not 1 <= p <= count for p in covered)
                or len(set(covered)) != len(covered) or covered != sorted(covered)
                or receipt['source']['pageCount'] != count):
            raise ValueError('Invalid page coverage')
        missing = sorted(set(range(1, count + 1)) - set(covered))
        if coverage['missingPages'] != missing or coverage['complete'] is not (not missing):
            raise ValueError('Inconsistent page coverage')
        pages = []
        for number in covered:
            directory = f'pages/page-{number:06d}/'
            data = {}
            for name in ('execution.json', 'stderr.log', 'raw.md', 'render.png'):
                relative = directory + name
                contents = source.read(relative, MAX_JSON_BYTES if name.endswith('.json') else MAX_FILE_BYTES)
                expected = valid_hash(receipt['pageArtifacts'][relative])
                if hashlib.sha256(contents).hexdigest() != expected:
                    raise ValueError('Artifact hash mismatch: ' + relative)
                data[name] = contents
            execution = json.loads(data['execution.json'])
            if execution.get('format') != 'readest-ovis-page-execution' or execution.get('version') != 1:
                raise ValueError('Unsupported page receipt')
            if execution['identity'] != identity:
                raise ValueError('Page identity differs from run identity')
            if (execution['source']['page'] != number
                    or execution['source']['pdfSha256'] != receipt['source']['pdfSha256']):
                raise ValueError('Page source identity mismatch')
            for name, key, container in [('raw.md', 'rawSha256', execution),
                                         ('stderr.log', 'stderrSha256', execution),
                                         ('render.png', 'renderSha256', execution['source'])]:
                if container[key] != hashlib.sha256(data[name]).hexdigest():
                    raise ValueError('Page artifact hash mismatch: ' + name)
            if (execution['status'] != 'process-completed' or execution.get('exitCode') != 0
                    or execution.get('childReaped') is not True or execution.get('processGroupStopped') is not True):
                raise ValueError('Covered page was not completed cleanly')
            elapsed = finite_seconds(execution['elapsedSeconds'])
            peak_rss = execution.get('peakSampledGroupRssBytes')
            if peak_rss is not None and (type(peak_rss) is not int or peak_rss < 0):
                raise ValueError('Peak sampled RSS must be a nonnegative integer or null')
            timings = parse_timings(data['stderr.log'].decode('utf-8', errors='replace'))
            if any(value is not None and (not math.isfinite(value) or value > elapsed + 0.1)
                   for key, value in timings.items() if key.endswith('Seconds')):
                timings['warnings'].append('native-stage-exceeds-process-wall')
                for key in list(timings):
                    if key.endswith('Seconds'):
                        timings[key] = None
            pages.append({'page': number, 'processSeconds': elapsed, 'nativeTimings': timings,
                          'rawSha256': execution['rawSha256'], 'rawBytes': len(data['raw.md']),
                          'renderSha256': execution['source']['renderSha256'],
                          'peakSampledGroupRssBytes': peak_rss})
        process_time = sum(page['processSeconds'] for page in pages)
        complete = terminal and receipt['status'] == 'process-completed' and not missing
        if complete and process_time > wall + 0.1:
            raise ValueError('Page process durations exceed sequential run duration')
        image_times = [page['nativeTimings']['imageEncodingSeconds'] for page in pages]
        image_total = sum(image_times) if image_times and all(t is not None for t in image_times) else None
        return {'format': 'readest-ovis-performance-profile', 'version': 1,
                'status': receipt['status'], 'complete': complete,
                'source': {'pdfSha256': receipt['source']['pdfSha256'], 'pageCount': count},
                'identity': {key: identity[key] for key in
                             ('modelSha256', 'projectorSha256', 'promptSha256', 'runtimeRevision', 'configuration')},
                'coverage': {'pageCount': count, 'coveredPages': covered, 'missingPages': missing,
                             'complete': coverage['complete']},
                'timing': {'runWallSeconds': wall, 'pageProcessSeconds': round(process_time, 6),
                           'outsidePageProcessesSeconds': round(wall - process_time, 6) if complete else None,
                           'imageEncodingSeconds': round(image_total, 6) if image_total is not None else None,
                           'imageEncodingPageCount': sum(t is not None for t in image_times)},
                'pages': pages,
                'verification': {'selectedArtifactHashesChecked': True, 'sourceAuthenticated': False,
                                 'nativeTimingsAuthenticated': False, 'ocrAccuracyChecked': False,
                                 'nativeFinishAuthenticated': False, 'backendLibrariesIdentified': False},
                'limitations': [
                    'Only covered-page execution, stderr, raw output and render hashes are checked.',
                    'Missing native timings are unknown, never zero; native counters can overlap.',
                    'Outside-page time includes all unprofiled runner work; it is not model load time.',
                    'Cancelled runs omit unfinished-page timings and cannot establish full-document speed.',
                    'Byte hashes identify artifacts, not trustworthy origin, EOS, OCR accuracy or loaded libraries.',
                    'This report contains document fingerprints; keep it private.']}
    finally:
        source.close()


def compare_runs(baseline, candidate):
    mismatches = []
    if not baseline['complete'] or not candidate['complete']:
        mismatches.append('incomplete-run')
    for key in ('source', 'coverage'):
        if baseline[key] != candidate[key]:
            mismatches.append(key)
    for key in ('modelSha256', 'projectorSha256', 'promptSha256'):
        if baseline['identity'][key] != candidate['identity'][key]:
            mismatches.append('identity.' + key)
    left, right = baseline['identity']['configuration'], candidate['identity']['configuration']
    producer_keys = {'cliSha256', 'runnerSha256', 'exporterSha256', 'mergerSha256', 'adapterSha256'}
    for key in sorted(set(left) | set(right)):
        if key not in producer_keys and left.get(key) != right.get(key):
            mismatches.append('configuration.' + key)
    old = {p['page']: p for p in baseline['pages']}
    new = {p['page']: p for p in candidate['pages']}
    common = sorted(set(old) & set(new))
    if set(old) != set(new) or any(old[p]['renderSha256'] != new[p]['renderSha256'] for p in common):
        mismatches.append('rendered-pages')
    a, b = baseline['timing']['runWallSeconds'], candidate['timing']['runWallSeconds']
    if a <= 0 or b <= 0:
        mismatches.append('nonpositive-run-duration')
    return {'format': 'readest-ovis-performance-comparison', 'version': 1,
            'comparable': not mismatches, 'mismatches': mismatches,
            'wallSpeedRatio': round(a / b, 6) if not mismatches else None,
            'ratioMeaning': 'baseline wall seconds divided by candidate wall seconds',
            'changedOutputPages': [p for p in common if old[p]['rawSha256'] != new[p]['rawSha256']],
            'producerCodeChanged': sorted(k for k in producer_keys if left.get(k) != right.get(k)),
            'runtimeRevisionChanged': baseline['identity'].get('runtimeRevision') != candidate['identity'].get('runtimeRevision'),
            'ocrAccuracyChecked': False, 'backendLibrariesIdentified': False,
            'limitations': ['Same settings do not establish same machine, power state, cache state or loaded backend.',
                            'One timing pair is observational; repeat interleaved A/B runs before claiming acceleration.',
                            'Different output hashes require quality review; identical bytes do not prove correct OCR.'],
            'baseline': baseline, 'candidate': candidate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=pathlib.Path)
    parser.add_argument('--run-prefix', help='Exact run directory inside a multi-run ZIP')
    parser.add_argument('--compare', type=pathlib.Path, help='Candidate run directory or ZIP')
    parser.add_argument('--compare-prefix', help='Candidate run directory inside ZIP')
    parser.add_argument('--output', type=pathlib.Path, help='Write a NEW JSON file instead of stdout')
    args = parser.parse_args()
    try:
        if args.compare_prefix is not None and args.compare is None:
            raise ValueError('--compare-prefix requires --compare')
        result = profile_run(args.run, args.run_prefix)
        if args.compare is not None:
            result = compare_runs(result, profile_run(args.compare, args.compare_prefix))
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        else:
            print(text, end='')
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print('Cannot profile Ovis run: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
