# H8 seen usability repair: title and native panel-label row

The two visible structural defects are improved in actual local output. The
section heading now flows as one paragraph without the artificial gap. All five
lower panel labels remain underneath the corresponding native images instead
of becoming five detached reading paragraphs. The page now has 10 blocks,
compared with 16 in the previous atomic diagnostic. Its main figure caption
remains ordinary reflowable text.

The original H8 blind result is still **0/1 in 17.73 seconds**. This is a further
opt-in seen-data refinement. It does not modify the default cold pipeline,
weaken existing safety thresholds or rewrite previous diagnostic results.

## Evidence, not textual guessing

The title uses an independent `paragraph_title` prior and two complete native
source lines. Existing 1 em region-closure, font-ratio and baseline-gap bounds
apply unchanged. Both lines are in the same verified column and source interval;
external content, conflicting priors and uncertain native tokens cause refusal.
Only the new paragraph-internal gap is set by the existing native source-gap
median. Every other token field and all resource tables are unchanged relative
to the caption-stage reader. No paper words, identifiers or font names are used
as exceptions.

For the labels, a second independent `figure_title` anchor supplies a boundary
below the image region. Between those anchors there is one native text baseline
with five separate text blocks, and five separate bottom-row images. Their
columns have a unique one-to-one native geometric correspondence. The closure
retains their original pixel positions; it does not infer an internal semantic
reading order or match label letters. Multiple text rows, body/footnote priors,
missing/reused panel columns, conflicting captions, an external source interval,
excessive distance/size or unresolved surrounding order cause refusal.

The region contains 17 original leaves / 49 source units. Independently rendered
graphic support occupies 76.80%, still above the unchanged 60% minimum. Its full
source-relative composition is checked against the independently accepted native
assets. The separate image-prior-only policy remains available unchanged; this
additional authority is explicitly enabled with `--caption-delimited`.

## Reading and interaction checks

The whole 28 px / 390 px reader and both changed regions were inspected against
the actual source page. The heading gap is gone, the bottom label row is visibly
attached, the body remains in column order, and the main caption still reflows.
All six actual native Canvas grids (20/24/28 px × 320/390 px, DPR 2) are bounded,
including native vector contours and image boxes, with no undersampled images.

The actual shipped viewer module was also exercised in jsdom with native Canvas.
The local-image action opens the exact complete figure composite at its 2,747 px
native width, making the labels available in a large scrollable view. The source
view encloses the complete figure/label region; its full-page action works.
Closing restores focus and preserves the reader. These are native decode/DOM
checks, not real browser interaction evidence.

529 source units and 3,072 source-inventory glyphs remain bijective. All 2,806
remaining vector paints preserve exact native geometry, resources and state.
The 72 paints no longer emitted as vectors are preserved inside the enlarged
native composite; this is not paint deletion. All 16 local images pass exact
member-composite pixel equality. The source plan is byte-identical, independent
source-support failures remain zero, and all target-grid requests are accepted.

Mapping classifies every token: 454 eligible / 27 refused. The graphical composite
remains refused for copy, including its spatially retained labels. The title-only
step preserves all mapping eligibility. Native H5/H6 regression still compares
all 30 reference blocks pixel-for-pixel and retains fallback/import/copy behavior.

New controls cover 14 title cases and 13 caption-delimited cases. The complete
local-geometry suite has 123 passing cases; the selected Python suites total
222, plus existing mapping, selection, interaction and hostile-bundle checks.

## Remaining limits

Whole-page reading acceptance remains **false**. Printed source line-end hyphens
are still visible in reflowed words; no uncertain character is deleted. Wide
figures still need local focus at mobile widths. Real browser compositing,
selection and clipboard behavior, the full app build, and mixed-engine pixel
ownership remain unverified. The separate native-clip replay comparator retains
its 20-pixel difference; source observer and serialized replay differences are
zero. Original-PDF fallback remains available.

Native preparation (4.09 seconds), cached reader continuation (37.50 seconds)
and title refinement (0.52 seconds) were separate stages, with independent
60-second caps on the first two. Their sum is not a cold benchmark.

## Reproduce without redistributing paper content

After official hash-verified source acquisition and the original plan stages,
run the atomic helper with `--image-priors --caption-delimited`, then the existing
verified reader continuation. Run `prepare_title_diagnostic.py READER MODEL OUT`
and audit against the original source plan. Run the six-grid renderer, text-map
builder and `test_spatial_focus.mjs` with the same native Canvas/jsdom test
runtime used by the other actual-module tests.

Public source and the standalone handoff contain only code, official acquisition
metadata and non-content results. H8 paper bytes, extracted text, glyph paths,
rendered images and populated reader/viewer bundles are excluded.
