# Retained-hyphen separator repair, seen data

The existing source-line hyphen rule missed alphabetic prefixes preceded by an
opening parenthesis or square bracket. A generated space consequently appeared
between a printed line-end hyphen and its continuation after reflow.

The rule now accepts one certified opening delimiter before the existing
alphabetic prefix. It retains that delimiter and every printed character,
including the hyphen. No dictionary, spelling correction, hyphen deletion or
Unicode substitution is used. Joins operate only inside an already established
paragraph. Additional guards require a forward nearby source line, leftward line
return, compatible type size, monotone source order and no intervening visible
source glyph. Numeric/minus expressions, closing or repeated opening delimiters,
unknown prefix/continuation, uppercase continuation and incompatible geometry
abstain. A corroborated secondary hyphen candidate may change spacing but never
certifies copying of an uncertain source character.

Fourteen authored boundary controls join the existing flow/bridge/component
suite: all 36 pass. Selection coverage is now 31 controls, including an exact
retained-hyphen copy and refusal of an uncertain prefix despite zero separator.
Mapping coverage is 35 controls. These are deterministic unit/DOM checks.

The seen H7 diagnostic reran only the affected flow, formula-hierarchy and mapping
stages from existing native components; it did not repeat extraction/model work.
The final reader changes exactly one token's `gap_em` from positive to zero.
All other token fields, glyph paints, native resource tables and source mappings
are unchanged. The one changed paragraph was rendered at 28 px/DPR 2 and inspected:
the artificial gap is gone while the native hyphen remains. All 16 blocks import
and paint through the actual entry in jsdom/native Canvas, with zero network calls.
A targeted copy attempt spanning the changed uncertain token is still blocked.

That actual token's two-extractor Unicode disagreement remains unresolved, so
this is a visible-spacing repair, **not** expanded copy certification. Source
hyphens remain in reliable copied text too; discretionary dehyphenation is not
claimed. Mapping contents are unchanged: 341 eligible and 26
refused tokens. Reading acceptance stays false, browser behavior is unverified,
and the original H7 **failed 0/1** and previous timeout remain unchanged. The
footnote geometry caveat is untouched. H7 content and rendered examples remain
outside public Git and the private distribution allowlist.
