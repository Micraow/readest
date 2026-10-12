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
  optional Markdown `caption`: a local original-PDF region
- `kind: "footnote"`, `marker`, `markdown`: preserved note text

Internal Markdown links may target a block ID. Native prose coordinates are not
required or fabricated. Visual boxes must lie within the declared source page.
Groups of related panels should be supplied as one source region with their
shared caption. A formula source region preserves its appearance; keep its
number as a separate Markdown block when it is outside the region.

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

## Verification boundary

This is a candidate integration. Real-browser end-to-end import acceptance is
still pending; service and component checks do not substitute for that check.

Synthetic tests cover parsing, wrong-PDF rejection, identity/cache changes,
corrupt cache, cancellation, selectable Markdown/math, local note navigation,
blocked active content, route switching, cached reopen and stale native analysis.
The local fixed-PDF acceptance is recorded outside the public source tree.
A successful import does not prove that OCR formulas are semantically correct,
that missing pages were processed, or that inference has phone-level latency.
