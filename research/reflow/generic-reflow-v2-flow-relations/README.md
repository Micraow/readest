# Reversible prose and float relations

Experimental follow-on to immutable `781ecd34`; current paper scope, seen-page diagnosis only. No holdout opened and no new CI or real-browser result.

The source column tree remains unchanged. A separate relation layer can keep a cross-column prose paragraph continuous by placing a verified column-top figure/caption pair immediately after its continuation. It does not reinterpret native paint or invent Unicode.

The contract was written first. Thirteen original controls now cover a positive continuation and negatives for early line ending, known terminal punctuation, next-paragraph indent, text-size change, nonprefix float, different column-band ancestry, missing/low-confidence/competing captions, partial caption lines and protected regions. All pass. An initial coding error consumed a generator during repeated box extrema; controls exposed it before the real-page diagnostic, and converting that iterable to a list fixed it.

On old D4, the existing local PP-S caption proposal (0.772 confidence) covered eleven complete source lines adjacent to one graphic. Geometry supported one cross-column relation: column widths differed by 0.43%, the previous line stopped 0.136em before its text right edge, the next main line was only 0.014em indented, and main text size matched. The last native glyph's Unicode semantics are unknown; this is explicitly a geometry-supported hypothesis, not a certified sentence parser.

Actual 390 CSS-pixel/20px static inspection shows the formerly interrupted sentence and remaining paragraph now read before the complete figure and caption. Paragraph blocks change from 8 to 7; all 707 original native unit PNG files are byte-identical. Forty-five small math/display bundles retain their source geometry. Logical output blocks record ordered source ranges rather than falsely filling the noncontiguous native range with float content. Unknown glyphs still do not receive guessed semantic text.

The additional relation-only diagnostic took 0.585s using existing plan/prediction files, excluding all previous extraction/model work. Static 20/28px layout QA took another 12.100s. A fresh full live-model pipeline attempt **timed out at 60.044s wall, 57.701s CPU and 667.348MiB sampled family RSS**, before the additional relation phase began. Original native unit rendering varied to 12.675s. This is preserved and is not blamed on the new 0.585s relation algorithm. A separate switchable local-canvas probe records paired and full costs.

Remaining failures: native-source hyphenation/awkward spacing, target-size/DPR undersampling, incomplete copy semantics, unvalidated local zoom and font controls, native light-backdrop restriction, no full interactive budget or untouched-paper validation. The current visual improvement does not pass universal paper acceptance.
