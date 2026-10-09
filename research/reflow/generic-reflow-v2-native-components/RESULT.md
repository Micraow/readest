# Exact component replacement; no whole-page speedup established

The limited OpenCV SAUF adapter passes **3,358 exact comparisons** of component
arrays, counts and ordered bounding slices: fourteen authored patterns, four
hundred seeded arrays, and 1,265 existing authored/seen-page alpha patches, each
with 4/8 connectivity. Four unsupported inputs refuse. The first control run's
empty-array mismatch is retained; the final adapter matches SciPy's empty-array
error too. There were no new model or package installations.

The isolated ownership copy differs from its frozen predecessor only in the
label/find_objects import, checked by the loader. A module-dictionary-based JSON
installer avoids triggering outside modules' lazy getters, verified by a hostile
lazy-module control. The existing image primitive library is already installed;
this experiment does not claim a smaller total mobile/runtime deployment.

Fresh complete requests, in the predetermined H5 then H6 order:

- H5: **46.943s wall, 44.865s total accounted CPU, 540.1 MiB sampled RSS**.
  The parsed final reader payload and all eleven 28px/DPR2 native-renderer PNGs
  exactly match the reviewed integrated reference.
- H6: **60.075s timeout, 55.653s total CPU, 544.4 MiB RSS**. No complete reader
  was accepted within budget. Its partial output is preserved and not resumed.

This is slower than the compact candidate's single H5 run. Varying shared load,
model/import times and observer overhead are recorded, so neither a speedup nor a
regression attributable solely to connected components is established. Lower
import breadth does not itself constitute net benefit. H6 remains a budget failure.

The H5 source/target gates and output equivalence are positive correctness
controls only. Original blind results stay **0/2**, these are seen diagnostics,
no new holdout was opened, and no CI/browser/selection/focus-zoom verification ran.
The native text-set cache is a separate experiment rather than a silent adoption.
