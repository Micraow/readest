# Main prose continuity around column-top floats

Written before this mechanism's tests and D4 output. Follows immutable `781ecd34`. Current scope remains printed academic papers, no ink-annotation work. Existing D4 is development only; no holdout is opened.

## Hypothesis

A geometric column tree supplies a safe regional traversal but can interrupt a main-prose sentence with a top-of-next-column figure and caption. Add a separate, reversible flow-relation graph. A weak model/native-tag caption hypothesis may pair with a unique adjacent bounded graphic after native coverage checks. That pair can be scheduled after a main paragraph continuation while its source and anchor identity remain explicit. The model never supplies text or ink.

## Measurable contract

1. Caption proposals must be confidence-qualified and nonconflicting. Whole native source lines must be contained within the proposal's bounded margin; no partial-line capture or object-crossing is allowed. Caption lines form one continuous source-line interval, bounded in height, and associate with exactly one immediately adjacent graphic in the same column. Missing/low-confidence/conflicting proposals abstain. No string such as a literal figure identifier selects a role.
2. A relocatable figure/caption pair must be a prefix of a column after a previous column. Native column widths must be compatible. The preceding source line must reach near its column's text right edge. The first main-prose line after the float must be unindented relative to its column's native text left edge and compatible in text size. A reliable terminal sentence mark rejects automatic continuation. A changed font/heading, indent, crossing region, or competing target abstains. These are hypotheses, not semantic ground truth.
3. Join only the immediately adjacent column-flow paragraph, bounded by its ordinary source baseline/indent paragraph break. Put the figure/caption immediately after that joined paragraph, never at an arbitrary document end. Preserve figure→caption adjacency and every source line's internal order. No additional source text, model OCR, or font guessing is introduced.
4. A cross-column paragraph is represented by an ordered list of source ranges. It is NOT falsely labeled as a single continuous native-index range: float ranges are distinct. In output its logical paragraph interval is continuous and its members occur once. Paint ownership remains a separate, unchanged ledger.
5. Audits must expose accepted/rejected relation candidates and geometry, model provenance, source ranges, output range, moved float IDs and explicit remaining uncertainty. The original column sequence remains stored so every relocation is reversible. A cycle, duplicate, missing unit or inconsistent range rejects the output.
6. The paragraph remains reflowable text/native-word units. This does not create a whole-column/body bitmap. Existing small local math groups retain relative geometry.

## Initial controls

- Positive: two equal columns; left prose reaches bottom/right; a top-right figure/caption prefix; right prose begins unindented and continues until its next indented paragraph. The paragraph must stay continuous and float follows it once.
- Negative: same float but left prose ends early; known terminal sentence punctuation; next body is indented; font/size changes; ambiguous competing captions; low-confidence/missing prior; float in the middle rather than prefix; crossing protected region.
- Exact source-line/paint bijection and pair order required in positive and negative cases. Source-native index monotonicity is not misreported after deliberate float relocation.

## Stop/failure boundary

If the caption cannot be validated or the cross-column relation is ambiguous, preserve the original traversal and report unresolved continuity. Do not claim that visual-column order solves logical paragraphs. After controls, inspect D4 source and complete 390px result. Retain new failures and all old outputs. This candidate is not eligible for unseen-paper evaluation until whole-page readability, native content, interaction/sampling and measured complete costs pass their separate gates.
