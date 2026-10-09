# Reuse identical native text-object paint sets

The source renderer repaints the same native text object once for each word.
H5 has 315 text-only units but 86 distinct native object sets; H6 has 748/136.
Evaluate a byte-bounded, per-page RGB cache for native_word units only. Render
an identical sorted native object set against its identical flat backdrop once,
in original global device coordinates and paint order. Reuse that renderer
result through each word's existing, independently assigned alpha-support mask.
This is not a page screenshot crop or Unicode redraw: unowned neighbor ink is
masked away. Compare EVERY word's supported RGB to the complete native source
page exactly, as before. A mismatch still fails. Background/paint set/scale must
all match. Graphics and nonword groups retain the frozen renderer.

The cache is at most 32 MiB and scoped to one render call/page. Evict least
recently used sets. If a complete frame cannot fit, use the original renderer
for the entire request; never bypass a guard. Native render counts, cache hits,
misses, evictions and bytes are recorded. This only changes source asset work;
target-grid requests still use their existing renderer.

Predefined gate: an existing authored native-alpha control, H5 and H6 must have
identical asset IDs, logical metrics, alpha arrays and RGB at every supported
pixel. Zero-alpha RGB is irrelevant to this mask-only intermediate; record any
byte difference separately. Both old and new source-support comparisons must
pass. Compare fresh-process old/new/new/old renderer stages on the same already
measured plan, with CPU/wall/RSS and all samples. Cached-plan stage costs are not
page latency. Only after exact equivalence and demonstrated gain, compose a NEW
full fresh request; keep all previous cold failures and budgets.
