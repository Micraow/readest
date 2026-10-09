# Prototype checkpoint

The original offline reader fixture passed all five sandbox-enabled Chromium checks: image decoding, formula zoom and source location, figure colors, explicit scanned-page fallback, and mobile-width/page navigation. The screenshots were visually inspected. [CI run](https://github.com/Micraow/readest/actions/runs/37870213958), tested commit `5448fd5070d7332dc8dae40de0ce2669b7ac0abd`. No paper images were used in CI.

This is an inspectable local research prototype, not production integration. Source and relation failures in the frozen batch remain unchanged. The synthetic native page reflows only 2/3 complete paragraphs. The scan is a full-page image, not successful text reflow.

A packaging correction moves newly added stages/reports beside the established experiment directories under `research/reflow/`. The dated directory remains the original early-experiment archive. No frozen algorithm or failed result is rewritten.

Next research gate: obtain a small licensed real-candidate role/parent dataset with document/source-held-out labels; target inline math vs display math, number vs operand/page-number and paragraph continuity. The now callable order head is a comparator, not the default engine. Do not improve the reported batch by retraining on its test pages.
