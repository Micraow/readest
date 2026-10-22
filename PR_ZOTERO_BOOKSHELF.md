# Add: import Zotero library PDFs into the bookshelf

## What this changes

The library import menu (`+`) gets a new entry, **From Zotero**. It opens a page
that lists the user's Zotero Personal Library (collections and items) and, for a
chosen paper, downloads its stored PDF into the local library. From there the
paper behaves like any imported book: it opens in the reader, keeps reading
progress, and is uploaded under the existing Books sync setting when cloud sync
is on.

Downloaded papers are filed into a group named after the paper's Zotero
collection, for example `Zotero/Methods/Papers`. Nested collections keep their
parent path, and the groups show up in the library sidebar like other groups.

## Screenshots

The Zotero page, browsing collections and offering to add a paper:

![Zotero page](https://github.com/Micraow/readest/blob/feat/zotero-to-bookshelf/screenshots/zotero-shelf-visual.png?raw=true)

A paper after it was downloaded and imported, filed under its Zotero collection:

![Paper on the bookshelf](https://github.com/Micraow/readest/blob/feat/zotero-to-bookshelf/screenshots/zotero-bookshelf-e2e.png?raw=true)

## How it fits together

- `services/zotero/` — Zotero Web API v3 client (read-only, GET only), a
  credential store, the library provider, the runtime, and a native transport
  that follows storage redirects without carrying credentials or caller headers
  across hosts.
- `services/externalLibrary/types.ts` — provider and download-cache types shared
  with the rest of the app.
- `components/zotero/` — the connection settings and the browsable shelf.
- `app/zotero/page.tsx` — sends a finished download through
  `appService.importBook`, then sets the collection group with `setBookGroup`.
  A paper is identified by the PDF's partialMD5, so downloading an item that is
  already on the shelf returns the existing book instead of a duplicate.

The patch only adds files plus small wiring in the library page, the import menu,
the library header, and the service worker; no existing behaviour changes.

## Credentials

The API key is kept the same way other integration credentials are kept: as a
plain field in the local Data tree (next to the Zotero library metadata), never
in the settings replica, so cloud sync does not carry it in the clear. The key
is checked against Zotero before it is saved. A user ID and the library metadata
stay on disk after disconnect so the cached list stays readable offline.

Private requests are kept out of the service worker cache. Any request with
`cache: no-store`, an `Authorization` header, a `Zotero-API-Key` header, or a
host of `api.zotero.org` is handled as `NetworkOnly`, so a key or a PDF copy
never lands in CacheStorage.

## Platform note

Downloading a PDF is not possible from the web build: the file request redirects
from `api.zotero.org` to `files.zotero.net`, which does not send CORS headers, so
a browser `fetch` is blocked. Listing collections and items works on the web.
The desktop and mobile builds use the Tauri HTTP transport, which does not go
through the browser's CORS rules, so the download works there. If the web build
should support it too, it needs a server-side proxy; this patch does not add one
and keeps the download path for native builds.

## Scope

- Personal Library only. Group libraries, linked files, and WebDAV are not
  supported; only PDFs stored in Zotero Storage are downloaded.
- Read-only: nothing is written back to Zotero.

## Testing

- `src/services/zotero/**` — API, credentials, provider, runtime, transport, and
  native IPC, as unit tests.
- `src/components/zotero/__tests__/ZoteroShelf.test.tsx` — browsing, collection
  grouping, add-to-library vs. open-in-reader, and cancelling a download on
  unmount.
- `src/__tests__/services/service-worker-private-requests.test.ts` — private
  requests never reach a caching strategy.
- `pnpm lint` (tsc + biome) and `pnpm build` pass.

The new UI strings are not extracted with `pnpm i18n:extract` in this patch. The
English strings are the source keys, and the zh-CN file includes translations for
the new UI text.
