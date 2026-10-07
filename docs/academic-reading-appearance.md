# Academic reading appearance

The reading toolbar now offers an **Aa** panel for font size and line spacing.
Changes apply to the current PDF, persist on this device, and preserve the
visible paragraph. Reset restores the book/global preferences. Adjusting the
appearance does not rerun PDF analysis or change the academic-12 cache.

Academic image viewers reserve separate space for their controls and description.
Initial fit uses the remaining image area, including device insets. Hiding the
controls keeps that area stable; zoom and pan still operate within it. Other
book image viewers retain their existing layout.

These changes follow same-file native comparisons. Default typography and saved
reader preferences can materially affect apparent density, so comparisons must
record font size, line spacing and window width. Caption completeness must be
checked against the original PDF, not inferred from another reader's longer
caption: body continuation can be incorrectly absorbed into captions.

## Acceptance on 2026-10-07

Source `dca7a24b17c69d47ef9fb8640c80ff9e6e396392` passed 195 focused tests
across 18 files, complete TypeScript/lint checks and production builds in the
dedicated [Linux](https://github.com/Micraow/readest/actions/runs/37639961974)
and [Android](https://github.com/Micraow/readest/actions/runs/37639962100) jobs.
Eight CI helper tests passed locally; each job also ran its applicable helpers.

The packaged Linux app was checked with actual PDFs. The initial Algorithm 2
viewer showed all 17 lines with controls visible; hiding/restoring the controls
kept the image area pixel-identical. Zoom, pan and return worked. Font size and
line spacing changed from 16/1.4 to 18/1.5 and 20/1.6 while retaining the current
paragraph. Restart retained that PDF's choices, another PDF kept its own
defaults, and reset restored 16/1.4. All 25 existing parse cache files retained
their bytes and timestamps.

At a 527px window width the appearance panel and visible body text remained
usable. A horizontal scrollbar was observed at 20px text: long unbroken content
can still require horizontal reading. Resizing the whole window also retains an
absolute scroll position rather than the same paragraph. These are remaining
limitations, not part of the verified font-change position preservation.

Android compilation and static APK checks do not establish real-device reading
quality. No Android hardware/emulator acceptance is claimed for this build.
