# Conservative ordinary-text selection candidate

Keep the visual native-vector/image reader and its geometric layout unchanged.
A separate map may expose ordinary native-word characters when an existing
one-to-one geometry bridge matches PDFium source glyph records to PDF.js paint
events, and their Unicode candidates agree exactly. Require complete bijection,
known scalar characters, no private-use/control/surrogate/replacement character,
no math-symbol category, and one compatible native baseline/direction. All
thresholds are typed config and each refusal has a reason. Small metadata is not
rejected just for being small, and a long string is not accepted just for length.
No paper ID, keyword or font-name branch is allowed.

Two extractors can share a bad PDF mapping: agreement is an eligibility signal,
NOT semantic certification. Preserve that field as false. Use known original
fixture text, intentional wrong/unknown mappings and geometry negatives first;
then measure coverage and manually compare actual seen-paper words with source
visuals. Do not consume another blind page. No OCR or model is introduced.

Place transparent character spans over the corresponding native glyph geometry,
with DOM order equal to reader logical order. Do not draw replacement Unicode
visually. Space normalization follows explicit reader token boundaries; source
hyphens remain literal. A copy range touching an unresolved word/image/formula
must be refused with an explanation, not silently omit or hallucinate content.
Ordinary native-word copy and mathematical expression semantics stay distinct.
Character/source links must survive font changes and return to the original
page coordinate. Ambiguous correspondence fails closed.

Before calling selection usable, check one original-only real-browser batch:
mouse selection/copy, spanning an unresolved formula, font change, source-return
highlight and no external network request. Native JS/schema tests alone are not
browser evidence. Existing H5/H6 reader remains available without this layer until
these tests pass; all original reports and deliverables stay unchanged.
