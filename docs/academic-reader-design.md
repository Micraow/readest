# Academic PDF reader (Phases 0–3)

## Baseline and scope

Based on upstream `readest/readest` main `4c3ccfe85d4afd81e674b67d6a0627d83ba0744d`.
The fork keeps its upstream remote and the Readest name and UI. The scope is read-only
Zotero Personal Library + Zotero Storage, and an optional, local, deterministic
born-digital academic PDF reading mode. No OCR, remote parsing, AI, translation,
annotation writes, Group Library sync, linked files or WebDAV are added.

## Existing boundaries reviewed

The architecture document, `libraryStore`, `bookDataStore`, `readerStore`, Book,
`bookService`, `ingestService`, `cloudService`, `AppService`, native/web filesystem
implementations, `RemoteFile`/`NativeFile`, reader routes, `FoliateViewer`, navigation,
annotation/progress hooks and `parallelViewStore` define these constraints:

- A normal Book is hash-addressed, stored in `Books`, and participates in metadata,
  reading-config and file sync. Even a transient import runs importer side effects.
- `FoliateViewer` mounts cloud/KOReader/BookOrbit progress sync, cover persistence,
  translation and annotation hooks. Putting a fabricated Zotero Book in its stores
  would require fragile guards throughout these unrelated subsystems.
- `DocumentLoader` and the `foliate-view` engine are the reusable PDF boundary.
  The engine already uses PDF.js, original page layout, scrolling and navigation.
- `AppService` exposes portable file I/O: native uses scoped files/rangefile reads
  (Android/Linux differ from Apple), and web uses IndexedDB. No shell parser is needed.
- The native bridge already exposes keyed OS-secret storage. Ordinary settings and
  replica sync are not suitable for a Zotero API key.

## Module placement and identity

`services/externalLibrary` defines the small provider contract and canonical shelf
models; `services/zotero` owns API v3, collection trees, bibliographic metadata,
stored-PDF attachment selection, download and local materialization. Every identity
contains provider, personal-library user ID, parent item key and attachment key.
There are no calls to `importBook`, `ingestFile`, `libraryStore.updateBooks`, cloud
upload or remote delete. Metadata and completed files live under a provider-owned
`Data/external-library/zotero/` subtree, outside `Books` and the normal sync adapters.
Using Data rather than the OS-evictable cache directory preserves offline copies.
A local manifest is published only after valid PDF bytes have been written.
Clear-local-copy deletes only this provider cache; metadata remains remote-owned.

The shelf is a dedicated content source linked from Library and Settings. The only
source-to-reader contract is a local `File`, title and local resume key. Credentials
never enter URLs, logs, general settings or normal cloud sync. Native secure storage
is preferred; platforms without it use explicitly disclosed session-only credentials,
so web remains supported without pretending plain localStorage is secure.
The service worker routes authenticated/no-store/Zotero requests through NetworkOnly;
its generic offline caches must not retain API keys or a second attachment copy.
API requests are direct to Zotero (no Readest proxy) with API version 3 and a header
key. Redirect downloads must not forward the API key to storage/CDN hosts.

## Reading boundary and integration risk

Provider documents open through a small source-neutral PDF surface reusing Readest's
`DocumentLoader`, original `foliate-view` renderer, theme, typography, navigation and
UI primitives. It does not instantiate an ordinary Book or mount its cloud/annotation
write hooks. This intentionally leaves normal library/parallel-reading behavior
unchanged. Provider PDF annotations are not edited or synchronized in this stage.
The conventional reader receives a small opt-in Reading entry for any local PDF.
Original PDF remains the default; closing Reading returns to the mounted original
view. Switching and closing visual zoom preserve the reading scroll position.

The isolated wrapper is a tradeoff: it repeats a small original-PDF toolbar, but avoids
large invasive guards across sync and reader stores. Do not add a second importer,
new branding, a new reading-settings system or changes to Foliate submodule code.

## Academic engine contracts

`services/academic` owns a standalone `ScholarlyDocument`, source geometry and pure
layout pipeline. Coordinates are normalized to the PDF.js scale-1, rotated viewport
(top-left origin), with source page, original item index and boxes on every block.
The pipeline clusters lines, detects column gutters and full-width bands, groups
paragraphs, classifies heading/list/reference/footnote text, suppresses repeated
marginalia, repairs conservative line-end hyphens and reconstructs reading order.
Figure, table, algorithm and display-math regions remain `visual-region` blocks.
Unknown/ambiguous layouts retain original page/region visuals rather than inventing
an order. Scanned documents report Reading unavailable and keep Original PDF usable.

The layout inspector is developed before classification. It independently toggles
raw items, lines, paragraphs, columns, visual boxes and final order/role labels and
shows source item IDs, font statistics and confidence. It is development-only.

PDF.js geometry extraction is asynchronous and page-bounded; deterministic analysis
runs in a module worker. Progress/cancellation and bounded page work keep a 100-page
file from freezing the main UI. The reader is one continuous responsive text flow.
Visual regions render only near the viewport, with capped DPR-aware canvases and
fullscreen pinch/pan/double-tap zoom. No persistent raster cache is created.

## Persistence and validation

Reflow cache is keyed by full PDF content SHA-256 plus parser/schema version. JSON
contains blocks, ordered block IDs, source maps and detection/debug data. Changed
bytes or version invalidate it; corrupt cache is ignored and regenerated. Provider
identity does not leak into the academic schema. Reading positions are local.

Tests cover API pagination, auth errors, hierarchy, stored attachment filtering,
cancellation, offline reopening, no normal Book creation or upload, and local-only
removal. Pure fixtures cover lines, columns, order, paragraphs, marginalia,
hyphenation, source integrity, visual insertion and invalidation. A public author/
publisher corpus includes HPCC as the primary visual/manual golden. Copyrighted
PDFs and private metadata/credentials are never committed.

## Phase gates and platform evidence

1. Phase 0: architecture and baseline builds/checks
2. Phase 1: provider/Settings/shelf/offline original-PDF workflow
3. Phase 2: inspector, deterministic engine, mapping and cache
4. Phase 3: continuous reader and manual integration, then stop

Android is first acceptance platform; Linux desktop is second. Windows, macOS, iOS
and web share TypeScript and PDF.js; only I/O/secure-storage/network adapters vary.
Each phase records executed checks separately from unavailable native smoke checks.
The cloud environment initially lacked native tooling. Task-local Rust, Clang, Linux
native libraries and Android SDK36/NDK28.2 are now provisioned. Native build and
device/runtime acceptance are tracked separately in the validation document. Real personal-library acceptance requires the user to configure
credentials securely in the app; mocked service checks do not substitute for it.

## Likely upstream conflicts

Keep edits to Library navigation, integration settings and the ordinary PDF reader
entry small. Most work is additive modules/routes/tests. Avoid changes to Book,
normal library serialization, CloudService, sync adapters, Foliate submodule commits,
platform bridges and general reader stores unless a proven boundary requires them.
