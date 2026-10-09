# Generic reflow v2: native paint/character mechanism probe

This isolated experiment makes a small, inspected improvement. **It is not a successful universal PDF reader, a promotion of local-break-v1, or a holdout result.** The prior negative assessment at c322fe44 is untouched.

## What changed

1. PDFium supplies native character geometry, text-object identity, ordered paint objects and activation switches. No OCR, layout model, font-name keyword rule, document ID rule or private-text upload is used.
2. Strict simple opaque background rectangles have separate IDs and logical-range attachments. They never enter foreground dependency closure.
3. Local visual output is rendered from an explicitly activated native-object set onto transparent pixels. It is no longer a rectangular patch from a complete foreground-page screenshot. When a text object contains unowned character ink intersecting the local crop, the page is rejected by a hard check. This is not yet a general glyph-level masking engine.
4. Compact fraction support can retain the original numerator, denominator, bar and adjacent expression geometry. Table borders stay foreground.
5. List continuation uses baseline spacing and alignment with text after a small marker; source line breaks need not create paragraph gaps. Heuristic values are centralized in typed `Config`, with decision traces. Numbered/multi-level lists and punctuation false positives remain unvalidated.
6. A separately serialized logical plan is compared with renderer emission order, as well as inventory ownership. Neither property proves correct semantic reading order or final visible-ink completeness.

## Inspected narrow findings

- One authored grey-panel/fraction/table control: its structural hard gates pass. The native fraction and table assets, and their WeasyPrint static placement, were inspected. Original control pixels are not a generalization dataset.
- Seen D5-P1: the grey panel remains reflowable text; four list items continue across their original source lines. At 390 px and 20/28 px, the two earlier false continuation gaps are no longer observed. The diagram remains local, and margin revision strokes do not appear inside these sentences. Five native control-code characters use original visual glyphs and are not counted as valid Unicode selection. The added annotation/text-clipping guard still rejects the whole page as unsupported; no whole-page success is claimed.
- Seen D4-P1: the candidate remains failed. Two local objects share native text-object ink with unowned content, and 215 mathematical-symbol characters remain in ordinary text. Annotation/text-clipping support is also incomplete. Seven shared-geometry character groups are possible multi-character/ink aliases, not certified glyph instances. Figure/background compositing is unverified.

The `exact_once` field means the extracted **character-record and paint-object IDs** are owned once. It does not mean every truly visible glyph/pixel is emitted once. Font/style changes, pure-letter mathematics, scripts, bidi/vertical writing, occlusion, clipping, masks, annotation appearances and misleading Unicode encodings remain open issues.

## Actual measured cost

Each final page run was a fresh Python process pinned to one CPU. Wall time covers interpreter/imports, local PDF open, extraction, planning, two base renders, every local native-object isolation render, PNG encoding, HTML and audit/trace/plan writes. CPU time and process peak RSS come from `wait4` after that process exits. The 1 GiB watchdog samples family RSS every 10 ms; it is not a kernel-enforced memory cgroup.

- Authored control: 0.83 s wall, 0.82 s CPU, 32.75 MiB peak RSS, 2 local isolation renders
- Seen D5-P1: 2.27 s wall, 2.26 s CPU, 50.48 MiB peak RSS, 11 local isolation renders
- Seen D4-P1: 11.61 s wall, 11.45 s CPU, 69.50 MiB peak RSS, 100 local isolation renders

Inputs were already local; OS file cache was not flushed. Browser startup/load/paint and interaction are excluded. Therefore these are **processing-only measurements, not an interactive 60-second/1-GiB acceptance result**. The much smaller `hot_pipeline_seconds` is not substituted for end-to-end page cost.

## Verification status

- Python compilation and two focused mechanism/negative-inventory tests: passed
- Static visual checks: WeasyPrint only, not Chromium or Android
- Local Chromium launch: blocked by `socket() Operation not permitted`; no alternate launch/sandbox bypass was attempted after the blocker was confirmed
- Actual selection, resize buttons and local zoom: unverified. `code/ci_original_control.py` is ready to test the authored control at 320/390/430 px and 20/28 px in a permitted Chromium environment. It takes no private PDF or source URL. It has not been run.
- No complete-body readability percentage, browser matrix pass, equation completeness score or causal gain over a valid baseline is reported

## Registered but unopened evaluation inputs

`HOLDOUT-REGISTRY.json` registers six source-document-disjoint DocLayNet validation pages: FAA handbook, EU tender, annual report, German law and two paper layouts. It excludes 36 previously seen source documents and prior arXiv IDs. The initial manuals/redbooks/Chinese-law quotas were ineligible because each validation stratum had only one, already-seen document; the metadata-only amendment is recorded. No new PDF, page image or output was opened.

`CHINESE-HOLDOUT-REGISTRY.json` adds the official 2025 National Immigration Agency Chinese educational booklet, fixed to physical page 3. Traditional Chinese is indicated by title/publisher; the actual script mixture, native-text-versus-scan status, size and bytes are still unknown. It has no human GT and requires an independent visual/content review. Over-size, unavailable or short inputs remain recorded failures, without content-driven replacement.

These are registrations, not completed input freezes: SHA256 of newly downloaded bytes must be recorded before source/output inspection. Current hard failures should be resolved in a separately versioned candidate before using this holdout.

## Reproduce the current mechanisms

Install `requirements.txt` into a suitable environment, then:

    python code/test_representation.py
    python code/create_control.py /private/output/original.pdf
    python code/measure_page.py /private/output/original.pdf /private/output/rendered

For actual browser checks, additionally install Playwright 1.62.0 and its official Chromium in a permitted environment, then run:

    python code/ci_original_control.py /tmp/generic-reflow-original-control

No private inputs belong in public CI. WeasyPrint is an optional static-diagnostic dependency, separate from the extraction/reader prototype.

## Durable scope

The public checkpoint contains original code, generic configuration, registration metadata, sources/licensing and aggregate diagnostics. Private source PDFs, extracted native text, HTML/assets and screenshots are kept in a separate private evidence archive. `CODE-CONFIG-CHECKPOINT.json` pins all engine/test code and the installed PDFium binary hash. The research code follows the repository license; upstream dependency notices remain necessary when distributing their binaries.

The next substantive target is glyph/paint ownership at shared text-object boundaries, coupled with interval-preserving inline math and complete paragraph relations. It must be demonstrated on controls and seen diagnostic pages before the registered unseen corpus is consumed.
