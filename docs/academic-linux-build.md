# Academic Linux acceptance build

The `Academic Linux acceptance build` workflow builds one Ubuntu 24.04 x86_64
executable with a production frontend and the debug CEF native profile. It does
not publish a release, container, website, or signed package.

Run it manually with **Run workflow**. For a source-control client without a
dispatch operation, update `.github/academic-linux-request.txt` and include
`[build-academic-linux]` in that commit's message. Ordinary source checkpoints
do not start the expensive job. One job can run at a time; its time limit is
75 minutes. pnpm, Cargo dependencies, and the pinned CEF archive are cached.

The workflow pins Node 24.19.0, pnpm 11.1.1, Rust 1.99.0, the repository's
CEF CLI version, and CEF 151.3.24. The archive is SHA-256 checked before
extraction. It uses the tracked public environment defaults and no deployment
or signing secrets. It runs the academic unit tests and application lint before
compilation; the larger local regression result is recorded separately in
[academic-reader-validation.md](academic-reader-validation.md).

Artifacts expire after seven days. `academic-linux-manifest` contains build
provenance and an ordered transfer manifest. Each `academic-linux-partNN`
artifact contains one 16 MiB-or-smaller part of `native.tar.gz`, keeping the
individual download below the consumer's 32 MiB limit. After downloading:

1. Check every part's size and SHA-256 against `transfer.json`.
2. Concatenate parts in the manifest's order and check the archive SHA-256.
3. Extract the unstripped `readest`, license and provenance into a new staging
   directory. Verify the ELF hash against `provenance.json`.
4. Match **every** CEF runtime hash in provenance against the separately pinned
   CEF distribution before combining them. The ELF alone is not a portable app.
5. Run the normal portable-package ELF, dependency and archive checks, then
   open the real acceptance PDFs in the desktop app. A successful CI build does
   not establish visual reading quality.

No user PDF, extracted paper text, screenshots, profile, or analysis cache is
sent to this workflow. Native acceptance and Library delivery remain separate
stages. The previously accepted package stays available until those pass.
