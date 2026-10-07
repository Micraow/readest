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

This is a UI checkpoint. Focused interaction tests cover per-document persistence,
reset, history/keyboard navigation, paragraph position and image fit. Production
build and native visual acceptance must still verify the initial viewer with
controls visible, narrow-window reading and appearance changes before a new
package is described as validated. Compilation alone does not establish Android
device reading quality.
