# Concrete integration seams and limits

Inspected source at research checkpoint 91d27378; the candidate currently ships only
as the unlinked `public/research/reflow-viewer.html` entry. No normal-reader adapter
below is implemented or claimed complete.

## Explicit entry point

`src/components/academic/AcademicReadingButton.tsx` lazy-loads
`AcademicReaderDialog`. Its `file`, `title`, optional `viewSettings` and
`onOpenChange` interface keeps PDF parsing off the ordinary opening path. An eventual
native-vector option should be an explicit experimental choice inside that boundary.
`src/app/zotero/page.tsx` hosts the button beside `OriginalPdfView`. Neither that
screen nor the regular `Reader` currently imports this experiment.

## Runtime boundary

`src/services/academic/runtime.ts` exposes `openAcademicPdf(file, signal)` returning
`AcademicPdfSession` with `analyze(storage, onProgress, signal)`,
`renderRegion(page, box, canvas, targetWidth, signal, trimBelow?)`,
`renderPage(page, canvas, signal)` and `destroy()`.

That interface currently delivers semantic geometry plus rasterized regions; it
does not expose this experiment's native path resources, paint states, affine
programs, PDFium glyph records or verified glyph-to-paint bridge. Calling
`renderRegion` is not equivalent to producing the native-vector reader. A real
adapter needs a separately versioned vector-capture result and explicit lifecycle /
abort handling, rather than pretending the present session already supplies it.

## Coordinate and identity boundary

Production `SourceSpan` uses `{page, boxes: Rect[], itemIndices: number[]}`;
`Rect` is a scale-one PDF.js **rotated viewport**, top-left coordinates.
The experiment stores `source_pixel_box` at `source_capture_scale` and character
`box_pdf`. For the current unrotated fixtures, division by the capture scale gives
source-point rectangles. A future adapter must carry explicit PDF page index,
rotation and viewport transform; it must not assume all PDFs are unrotated.

Both current H5/H6 PDF fixtures contain exactly one page. H5's printed page label
is 9, but its fixture PDF page index is 0. They are source-page fixtures, not full
multi-page originals. Printed page labels must never be used as numeric page indices.

`native_event` is a paint-event identity, and `source_glyph` is an immutable native
glyph identity. Neither is a production PDF.js text-item index. Do not copy either
into `SourceSpan.itemIndices` without a proven cross-schema correspondence. Source
rectangle return can remain geometric while semantic identity is unavailable.

## Semantic boundary

Production `InlineRun` can be text or source-preserved content. Native-vector
appearance must not be flattened into text runs merely because two extractors agree.
The experiment has eligible scalar text and explicit unresolved sentinels; ranges
crossing an unresolved formula refuse. This rule must survive any adapter instead
of turning an unknown formula into an empty run. Keep semantic certification false.

## Reading position and lifecycle

`components/academic/readingAnchor.ts` provides a UI-only `ReadingAnchor` with
`blockId`, optional `textOffset`, `viewportY` and `blockRatio`; it reads
`[data-block-id]` and skips button / aria-hidden text. Candidate block IDs currently
come from a particular prepared page order. Do not persist its offsets under a normal
reader fingerprint until the vector layout/schema version is part of the identity.

Preserve the existing dialog's top-level Escape stack, focus trap, cancellation and
`useAcademicHistory` behaviour when embedding a renderer. The experiment's own
native dialog helper is tested independently; that does not certify interaction
inside the production modal stack.

## Adoption gates

1. Versioned native extraction/capture contract and original-PDF page provenance.
2. Rotated-page/source-box controls and explicit semantic-index correspondence.
3. Abort/destroy behaviour and bounded resource ownership in the app session.
4. Real browser mouse/keyboard selection, clipboard, source return and no-network QA.
5. Full Readest web/Tauri build and platform smoke tests.

Until these pass, use the isolated entry. Do not replace the default reader, extend
production cache schemas, claim arbitrary-PDF support or reinterpret precomputed
resource loading as cold extraction performance.
