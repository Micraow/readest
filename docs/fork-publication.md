# Fork CI and publication

Pushing source to `main` runs the existing checks and builds. It does not by
itself authorize publishing a container, deploying a production website, or
uploading a nightly release.

Automatic publication is disabled unless the repository variable
`ENABLE_AUTOMATED_PUBLISHING` is explicitly set to the string `true`:

- Docker image build/push and manifest publication
- Production Vercel deployment
- Nightly release builds and manifest upload, including the `always()` cleanup path
- Nix cache uploads and publication of Scorecard results to OpenSSF

Nix builds still run with public cache reads, and Scorecard analysis and its
repository-local reports still run. Ordinary PR/main checks and CodeQL are
unchanged. Manually triggered release workflows keep their existing behavior.

Setting the variable is a separate repository-owner decision requiring the
intended services, destinations and credentials to be configured. No variable,
secret or repository permission is created or modified by this source change.
