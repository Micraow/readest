# Lossless intermediate-wire experiment

H6's prior complete request wrote/read repeated 10–11 MiB pretty-printed native
plans and stopped at the 60-second limit. This experiment changes only JSON
whitespace in owned research modules. It does not remove trace records, fields,
source paints, geometry checks, cache fingerprints, file writes or stages.
Third-party modules and the standard json module are not monkeypatched.

A module-local facade retains json API behavior but overrides dumps/dump
indentation and separators to compact JSON. Exact parsed values must be retained,
including Unicode, numeric value/negative zero, ordering and default error
behavior. Only modules under the owned research tree can opt in; every patched
module and serialization count is traced. Frozen files remain unchanged. Hashes
of encoded plans necessarily change, so they cannot hit the old asset cache.

Before full requests, compare authored nested/scalar/Unicode cases and actual
seen-page intermediate plan serialize/decode A-B-B-A costs. Then use a fresh,
complete H5 followed by H6 request under the same one-CPU/1GiB/60s supervisor.
No cached plan/model/glyph/image may be supplied. Final reader parsed payload,
unit order, native images and rendered output must match the existing reviewed
mechanism version. Timed-out outputs remain failures and are not resumed.
No new holdout, model, font or geometry heuristic is introduced.

This addresses avoidable research-wire cost, not the model runtime deployment
size or reading defects. Source/target pixel proofs stay mandatory. Report actual
full-pipeline costs; the microbenchmark is not page latency. OS cache is not
flushed. Selection, browser, zoom and overall reading acceptance remain separate.

## Attempt 1 retained; execution fix before attempt 2

H5's target request completed asset generation but then failed writing the new
wire report: its imported report function had been shadowed by the existing
per-request report dictionary. H6 timed out earlier in asset regeneration.
Preserve both attempts and source snapshot. Alias the function `wire_report`;
this changes reporting only. Add a module-scope test proving standard json and
outside modules remain untouched. A fresh full H5 then H6 request follows; no
partial output is resumed, and the first failures remain in the final result.
