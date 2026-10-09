# PDF engine choices and representation limits

Research date: 2026-10-09. Sources below are official documentation and upstream source code. This document describes an isolated representation experiment, not a production dependency approval or a successful generic-reflow result.

The current experiment targets **PDFium 153 / pypdfium2 5.13**. The complete version/build strings written by each run's audit are authoritative; pin the actual wheel, native binary and hashes for reproduction. Current upstream documentation can describe APIs or behavior newer than this build. Probe required symbols and test behavior against the installed binary rather than assuming that every current API is available.

## What the current prototype may claim

- A native **character and page-paint-object inventory**, with character-to-text-object associations and a proposed logical ownership plan.
- No equal-width subdivision of extracted text runs is needed to obtain PDFium character geometry.
- Object activation can support controlled rendering experiments without rewriting the input PDF.
- Exact-once accounting of the records that were extracted is a structural check only.

It must **not** claim a complete inventory of genuinely visible painted glyphs. Character extraction, native glyph identity, final pixel visibility, semantic Unicode correctness, reading order and visual reconstruction are different properties. In particular, an extracted character can be invisible, one painted glyph can represent several characters, and a crop can include paint not assigned to the crop in the logical inventory.

## Recommendation

Use PDFium/pypdfium2 for the first executable native-character/object probe. Keep the engine behind a small adapter and retain explicit unsupported/unknown outcomes. Use PDF.js as the browser-integration candidate after checking the version actually used by Readest. Treat MuPDF/PyMuPDF as a technically strong alternative requiring a deliberate licensing decision. Use pdfminer.six/pypdf for auxiliary inspection rather than final visibility truth.

None of these libraries automatically identifies semantic background, prose, formula and figure roles. Those are hypotheses above the engine, and need independent tests.

## PDFium / pypdfium2

### Useful interfaces

The public text API includes `FPDFText_GetCharBox`, `FPDFText_GetLooseCharBox`, `FPDFText_GetMatrix`, `FPDFText_GetCharOrigin`, `FPDFText_GetCharAngle`, and `FPDFText_GetTextObject`. It also exposes generated-character and Unicode-map-error flags. Several are explicitly experimental. pypdfium2 provides a helper layer plus `pypdfium2.raw` for C APIs not covered by helpers. [PDFium text header](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_text.h), [pypdfium2 API layers](https://pypdfium2.readthedocs.io/en/stable/python_api.html#preface)

Page objects expose text, path, image, shading and Form types. Object bounds, matrices, text rendering modes, colors and some transparency information are available. Clip-path geometry has a separate public interface. These interfaces are useful evidence but do not constitute a full renderer-device trace. [Object/edit header](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_edit.h), [transform/clip header](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_transformpage.h)

`FPDFPageObj_SetIsActive(false)` excludes an object from rendering while keeping it in memory. The upstream progressive-render test verifies that this affects the next render without regenerating content. This supports a small number of baseline/background/foreground passes on a dedicated in-memory document instance. Restore state with checked return values and `try/finally`; do not save the modified document over the input. [Activation rendering test](https://pdfium.googlesource.com/pdfium/+/dbf74efd6b17bb39818108c838613cb34404bab3/core/fpdfapi/render/fpdf_progressive_render_embeddertest.cpp)

### Characters are not painted glyph instances

Upstream `CPDF_TextPage::AddCharInfo` normalizes the U+FB00–U+FB06 ligature range into multiple character records using copied geometry. A ligature therefore can have several character indices but one ink support. Keep a character-to-ink-group relation; never emit a duplicate image just because character indices differ. Shared geometry is evidence of possible co-ownership, not by itself a universal deduplication rule: separately painted overprints can also share geometry. [Text-page implementation](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/core/fpdftext/cpdf_textpage.cpp)

The text returned by `get_text_range` can have a different length from the internal character list, and this helper is documented as UCS-2-limited. Do not zip an extracted string with per-index boxes; preserve native character indices and mapping diagnostics. Generated spaces/newlines are not native painted primitives. [pypdfium2 Text Page documentation](https://pypdfium2.readthedocs.io/en/stable/python_api.html#text-page)

`FPDFTextObj_GetRenderedBitmap` can rasterize a text object with the native engine, but its isolated result is not the same as its contribution after all page compositing. `FPDFFont_GetGlyphPath` also is not an API accepting an arbitrary original glyph ID: the implementation translates the supplied value through Unicode-to-charcode lookup. Missing, ambiguous or misleading Unicode mappings cannot be repaired by assuming that path API recovers the original glyph identity. [Text rendering/font implementation](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/fpdfsdk/fpdf_edittext.cpp)

### Forms, clipping, transparency and visibility

- Preserve the instance path, parent transform and clipping context for each Form occurrence. A reusable resource identifier is not an occurrence identifier. Either compose all relevant transforms or reject unsupported descendants; do not call uncomposed Form-space boxes page-space truth.
- Page-object order is useful for candidate occlusion reasoning, but is not a complete sequence of all internal glyph, pattern, mask and group paint operations.
- A character bbox is not an exact glyph coverage mask. Bbox intersection with later paint only establishes potential occlusion.
- Text rendering mode 3 is not the only visibility case: clipping-only text, zero alpha, optional content, crop/clip exclusion, later occluders and annotation appearances need independent treatment.
- Removing an apparent background may change a foreground's result under non-Normal blending, soft masks, non-isolated transparency or knockout groups. Such groups should remain indivisible until a validated reconstruction method exists.
- A full foreground-page raster followed by rectangular crops does not isolate the selected object's paint. Other foreground objects or neighboring glyphs inside the crop remain present. A white page background also remains white unless transparent rendering was explicitly requested and verified.

These are conservative engineering implications of the exposed object/clip APIs and the renderer's compositing responsibilities, not claims that the present prototype has implemented those cases.

### Runtime and licensing

PDFium is not thread-safe, including concurrent calls on different documents. Use serialized calls or separate processes, and explicitly release text pages, bitmaps, pages and documents. The pypdfium2 helper API remains a separately versioned abstraction; using `raw` requires careful ownership and lifetime management. [pypdfium2 API preface](https://pypdfium2.readthedocs.io/en/stable/python_api.html#preface)

pypdfium2 itself is available under Apache-2.0 / BSD-3-Clause terms. Its documentation/examples are CC-BY-4.0. PDFium is described upstream as BSD-style; its current top-level license file also includes Apache text. Redistributing a native build requires its actual license bundle, including dependency licenses and relevant notices. Do not reduce the entire binary's license situation to a single BSD label. Build options/runtime linkage can change the required notices. [pypdfium2 licensing](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing), [PDFium LICENSE](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/LICENSE), [pypdfium2 Apache license](https://github.com/pypdfium2-team/pypdfium2/blob/main/LICENSES/Apache-2.0.txt), [pypdfium2 BSD license](https://github.com/pypdfium2-team/pypdfium2/blob/main/LICENSES/BSD-3-Clause.txt)

## PDF.js

`getTextContent()` exposes text items containing a string, transform, width, height, font name and direction. It does not expose a stable public, one-record-per-painted-glyph ledger. Its text must not be converted to supposedly native per-character geometry by dividing the item width. [Public API](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib.html)

The current official API exposes `getOperatorList()` and rendering options `recordOperations` and `operationsFilter`. Recorded operation bounds/dependencies are useful for tracing and selective-rendering experiments. **Check Readest's actual pinned PDF.js version before proposing these as available integration APIs.** Availability in current draft documentation is not evidence that an existing Readest bundle implements them. [API source](https://mozilla.github.io/pdf.js/api/draft/api.js.html)

Filtering is not equivalent to disabling only pixels: the renderer checks `operationsFilter` before executing an operation. Skipping `showText` can lose text-position updates; skipping path operations can disturb path consumption or pending clipping. Preserve state dependencies or instrument the paint branch while retaining state transitions. Transparency groups and masks require more than a simple allowlist. [Canvas renderer](https://raw.githubusercontent.com/mozilla/pdf.js/master/src/display/canvas.js)

True glyph-instance tracing could instrument a pinned renderer's `showText`/`showType3Text` paths, retaining font, advance, transform, paint index and group/clip context. That is internal-API work with maintenance cost, not a capability already supplied by ordinary text extraction. Upstream warns that direct core-layer APIs can change. [Layer stability guidance](https://mozilla.github.io/pdf.js/getting_started/)

License: Apache-2.0; preserve applicable notices and audit the actual shipped dependencies. [PDF.js LICENSE](https://github.com/mozilla/pdf.js/blob/master/LICENSE)

## MuPDF / PyMuPDF

This is the strongest high-level starting point for the desired inspection data:

- `get_texttrace()` supplies character Unicode, glyph ID, origin and bbox, plus span sequence number, opacity, rendering type and layer.
- `get_bboxlog()` supplies ordered text/path/image/shading entries; its sequence corresponds to `seqno` values.
- `get_cdrawings(extended=True)`/`get_drawings(extended=True)` adds path, clip and group hierarchy, including group blend mode, opacity, isolation and knockout information.

These still do not make overlapping bboxes proof of final visibility. [Text trace and bbox log](https://pymupdf.readthedocs.io/en/latest/functions.html#Page.get_texttrace), [drawing/group APIs](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_drawings)

For a fuller trace, `mutool trace` records rendering device calls, and a custom `fz_device` can observe text, paths, images, clipping, masks, groups and tiles. Precise output reconstruction still must obey those compositing semantics. [Trace command](https://mupdf.readthedocs.io/en/1.27.0/tools/mutool-trace.html), [device interface](https://raw.githubusercontent.com/ArtifexSoftware/mupdf/master/include/mupdf/fitz/device.h)

MuPDF and PyMuPDF are available under AGPL or a commercial agreement. Do not introduce this as a silently interchangeable permissive dependency. Readest's concrete license, integration, redistribution and any network-service obligations must be checked; being open-source alone does not establish compliance. This document is an engineering risk assessment, not a legal compatibility conclusion. [Official licensing statement](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright), [PyMuPDF COPYING](https://github.com/pymupdf/PyMuPDF/blob/main/COPYING)

## pdfminer.six + pypdf

pdfminer.six's text device tracks per-character placement from font/CID/width, text matrix, spacing and rise. Its `LTChar` bbox is constructed from text advance, font size and descent; it is a layout box rather than a guaranteed tight glyph-ink outline. It can be useful as a second extraction view. [Text device](https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/pdfdevice.py), [LTChar implementation](https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/layout.py)

However, in the upstream interpreter inspected for this research, `do_gs` is a TODO and `do_W`/`do_W_a` do not implement clipping. Conventional extraction therefore cannot be the authoritative alpha/clip/visibility engine. [Interpreter source](https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/pdfinterp.py)

pypdf is useful for inspecting content streams, resource dictionaries, ExtGState and Forms. Its visitors expose operators and matrices, while `visitor_text` may return a fragment as large as a line. Its documentation warns about coordinates in complicated Form contexts. It is not a renderer; combining it with pdfminer.six does not supply missing compositor behavior automatically. [Visitor documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html#using-a-visitor)

Licenses: pdfminer.six is MIT; pypdf is BSD-3-Clause. [pdfminer.six LICENSE](https://github.com/pdfminer/pdfminer.six/blob/master/LICENSE), [pypdf LICENSE](https://github.com/py-pdf/pypdf/blob/main/LICENSE)

## Bounded execution and validation plan

The following are implementation recommendations, not measured guarantees:

1. Keep native character records, paint-object instances, proposed semantic roles, ink groups and logical reading intervals as separate concepts. Allow multiple characters per ink group and retain unknown mappings.
2. Initially separate only independently validated simple background cases. Never feed background containment into foreground connectivity. Do not infer safe separation from color or bbox size alone.
3. Preserve unsupported compositing groups as local visual units or fail explicitly. A mapped Unicode value alone is insufficient evidence to re-typeset a formula or styled/positioned native text faithfully.
4. Reconstruct at original positions and compare with a native baseline before evaluating reflow. DOM atom counters must be supplemented by checks for extra/missing pixels and text in crops.
5. Use a small, bounded number of rendering passes and a pixel budget; never re-render an entire page for every character. For scale, a 4-million-pixel RGBA bitmap alone uses about 16 MB, excluding decoding, fonts and other buffers.
6. Enforce one-core, 60-second wall and 1-GiB memory limits at a page-process boundary. Release native resources explicitly. Report timeout, memory exhaustion and unsupported cases honestly; no library guarantees arbitrary-PDF compliance with those limits.
7. Use no default OCR/VLM path. Missing Unicode, raster-only text or unsupported structure remain declared limitations rather than manufactured selection success.
8. Freeze engine versions and code/configuration before held-out evaluation. Synthetic controls should cover ligatures, duplicate overprints, white-on-dark text, pure-text formulas, rotated/vertical text, nested Forms, partial clipping, alpha-zero text, later opaque occlusion and overlapping/crossing background ranges.

No private PDFs, extracted text, crops or source-page images are included in this document.
