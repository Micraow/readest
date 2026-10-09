# Official reading-order subnetwork: callable, no measured quality gain

The official Apache-2.0 PP-DocLayoutV2 reading-order subnetwork runs locally on the same PP-DocLayout-S candidate boxes. It loads 20,743,304 parameters (82,973,216 FP32 bytes, about 83 MB), not the 267K-parameter model from a different paper. Peak process-group RSS was 644312 KiB (about 629 MiB). Ordinary per-page ordering took 24.7–82.1 ms on one CPU affinity; this does not establish a dedicated CPU quota or mobile performance. Loading time was not recoverable.

Across six new paper pages there are 34 source-annotated complete prose units. Only 27 are covered at least 90% by one detector candidate. Of 97 source-ordered unit pairs, 57 are scoreable and 40 are not; both the strong column geometry baseline and learned ordering have 0 errors among the 57. The pairs cluster within papers, so this is neither a general risk guarantee nor an end-to-end score. A naive independent-binomial Wilson upper bound would still be about 6.3%; independence is not established. Two seen pages contribute 31 additional conditional pairs, also with no difference.

Full candidate orders are identical on six of eight pages. BatchNorm swaps two overlapping inline-formula detections; Swin swaps duplicate overlapping heading boxes. Neither change demonstrates a better reader. The model cannot recover content omitted or fused by the candidate generator. All sixteen ordinary/reversed-input inference results were saved; final JSON serialization failed on a NumPy scalar and metadata was reconstructed without rerunning inference. This recorder failure is disclosed in the public run result.

Do not add the 83 MB head to the default prototype on these results. Retain it as a licensed, callable comparison for future candidate-role/segmentation work. No model was trained on these pages. Upstream training overlap is unknown, so new-to-our-development pages are not guaranteed unseen by the pretrained model.

Official sources:
- [PaddlePaddle weights and model license](https://huggingface.co/PaddlePaddle/PP-DocLayoutV2_safetensors/tree/880e8971b88938518611c54fc0f59ad57849c9d4)
- [Official PaddleX implementation](https://github.com/PaddlePaddle/PaddleX/blob/develop/paddlex/inference/models/object_detection/modeling/pp_doclayout_v2.py)
- [Google sparse graph paper page](https://research.google/pubs/text-reading-order-in-uncontrolled-conditions-by-sparse-graph-segmentation/): no official code/weights link was found there; this is not proof that no implementation exists anywhere.

No paper PDF, crop, raw source text or model weights are published with this result.
