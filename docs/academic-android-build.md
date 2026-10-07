# Parallel Android reading test build

The `Academic Android unsigned build` workflow produces one arm64 release APK
with the academic-12 reader. Use **Run workflow**, or explicitly include
`[build-academic-android]` in a main-branch commit. Ordinary commits skip this job
before runner allocation. For that explicit marker push, the separate Android
tests/lint/build replace the unrelated Nix, web and host-native build lanes;
ordinary source and pull-request checks keep their existing behavior.

The optional `academicBuild=true` Gradle property selects
`com.bilingify.readest.academic`, displayed as **Readest 学术测试版**. It preserves
the original Java/JNI namespace while giving the APK a separate installation and
data directory. Normal builds without that property keep the original identity.

The test variant keeps local file import and ordinary network/API access,
including the read-only Zotero integration. It does not claim the production
Readest, Google Drive or OneDrive OAuth callbacks or web app links, and its
in-app updater is disabled. Those account sign-in callbacks are unavailable in
this parallel test variant; it must not replace or interfere with an existing
official installation.

The job pins Node 24.19.0, pnpm 11.1.1, Rust 1.99.0, JDK 17, Android SDK 36,
Build Tools 36.0.0 and NDK 28.2.13676358. The npm mobile CLI's generated AGP
8.11.0/Gradle 8.14.3 scaffolding uses Kotlin 2.2.10 to support the app's current
AndroidX dependencies. A small Gradle/Kotlin/manifest probe runs before expensive
Rust compilation. The full build then verifies native plugin integration.

The first run (37633805686) failed in this cheap probe, before frontend or Rust
compilation: its temporary directory did not retain the app-relative `.env`
location. The probe now preserves the `readest-app/src-tauri/gen/android`
structure and copies only the tracked public `.env`. Gradle accepts regular
files rather than any existing path. A regression test verifies the temporary
lookup stays inside that app directory.

No private signing material is sent to this workflow. Its release APK is
**unsigned and not installable** until separately signed with the approved
dedicated test identity. It must not silently use a fresh debug certificate for
the original package ID. The old development key is unavailable, so the original
test APK's signature cannot be reproduced or recovered from that APK.

`academic-android-manifest` and the checksummed 16 MiB artifact parts preserve the
unsigned candidate and provenance for seven days. Reassemble in `transfer.json`
order and verify every part and the full APK hash. A failed source or APK gate
quarantines the candidate; inspect its recorded evidence before signing.

Validation includes the merged identity and provider authorities, original
MainActivity namespace, arm64-only ELF payload, 16 KiB alignment, compressed
native libraries and absence of signatures. After local signing, verify the
signature, certificate fingerprint, identity, alignment and final SHA-256 again.
Neither compilation nor signing establishes real Android device reading quality.

No PDF, paper extraction, account profile, keystore, password, or deployment
credential belongs in these source or build artifacts. Do not publish the
unsigned candidate as an installable release or upload a private key as a normal
workflow artifact.

## Verified candidate on 2026-10-07

The recovery [run 37639962100](https://github.com/Micraow/readest/actions/runs/37639962100)
succeeded for source `dca7a24b17c69d47ef9fb8640c80ff9e6e396392`. The unsigned APK
was independently recovered from checksummed artifact parts and checked again
with official Android Build Tools 36.0.0. It contains only compressed arm64
libraries, passes 16 KiB alignment, and uses the separate academic app/provider
identity with the original MainActivity namespace. Its version is 0.12.12 / 12012,
minimum Android API 26 and target API 36.

Local signing used the explicitly approved dedicated test identity. The final
APK is 36,565,458 bytes, SHA-256
`d901232e91db1f70254ec72bd6ed7a3f030bf1682f059fe60aec57a44f2828e6`.
APK Signature Scheme v2 and v3 verification and post-signing alignment passed.
Its public certificate SHA-256 is
`c69930d562568bbbf8e4317f38d3847dbb44ba8c99f29b49a62a0b6b35729432`.
The private key was not uploaded to CI, source control or ordinary artifacts;
secure user-controlled backup remains pending. Do not overwrite that key when
preparing future updates. Android device/emulator reading acceptance remains
pending; the corresponding reading UI was visually checked in the Linux build.
