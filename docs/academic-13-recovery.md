# Academic 13 recovery checkpoint

Status at 2026-10-07 17:25 UTC. This record identifies existing build outputs;
it does not authorize or require another build.

## Exact source and outputs

- Source commit: `8b95861016dec96365fe99db8de58af42504c190`
- Source tree: `21ca274fdc1156e6b637d44b2efc1a28c29b6bae`
- Parser: `academic-13`
- Linux run: [37651083824](https://github.com/Micraow/readest/actions/runs/37651083824)
- Android run: [37651083868](https://github.com/Micraow/readest/actions/runs/37651083868)

Both runs succeeded. Retrieve their manifest and numbered part artifacts from
GitHub Actions. Check each downloaded ZIP against its Actions digest before
extracting only the expected member. Verify each inner part against
`transfer.json`, concatenate in the manifest's order and verify the combined
archive before extracting. Do not trust filenames alone.

Linux artifact IDs:
`academic-linux-manifest` 11496870929;
`academic-linux-part00` 11497015802;
`academic-linux-part01` 11495849921;
`academic-linux-part02` 11497580055;
`academic-linux-part03` 11495934552.

The reconstructed Linux tar contains only `readest`, `provenance.json` and
`LICENSE`. Its SHA-256 is
`afbb677001c9aa0c1d918e89209588363a6c7b0401bbe13f9e2ddfced11c6798`.
The unstripped ELF is 226672560 bytes with SHA-256
`a4d8a476e52793be12c5b9616f348ae2fd9675783406688a70710f36f3c08b49`.

Recover the pinned official CEF archive using
[scripts/academic-linux-ci.py](../scripts/academic-linux-ci.py).
The archive SHA-256 is
`db53c43fdace8b7ee4af0f005120116d6973aa9d8eb7702c0617badf9be8684e`.
Match every runtime-file digest against `cefRuntimeSha256` in provenance,
including locales and licenses. No compiler installation is needed to recover
this executable. If stripping a copy for distribution, compare all allocated
ELF sections and loadable segments to the original, then verify dynamic linkage.
Keep the unmodified CI input and provenance separate from the portable package.

Android artifact IDs:
`academic-android-manifest` 11498285859;
`academic-android-part00` 11498201086;
`academic-android-part01` 11497916491;
`academic-android-part02` 11498066243.

The reconstructed unsigned APK is 36479039 bytes with SHA-256
`d1a97f47af55f705a60c8fb0c8be45457ac5df5b8815593439b43225a980a9f8`.
Its identity is `com.bilingify.readest.academic`, version
`0.12.12-academic.13` / 12013, arm64-v8a only. Retain it as an unsigned build
input. The earlier local signing key is unavailable after the workspace reset;
do not generate a different key and call the resulting package an in-place
update. No private key belongs in this repository or ordinary build artifacts.

## Remaining acceptance and persistence

1. Reassemble the portable candidate from the verified ELF and CEF runtime.
2. Run it in the native desktop application using a fresh isolated profile.
   Recover private input PDFs through their authorized local source; never add
   them or extracted fixtures to the repository or public build artifacts.
3. Capture the reported equation and following paragraph in light and dark
   reading themes, author order and deferred note, and citation/footnote return.
   The equivalent checks were observed before the reset, but their local
   screenshots were not persisted.
4. Finish the other two papers' short regression: paragraph continuity,
   mathematics, grouped figures, algorithm zoom, narrow-window long text and
   cache reopening. A new profile cannot establish preservation of cache
   modification times from the lost profile.
5. Archive only application/runtime files, licenses, checksums and accurate
   usage notes. Save the verified package and representative screenshots before
   reporting delivery.

The earlier Android emulator run stopped at its KVM access gate. Linux screenshots
must not be described as Android device acceptance. System-driven Android theme
changes still require an actual Android runtime check.
