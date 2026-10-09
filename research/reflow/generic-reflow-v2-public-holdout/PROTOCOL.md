# One independent public-paper page: preregistered bounded evaluation

Freeze source and mapping policy at commit 934e250ab16ffb570d68c69e6a6e2aad0246c3be
before acquiring or inspecting the new paper page. No font-name, keyword, paper-ID
or fixture-specific rule may be added during this evaluation. H5/H6 are seen
regression fixtures, not a generality claim. Earlier blind outcomes remain 0/2.

## Selection

Select one publicly accessible non-physics research paper from its official
proceedings/publisher site, outside the H5/H6 source documents. Use PDF page 4
(zero-based index 3) without searching the document for a convenient page. Record
URL, full-document SHA256, extracted-page SHA256 and page count. The source must
be <= 10 MiB; transfer timeout <= 45 seconds. If unavailable, record that blocker
instead of silently substituting a more convenient page. Report actual column,
font and formula/figure characteristics after selection, not assumptions of diversity.

## Execution budget

Run the existing integrated-paper-1 complete request once, from the original
selected one-page PDF fixture, with installed model weights/runtime only. Overall
wall limit 60 seconds; terminate its process group on timeout and preserve all
partial stage files/logs. No model download, per-page tuning, retry, changed crop,
window expansion or fallback to whole-page images may turn a failed run green.
If that request fails, report the failure; diagnostics may inspect its retained
outputs, but no resumed/precomputed route counts as a cold pass.

## Predeclared acceptance gates

1. Complete the original request within 60 seconds without error or missing stages.
2. Existing strict gates: exact native source replay, zero failed source-support
   units, source-unit bijection, zero observer pixel difference, and all target
   local-image requests accepted. No relaxed tolerances.
3. Build selection using the frozen map policy. Every reader token is represented
   as eligible text or an explicit refusal. No unknown formula silently disappears.
4. Produce bounded native reader layouts at 20/24/28 px, 320/390 px widths. Inspect
   the actual source/reader visuals for omitted ink, column-order errors, broken
   formulas and unusable reading flow. Record failures even if structural tests pass.
5. Inspect a preregistered convenience sample: the first five eligible ordinary
   tokens from the first body paragraph and the first unresolved mathematical
   token, if available. This is a spotcheck, not semantic certification.

Report structural, performance, reading-flow and mapping outcomes separately.
Real browser selection/clipboard/focus/CSP acceptance remains unverified and cannot
be passed by this experiment. One successful new page would not establish a general
Readest solution; one failed page stays in the recorded denominator.
