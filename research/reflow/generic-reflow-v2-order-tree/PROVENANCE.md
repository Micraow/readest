# Dependency and prediction provenance

Original code follows the repository's LICENSE. No third-party code, model binaries, private PDF, extracted paper text, screenshot, credential or URL from an annotation is included in this public checkpoint.

## Reused local layout model

PP-DocLayout-S, previously downloaded from the official PaddlePaddle repository at recorded revision `8ac289e66575bb9bba6e15c53719d8b15cc9b3b2`. The current [official model card](https://huggingface.co/PaddlePaddle/PP-DocLayout-S) identifies Apache-2.0; the revision-specific model card was not retrievable through the web reader during this pass. Actual local binary hashes below, not a moving model-card claim, identify what ran. This detects region rectangles; it does not supply paper text or replace native glyphs.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| inference.pdiparams | 4,804,904 | 491c3382d84ca04d2033afbee0c105942ed82fea392bb4a19170646adebe088a |
| inference.json | 339,876 | ac09e931895d4c442e5379ab3b7e9b583baf288e816ab7675ca519da9eb2a9d7 |
| inference.yml | 1,579 | 6f690098c438214c67822239a568f0bc2bbe97a8f02fba93e492d4f2c47523c3 |

Research runtime: PaddlePaddle 3.3.1 / PaddleX 3.7.2; installed distribution LICENSE files both state Apache-2.0. The model/runtime was already local, and the predictor blocks outbound Python socket connections while executing. This does not claim the full Python environment is audited or deployment-sized. PDFium 153.0.7999.0/pypdfium2 5.13 retains native source rendering; see the original v2 dependency assessment for licenses and API limitations.

## Two different prediction sources

- Historical frozen cached D4 JSON SHA-256 `39d5747c5c22854a2e8ea87164e2804c2365678457aeb55e04fc3b1a90838deb`; original MuPDF 2448×3168 raster. Cached inference cost is not recharged as a new inference observation.
- New offline D4 JSON SHA-256 `3088541ce9d878760912a36fb2e26e44ce15d9de38b5aee08eacaafe7ad0a708`; PDFium 2448×3168 raster with annotation/form drawing disabled, fresh model child. The 52.669s measured pipeline includes this child completely. Private diagnostic metadata originally mislabeled the adapter input as cached; the preserved run has an explicit erratum and current code/tests distinguish provenance.

Both are old-page development evidence. Neither is an unseen-document evaluation. All holdout PDFs/images remain unopened, including the metadata-only registered official Traditional-Chinese nonacademic source now reserved for future scope.
