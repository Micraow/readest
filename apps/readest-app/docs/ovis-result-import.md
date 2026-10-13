# Local Ovis result import

Reading mode can import an Ovis result JSON for the currently open PDF. This is
an import/rendering slice, not an in-app inference service. It does not download
models, start an inference server or send PDF content to a provider.

Open a PDF → Reading mode → Import Ovis result. After a valid import, **Ovis**
and **Native PDF text** select the two reading routes. **PDF** retains the
original viewer. A cached Ovis result is restored on the next reading-mode open.
A wrong PDF or invalid bundle leaves the currently readable document intact.
Only covered pages are shown in a partial result, with an explicit coverage
warning. Inline OCR symbols may remain inaccurate.

## Version 1 contract

The root has `format: "readest-ovis-reflow"`, `version: 1`, a full-file
`pdfSha256`, original `pageCount`, `identity`, and nonempty `pages`.

`identity` records 64-character lowercase `modelSha256`, `projectorSha256`,
`promptSha256`, a 40-character `runtimeRevision`, and a flat `configuration`
object of strings, finite numbers or booleans. Include the adapter version,
render DPI, generation parameters and any configuration that affects output.
These are producer-declared provenance; the reader checks the PDF bytes and
cache integrity, not the authenticity of model weights absent from the app.

Each page has its original 1-based `page`, `width`, `height` in PDF.js scale-one
rotated viewport points, and ordered `blocks` with globally unique `id` values:

- `kind: "markdown"`, `markdown`: selectable prose, math or HTML table content
- `kind: "visual"`, `role: "figure" | "equation"`, `box: {x,y,width,height}`,
  optional Markdown `caption`: a local original-PDF region; optional finite
  `sourceFontSize` of at least one source-PDF point scales equation crops relative
  to the reader's text size (it has no effect on figure sizing)
- `kind: "footnote"`, `marker`, `markdown`: preserved note text

Internal Markdown links may target a block ID. Native prose coordinates are not
required or fabricated. Visual boxes must lie within the declared source page.
Groups of related panels should be supplied as one source region with their
shared caption. A formula source region preserves its appearance; keep its
number as a separate Markdown block when it is outside the region.

Bundles without `sourceFontSize` retain the existing 12-point fallback. Adding
the measurement changes the bundle content checksum, not the model identity.
The source box and PDF pixels are unchanged; the measurement only supplies the
point-to-reader-font ratio. Unknown fields and invalid sizes remain errors.
The reader still caps crops to the available width. Its existing one-point
denominator safety floor determines the supported minimum: the exporter omits
sub-point measurements and the importer rejects explicitly supplied sizes below
one point.

All imported Markdown is sanitized. Model-supplied images/media/frames cannot
load; visuals use the already opened local PDF session. After sanitization,
Markdown and raw table math use KaTeX's HTML visual layer with bundled local
fonts and accessible MathML. Only the trusted renderer may generate math layout
styles; imported HTML styles remain blocked. Mathematical alphabets therefore
do not depend on a browser implementing legacy MathML `mathvariant` values.
The KaTeX stylesheet is scoped to Ovis content and retains its upstream license.
Figure/formula zoom and reading appearance reuse the existing reader.

The original TeX remains in the formula's accessibility annotation. Ordinary
text selection is not a structured-math or lossless-LaTeX clipboard export.
Some bracket-delimited TeX containing URL-shaped text still conflicts with
Markdown link boundaries; this renderer change does not claim complete TeX
syntax support. Compare unfamiliar notation with the original PDF.

## Collected Ovis notes

An explicitly typed Ovis footnote with an unambiguous Markdown link from another
non-footnote block is shown in a **Notes** section after the main reading flow.
This keeps page-end notes from interrupting the next page's prose. Figure
captions can provide the link too. Note text, labels, block IDs, source pages and
existing return links are retained; repeated labels on different pages are not
merged or renumbered.

The reader uses the same Markdown parser and sanitizer as the displayed content;
the Markdown-generated link must survive as a clickable HTML anchor. Link-like
examples in code, mathematics or image descriptions do not move a note. Raw HTML
links alone are not used to infer this relationship. Unlinked notes and notes
with competing HTML targets remain in place. Native PDF footnotes, including
author and publication information, keep their existing presentation.

Collection changes only the displayed rows, not the imported bundle, cached
reading order or source ownership. It does not merge split paragraphs, remove
page numbers or invent missing references. Existing Ovis return links still
point to their recorded block, which may be the first reference rather than the
precise place most recently clicked.

## Local cache

Ovis uses `academic/ovis/<pdf SHA>/`, independent of the native layout cache.
Content files bind the canonical model/runtime/config identity and a canonical
bundle checksum; a validated current pointer selects the last import. Reopen
checks the PDF, pointer, payload checksum, schema and identity before deriving
reader blocks again. Changed model, projector, prompt, runtime, configuration or
content gets a different content key. Cache failure does not prevent reading a
validated import. Pointer publication is serialized per PDF within the reader process. Cancellation
or a failed pointer write restores the prior selection before the next publication;
reads wait for publication to settle. If storage itself cannot accept the rollback,
persistence is unavailable, while the current in-memory document stays usable.

## Exporting reviewed local adapter results

`scripts/academic/export-ovis-result.py` consumes a PDF, one processed page's
block/provenance JSON, and the identity JSON. It verifies the processed PDF/page
identity and writes the import contract without copying PDF images or weights.
The utility requires PyMuPDF and currently accepts unrotated pages only.

```sh
python scripts/academic/export-ovis-result.py \
  --pdf /local/source.pdf --page 2 \
  --result-dir /local/processed-page \
  --identity /local/ovis-identity.json --output /local/page.ovis.json
python scripts/academic/test_export_ovis_result.py
```

The processed directory contains `blocks.json`, `receipt.json` and
`native-math.json` from the local Ovis-first adapter. No research paper, real OCR
result, model weights or private inputs belong in the public repository.

Reviewed equation crops additionally measure native PDF font sizes. PyMuPDF's
[RAWDICT span size and character positions](https://pymupdf.readthedocs.io/en/latest/textpage.html#span-dictionary)
provide this geometry; glyph/line bounding-box height is not a font size. The
exporter selects characters whose bbox centers lie in the crop and excludes
whitespace, synthetic characters and text marked invisible or transparent.
Measurement requires native `alpha` and `char_flags` visibility fields
(PyMuPDF 1.25.3 or newer); missing fields on older versions cannot establish
visible glyphs, so their equation crops keep the fallback.
If an in-crop glyph's visibility is unknown, the whole crop's measurement is
omitted; discarding just that glyph could bias the remaining size samples.
Each selected horizontal glyph's scalar size must agree with its independently
reported `get_texttrace()` writing-axis scale, matched by character and origin.
All trace glyphs at that origin must agree in scale, including glyphs with a
different or unavailable Unicode mapping. Unmatched characters remain unknown.
Nonuniform transforms, rotated glyphs and missing/conflicting native evidence
omit the measurement. This avoids relying on glyph height, which PyMuPDF may
normalize even for fonts with less than one em between ascender and descender.
The check follows the upstream [text-trace scale calculation](https://github.com/pymupdf/PyMuPDF/blob/1.26.6/src/__init__.py#L21320-L21322)
and [MuPDF matrix expansion](https://github.com/ArtifexSoftware/mupdf/blob/1.26.11/source/fitz/geometry.c#L297-L301).
Each character contributes one size sample, regardless of font, span splitting
or glyph area. The median must also equal the largest sampled size, allowing
minority smaller scripts but abstaining when any larger glyph competes with it.
A lone large glyph might be an operator or the only main letter above a long
script; geometry alone cannot decide. This deliberately skips some valid
large-symbol formulas and script-dominated formulas rather than guessing their
primary size. Distinct middle samples, empty/raster-only crops and sub-point
measurements also omit the field.

This is a conservative geometric estimate, not formula recognition, semantic
validation or proof that a PDF's hidden text is accurate. It does not alter
formula crop resolution, boxes, raw Markdown/KaTeX, figure sizing or provenance.

## Exporting arbitrary raw Ovis Markdown

The same offline utility can take a PDF, an explicit 1-based page, the raw UTF-8
Ovis Markdown for that page, and a complete identity JSON. Filenames, paper
titles, figure numbers and page numbers are not a fixed case list.

```sh
python scripts/academic/export-ovis-result.py \
  --pdf /local/document.pdf --page 3 \
  --markdown /local/raw-page.md \
  --identity /local/ovis-identity.json --output /local/page.ovis.json
python -m unittest discover -s scripts/academic -p 'test_export_ovis*.py'
```

`--markdown` and `--result-dir` are mutually exclusive. Both require PyMuPDF;
neither runs a model. Raw mode requires all identity fields from the version 1
contract above. Optional `--expected-pdf-sha256` and
`--expected-markdown-sha256` reject input bytes that differ from known hashes.
These hash options apply only to raw mode; reviewed mode continues checking
its existing `native-math.json` source PDF/page receipt.

Raw mode preserves model words, LaTeX and table markup, including recognition
errors. Starting with an image, it groups adjacent Ovis images and intervening
short labels with a following `Figure N`, `Fig. N` or `图 N` caption. Short
paragraphs before the first image remain visible in the body; their location
inside a figure cannot be assumed. Grouped labels remain available in the
figure disclosure. Referenced, unambiguous superscript note definitions
move to linked footnotes with a return link; unreferenced or duplicate definitions
remain in the body. Code spans, fences, indented code and HTML `pre`/`code`
contents are not interpreted as notes or images. No native formula/table
comparison or source replacement runs here.
Use the reviewed mode when such evidence-based replacements already exist.

Image geometry must be supplied as a standalone Ovis tag:
`<img src="images/bbox_LEFT_TOP_RIGHT_BOTTOM.jpg" />`, with integer coordinates
in the model's normalized 0–1000 page space. The utility converts those boxes
to PDF points and crops only the supplied PDF. A figure group uses the panel
union with 2.5% of the shorter page side as padding, clipped to the page and,
when native caption text is available, capped above its matching caption.
Other images retain their individual boxes. There are no paper-specific
coordinates or text corrections. Unsupported/missing image geometry, nonpositive
or out-of-bounds boxes, an exact whole-page crop or group union, out-of-range
pages, and rotated pages are rejected rather than silently replaced.

The output is the same strict importable bundle, plus local audit files:

- `page.ovis.provenance.json`: raw PDF/Markdown/identity-file SHA-256 values,
  the declared page and identity, exact bundle hash, adapter/PyMuPDF version,
  and crop source block IDs, normalized model boxes, PDF boxes and PNG hashes
- `page.ovis-assets/`: 144-DPI source-PDF crop PNGs for offline inspection

The audit PNGs and sidecar are not needed by the app. The app renders visual
regions from its already-open local PDF. A crop can be reproduced with the
recorded PDF bytes, page, point box, DPI and PyMuPDF version; its hash can then
be compared with the receipt. The original raw Markdown is not overwritten.
Keep these generated audit artifacts local when their inputs are private.

**Provenance boundary:** the caller declares that the Markdown belongs to the
selected PDF/page. Bbox coordinates and model/runtime identity are also
producer-declared. Hashes establish byte identity, not correct OCR, correct
image detection or an authenticated model run. The sidecar explicitly records
that OCR accuracy, model geometry and native mathematics were not verified.
No `native-math.json` or inference receipt is fabricated by raw mode.

## Verification boundary

This is a candidate integration. Real-browser end-to-end import acceptance is
still pending; service and component checks do not substitute for that check.

Synthetic tests cover parsing, wrong-PDF rejection, identity/cache changes,
corrupt cache, cancellation, selectable Markdown/math, local note navigation,
blocked active content, route switching, cached reopen and stale native analysis.
The local fixed-PDF acceptance is recorded outside the public source tree.
A successful import does not prove that OCR formulas are semantically correct,
that missing pages were processed, or that inference has phone-level latency.

## Assemble multiple exported pages

`scripts/academic/merge-ovis-results.py` combines existing single-page or
multi-page bundles into one file accepted by **Import Ovis result**. It requires
Python and the same PyMuPDF dependency as the exporter. Run these commands from
`apps/readest-app`; the output directory must already exist.

First export each processed page using either exporter mode above, using the
same complete model/runtime/configuration identity. Then assemble the results:

```sh
python scripts/academic/merge-ovis-results.py \
  --pdf /local/document.pdf \
  --input /local/page-3.ovis.json \
  --input /local/pages-1-2.ovis.json \
  --output /local/document.ovis.json \
  --require-complete
python -m unittest discover -s scripts/academic -p 'test_*.py'
```

Repeat `--input` for every bundle; each may already contain several pages and
input order does not matter. `--require-complete` rejects any missing page from
the actual PDF before writing. For a deliberately partial result, omit that
flag: the command warns on stderr and reports exact covered and missing page
numbers in its JSON stdout and audit receipt. Page numbers always refer to the
original PDF. Open that PDF in Readest, choose **Reading mode → Import Ovis
result**, and select `document.ovis.json`. A complete assembly covers all of the
PDF's pages through the existing reader; a partial assembly still shows the
reader's coverage warning. The audit receipt is not imported into the app.

The merger reads the actual PDF bytes once and verifies every input's SHA-256,
page count and per-page rotated viewport dimensions against that PDF. Dimension
comparison allows only floating-point geometry noise (absolute `0.0001` PDF
point or relative `0.0000001`); it never rewrites a page size or crop. Mixed
page sizes and already-exported rotated viewport geometry are supported; the
single-page exporter itself still accepts only unrotated pages.
All model, projector, prompt, runtime and flat configuration fields must match.
Configuration key order and equivalent JSON numbers (`0` and `0.0`) do not
matter, while booleans and numbers remain distinct. It rejects duplicate pages,
even identical copies, and duplicate block IDs within or across inputs.

Validation mirrors the strict v1 reader contract in
`src/services/academic/ovis.ts`, including optional `sourceFontSize` and
`caption` types, nonempty text, finite values and in-page crop bounds. Unknown
fields, invalid JSON and ambiguous duplicate JSON field names are errors.
Pages are sorted by their original number; block order, repeated paragraphs
across pages, Markdown/HTML, equations, footnotes, link targets, crop boxes and
optional metadata remain unchanged. The merger neither deduplicates text nor
repairs OCR or dangling links. DOM sanitization and local-PDF crop rendering
remain the reader's responsibility.

Alongside `document.ovis.json`, the command writes
`document.ovis.provenance.json` with:

- The supplied PDF's SHA-256 and the declared common identity
- Each input's exact byte hash and original page numbers, indexed by CLI order
- Every output page's input index and source-bundle byte hash
- Actual page count, covered/missing page lists and completeness
- Exact output bundle byte hash and merger/PyMuPDF versions
- Explicit verification limits; a model run and OCR accuracy are not authenticated

Filenames and local paths are not recorded. Renaming the PDF or input files
without changing their bytes does not change the assembled bundle or receipt.
The receipt binds existing input bytes, not the truth of producer-declared
model identity or page attribution. It does not ingest or authenticate an
input's separate exporter sidecar. Keep original inputs and their sidecars
locally if you need to trace back further to raw Markdown or crop PNGs.

The merger validates all inputs and output destinations before publishing.
Bundle/receipt paths must differ from all sources and cannot be file symlinks,
hardlinked files or directories. An output name ending `.provenance.json` is
reserved for receipts. Both outputs are serialized and staged before replacing
either; the receipt is published first and the bundle last. A caught bundle
publication failure restores the previous receipt. Each replacement is atomic,
but the pair is not a crash-atomic transaction: after interruption, check that
the receipt's `bundleSha256` matches the bundle bytes or rerun the command. A
receipt restoration failure is reported explicitly instead of claiming success.
