# Native prose fusion preview

`src/services/academic/ovisProseFusion.ts` is an experimental, pure preview API.
It is deliberately not connected to the reader, Ovis import, or persistent cache.
Call `previewNativeProseFusion(validatedOvisBundle, nativeScholarlyDocument)` to
inspect proposed replacements and per-block decisions. The result is not an
importable Ovis bundle; it retains both the original and replacement text plus
native source coordinates for review.

The first version only handles long English/ASCII prose paragraphs. It requires the
same PDF fingerprint and page geometry, a unique match in both directions,
consistent reading order, a single native column, usable native glyph evidence,
and plain text inline runs. Matching uses exact six-word boundary anchors. The
only non-identical words permitted are a very small number of interior lowercase
words with one i/l optical-confusion substitution. Digits, common English number
words, capitalized names, reference numbers,
hyphens, additions, deletions, and boundary changes are not repaired speculatively.
Common ligatures and soft line wrapping are normalized; mathematical superscripts
are not. Multiple paragraphs, Markdown hard breaks, and indented code are rejected.

Recognized complex or ambiguous content stays with Ovis, including Markdown tables,
formulas, visuals, footnotes, styled/ambiguous native runs, duplicated paragraphs,
and conflicting order. These gates are heuristic, not a calibrated confidence
score or a guarantee that an accepted correction is right. Undetected inline math
or lowercase names can escape heuristics. Retaining Ovis content does not establish that its
formulas or tables are correct. Original PDF visuals remain the reference.

## Validation and limits

Synthetic tests cover both accepted replacements and fail-closed cases. Real PDF
extraction can be evaluated separately, but matching a synthetic OCR surrogate
does not measure improvement on real Ovis output. A different PDF edition must
not be assigned a matching fingerprint just to run a comparison.

Before enabling this in the reader, evaluate matched original PDFs and actual
Ovis runs; visually audit every changed span and preserve provenance. Check
numbers, names, citations, column order, line-end hyphenation, and inline math.
Keep a source-page fallback for anything uncertain. Scanned PDFs may have no
usable native text and require OCR.

This postprocessing experiment does not reduce Ovis inference time. Selective
region OCR is a separate step requiring high-recall layout detection, crop
validation, reading-order reconstruction, and full-page fallback.
