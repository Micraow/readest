import { stubTranslation as _ } from '@/utils/misc';
import type {
  DownloadProgress,
  ExternalAttachment,
  ExternalCollection,
  ExternalCollectionNode,
  ExternalItem,
} from '../externalLibrary/types';

export interface ZoteroCredentials {
  userId: string;
  apiKey: string;
}

export type ZoteroErrorCode =
  | 'authentication'
  | 'network'
  | 'rate-limit'
  | 'not-found'
  | 'invalid-data'
  | 'storage'
  | 'no-pdf';
export class ZoteroError extends Error {
  constructor(
    public readonly code: ZoteroErrorCode,
    message: string,
  ) {
    super(message);
    this.name = 'ZoteroError';
  }
}

export type ZoteroFetch = (url: string, options: RequestInit) => Promise<Response>;
export type ZoteroWait = (milliseconds: number, signal?: AbortSignal) => Promise<void>;
export const API_ORIGIN = 'https://api.zotero.org';

export function validateUserId(value: string): string {
  if (!/^[1-9]\d{0,15}$/.test(value)) {
    throw new ZoteroError('invalid-data', _('Enter your numeric Zotero User ID'));
  }
  return value;
}

export function validateKey(value: string): string {
  if (!/^[A-Z0-9]{8}$/.test(value)) {
    throw new ZoteroError('invalid-data', _('Invalid Zotero item or collection key'));
  }
  return value;
}

export function checkCancelled(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
}

export function isCancelled(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

export const waitForZotero: ZoteroWait = (milliseconds, signal) =>
  new Promise((resolve, reject) => {
    checkCancelled(signal);
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException('Cancelled', 'AbortError'));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort);
      resolve();
    }, milliseconds);
    signal?.addEventListener('abort', abort, { once: true });
  });

export function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
const string = (value: unknown): string => (typeof value === 'string' ? value : '');
const version = (value: unknown): number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : 0;
const safeKey = (value: unknown): string | null =>
  typeof value === 'string' && /^[A-Z0-9]{8}$/.test(value) ? value : null;
export const safeFilename = (value: string, key: string): string =>
  value
    .split(/[\\/]/)
    .pop()
    ?.replace(/[\u0000-\u001f\u007f]/g, '')
    .slice(0, 180) || `${key}.pdf`;

export function buildCollectionTree(collections: ExternalCollection[]): ExternalCollectionNode[] {
  const visited = new Set<string>();
  const nodes: ExternalCollectionNode[] = [];
  const keys = new Set(collections.map((c) => c.key));
  const sorted = [...collections].sort(
    (a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key),
  );
  const build = (collection: ExternalCollection): ExternalCollectionNode => {
    visited.add(collection.key);
    return {
      ...collection,
      children: sorted
        .filter((c) => c.parentKey === collection.key && !visited.has(c.key))
        .map(build),
    };
  };
  for (const collection of sorted) {
    if ((!collection.parentKey || !keys.has(collection.parentKey)) && !visited.has(collection.key))
      nodes.push(build(collection));
  }
  // Malformed cyclic/orphan metadata must remain navigable without infinite recursion.
  for (const collection of sorted) if (!visited.has(collection.key)) nodes.push(build(collection));
  return nodes;
}

export function selectStoredPdf(attachments: ExternalAttachment[]): ExternalAttachment | null {
  return [...attachments].sort((a, b) => a.key.localeCompare(b.key))[0] ?? null;
}

/** Web API v3, Personal Library only. All network operations are GET. */
export class ZoteroApi {
  private nextRequestAt = 0;
  private readonly prefix: string;
  constructor(
    private readonly credentials: ZoteroCredentials,
    private readonly fetcher: ZoteroFetch,
    private readonly wait: ZoteroWait = waitForZotero,
  ) {
    this.prefix = `${API_ORIGIN}/users/${validateUserId(credentials.userId)}`;
    if (
      !credentials.apiKey ||
      credentials.apiKey.length > 256 ||
      /[\s\x00-\x1f\x7f]/.test(credentials.apiKey)
    ) {
      throw new ZoteroError(
        'authentication',
        _('Enter a Zotero API key with library and file read access'),
      );
    }
  }

  private async request(path: string, signal?: AbortSignal, file = false): Promise<Response> {
    for (let attempt = 0; attempt < 3; attempt++) {
      checkCancelled(signal);
      const delay = this.nextRequestAt - Date.now();
      if (delay > 0) await this.wait(delay, signal);
      checkCancelled(signal);
      let response: Response;
      try {
        response = await this.fetcher(`${this.prefix}/${path}`, {
          method: 'GET',
          // Fetch strips Authorization on cross-origin redirects. A custom
          // Zotero-API-Key header would NOT receive that protection. Native
          // transport additionally follows storage redirects without any headers.
          headers: {
            'Zotero-API-Version': '3',
            Authorization: `Bearer ${this.credentials.apiKey}`,
          },
          signal,
          redirect: file ? 'follow' : 'error',
          credentials: 'omit',
          referrerPolicy: 'no-referrer',
          cache: 'no-store',
        });
      } catch (error) {
        checkCancelled(signal);
        if (isCancelled(error)) throw error;
        throw new ZoteroError(
          'network',
          _('Could not reach Zotero. Check your connection and try again'),
        );
      }
      checkCancelled(signal);
      const backoff = Number(response.headers.get('Backoff'));
      if (Number.isFinite(backoff) && backoff > 0) this.nextRequestAt = Date.now() + backoff * 1000;
      if (response.status === 429 || response.status === 503) {
        const retryHeader = response.headers.get('Retry-After');
        const retrySeconds = retryHeader ? Number(retryHeader) : NaN;
        const retryDate = retryHeader ? Date.parse(retryHeader) : NaN;
        const retryDelay =
          Number.isFinite(retrySeconds) && retrySeconds >= 0
            ? retrySeconds * 1000
            : Number.isFinite(retryDate)
              ? Math.max(0, retryDate - Date.now())
              : 1000 * 2 ** attempt;
        this.nextRequestAt = Math.max(this.nextRequestAt, Date.now() + retryDelay);
        if (attempt < 2) {
          await response.body?.cancel();
          continue;
        }
        throw new ZoteroError('rate-limit', _('Zotero is busy. Please wait before trying again'));
      }
      if (response.status === 401 || response.status === 403)
        throw new ZoteroError(
          'authentication',
          _('Zotero denied access. Check the User ID and API key library and file permissions'),
        );
      if (response.status === 404)
        throw new ZoteroError(
          'not-found',
          file
            ? _(
                'This PDF is not available in Zotero Storage. Linked files and WebDAV are not supported',
              )
            : _('The Zotero library or item was not found'),
        );
      if (!response.ok)
        throw new ZoteroError(
          'network',
          _('Zotero could not complete the request. Try again later'),
        );
      return response;
    }
    throw new ZoteroError('rate-limit', _('Zotero is busy. Please wait before trying again'));
  }

  private async list(path: string, signal?: AbortSignal): Promise<unknown[]> {
    const result: unknown[] = [];
    // Build offsets ourselves. Never send credentials to URLs from Link headers.
    for (let start = 0; start < 1_000_000; ) {
      const response = await this.request(`${path}?format=json&limit=100&start=${start}`, signal);
      let page: unknown;
      try {
        page = await response.json();
      } catch {
        throw new ZoteroError('invalid-data', _('Zotero returned invalid library data'));
      }
      checkCancelled(signal);
      if (!Array.isArray(page))
        throw new ZoteroError('invalid-data', _('Zotero returned invalid library data'));
      result.push(...page);
      start += page.length;
      const totalHeader = response.headers.get('Total-Results');
      const total = totalHeader !== null ? Number(totalHeader) : NaN;
      if (page.length === 0 || (Number.isFinite(total) ? start >= total : page.length < 100))
        return result;
    }
    throw new ZoteroError(
      'invalid-data',
      _('The Zotero library is too large to load in one request'),
    );
  }

  async listCollections(signal?: AbortSignal): Promise<ExternalCollection[]> {
    const rows = await this.list('collections', signal);
    return rows.map((row) => {
      const raw = object(row);
      const data = object(raw['data']);
      return {
        key: validateKey(string(raw['key'])),
        version: version(raw['version']),
        name: string(data['name']) || _('Untitled collection'),
        parentKey: safeKey(data['parentCollection']),
      };
    });
  }

  async listItems(signal?: AbortSignal): Promise<ExternalItem[]> {
    const rows = await this.list('items/top', signal);
    return rows
      .filter(
        (row) =>
          !['attachment', 'note', 'annotation'].includes(
            string(object(object(row)['data'])['itemType']),
          ),
      )
      .map((row) => {
        const raw = object(row);
        const data = object(raw['data']);
        const creators = Array.isArray(data['creators']) ? data['creators'] : [];
        const authors = creators
          .map((creator) => {
            const person = object(creator);
            return (
              string(person['name']) ||
              [string(person['firstName']), string(person['lastName'])].filter(Boolean).join(' ')
            );
          })
          .filter(Boolean);
        return {
          key: validateKey(string(raw['key'])),
          version: version(raw['version']),
          title: string(data['title']) || _('Untitled item'),
          authors,
          year: string(data['date']).match(/\b\d{4}\b/)?.[0] ?? '',
          venue:
            string(data['publicationTitle']) ||
            string(data['proceedingsTitle']) ||
            string(data['bookTitle']) ||
            string(data['university']) ||
            string(data['publisher']),
          collectionKeys: (Array.isArray(data['collections']) ? data['collections'] : [])
            .map(safeKey)
            .filter((key): key is string => key !== null),
        };
      });
  }

  async listAttachments(itemKey: string, signal?: AbortSignal): Promise<ExternalAttachment[]> {
    const rows = await this.list(`items/${validateKey(itemKey)}/children`, signal);
    const attachments: ExternalAttachment[] = [];
    for (const row of rows) {
      const raw = object(row);
      const data = object(raw['data']);
      const key = safeKey(raw['key']);
      if (
        !key ||
        data['itemType'] !== 'attachment' ||
        data['parentItem'] !== itemKey ||
        data['contentType'] !== 'application/pdf' ||
        !['imported_file', 'imported_url'].includes(string(data['linkMode']))
      )
        continue;
      attachments.push({
        key,
        parentKey: itemKey,
        version: version(raw['version']),
        filename: safeFilename(string(data['filename']), key),
        md5: /^[a-f\d]{32}$/i.test(string(data['md5'])) ? string(data['md5']).toLowerCase() : null,
      });
    }
    return attachments.sort((a, b) => a.key.localeCompare(b.key));
  }

  async download(
    attachment: ExternalAttachment,
    signal?: AbortSignal,
    onProgress?: (progress: DownloadProgress) => void,
  ): Promise<ArrayBuffer> {
    const response = await this.request(`items/${validateKey(attachment.key)}/file`, signal, true);
    const etag = response.headers.get('ETag')?.replace(/^"|"$/g, '').toLowerCase();
    if (attachment.md5 && etag && /^[a-f\d]{32}$/.test(etag) && attachment.md5 !== etag) {
      await response.body?.cancel();
      throw new ZoteroError(
        'invalid-data',
        _(
          'The Zotero Storage PDF differs from its metadata. Refresh the library or sync the file in Zotero',
        ),
      );
    }
    const size = Number(response.headers.get('Content-Length'));
    const total = Number.isFinite(size) && size > 0 ? size : undefined;
    const maxBytes = 512 * 1024 * 1024;
    if (total && total > maxBytes) {
      await response.body?.cancel();
      throw new ZoteroError(
        'invalid-data',
        _('This PDF is too large to download (maximum 512 MB)'),
      );
    }
    const reader = response.body?.getReader();
    if (!reader) throw new ZoteroError('network', _('Zotero returned an empty file'));
    const chunks: Uint8Array[] = [];
    let received = 0;
    const abort = () => {
      void reader.cancel().catch(() => undefined);
    };
    signal?.addEventListener('abort', abort, { once: true });
    try {
      while (true) {
        checkCancelled(signal);
        const chunk = await reader.read();
        checkCancelled(signal);
        if (chunk.done) break;
        received += chunk.value.byteLength;
        if (received > maxBytes)
          throw new ZoteroError(
            'invalid-data',
            _('This PDF is too large to download (maximum 512 MB)'),
          );
        chunks.push(chunk.value);
        onProgress?.({ received, total });
      }
      if (!received || (total && received !== total))
        throw new ZoteroError('network', _('The PDF download was incomplete. Try again'));
      const bytes = new Uint8Array(received);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.length;
      }
      return bytes.buffer;
    } catch (error) {
      await reader.cancel().catch(() => undefined);
      checkCancelled(signal);
      if (error instanceof ZoteroError || isCancelled(error)) throw error;
      throw new ZoteroError('network', _('The PDF download was interrupted. Try again'));
    } finally {
      signal?.removeEventListener('abort', abort);
      reader.releaseLock();
    }
  }
}
