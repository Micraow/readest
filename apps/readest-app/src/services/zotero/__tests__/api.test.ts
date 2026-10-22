// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ZoteroApi, ZoteroError, buildCollectionTree, selectStoredPdf } from '../api';

const userId = '12345';
const apiKey = 'private-test-key';
const json = (value: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(value), { headers });
const item = (key: string, extra = {}) => ({
  key,
  version: 2,
  data: {
    key,
    itemType: 'journalArticle',
    title: 'Paper',
    creators: [{ firstName: 'Ada', lastName: 'Lovelace', creatorType: 'author' }],
    date: '2025-06-01',
    publicationTitle: 'Journal',
    collections: ['COLLECT1'],
    ...extra,
  },
});

describe('read-only Zotero v3 API', () => {
  it('paginates with trusted numeric offsets, never a server-supplied URL', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        json(
          Array.from({ length: 100 }, (_, n) => item(`ITEM${String(n).padStart(4, '0')}`)),
          { 'Total-Results': '101', Link: '<https://attacker.invalid/steal>; rel="next"' },
        ),
      )
      .mockResolvedValueOnce(json([item('ITEM0100')], { 'Total-Results': '101' }));
    const api = new ZoteroApi({ userId, apiKey }, fetcher);
    expect(await api.listItems()).toHaveLength(101);
    expect(fetcher.mock.calls[1]![0]).toBe(
      'https://api.zotero.org/users/12345/items/top?format=json&limit=100&start=100',
    );
    for (const [url, options] of fetcher.mock.calls) {
      expect(url).toMatch(/^https:\/\/api\.zotero\.org\/users\/12345\//);
      expect(url).not.toContain(apiKey);
      expect(options.method).toBe('GET');
      expect(options.headers).toMatchObject({
        'Zotero-API-Version': '3',
        Authorization: `Bearer ${apiKey}`,
      });
      expect(options.headers).not.toHaveProperty('Zotero-API-Key');
    }
  });

  it('maps bibliography and filters standalone attachments and notes', async () => {
    const api = new ZoteroApi(
      { userId, apiKey },
      vi
        .fn()
        .mockResolvedValue(
          json([
            item('ITEM0001'),
            item('ATTACH01', { itemType: 'attachment' }),
            item('NOTE0001', { itemType: 'note' }),
          ]),
        ),
    );
    expect(await api.listItems()).toEqual([
      {
        key: 'ITEM0001',
        version: 2,
        title: 'Paper',
        authors: ['Ada Lovelace'],
        year: '2025',
        venue: 'Journal',
        collectionKeys: ['COLLECT1'],
      },
    ]);
  });

  it.each([
    '../123',
    '123/other',
    'abc',
    '0',
    '123?key=secret',
  ])('rejects invalid user ID %s', (value) => {
    expect(() => new ZoteroApi({ userId: value, apiKey }, vi.fn())).toThrow(ZoteroError);
  });

  it('rejects invalid item keys before any request', async () => {
    const fetcher = vi.fn();
    await expect(
      new ZoteroApi({ userId, apiKey }, fetcher).listAttachments('../bad'),
    ).rejects.toThrow();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('returns a safe auth error without exposing upstream text or credentials', async () => {
    const api = new ZoteroApi(
      { userId, apiKey },
      vi.fn().mockResolvedValue(new Response(apiKey, { status: 403 })),
    );
    await expect(api.listItems()).rejects.toMatchObject({ code: 'authentication' });
    try {
      await api.listItems();
    } catch (error) {
      expect(String(error)).not.toContain(apiKey);
    }
  });

  it('honors Retry-After and Backoff with cancellable waiting', async () => {
    const wait = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 429, headers: { 'Retry-After': '3' } }))
      .mockResolvedValueOnce(json([], { Backoff: '2' }))
      .mockResolvedValueOnce(json([]));
    const api = new ZoteroApi({ userId, apiKey }, fetcher, wait);
    await api.listItems();
    await api.listCollections();
    expect(wait.mock.calls[0]![0]).toBeGreaterThanOrEqual(2900);
    expect(wait.mock.calls[1]![0]).toBeGreaterThanOrEqual(1900);
  });

  it('stops immediately for cancellation', async () => {
    const controller = new AbortController();
    controller.abort();
    const fetcher = vi.fn();
    await expect(
      new ZoteroApi({ userId, apiKey }, fetcher).listItems(controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('only accepts stored PDF children of the requested parent', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      json([
        item('ATTACH01', {
          itemType: 'attachment',
          parentItem: 'ITEM0001',
          linkMode: 'linked_file',
          contentType: 'application/pdf',
        }),
        item('ATTACH03', {
          itemType: 'attachment',
          parentItem: 'ITEM0001',
          linkMode: 'imported_url',
          contentType: 'application/pdf',
          filename: '../../paper.pdf',
          md5: 'a'.repeat(32),
        }),
        item('ATTACH02', {
          itemType: 'attachment',
          parentItem: 'ITEM0001',
          linkMode: 'imported_file',
          contentType: 'application/pdf',
        }),
        item('ATTACH04', {
          itemType: 'attachment',
          parentItem: 'OTHER001',
          linkMode: 'imported_file',
          contentType: 'application/pdf',
        }),
        item('ATTACH05', {
          itemType: 'attachment',
          parentItem: 'ITEM0001',
          linkMode: 'imported_file',
          contentType: 'text/html',
        }),
      ]),
    );
    const attachments = await new ZoteroApi({ userId, apiKey }, fetcher).listAttachments(
      'ITEM0001',
    );
    expect(attachments.map((a) => a.key)).toEqual(['ATTACH02', 'ATTACH03']);
    expect(selectStoredPdf(attachments)?.key).toBe('ATTACH02');
    expect(attachments[1]!.filename).toBe('paper.pdf');
  });

  it('preserves hierarchy and contains malformed cycles without recursion', () => {
    const tree = buildCollectionTree([
      { key: 'PARENT01', name: 'Parent', version: 1, parentKey: null },
      { key: 'CHILD001', name: 'Child', version: 1, parentKey: 'PARENT01' },
      { key: 'ORPHAN01', name: 'Orphan', version: 1, parentKey: 'MISSING1' },
      { key: 'CYCLE001', name: 'Cycle A', version: 1, parentKey: 'CYCLE002' },
      { key: 'CYCLE002', name: 'Cycle B', version: 1, parentKey: 'CYCLE001' },
    ]);
    expect(tree.find((n) => n.key === 'PARENT01')?.children[0]?.key).toBe('CHILD001');
    expect(JSON.stringify(tree)).toContain('ORPHAN01');
    expect(JSON.stringify(tree).match(/CYCLE001/g)).toHaveLength(2); // key + the other's parentKey
  });
});

describe('Zotero PDF download', () => {
  const attachment = {
    key: 'ATTACH01',
    parentKey: 'ITEM0001',
    version: 2,
    filename: 'paper.pdf',
    md5: null,
  };
  it('uses the official attachment endpoint with redirect-safe auth and progress', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response('%PDF-1.7', { headers: { 'Content-Length': '8' } }));
    const progress = vi.fn();
    const bytes = await new ZoteroApi({ userId, apiKey }, fetcher).download(
      attachment,
      undefined,
      progress,
    );
    expect(new TextDecoder().decode(bytes)).toBe('%PDF-1.7');
    expect(progress).toHaveBeenLastCalledWith({ received: 8, total: 8 });
    expect(fetcher).toHaveBeenCalledWith(
      'https://api.zotero.org/users/12345/items/ATTACH01/file',
      expect.objectContaining({
        method: 'GET',
        redirect: 'follow',
        credentials: 'omit',
        headers: { 'Zotero-API-Version': '3', Authorization: `Bearer ${apiKey}` },
      }),
    );
  });
  it('cancels a blocked response reader without publishing a partial download', async () => {
    const controller = new AbortController();
    const cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({
      start(source) {
        source.enqueue(new TextEncoder().encode('%PDF-1.7'));
      },
      cancel,
    });
    const fetcher = vi.fn().mockResolvedValue(new Response(stream));
    const download = new ZoteroApi({ userId, apiKey }, fetcher).download(
      attachment,
      controller.signal,
      () => controller.abort(),
    );
    await expect(download).rejects.toMatchObject({ name: 'AbortError' });
    expect(cancel).toHaveBeenCalled();
  });
  it('reports a truncated response and a missing Zotero Storage file', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response('%PDF-1.7', { headers: { 'Content-Length': '100' } }))
      .mockResolvedValueOnce(new Response('', { status: 404 }));
    const api = new ZoteroApi({ userId, apiKey }, fetcher);
    await expect(api.download(attachment)).rejects.toMatchObject({ code: 'network' });
    await expect(api.download(attachment)).rejects.toMatchObject({ code: 'not-found' });
  });
  it('rejects mismatched storage ETag before reading the file', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response('%PDF-1.7', { headers: { ETag: `"${'b'.repeat(32)}"` } }));
    await expect(
      new ZoteroApi({ userId, apiKey }, fetcher).download({ ...attachment, md5: 'a'.repeat(32) }),
    ).rejects.toMatchObject({ code: 'invalid-data' });
  });
});
