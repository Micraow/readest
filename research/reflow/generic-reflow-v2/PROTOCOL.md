# Generic reflow v2: isolated representation probe

Status: implementation research, not a replacement reader or a successful generalization claim. Prior candidate and final negative assessment are immutable (c322fe44a6ef91cc88963385720546d304d96a86). No OCR or model is used.

## Hypothesis and narrow first improvement

Native paint objects carry useful separation that a connected-ink graph destroys. A filled rectangle behind text should become a resizable background attachment, not a dependency edge that locks all foreground prose. The first probe must preserve the grey-box text as reflowable native text while separately accounting for the paint. Mathematical strokes and table borders must remain foreground unless the strict filled-rectangle rule is met.

The pipeline is PDFium native extraction -> typed paint/glyph inventory -> background/foreground separation -> explicit reading-order plan -> interval-aware output -> independent browser event/selection/zoom audit. Text objects are mapped from native character indices. Invalid Unicode mappings and invisible text rendering are tracked explicitly. Valid mapping is not proof that a PDF's encoding is semantically correct. Unsupported mappings retain local glyph visuals and cannot count as selectable-text success. Native character ordering is not assumed to be correct reading order.

Background candidates require an opaque fill, no stroke, a simple axis-aligned rectangle, sufficiently many enclosed native glyphs, and paint order earlier than the text. Every rejection/acceptance records measurements and configuration fields. Foreground paths/images retain their object identities; only local foreground relations can form local image/formula islands. Background containment is never a foreground union operation. Form containers/transforms, occlusion, clipping, unusual blend modes and annotation appearances remain explicit risks until tested.

## Hard failures

- Any emitted visible primitive missing or repeated; duplicate selection text inside a visual object.
- Output DOM atom sequence differs from the separately serialized logical plan or its intervals overlap/reverse. This is a structural condition, not semantic proof of reading order.
- A background joins prose into an image, a whole-page image is used as reader output, or a local island absorbs a long prose region.
- A displayed formula or table stroke is omitted, or unverified Unicode is counted as successful selection.
- Actual cold end-to-end page process exceeds 60 seconds or 1 GiB peak RSS under one-core affinity. CPU time, startup/import, extraction, raster, grouping and output are measured, with browser load/QA separately reported and included in total when claiming an interactive page budget. Cached inputs are disclosed. Network download is excluded from processing time but logged if used. Multi-arm groups are never called page latency.

## Evaluation sequence

1. One small original mechanism control; independently check a shaded panel, mathematical stroke, and table border.
2. Immediately diagnose old D5-P1 and D4-P1. These are seen, development-only examples. Any change prompted by them is labelled diagnostic tuning, even if generic.
3. Freeze code/configuration and select new source-document-disjoint nonacademic and paper pages from official metadata before viewing their PDF/images/output. Register selection seed, exclusions, page identifiers, input hashes and code hash. No replacement after output inspection.
4. Evaluate fixed pages with complete body units and actual browser inspection at 320/390/430 px and 20/28 px. Treat unknown order, Unicode, equations, continuation, interaction or visibility as unknown, not success. No overall readability score until the references and complete evaluation are available.

No public commit may contain private source PDFs, native text, crops, page images, source URLs with credentials, or model weights. Public artifacts are original code, generic settings, aggregate diagnostics and original controls. Exact-once inventory coverage is necessary but does not prove source visibility completeness or readable results.

## Mechanism amendments during seen-page diagnosis

- Effective font size uses the native text matrix, not `FPDFText_GetFontSize` alone. D5 uses font size 1 with a roughly 10x matrix.
- Local raster output now toggles native objects and renders only the owned object set to transparent pixels. It no longer takes a rectangular patch from the full foreground page. If a text object has unowned glyph records intersecting the output crop, the page fails rather than certifying glyph isolation.
- An axis-aligned horizontal stroked path with native characters both above and below is a fraction-support candidate. Reach and width bounds live in `Config`. It may attach a compact local expression, never a background. This is a geometric heuristic, not a formula recognizer; unrelated nearby prose and pure-text formulas remain failure risks.
- A list marker candidate is one non-alphanumeric, non-math-symbol character narrower than a configurable em limit. A subsequent source line continues its paragraph only when baseline spacing and marker-following text alignment agree; a new marker always starts a new unit. This is not a validated general list parser. Numbered lists, multi-character markers, nested lists, hanging punctuation, multi-column continuations and body lines beginning with punctuation can be misidentified. D5 is diagnosis evidence only. All decisions emit trace records.
- Background ranges must have contiguous owners and cannot cross. Local visual units can own a background relationship too; a background remains independent paint, not a foreground union edge. This still needs compositing reconstruction verification on complex real figures.
- Mathematical-symbol text left in ordinary CSS text triggers a hard failure. Pure-letter formulas, scripts, styles, colors, direction and semantic encoding can still escape this incomplete guard and remain unknown. No readability or formula-completeness acceptance is implied by an empty hard-failure list.
