# Separate seen-page recovery and safe failure presentation

The single registered recovery request on commit 103863c0 ran for 37.02 seconds
(36.66 child CPU), below the 60-second cap, with no retry. The original frozen
holdout stays **failed 0/1**. This recovery also fails and produces no reader.
The empty-glyph exception is gone; region order remains unresolved.

A full-size inline glyph has a displaced native baseline. The new shared line
association requires strictly nested source-index intervals, enclosing horizontal
bounds, vertical overlap and exactly one host. It does not inspect characters,
font names or paper identifiers. 28 authored order controls and 21 local geometry
controls pass. Existing H5/H6 line plans remain identical.

The next blocker is upstream ownership grouping: the initial fraction-support
rectangle expands two thin strokes by 3 body em sideways and 1.25 body em
vertically. It collects 38 glyphs from the starts of three prose lines into one
protected object. Later order diagnostics correctly refuse this overlap. A future
fix must change that early ownership proposal and reverify native replay; simply
loosening order gates or splitting the retained paint without proof is unsafe.
No second cold request was attempted.

The experimental viewer now accepts a separate local failure bundle. It displays
the reason as text and an explicit source-PDF download link. It never paints the
PDF as a successful reflow; an existing loaded reader remains visibly identified
as the prior document. Imported HTML is inert, external PDF URLs and prototype
keys are rejected, and focus moves to the source action. Native Node canvas tests
still exactly match all 30 H5/H6 reference blocks. Browser interaction is pending.
The H7 source fallback exists locally for diagnosis; the paper is not in Git.
