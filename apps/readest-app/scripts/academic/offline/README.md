# Offline Ovis package launcher

This directory contains the source for the standalone Linux x86-64 CPU launcher.
It uses the existing generic Ovis PDF runner/exporter/merger. It does not register
Tauri commands, change application permissions, download models, or enable GPU
inference. It is separate from Readest's in-application execution capability.

## Distribution layout

Copy these three source files to the root of a prepared portable distribution:

```text
run.sh
launch.py
test_launcher.py
SHA256-MANIFEST.json
prompt.txt
bin/llama-mtmd-cli
bin/                       # required, relocatable native libraries
models/OvisOCR2-Q3_K_M.gguf
models/mmproj-OvisOCR2-Q8_0.gguf
python/bin/python3.12
python/lib/                # isolated standard library and PyMuPDF
scripts/run-ovis-pdf.py
scripts/export-ovis-result.py
scripts/merge-ovis-results.py
scripts/ovis_markdown.py
licenses/
```

The prepared Python runtime must load only its bundled standard library,
site-packages and `scripts/`, for example through an adjacent `python3.12._pth`
file. ELF library lookup must work relative to the executable without an
inherited `LD_LIBRARY_PATH`. The shell entry clears inherited environment
variables and invokes Python with `-I -S -B`.

The manifest is JSON with a `files` array. Every entry has a relative POSIX
`path`, integer `bytes`, and lowercase SHA-256 `sha256`. It covers every shipped
regular file except the manifest itself. Runtime directories reject unlisted
files and symlinks. Compare the manifest's digest with a trusted delivery
channel before running the launcher: this check detects corruption and is not
a signature or a substitute for authenticating the distributor. Do not replace
libraries or insert unlisted plugins into a distribution.

A binary distribution must supply all required component licenses/notices and
corresponding-source access directions. This source-only directory does not
include models, interpreters, native libraries, or a complete redistributable
binary package.

## Use a prepared package

For a `.tar.zst` distribution, first extract it with `tar --zstd -xf FILE.tar.zst`.
Then, from its top-level directory:

```sh
./run.sh --check
./run.sh "/absolute/path/document.pdf" "$HOME/new-ovis-result"
```

Use an output directory that does not exist and whose parent already exists.
The input PDF is never changed. `result/bundle.json` is published atomically
with the terminal receipt only after all pages complete and the existing
merger verifies complete coverage. Original model text, per-page diagnostics,
figure crops and source hashes remain available. Failed/cancelled runs do not
publish a complete result; retry with a new output directory.

The launcher requires Linux x86-64 and glibc >= 2.38. Its CLI revision is
`5266f24da75dc449bd56cbed7addb9c8e4a6a73e`. Runtime filenames identify the fixed
OvisOCR2 Q3_K_M model and Q8_0 projector profile; the distribution manifest binds
their actual bytes. No document titles, page numbers, content corrections or
paper-specific geometry are encoded here.

Defaults are two CPU threads, 144 DPI, 2048 visual tokens, an 8192-token context,
4096 output tokens, Flash Attention enabled, 15 minutes per page and six hours
for the whole task. Pages are processed sequentially. The default visible-memory
startup guard is 6 GiB; the sampled process-group RSS stop threshold is 4 GiB.
`--low-memory` uses 1024 visual tokens, a 3 GiB startup guard and a 2 GiB sampled
RSS threshold. These are conservative guardrails, not measured minimum
requirements or kernel limits. Container limits may be lower. The lower visual
budget can reduce small-text, table and diagram quality.

The inherited runner rejects encrypted PDFs, rotated pages, inputs over 512 MiB
and rasters over 24 million pixels. `--threads` allows 1–8, `--page-timeout`
allows up to 3600 seconds and `--wall-timeout` up to 86400 seconds. Ctrl+C
cancels the task and reaps its owned process group. Existing files are not
overwritten and unrelated processes are not terminated.

`--check` verifies package hashes, bundled imports and the CLI version without
loading the model. Neither this check nor successful process exit proves OCR
completeness, authenticated EOS, absence of output truncation, or GPU support.
The local CLI receives `--offline`; this is not an OS network sandbox. Always
compare important text, equations and table values with the source PDF.

## Synthetic launcher tests

With a prepared runtime containing PyMuPDF:

```sh
python/bin/python3.12 -I -S -B test_launcher.py
```

The tests cover integrity failures, extra files, symlinks, unsafe manifest paths,
platform/ABI rejection, memory guards, fixed profile arguments and no-model
`--check` behavior. They do not execute model inference or require networking.
The parent `test_run_ovis_pdf.py` and exporter/merger tests separately exercise
the generic producer lifecycle with synthetic PDFs and fake local children.

SPDX-License-Identifier: AGPL-3.0-or-later
