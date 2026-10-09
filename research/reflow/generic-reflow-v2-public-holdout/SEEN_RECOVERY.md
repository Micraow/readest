# Separate seen-page recovery and safe failure presentation

The single registered recovery request on commit 103863c0 ran for 37.02 seconds
(36.66 child CPU), below the 60-second cap, with no retry. The original frozen
holdout stays **failed 0/1**. This recovery also fails and produces no reader.
The empty-glyph exception is gone; region order remains unresolved. The retained
original-position replay also differs by 108 pixels, with 108 pixels quarantined.
Its failure was generated before the order exception and is an independent blocker.

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

## Opt-in support experiment, not enabled by default

A nearest projected-component selector reduces the problematic local support from
38 glyphs to four without Unicode/font rules. Seven authored selector controls
pass. One native extraction took 6.06 seconds; downstream diagnosis reused the
retained model prediction with zero model inference. Replay difference falls to
45 pixels but remains nonzero, and a centered display equation still lacks a
unified line envelope. There is no usable reader. The candidate keeps this
selector explicitly opt-in; fail-closed ownership and order requirements remain.
No additional cold request was made.

The remaining quarantine belongs to a long separator incorrectly treated as a
fraction in the early proposal. A new authored control makes the opt-in selector
reuse the existing downstream 3-em fraction-bar width bound. This additional
change has not yet had a native replay run and is not credited with fixing pixels.
The opt-in selector now has eight controls; local geometry has 29 in total.
Future requests write both replay and order gate outcomes before raising an error,
and the one-shot wrapper packages a local explicit source fallback after failure.
