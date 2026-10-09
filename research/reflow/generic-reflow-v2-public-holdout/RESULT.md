# New public-page holdout fails before reader generation

H7 is fixed PDF page 4 of the official NeurIPS 2017 *Attention Is All You Need*
paper. Source/mapping policy was frozen before acquisition. The 11-page source
and derived one-page fixture hashes are recorded in RESULT.json. Printed page
label 4, original document index 3 and derived fixture index 0 remain distinct.

The first and only complete request failed after **37.01 seconds**, with **38.03
seconds accounted child CPU**. It did not hit the 60-second timeout. The native
fraction stage called min/max on an empty source-glyph set belonging to a thin
standalone graphic paint. Glyph capture, selection mapping and reader rendering
were never reached. Their gates are **not run**, not passed.

This new holdout is **0/1**. Earlier blind results remain **0/2**. The source page
adds two side-by-side diagrams, a caption, inline stacked fractions, a centered
numbered equation and a footnote. Its body still has one column, so this does not
establish a new third column count. It is not a general Readest success.

All first-run logs and partial outputs are retained. No retry, threshold change,
keyword/font rule, whole-page fallback or resumed run was used to turn the failure
green. A later generic fix declines interval proposals without native glyphs and
retains the original paint owner. Five authored regression controls reproduce the
empty-collection assumptions; they are separate from the failed holdout. The valid
fraction controls remain in the suite. Real browser acceptance is still open.

## Separate post-failure diagnostic

The repaired fraction-closure function was applied once to the retained partial
plan, explicitly as **seen-data diagnosis**, not a cold request. It considered
seven geometric bar candidates, declined the one glyph-free proposal, and retained
all three glyph-free units. Source glyph multiset and paint-ID set are unchanged;
no new groups, native renders, model runs or reader output were produced. The
original failed request and **0/1** result remain immutable.
