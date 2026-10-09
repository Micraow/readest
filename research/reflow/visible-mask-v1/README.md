# Visible masks: mechanism repaired, limited new-page evidence

This round changes physical source ownership only. It retains the prior detector, native candidate construction, column inference, number/caption rules, k2 engine/settings and renderer. Actual final RGB pixels are authoritative: the PDF renderer has already applied painting order, clipping, white occlusion and transparency. Bounding rectangles of paint operations never become semantic parents.

Each eight-connected nonwhite component is compared with existing semantic candidate seeds. A uniquely supported component extends that candidate's visible mask. Zero or multiple supporting candidates refuse the page; they are not assigned by nearest-neighbour guessing. Candidate crops include only their owned final pixels. Distinct masks can coexist without merging their enclosing rectangles. This is conservative visible ownership, not recovery of the original painter's unique causal contribution under alpha blending.

## Invariant validation

Six original ordered-paint fixtures were frozen before execution. Broad white background, white overpaint, and text drawn after a background were accepted. Transparency crossing two objects, touching independent objects and an unseeded isolated mark were refused. Every case reconstructed the exact final RGB image after its appropriate guard. A separate deterministic source-layer oracle check on the three accepted cases found zero wrong-owner pixels and no resurrection of hidden ink. This oracle used source-layer identities rather than the component algorithm.

An initial integer-label oracle raster dropped antialiased font-edge pixels and was invalid. Its audit is preserved; the corrected oracle uses RGB layer masks. Neither the mask algorithm nor the six original outcomes changed. The fixture pass took 0.043 seconds and 49,880 KiB peak RSS. These are tiny synthetic ownership fixtures, not document-reading benchmarks.

## Real candidates: one regression and one new page

ConvNeXt v2 page 3 is explicitly a seen mechanism regression. Its previous wide white paint bbox no longer merges the left chart with the right-column continuation. The paragraph's left end now precedes its right start, and headings 2.1 and 2.2 are ordered correctly. All 3,891 visible components found unique candidate support, with zero uncovered/duplicated ink. Complete prose reflow improved from 0/4 in the previous column pipeline to 2/4; the original k2 baseline remains 4/4. Two complete units remain protected because the unchanged native-parent fallback marks their region uncertain. Across all body glyphs including fragments, 2,495/3,208 entered candidate word reflow. This is a mechanism improvement, not new-page generalization.

MobileNet v1 page 3 was selected and the code frozen before its download or inspection. Its public PDF hash is in `INPUT-FREEZE.json`. Of 12 preregistered complete prose units, ten entered word reflow, two remained original crops. Nine have visible wrapping evidence; one short single-line unit does not independently demonstrate a changed line break and is reported separately. All 2,969 visible components had unique support, with zero uncovered/duplicated ink and no whole-page fallback. Candidate body-glyph membership is 2,418/2,615 including the two page-boundary fragments. The original k2 baseline visibly reflowed all 12 local prose units, although its mathematical/diagram relationships were not all sound.

The mask pipeline retains the summation and its lower indices in equation (3), whereas baseline k2 places the lower-index fragment after the equation number. It keeps the four diagram boxes in Figure 2(b) on their original row; baseline k2 places the fourth box on another row. The three panels and captions remain in their source sequence. Protected math on this two-column input remains substantially more readable than the wide single-column formulas in the previous RoFormer experiment. This has been inspected in PNG output, not accepted on a phone or verified character-by-character.

The new page also exposes unresolved relation errors. There are three formal equation labels, of which the unchanged detector/rule system accepts two. Equation (5) is missed as an atomic formula and processed with surrounding text. Two internal numerator `1` tokens are additionally typed as formula numbers. They are physically part of the same formula and remain visually in place, so these are **role errors**, not observed cross-formula displacement. Formal-label recall is 2/3 and accepted formula-number role precision is 2/4 on this tiny page. Neither should be promoted to a corpus accuracy estimate. The unnumbered ratio's physical grouping does not validate those erroneous labels.

No algorithm, threshold or model was changed after either real output. The new MobileNet page is now a diagnostic. Source references and all candidate/baseline output tiles were self-audited; there is no independent full-page acceptance claim. Original-image regions remain in all denominators. Exact source-mask coverage does not prove semantic ownership when the semantic seed itself is wrong.

## Resource measurements

ConvNeXt and MobileNet composition took 2.73 and 2.78 seconds respectively. The external compositor process-group monitor, including k2 children, peaked at 539,888 KiB; the Python process's own high-water RSS was 307,704 KiB. The new-page detector inference was 0.49 seconds, with 579,436 KiB process high-water RSS; startup plus inference took 4.88 seconds. All ran serially on one CPU within the 1-GiB ceiling. No model download, training or paid API was used. The seen ConvNeXt detector JSON was reused unchanged.

## Next falsifiable step

The broad-background compositor mechanism is now repaired for these cases. Further model work should target the remaining semantic seed/role/parent uncertainty, not relearn RGB conservation. The next useful gate is a small rights-checked real-source annotation set separating formal labels, mathematical operands, caption labels, body prose and uncertain native parents. Include source-family holdouts and candidate misses; compare a strong fixed column/geometry rule with a tiny relation scorer at equal accepted-error risk. It must improve readable complete-prose coverage without confident wrong ownership. The successful synthetic 25-parameter probe is not sufficient evidence for that decision.

Do not tune away the two internal-`1` mistakes or the native-parent fallbacks on this page. Study their classes using newly registered source families. Pixel masks remain a renderer invariant and refusal mechanism; graph relations remain separately accountable. The current experiment ends with this checkpoint, rather than silently changing the held-out result.

## Reproduction and public scope

Use the sibling dependencies documented by `column-relations-v1`, with SciPy for component labeling. `INPUT-FREEZE.json` records public input hashes; `PIPELINE-FREEZE.json` records the pre-input algorithm hashes and partitions; `CODE-FREEZE.json` records the earlier fixture freeze. The source-layer oracle is a separately labeled post-run check. Paper PDF bytes, crops, detector predictions and glyph records stay local; only original code, public URLs/hashes and aggregate evidence are published. This is not integrated into the Readest app and no Android/package tests were run.
