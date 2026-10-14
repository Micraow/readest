# Inspect Ovis timings without rerunning the model

`profile-ovis-run.py` is a standalone, standard-library-only diagnostic tool.
It reads an existing runner output directory or ZIP. It never extracts the ZIP,
loads a model, runs a native executable, changes the source results, or contacts
a network service. It works with existing version-1 runner receipts, so a frozen
runtime distribution does not need to be modified or have its manifest changed.

```sh
python3 -B profile-ovis-run.py /path/to/completed-run
python3 -B profile-ovis-run.py /path/to/results.zip --run-prefix archive/run-a
```

A ZIP can contain both a cancelled attempt and a later successful run. If more
than one root contains `run.json`, the tool refuses to guess: select the exact
root with `--run-prefix`. The chosen root's `result/run.json` takes precedence
over its nonterminal `run.json`. Neither filename alone proves success. The
terminal receipt must declare a clean completion and full page coverage before
the report marks the run complete.

JSON is written to stdout by default. `--output /path/to/new-profile.json`
creates a new file exclusively and never overwrites an existing file. Reports
omit OCR text, images and local absolute paths, but contain document and output
fingerprints, timing information and recorded runtime settings. Keep them
private unless their disclosure is intended. Do not commit personal reports,
input documents or result archives to the public repository.

## What is measured

- Run wall time comes from the selected runner receipt.
- Page process time comes from each covered page's execution receipt, including
  native startup, model loading, image encoding, prefill, generation and shutdown.
- Image encoding is summed from the native `mtmd batch encoding done in ... ms`
  lines when present. It is unknown, not zero, when the logs omit those lines.
- Native load, prompt-evaluation and evaluation counters are shown separately
  when an unambiguous `llama_perf_context_print` summary is present. These are
  native counters, not authenticated token counts or proof of generation ending.
  Duplicate summaries are marked ambiguous rather than added together.
- Outside-page time is complete-run wall time minus the sum of page-process
  durations. It includes all unprofiled Python work within the recorded interval,
  such as hashing, rendering and export. It is not model-loading time. Launcher
  checks and preflight before that interval are not included.

Native counters may overlap, so the tool does not subtract their sum from wall
time to invent a decode or overhead duration. A counter greater than page wall
time is flagged and discarded. Missing phase logs cannot be reconstructed from
elapsed time. For cancelled runs, only completed, covered pages are profiled;
unfinished-page timings are deliberately excluded and a full-run ratio is refused.

The selected receipt's hashes are checked for each covered page's execution
receipt, stderr, raw output and raster. Page identity, source identity, child
cleanup and exit status must agree. This checks consistency, not provenance or
all exported assets. SHA-256 is not a signature. Symlinks, ZIP traversal paths,
duplicate ZIP members and oversized artifacts are rejected. Reads are bounded
at 8 MiB per JSON receipt, 64 MiB per other artifact and 100,000 ZIP entries.

## Conservative A/B comparison

Run the same document separately with the original and candidate prepared
packages, writing to new output directories. Then compare the saved results:

```sh
python3 -B profile-ovis-run.py /path/to/baseline-run \
  --compare /path/to/candidate-run --output /path/to/new-comparison.json
```

ZIP candidates also support `--compare-prefix`. Comparisons require complete
runs, identical PDF/model/projector/prompt fingerprints, matching page coverage
and rendered images, and equal recorded configuration values. Different thread
counts, image budgets or timeout settings are reported as mismatches, with no
speed ratio. Producer code hashes and declared native source revisions may
change; those differences are listed explicitly. Unknown configuration fields
fail closed so an unreviewed future setting cannot be silently ignored.

`wallSpeedRatio` is baseline wall seconds divided by candidate wall seconds.
It is an observational ratio for those two runs, not a general speed guarantee.
Per-page raw-output hashes show which pages changed. Compare important text,
formulas, tables and completeness against the source, especially on changed
pages. Matching output bytes do not establish correct OCR or authenticated EOS.

The existing receipts do not identify all dynamically loaded backend libraries.
A matching CLI hash cannot prove that a particular AVX2 library was used. Keep
package manifests, backend validation records and loader verification with the
private experiment. The profiler explicitly reports this identity limitation.

For a reproducible target-machine experiment, keep the machine, power mode,
model, prompt, visual budget and threads fixed. Run interleaved A/B pairs using
separate output directories; include cold/warm-cache conditions in your private
experiment notes and repeat enough to see run-to-run variance. Review quality
before concluding that a shorter runtime is a usable improvement. A CPU
microkernel result is not a measured full-document OCR speedup.

## Synthetic verification

```sh
python3 -B test_profile_ovis_run.py
```

Tests construct their own tiny receipts, dummy artifact bytes and nested ZIPs.
They require no model, user document, network or PyMuPDF installation.

SPDX-License-Identifier: AGPL-3.0-or-later
