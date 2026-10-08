# Official Docling CPU diagnostic study

This isolated study evaluates four already-inspected public pages. It is not a blind holdout, an application release, or Android validation. No user PDFs or extracted private content belong in this directory.

The official Docling Serve CPU v1.30.0 image is fixed to its published linux/amd64 digest. The image contains the runtime and models; there is no dependency installation or model download during conversion. The Docling Serve source is MIT licensed. Model and dependency versions/hashes are reported from the image; bundled licenses remain with the distribution.

Sources: official [container package](https://github.com/docling-project/docling-serve/pkgs/container/docling-serve-cpu/1107840401?tag=v1.30.0), [Containerfile](https://github.com/docling-project/docling-serve/blob/v1.30.0/Containerfile), [README/license](https://github.com/docling-project/docling-serve/blob/v1.30.0/README.md).

The workflow downloads only manifest-listed arXiv PDF versions and fails on hash mismatch, oversized files, insufficient disk, missing models, conversion timeout, or missing outputs. Conversion runs with no network, no repository credentials, a read-only root and input mount, a single writable evidence directory, 2 CPUs and 6 GiB RAM. It uses the standard layout/native-text/TableFormer pipeline, without custom paper rules or formula VLM enrichment. HTML rendering uses sandbox-enabled Chromium and blocks external requests.

Only JSON/Markdown/HTML, source and region PNGs, rendered output, and runtime metadata are preserved as a seven-day artifact. The image, dependencies and downloaded input PDFs are not artifacts. The source PNG and public extracted text are explicitly from the public works in the manifest.

Human review must separately inspect role contamination, missing/duplicated text, table/caption association, reading order, formula/figure clipping and genuinely usable body reflow. Detection boxes and text counts are not a correctness score. Four pages and desktop runtime measurements do not establish mobile feasibility or generalization.
