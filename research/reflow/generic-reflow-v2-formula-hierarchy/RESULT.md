# Formula hierarchy, seen-page result

## Useful change

The new reader separates an independently owned equation core from its number.
It reuses native images/vectors and never substitutes Unicode or splits a glyph.
H5 has two accepted formula hierarchies; H6 has one. The wide H5 core is 39.0%
larger on the same 390px viewport (effective scale 11.99 -> 16.67px). H6's changed
core is 10.8% larger at 20px, 25.1% larger at 28px. Its number follows on a short
right-aligned row. The formerly detached H5 number is again beside its formula.
These are improvements to already seen pages, not new blind results.

The two unpacked old composites are reconstructed exactly from independent
child RGBA at their original target grid: 0 different pixels and no overlapping
supports. The separate formula/number case retains the existing two resources.
Native unit counts stay 316/749, but these counts do not prove ink completeness.
The already indivisible two-row formula in H6 is retained unchanged.

## Tests and visual review

16 authored relation tests and 18 layout cases pass. They include unknown
Unicode, prose/citation, interrupted logical intervals, ambiguous associations,
cross-column candidates, tall columns and extra-unit negative cases.
Candidate 1 refused the detached number because the prior region tree called a
compact two-singleton band two columns. Candidate 2 uses only the explicitly
bounded contraction described in CONTRACT.md; both versions remain private.
A test originally compared two floating-point divisions using exact equality;
12.2 vs 12.199999999999998 failed. The assertion now has 1e-12 tolerance; the layout
was unchanged. This test defect is retained in the evidence.

All 17 full-page CSS-sized review bands were actually viewed on 2026-10-09:
H5 20px: 2; H5 28px: 3; H6 20px: 4; H6 28px: 8. Both original source pages were
also viewed again. The prior paragraph/column improvements remain. Formula
cores, numbers and neighboring prose were reviewed; no new omitted body section
or number duplication was observed. This was native Node canvas, not a browser.

At the actual output scale/DPR all new child resources have sufficient sampling;
the geometric audit reports no canvas overflow or inter-token bounding-box
contact. A strict isolated-child translation of 3 device pixels still FAILS on
H5: 15/42/15 changed pixels across the affected cases, maximum channel difference
1. H6's four cases are exact. This is retained as a strict numerical failure,
not patched by thresholding. Uniform placement geometry and original resources
remain intact; neither this nor visual review proves mixed-engine page pixels.
Older source vector contour overflows (86/237) also remain disclosed.

## Size and cost

H5 payload 598,781 bytes (previous 604,447), 300 vector tokens and 11 local images,
134,300 PNG bytes, 98 shared contours. H6 payload 1,304,864 bytes (previous
1,305,387), 719 vector tokens and 27 local images, 212,559 PNG bytes, 209 contours.
No new dependency or model was added. The unchanged PDFium/PDF.js/native-canvas
runtime requirements still apply. This is source-light only.

Hierarchy construction alone measured 0.247/1.560 seconds wall on the shared
machine, with cached native plan, model prediction, glyph capture and target
images. It was not a fresh supervised request; it is not a page latency or CPU
claim. The previous two complete cold-page attempts both timed out at 60 seconds.
Those failures remain. There is no new CI result.

## Still fails overall acceptance

- The wide H5 formula is larger but still small at fit width, especially compared
  with 28px body text. It needs a verified local focus/zoom path.
- H6 source-line hyphens, separated title blocks and tall rotated marginal tail
  remain visible. Nothing was silently discarded to shorten the page.
- Browser behavior, text selection/copy and semantic Unicode are unverified.
- Mixed-renderer full pixel ownership and full cold page budget are not passed.
- H5/H6 remain seen; the frozen original blind outcome is still 0/2. No additional
  registered holdout was opened. No paper-specific branches were added.
