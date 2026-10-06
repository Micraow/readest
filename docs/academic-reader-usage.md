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

There is no OCR, AI, translation, remote parsing, Markdown/EPUB conversion or
annotation-write integration in this feature.

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
