# Zotero and Academic Reading Mode

This fork adds a read-only Zotero content source and an optional local academic PDF
reading mode. Ordinary PDF opening remains unchanged.

## Connect Zotero

1. Open **Settings → Integrations → Zotero**.
2. Enter your numeric Zotero User ID and an API key with personal-library and file
   read access. See the [official Zotero API documentation](https://www.zotero.org/support/dev/web_api/v3/basics).
   Prefer a read-only key. Do not put a key in source code, a URL, logs or a bug report.
3. Select **Test and save**, then **Open Zotero Library**. The library import menu
   also contains **Zotero Library**.

Native platforms use the existing system-keychain bridge when available. Otherwise
the connection form explicitly reports session-only storage: the API key stays in
memory and must be entered again after restarting. Cached library metadata and PDFs
remain available without a key. Nothing is sent through a Readest API proxy.

Only Personal Library and Zotero Storage PDFs are supported. Group Libraries,
linked files, WebDAV, note editing and remote modifications are outside this scope.
The client performs GET requests only; it does not write Zotero annotations.

## Browse and read

Collections retain their hierarchy. Rows show title, authors, year, venue and
**Not downloaded** or **Saved offline**. PDF bytes are requested only when you open
a paper. If several stored PDFs exist, the first valid attachment by key is used.
Downloads show progress and can be cancelled.

A downloaded file is a provider-owned local cache, outside the ordinary Readest
Book library and cloud-upload pipeline. Reopening it works offline. **Clear local
copy** removes only the device copy; it does not delete anything in Zotero.
**Refresh** updates metadata. Clear and download a local copy again when you want
new attachment bytes from Zotero.

## Reading Mode

Open a PDF, then choose **Reading** in its toolbar. This works for ordinary local
PDFs and provider-cached PDFs. The **PDF / Reading** controls return to Original PDF.
The mode is never entered automatically.

- Born-digital text is arranged into a responsive, continuous vertical flow
- Figures, tables, algorithms and complex display math preserve their PDF layout
- Tap a visual region to open the existing fullscreen image viewer; zoom/pan and
  double-tap or double-click are supported
- Closing the viewer retains the Reading scroll position
- Uncertain regions preserve original PDF visuals; a document without a usable
  text layer keeps Original PDF available and does not use OCR

Analysis is local, cancellable and page-bounded, with a worker where supported.
Unchanged PDF bytes reuse a versioned reflow cache. Regions are rendered near the
viewport rather than saved as a persistent image collection. Typography reuses
Readest's global or current-book font size, family and line spacing.

The built-in PDF-text path does not run OCR, AI, translation, remote parsing,
Markdown/EPUB conversion or annotation writes. Pre-generated Ovis results can
also be imported as a separate reading source, as described below.

## Read an external Ovis result

The usable Ovis workflow has two steps: generate a local bundle outside Readest,
then import it into Reading mode. This build does not start the model in the app.
No account or upload is required by the runner/import workflow.

If you already have the bundle:

1. Open the **same, unchanged PDF** in Readest and enter **Reading**.
2. Choose **Import Ovis result** and select the completed run's
   `result/bundle.json`. Do not select `raw.md`, `identity.json`, `run.json`,
   `bundle.provenance.json`, or an individual page result by mistake.
3. Check the displayed page coverage, reading order, figures, formula symbols
   and notes against **PDF**. Full page coverage does not prove correct OCR.
4. **Native PDF text** and **Ovis** switch the reading source. **PDF** returns to
   the original page view. Native PDF text requires a usable text layer; if that
   switch fails, the current Ovis source stays active. A rejected import also
   leaves the current source intact.
5. Reopening the same PDF reuses an intact Ovis cache where the app's local
   storage is available. Keep the original PDF and completed bundle as recovery
   files; cache persistence can fail or be cleared independently.

### Generate the bundle on Linux

This is currently a developer-prepared workflow, not a one-click runtime
installer. Obtain trusted local resources first: Python with PyMuPDF, a compatible
`llama-mtmd-cli` and its full libraries, Ovis GGUF model/projector, and a UTF-8 OCR
prompt. The repository does not ship a redistributable runtime/weights package.
Use independently checked sources and hashes; a supplied source revision alone
is not a build attestation. The fixed resource inspection tool is documented in
[OVIS-RUNTIME.md](../apps/readest-app/scripts/academic/OVIS-RUNTIME.md); its snapshot
verification does not authorize execution.

From the repository root, replace these example paths with your prepared local
files. The output parent must exist, and `paper-run` must **not** already exist.
All four producer scripts must remain together in
`apps/readest-app/scripts/academic/`.

```sh
python3 apps/readest-app/scripts/academic/run-ovis-pdf.py \
  --pdf /absolute/input.pdf \
  --cli /absolute/runtime/bin/llama-mtmd-cli \
  --model /absolute/runtime/models/model.gguf \
  --mmproj /absolute/runtime/models/projector.gguf \
  --prompt /absolute/runtime/prompt.txt \
  --runtime-revision 5266f24da75dc449bd56cbed7addb9c8e4a6a73e \
  --output-dir /absolute/outputs/paper-run
```

That revision is the inspected llama.cpp source revision; use it only for a
runtime actually built from that source. The runner does not authenticate this
operator-declared value. It records the actual input and producer byte hashes.
Its current defaults process every page sequentially on CPU with two threads.
It does not download dependencies or weights. The CLI's `--offline` flag prevents
its automatic downloads; it is not an operating-system network sandbox.

Import only after the process exits successfully **and**
`paper-run/result/run.json` has `status: "process-completed"`, complete coverage
and no missing pages. The final bundle and receipts are published together.
`Ctrl+C`, timeout or failure after run-directory creation leaves diagnostics
there without publishing a completed result. An earlier preflight or input-hash
failure may create no directory. Retry into a different new directory;
there is no automatic resume and no overwrite of previous runs.

The default limits are 15 minutes per page and one hour per document. Larger
inputs may need reviewed limits; the sampled RSS guard is not a hard kernel
memory limit. Encrypted PDFs, rotated pages and excessively large rasterized
pages are rejected. A zero CLI exit cannot distinguish EOS from token truncation,
so inspect content before relying on it. Model misreadings are not silently
corrected or hidden behind whole-page images.

## Developer inspection and regression

Development builds expose **Inspect layout** after analysis. Toggle raw items,
lines, paragraphs, columns, visual regions and reading order independently. Select
a block to inspect its geometry, source item references, fonts and confidence.
The inspector is hidden in production builds.

Run the local corpus harness from `apps/readest-app`:

```sh
node --experimental-strip-types scripts/academic-regression.mjs /path/to/pdfs \
  --output /path/to/report.json
```

It reads local PDFs with the installed PDF.js version and performs no downloads or
uploads. The public-source manifest and HPCC SHA-256 are documented in
[academic-pdf-corpus.json](./academic-pdf-corpus.json). Never commit the PDFs, full
extracted text, credentials or private library metadata.

For constrained native builds, `READEST_BUILD_SOURCEMAPS=0` disables only production
browser sourcemaps. Normal builds retain upstream sourcemap behavior. See
[validation](./academic-reader-validation.md) for exact checks and remaining limits.
