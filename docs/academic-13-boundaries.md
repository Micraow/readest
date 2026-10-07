# Academic 13: content boundaries and reading navigation

The parser now keeps tightly connected spanning author rows together across a
body-column gutter. Raised note marks remain attached to their author row, so
the true body-column start can be used to join text around a deferred footnote.
Small fraction numerators can use their visible fraction rule to associate with
the surrounding prose baseline.

Displayed equations stop before the following prose even when a stretchy PDF
font glyph has an oversized nominal descender. Hyphenated prose continuations
with mostly mathematical symbols remain selectable text instead of being
absorbed into a neighboring display. The cache version advances to academic-13.

Equation and inline-math canvases follow the live reading theme through
presentation-only blending. This does not rewrite source pixels, change figure
colors, or change the original-layout zoom rendering. Long unbroken text can
wrap in the reading column rather than requiring a document-wide horizontal
scrollbar.

An independent in-memory navigation index links exact numeric citations to a
unique recognized bibliography entry, and standalone superscript footnotes only
when the source page/column establishes a unique prose-note pair. Ambiguous
markers remain ordinary text. Return keeps the clicked anchor and viewport
offset, including after a font change, and works through nested jumps and
reader overlays. This is inferred reading navigation, not a claim that the PDF
contained those hyperlinks. Original PDF annotation extraction is not added in
this phase; paragraph and source ownership are unchanged by the navigation index.

## Validation checkpoint

306 focused parser, navigation, UI and image-viewer tests passed across 27 files.
Five independent synthetic cases cover spanning authors/body columns, deferred
notes, oversized display bounds, mathematical prose and inline numerator
association. The newly reported private PDF was checked locally against its
original pixels; affected sentences are complete in text and separate from the
rendered equation crops. No PDF or extracted private fixture is included here.

Previously accepted papers were reanalyzed. MP and the single-column document
retain identical visual sources. The other two-column sample keeps its visual
count; small boundary adjustments and improved inline-fraction associations were
reviewed against the original crops. Source coverage is a supplementary check,
not evidence of visual reading quality by itself.

Production build, type checks and fresh native acceptance are still required for
this checkpoint. The separate Android emulator attempt
[37647760482](https://github.com/Micraow/readest/actions/runs/37647760482) stopped
at its initial KVM access gate before downloads or app launch. It provides no
Android runtime or dark-theme acceptance evidence. No KVM permissions were changed.
