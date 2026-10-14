# Original synthetic native OCR benchmark, 2026-10-14

This is real Ovis model inference on one tiny, original synthetic page in a shared
cloud environment. It is **not** a measurement on a user's computer or a full PDF,
and is not an OCR-completeness or accuracy certification. No default profile,
model, whole-page OCR pipeline or user document was changed.

The complete portable numeric record, input fingerprints, original fixture,
environment and timing boundaries are in
[`NATIVE-BENCHMARK-20261014.json`](NATIVE-BENCHMARK-20261014.json).
No private document, user result, absolute filesystem path or credential is included.

## Serial control result

All three runs use the same CLI bytes, weights, raster, prompt and settings.
They ran serially in the following order:

| Backend | Process wall seconds | Vision encoding seconds | Image prefill seconds | Native eval seconds | Sampled peak RSS bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| AVX2, before | 12.420774 | 4.299 | 5.228 | 1.10022 | 911159296 |
| Generic | 139.595207 | 32.908 | 91.353 | 10.18309 | 798035968 |
| AVX2, after | 12.482859 | 4.174 | 5.814 | 0.98802 | 911355904 |

Generic wall time divided by the mean AVX2 wall time is 11.210830725. This is an
observational ratio for this small fixture, not a prediction for documents or
other machines. The AVX2 runs used about 108 MiB more sampled resident memory in
this control. All three exited zero, stopped their owned process groups and
reaped their direct children. Every raw output was 137 bytes with SHA-256:

```text
334289b1efa26b2d4f7ac5b0a5057b95276879c02ebb2a0cc493c93e98ee1207
```

Identical output is a useful regression check, not proof that OCR is correct or
reached EOS. The 64-token output cap is deliberately small. The micro-batch size
was 128 throughout this control. Exploratory 256/512 trials did not establish a
reliable improvement and do not justify changing defaults. Exploratory trials
with overlapping command sequences are excluded from the control above.

## Environment and boundaries

- Linux x86-64, AMD EPYC 9V74 cloud CPU, glibc 2.41
- Python 3.12.14, PyMuPDF 1.26.6
- Native source revision `5266f24da75dc449bd56cbed7addb9c8e4a6a73e`
- Two threads, CPU only, image-token cap 1024, context 2048, output cap 64
- Batch 512, micro-batch 128, Flash Attention on, seed 0, temperature 0
- `--no-warmup --perf -lv 4`, identical on both sides
- 180-second page timeout, 200-second runner deadline, 1800-MiB sampled
  process-group RSS guard, one-second termination grace

Process wall timing starts at `run-ovis-pdf.py::infer()` entry and ends after
owned-child cleanup. It excludes preparing the fixture and hashing parent
inputs. The RSS guard is sampled, not a kernel limit, and excludes the parent.
The command environment comes from the existing runner's `child_environment(2)`.
`--offline` is an application flag, not an OS network sandbox.

Vision encoding uses the `mtmd batch encoding done` interval. Image prefill uses
complete `image decoded (batch N/M)` helper intervals. Native eval comes from the
native performance counter. Native load and prompt-eval counters overlap other
work in this revision; do not add them to these durations. See
[`OVIS-PERFORMANCE.md`](../../OVIS-PERFORMANCE.md) for the verified logging and
synchronization details. The shared cloud host is not a dedicated benchmark
machine; CPU allocation, power state and cold-cache conditions were not fixed.

## Reproduce the fixture and supervised command

Use trusted, separately prepared generic and AVX2 packages with the recorded
fingerprints. Preserve both packages and their loader/dependency closures. Do
not replace libraries in place. The AVX2 backend requires AVX, AVX2, FMA, F16C,
SSE4.2 and BMI2 on all CPUs that may execute it; the normal prepared package
entry performs that guard. The diagnostic invocation below calls the native
executable directly, so verify the CPU requirements before using it.

From the repository root, run the following Python command separately for each
backend, in AVX2 / generic / AVX2 order. Replace the four positional arguments
with the trusted CLI, model, projector and a NEW output directory. All parent
directories must already exist. Do not run the variants concurrently. The
existing runner supervises the native child; no model is downloaded.

```sh
python3 -B - /absolute/package/bin/llama-mtmd-cli \
  /absolute/package/models/OvisOCR2-Q3_K_M.gguf \
  /absolute/package/models/mmproj-OvisOCR2-Q8_0.gguf \
  /absolute/new-benchmark-directory <<'PY'
import ctypes, hashlib, importlib.util, json, pathlib, signal, sys, time
from types import SimpleNamespace
import fitz

cli, model, projector = [pathlib.Path(p).resolve(strict=True) for p in sys.argv[1:4]]
output = pathlib.Path(sys.argv[4]).absolute()
output.mkdir(mode=0o700)  # exclusive: existing output is never overwritten
academic = pathlib.Path('apps/readest-app/scripts/academic').resolve(strict=True)
spec = importlib.util.spec_from_file_location('runner', academic / 'run-ovis-pdf.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
spec = importlib.util.spec_from_file_location('profiler', academic / 'profile-ovis-run.py')
profiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiler)
with fitz.open() as document:
    page = document.new_page(width=300, height=400)
    for x, y, text, size in [
        (24, 40, 'Readest OCR benchmark', 18),
        (24, 75, 'One small original synthetic page.', 11),
        (24, 95, 'Alpha beta gamma. 12345.', 11),
        (24, 115, 'The quick brown fox jumps.', 11),
    ]:
        page.insert_text((x, y), text, fontsize=size)
    raster = page.get_pixmap(dpi=144, alpha=False).tobytes('png')
assert hashlib.sha256(raster).hexdigest() == 'd1b5b2a3acd233aa90f548c7041921bc72e0890305b99a7ff89f158140bb2600'
(output / 'synthetic.png').write_bytes(raster)
(output / 'prompt.txt').write_text('Extract all text from the image. Return text only.')
command = [str(cli), '--model', str(model), '--mmproj', str(projector),
    '--file', str(output / 'prompt.txt'), '--image', str(output / 'synthetic.png'),
    '--offline', '--no-escape', '--threads', '2', '--threads-batch', '2',
    '--ctx-size', '2048', '--n-predict', '64', '--image-max-tokens', '1024',
    '--gpu-layers', '0', '--no-mmproj-offload', '--seed', '0', '--temp', '0',
    '--batch-size', '512', '--ubatch-size', '128', '--flash-attn', 'on',
    '--no-warmup', '--perf', '-lv', '4']
args = SimpleNamespace(threads=2, page_timeout_seconds=180,
                       max_rss_mib=1800, kill_grace_seconds=1)
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, runner.cancel)
signal.signal(signal.SIGCHLD, signal.SIG_DFL)
if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
    raise OSError('Could not enable child reaping')
receipt = runner.infer(command, output, args, time.monotonic() + 200,
                       {'kind': 'original-synthetic-raster'}, {'diagnosticOnly': True})
receipt['nativeTimings'] = profiler.parse_timings((output / 'stderr.log').read_text())
receipt['rawBytes'] = (output / 'raw.md').stat().st_size
with (output / 'summary.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt, indent=2))
PY
```

The fixture fingerprint depends on the stated renderer version. Investigate a
mismatch; do not remove the assertion to claim a matching reproduction. Native
logs may include local model paths; keep your raw diagnostics private unless
intentionally sharing them. The public numeric record above is sanitized.
Actual loaded-library verification is separate from hashing a named backend file.

This artifact does not change or recommend changes to the production OCR task,
visual budget, thread default or micro-batch default. Full-PDF accuracy and
performance on the target machine remain unmeasured.

SPDX-License-Identifier: AGPL-3.0-or-later
