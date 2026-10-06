# Academic layout fixtures

`hpcc-geometry.json` contains geometric measurements from the publicly available
HPCC author PDF, SHA-256
`8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a`,
extracted with PDF.js 6.2.108. These are physical pages 6 and 10 in scale-1 rotated
viewport coordinates (top-left origin, points).

All original text strings were removed and replaced with synthetic `x` characters.
The three caption labels are synthetic test labels. Font identifiers/families were
replaced. Only bounding rectangles of forms and rules remain; there are no original
vector paths, glyph strings, images or PDF bytes. Coordinates are rounded to 0.001
points. All source text item indices are retained, including whitespace runs, to
exercise exact source accounting. The 27 algorithm number-item indices are measured
from the original extraction; their original strings are not included.

The fixture checks complete algorithm boundaries and grouping the eight vector
panels with their shared caption. It does not prove text extraction or semantic
reading quality. `scripts/academic-regression.mjs` runs those geometry/source checks
on a user-supplied local PDF directory, parsing the actual PDFs again by default.
It performs no downloads or uploads. Full PDFs and full-text outputs must remain
outside this repository.
