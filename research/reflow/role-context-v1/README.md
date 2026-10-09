# Role/context baseline: regression gains, weak new-source coverage

The stronger fixed geometry rules require a number label to lie outside the formula's glyph-derived core. Bare labels additionally need column-margin evidence. A text/native-parent region may regain word reflow only with high detector confidence, at least90% glyph support, stable body font size and sufficient prose context. Detached display-like mathematical lines force an original crop. Pixel ownership and all other components remain those of `visible-mask-v1`.

Six original positive/negative controls passed before the real runs. Two previously seen pages are regression only. Two new sources, the 2000 Adiabatic paper and Swin Transformer, were selected before inspection and processed once without tuning.

## Results

| Partition/input | Complete prose candidates | Main finding |
| --- | ---: | --- |
| Seen ConvNeXt p3 | 4/4, all visibly wrapped | Consistent native prose regains reflow; prior order repair retained |
| Seen MobileNet p3 | 9/12 candidates, 8 visibly wrapped plus1 short inconclusive | Internal numerator1 tokens no longer typed as labels; detected mixed formula/text region is now protected |
| New Adiabatic p3 | 2/8 | Dense adjacent prose/math remains coarsely protected; formal section-number labels all missed |
| New Swin p4 | 0/7 | One unseeded visible component triggers whole-page original fallback |

All four final outputs retain source ink without uncovered or duplicated pixels. This is not a quality pass: new-source complete-prose candidate coverage is only2/15. Original-image fallback remains in every denominator. The source-defined Adiabatic units include prose interrupted by display objects, so its unit A4 requires all its prose portions to remain supported; tiny words are not dropped from that denominator.

MobileNet's accepted formal-label roles are now2/2, with recall still2/3. Equation5 remains a missed detector candidate, and its mixed text region is protected instead of being silently reflowed. This local precision improvement does not establish broad label support.

The Adiabatic paper uses identifiers (2.4) through (2.12). All nine are outside the inherited integer-only candidate grammar, so relation candidate recall is0/9. This is an input-schema omission, not nine demonstrated failures of an otherwise supplied pair scorer. Most math shapes survive in original crops, but several prose/math groups become too small at390pixels; labels2.9 and2.12 are separate crops, so the intended atomic association is not certified. Its raw k2 baseline wraps the prose with uneven indentation and keeps labels near their expressions; changed mathematical line breaks were not automatically classified as semantic errors.

Swin's physical paint envelope covers the full page, yet the semantic-mask stage has one unseeded component with1,137pixels. Read-only post-run reconstruction locates a black horizontal footnote separator: native stroke-path343, spanning approximately94.9PDFpoints. The line is neither text nor a detected picture, so the semantic seeds omit it. The conservative guard returns the original page unchanged. The baseline k2 wraps all seven local prose units, but inserts page number4 into the cross-column continuation, so one unit fails the order check. Refusal in our method preserves content but gives zero mobile reflow.

This is another useful boundary: broad paint boxes must never own arbitrary black pixels, but legitimate native graphic primitives still need a source-supported semantic or auxiliary parent. Removing the separator, loosening pixel coverage or changing the current test after seeing it would hide the defect.

## Next falsifiable change

Register a typed native-primitive relation before another new source: a uniquely matched horizontal stroke immediately above a detected footnote may seed that complete divider component into the footnote parent. Require actual stroke geometry, final visible pixels and unique nearby footnote context; do not use broad fill rectangles or delete white paint. Other unseeded components must continue to refuse. Separately specify the formal-identifier grammar as a general schema covering section-number tags, with negative operand/header cases. Current papers become regressions only.

The algorithm hashes stayed unchanged throughout real evaluation. A preparation-only JSON serialization issue arose because PyMuPDF rawdict includes binary image payloads for fraction bars; binary payloads were omitted from QA metadata, while source PDF/raster and glyph processing remained unchanged. No PDF was re-downloaded for that repair. Public code/aggregates exclude papers and crops.

Single-CPU composition took approximately2.0–2.8seconds per page. The detector used under600MiB process RSS. Resource measurements and all quality denominators are distinct from CI; no application integration or Android tests ran. Visual checking was self-audit, with unchanged prior regions compared to earlier output and changed regions inspected. This stage does not establish production or cross-source fidelity.
