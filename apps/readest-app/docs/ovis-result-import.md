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
load; visuals use the already opened local PDF session. Markdown and raw table
math use the existing KaTeX/MathML path. Figure/formula zoom and reading
appearance reuse the existing reader.

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
