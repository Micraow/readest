# Existing-renderer glyph resource probe

Current baseline is frozen at c51e6355. This next experiment addresses runtime/resource reuse, not new document/holdout scoring. Product source remains unmodified. Only the cloud terminal/native non-browser renderer may be used locally; prior Chromium/browser access denials remain in force.

## Scope and minimum outcome

Inspect the PDF.js version already pinned by Readest (lockfile 6.2.108) from its official package/source, with license, exact package integrity and local files recorded. Determine whether its actual paint operations retain native font/glyph identity separately from candidate Unicode. A known glyph must not be redrawn by substituting the semantic Unicode value. In particular, native glyph-resource identity, ligature expansion, font transforms, and unknown/misleading character maps must remain distinct.

Use the existing original small control first, then only previously seen D4 if the mechanism is coherent. Do not invent a large idealized fixture suite that postpones real content. Do not run OCR, external model services, or privately upload PDFs. Node/native-canvas rendering, if available, is explicitly non-browser evidence.

## Falsifiable gates

- Capture actual renderer-native glyph/font references and paint-state transforms, not equal-width slices of text items or bbox screenshots.
- Every captured paint operation is represented once. Operator/glyph counters and final pixel reconstruction are separate tests.
- Original-coordinate replay must match the same pinned engine's baseline under native paint order. Actual relocation/scale of a bounded local group must retain its relative geometry and all owned strokes without foreign text.
- Shared font/glyph resources are measured in bytes and counts; render/read startup and cache lifetimes remain visible. No per-word PNG proliferation is relabeled as vector reuse.
- Unsupported clipping, blend/group state, Type3 programs or lost font identity must abstain or remain a bounded declared unsupported primitive. Never lock the entire page/body as a successful reading result.
- Candidate Unicode is not certified semantic selection. A native glyph can be visually preserved while its copy mapping is unknown.
- A private/internal renderer API implies version-pinning and maintenance cost. A successful authored control is not proof that existing PDFium logical/paint IDs can be mixed with PDF.js IDs. Any cross-engine mapping requires its own exact ownership/interval proof.

If the pinned renderer cannot expose reproducible native resources within these constraints, retain a negative result and keep the prior native target-grid path. No production integration, actual browser interaction, or unseen-paper acceptance is promised by this probe.
