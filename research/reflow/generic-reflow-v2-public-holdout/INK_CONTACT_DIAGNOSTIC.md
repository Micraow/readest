# Bounding-box contact is not actual ink contact

The retained H7 footnote warning concerns two contour bounding rectangles. A new
read-only audit paints each affected token separately using the unchanged native
reader painter and its actual layout transform. It omits only the painter's one
white background rectangle to expose transparent alpha. All nonzero alpha counts,
including alpha=1; there is no visibility threshold or tolerance relaxation.

At 20/24/28 px, widths 320/390/800 px and DPR 1/2, all 18 actual-grid cases have
nonempty support for both tokens and **zero shared nonzero-alpha pixels**. The
warning is conservative in these tested layouts and does not require merging
content or altering the existing paragraph geometry. The source glyphs, paths,
reading order, selection protection and native ownership gates are untouched.

Eight authored controls distinguish intersecting bounding boxes with disjoint
shapes, true one-pixel collisions, faint alpha collisions, adjacent pixels,
empty support, mismatched dimensions, oversized allocations and symmetry.
A contact result never authorizes an automatic merge. No hand-created ink or
paper-specific coordinate/word rule is introduced.

This is finite-grid native Canvas evidence. It does not prove every arbitrary
scale, browser compositor behavior, or mixed-engine source ownership. The earlier
geometric warning remains in its historical report. This narrows that warning's
meaning rather than erasing its evidence or certifying overall reading acceptance.
