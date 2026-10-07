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

## Build and runtime checkpoint, 2026-10-07 17:25 UTC

The exact application source is
[8b958610](https://github.com/Micraow/readest/commit/8b95861016dec96365fe99db8de58af42504c190).
The [Linux build](https://github.com/Micraow/readest/actions/runs/37651083824)
and [unsigned Android build](https://github.com/Micraow/readest/actions/runs/37651083868)
both completed successfully, including production frontend compilation, academic
tests, type checks and source-integrity gates. These are build results, not
Android runtime acceptance.

The Linux candidate was exercised in the native CEF application before the test
workspace was reset. The reported author ordering, deferred corresponding-author
note, equation/prose boundary and complete following sentence were visibly
correct. Displayed and inline mathematics followed the selected dark reading
theme; ordinary color figures and original-image zoom retained their source
colors. Citation [34] and footnote 5 in the second two-column sample navigated
to the correct targets and returned to the clicked body context.

That reset removed the local screenshots, test profile and unfinished package.
These observations are recorded as prior native checks, not as a surviving
screenshot deliverable. The final two-paper regression and fresh package launch
remain pending. Source, Linux executable and the reported PDF have since been
recovered and verified without recompiling. See the
[recovery checkpoint](academic-13-recovery.md) for the exact build inputs and
remaining acceptance work.

The Android signing key and the locally signed, unpublished revision-13 APK
were also lost. The CI artifact is unsigned. It cannot be presented as an
installable update to the previously delivered test app, and a different key
cannot preserve that app's signature compatibility.

The separate Android emulator attempt
[37647760482](https://github.com/Micraow/readest/actions/runs/37647760482) stopped
at its initial KVM access gate before downloads or app launch. It provides no
Android runtime or system-theme acceptance evidence. No KVM permissions were changed.
