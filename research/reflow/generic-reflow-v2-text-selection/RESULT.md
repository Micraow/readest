# Experimental selection candidate: deterministic checks pass; browser gate pending

The conservative two-extractor mapping remains unchanged. H5 exposes 285 eligible
tokens / 1,332 characters and refuses 26 tokens; H6 exposes 682 eligible tokens /
3,920 characters and refuses 64. Eligibility is not semantic certification.

New original source adds transparent geometry-aligned character spans, logical
spaces and paragraph boundaries, source-glyph/source-box links, and a copy event
guard. A range touching an unresolved token refuses the entire copy. Unknown
formula/image content stays visible through the original native painter and can
return to its source box. Selected ordinary characters return to their original
boxes. Font/page changes clear old selections. The original canvas painter and
formula layout code are unchanged.

Verification: 22 existing Python mapping controls and 27 JavaScript DOM/geometry/
copy controls pass. DOM checks use jsdom, **not a real browser**. They cover forward,
reverse, partial, element-boundary, cross-block and collapsed selections, formula
refusal, exact clipboard payload, unavailable clipboard API, original source-box
return, font transforms, stale-range clearing, and partial-surrogate rejection.
Private H5/H6 maps pass finite geometry and identity checks at 20/24/28 px and
320/390 px widths (12 page/size combinations). JavaScript syntax and Python
packager compilation pass. A separate experimental private HTML was packaged;
the previously delivered no-selection preview remains unchanged.

Real-browser mouse selection, highlight alignment, actual system clipboard,
source dialog interaction and network observation remain unverified. The prior
local Playwright launch/escalation route is blocked; it was not retried or bypassed.
Do not call selection usable or integrate the candidate into Readest until that
gate passes. No cold request, public push, application integration, or CI run occurred.

## Reproduce the focused controls

Run `python code/test_text_map.py <new-output-directory>` from this directory.
Run `node code/test_selection.mjs` with jsdom resolvable, or set
`SELECTION_TEST_PACKAGE` to an absolute package.json path in a local installation
that already has jsdom. Packaging optionally reads `text_map` from each private
input-manifest entry; without it the no-selection rendering still works.

## Usability and validation hardening follow-up

A concrete fail-open validation case was fixed: non-finite or missing native size /
baseline values could bypass numeric comparisons. Mapping now rejects those values,
invalid glyph boxes and malformed characters, and compares source metric fields
against the immutable native records. Mapping controls expand to 31 passing cases.
Rebuilding both private H5/H6 maps produces exactly the previous JSON data after
serialization, so this stricter validation does not reduce seen-paper coverage.

The viewer now provides keyboard-operable paragraph-selection and local image /
formula-view buttons, a live status region and labelled source dialog. Dialog close
and Escape clean up source content and restore focus; a removed opener falls back
to the font selector. Page changes reset the old dialog, and delayed image decoding
cannot open a view belonging to a superseded page. Ten additional jsdom controls
cover keyboard selection across a visual line break, unresolved-content refusal,
detached selections, dialog cleanup/focus, reset, repeated close and late events.
All 27 earlier selection controls still pass. These checks simulate dialog state;
they do not certify actual browser modality, keyboard gestures or clipboard access.

## Measured selection advances and direction limit

Transparent character spans now use measured monospace advances scaled horizontally
to the native glyph box width. Missing/zero/non-finite advances mark that character
unresolved, so copying refuses rather than relying on an unverified hit area. This
is an implementation correction, not proof of browser selection rectangle alignment.
The current left-to-right layout now explicitly refuses unsupported RTL/bidirectional
classes. Horizontal glyph angle alone does not establish reading direction.
Mapping controls: 34 pass. Selection controls: 29 pass. These policy changes are
frozen before selecting the next independent public-paper page.
