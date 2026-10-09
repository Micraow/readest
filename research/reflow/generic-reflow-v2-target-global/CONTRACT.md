# Direct global alpha at the actual target grid

The frozen target renderer already partitions the complete global-device alpha,
not its provisional local crop. It nevertheless first renders two or more local
crops for stability, allocates another global bitmap, and then discards the local
RGBA. Evaluate one reusable page-scoped global BGRA canvas for those alpha calls.
No native paint object, mask, source-support proof, or final render is removed.

For a shared object, use a FIXED window from its unchanged native object box and
the first window at which the old two-window comparison could succeed (existing
initial padding + existing step). Never expand that window on a failure. Render
only the selected original native object in original page device coordinates;
count ALL global nonzero alpha and the window's alpha. Any ink outside the fixed
window refuses. Partition the cropped full alpha using the unchanged ownership
algorithm. The local-crop numerical comparison is no longer needed because the
local raster is never used; exact global completeness replaces that redundant
path. Trace this as a different proof, not a successful crop-stability test.

Closed text sets retain their original fixed unit window and original native
paint order. Both modes clear and reuse a single BGRA canvas per request. Bounds
remain the existing 32M reference /4M object /8M unit pixels. Source/backdrop,
actual requested font/DPR grid, cache fingerprint and unknown-Unicode semantics
remain unchanged. No whole-page bitmap is output to the reader.

Predefined gates: first compare the existing authored alpha control, then all H5
and H6 fallback assets at the existing 28px/DPR2 request, in old/new/new/old fresh
process order. All accepted unit IDs, logical dimensions/anchors, alpha and every
supported RGB pixel must equal the old path. Record zero-alpha RGB separately.
The final full native RGB check remains mandatory. Add deliberate undersized
window and over-budget negative controls and compare reusable-canvas full RGBA
against an independent old full-object reference. No new ideal paper fixture.
Only after exact equivalence and measured stage benefit may a fresh complete
request be attempted. All existing timeouts remain failures; all pages are seen.
