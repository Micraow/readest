# Local source-glyph reader prototype

This is a research tool, outside the production app. It processes a local native PDF through the frozen PP-DocLayout-S / source-mask / k2 pipeline, then writes a self-contained offline HTML reader. A protected object can be enlarged or located on the full original page. This makes small retained images inspectable; it does not solve mathematical reflow or reading order.

## Run with existing dependencies

Use the existing official dependencies recorded in neighboring research stages. No model is downloaded by this command. The root is the directory containing the experiment folders; flags can point to an existing PaddleX virtual environment, official PP-S model and compiled k2 harness.

```sh
python stroke-object-batch-v1/code/monitor.py python local-reader-v1/code/run.py \
  --pdf /path/to/local.pdf --pages 1,2 --output-dir /path/to/new-output \
  --research-root /path/to/experiments \
  --paddle-python /path/to/paddle-venv/bin/python \
  --layout-model /path/to/PP-DocLayout-S \
  --harness /path/to/k2-reflow-harness
```

Open the output `reader.html` locally. It embeds all required images and makes no network request. Keep this file private for private source PDFs: the source images are embedded in it. Output directories must be empty to protect earlier evidence. The prototype allows up to eight selected pages per run, checks a 16-million-pixel per-page raster budget, and preserves the whole page if native text is unavailable or a processing stage fails. The external monitor enforces one CPU affinity and a 960 MiB process-group RSS margin; its 60-second bound is for the whole selected run. Each CLI page also has a 60-second processing budget.

## Provenance and limits

The compositor is `stroke-object-batch-v1` unchanged except for the independently tested `fill-imgmask` physical-envelope support in `stencil-paint-v1`. The official 83 MB learned ordering head is excluded because the frozen batch demonstrated no order gain. No human object box drives processing. No text is transcribed by a model.

The viewer displays a fixed 390px raster layout. A narrower window scales it; it does not recompute line wrapping. Text selection, search, screen-reader access, hyperlinks, cross-page continuity, CJK, scanned-page recognition and Android performance are not validated. Known failures include inline formula/prose merging, small original fragments, mixed font size, auxiliary page numbers inserted into prose order, and inaccurate candidate boundaries. Full original fallback is not reflow success.

The original two-page fixture contains a native text/figure/equation page and a raster-only copy. After correcting a virtualenv-path integration bug, the native page processes in 6.64 seconds and the raster-only page preserves its original in 0.45 seconds. Process-group peak is 644484 KiB (about 629 MiB), one CPU affinity. Self-audit finds two of three native prose paragraphs genuinely wrapped, with the first retained small. This is a functional fixture, not generalization evidence.

Browser interaction is validated only by the existing permitted GitHub Chromium CI route. A passing UI test is not PDF semantic, accessibility, native-shell or Android acceptance. Browser status and exact tested hash are recorded separately.

Original code follows the repository's AGPL-3.0 license. Third-party dependencies retain their own licenses; no dependency source, model weights or third-party papers are bundled.
