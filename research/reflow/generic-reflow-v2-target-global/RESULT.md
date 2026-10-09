# Global target-alpha reuse: correctness controls pass, performance gate not met

Six independent full-RGBA authored comparisons and four negative controls pass.
The deliberately undersized window reports 4,941 omitted alpha pixels; over-budget
and invalid windows refuse. No crop expansion is used to turn that failure green.

Control/H5 completed old-new-new-old stages preserve all asset IDs, metrics,
alpha and supported RGBA exactly. H5 mask renders fall 22 to 12; its local asset
renders remain 24. H5 wall seconds were 12.139, 14.019, 14.838, 27.304, under
variable shared-host load. This does not establish a reliable net speedup.

H6's first old and new target stages completed at 37.368 and 31.302 seconds;
both produce all 27 requested assets, identical metrics and all visible RGBA.
Native mask calls fall from 77 to 27, while asset renders remain 56. However,
the second new process timed out at **60.275s**, **53.607s total accounted CPU**.
The paired sequence stopped on that failure before the final old repeat. It is
incomplete and cannot be reported as a successful A-B-B-A performance result.

All runs explicitly reused the native plan; none is a cold-page time. No new full
cold request was started, the mechanism is not adopted, and no new holdout/CI
was used. Existing cold failures and strict reading/selection limits remain.
The next priority is the useful private reading/source-return trial and reliable
text selection, rather than more serial single-page micro-optimizations.
