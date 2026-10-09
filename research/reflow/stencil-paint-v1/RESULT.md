# Stencil paint support: mechanism fixed, reader quality still limited

A generic physical paint-type omission was found in the frozen BatchNorm result: MuPDF reports stencil bitmap painting as `fill-imgmask`, which was absent from the envelope whitelist. All 2055 uncovered source pixels belonged to the algorithm frame's right border. The semantic-mask guard already assigned every source pixel uniquely.

This separate round adds only that event type. Six original PDF controls pass exact source containment and RGB conservation, including color, rotation, inverse stencil, white overpainting and clipped pixmap origin. The seen BatchNorm page then has zero uncovered/duplicate ink and no full-page refusal. Runtime is 3.23 seconds; peak process-group RSS 299580 KiB on one CPU affinity.

Quality remains poor: only 1/8 complete source-annotated prose units genuinely reflows in full; inline formula detections merge much prose into atomic originals. The page number remains unclassified and is inserted between left and right column prose. The algorithm box is complete but small. This is a mechanism regression, not a new holdout, and does not revise the 22/34 frozen batch result.

No border threshold was tuned, no page-specific case was introduced, and no source PDF or crop is public. Original fixture source can reproduce all controls. A next role model must distinguish inline mathematical material and auxiliary page numbers from paragraph/display objects; page-level order alone cannot repair those candidate errors.
