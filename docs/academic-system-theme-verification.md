# System-driven theme verification

## Verified code path

`theme-system-events.test.tsx` exercises the real `initSystemThemeListener`,
theme store, and academic `useMathCanvasStyle` subscriber. The platform flags
cover the non-iOS Linux and Android paths; the media-query event is synthetic.

For each path, the tests cover:

- Light → dark → light media events update the system state, persisted state,
  document theme, and math presentation without directly setting the state
  under test.
- Visibility events catch up when a media change was missed.
- Explicit light/dark choices override system changes, and Auto resumes the
  current system color.

The six tests pass. Mutation checks show four failures when the media listener
is omitted, and two failures when visibility catch-up is omitted. The original
production file was restored byte-for-byte after each check. No production
theme change was required.

The combined academic, image-viewer, theme-store and event-chain suite has
362 passing tests. Application TypeScript and Biome lint pass. This is focused
verification; the previously recorded unrelated full-suite fixture and Nix
limitations remain.

## Native acceptance boundary

The delivered Linux CEF binary from `bf7abe8` was inspected in its existing
isolated test profile. Its reader menu showed Auto Mode. The available Xfce
Appearance panel offered only the existing custom style and OrbitOS, without
a light/dark switch. The existing Xsettings properties also had no color-scheme
or prefer-dark entry. No OS or application theme setting was changed.

Therefore this session did not generate a real OS color-scheme transition.
The OS → CEF media event portion remains unverified, as does Android runtime
theme behavior. The simulated Linux/Android flags above do not establish
native device acceptance, and a manual app theme toggle would not close that
gap. The current package does not need rebuilding for these test-only changes.

Existing academic component tests separately verify that live math styling
does not reparse the PDF, alter source geometry, recolor ordinary figures, or
change the original source passed to zoom.
