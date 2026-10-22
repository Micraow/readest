// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { md5 } from 'js-md5';
import type {
  ExternalAttachment,
  ExternalItem,
  ExternalLibraryStorage,
} from '../../externalLibrary/types';
import { ZoteroCache } from '../cache';
import { ZoteroProvider } from '../provider';

const item: ExternalItem = {
  key: 'ITEM0001',
  version: 7,
  title: 'A paper',
  authors: ['A. Author'],
  year: '2025',
  venue: 'Journal',
  collectionKeys: [],
};
const pdf = new TextEncoder().encode('%PDF-1.7\n%mock fixture\n%%EOF').buffer;
const attachment: ExternalAttachment = {
  key: 'ATTACH01',
  parentKey: item.key,
  version: 8,
  filename: 'paper.pdf',
  md5: md5(pdf),
};
const createStore = () => {
  const files = new Map<string, ArrayBuffer>();
  const store: ExternalLibraryStorage = {
    read: vi.fn(async (path) => files.get(path) ?? null),
    write: vi.fn(async (path, data) => {
      files.set(path, data);
    }),
    remove: vi.fn(async (path) => {
      files.delete(path);
    }),
    exists: vi.fn(async (path) => files.has(path)),
  };
  return { store, files };
};
const createApi = () => ({
  listCollections: vi.fn().mockResolvedValue([]),
  listItems: vi.fn().mockResolvedValue([item]),
  listAttachments: vi.fn().mockResolvedValue([attachment]),
  download: vi.fn().mockResolvedValue(pdf),
});

describe('Zotero local materialization', () => {
  it('only fetches PDF bytes when opening and reopens durably without credentials or network', async () => {
    const { store, files } = createStore();
    const api = createApi();
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api);
    const snapshot = await provider.refresh();
    expect(snapshot.items).toEqual([item]);
    expect(api.download).not.toHaveBeenCalled();
    const first = await provider.open(item);
    expect(first.file.type).toBe('application/pdf');
    expect(first.resumeKey).toBe('zotero:12345:ITEM0001:ATTACH01');
    expect(await first.file.arrayBuffer()).toEqual(pdf);
    expect(await provider.hasLocal(item.key)).toBe(true);
    expect(
      [...files.keys()].every((path) => path.startsWith('external-library/zotero/12345/')),
    ).toBe(true);
    const offline = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => null);
    expect((await offline.loadCached())?.items).toEqual([item]);
    expect(await (await offline.open(item)).file.arrayBuffer()).toEqual(pdf);
    expect(api.download).toHaveBeenCalledTimes(1);
  });

  it('clears only local PDF and record while retaining remote-owned metadata', async () => {
    const { store, files } = createStore();
    const api = createApi();
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api);
    await provider.refresh();
    await provider.open(item);
    await provider.clearLocal(item.key);
    expect(await provider.hasLocal(item.key)).toBe(false);
    expect((await provider.loadCached())?.items).toEqual([item]);
    expect([...files.keys()]).toEqual(['external-library/zotero/12345/library.json']);
    expect(api.download).toHaveBeenCalledTimes(1);
  });

  it('does not publish a cancelled download, including cancellation during local write', async () => {
    const { store, files } = createStore();
    const controller = new AbortController();
    const originalWrite = store.write;
    store.write = async (path, bytes) => {
      await originalWrite(path, bytes);
      if (path.endsWith('.pdf')) controller.abort();
    };
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () =>
      createApi(),
    );
    await expect(provider.open(item, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(await provider.hasLocal(item.key)).toBe(false);
    expect([...files.keys()]).toEqual([]);
  });

  it('rejects non-PDF responses and checksum mismatch before publishing', async () => {
    const { store, files } = createStore();
    const api = createApi();
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api);
    api.download.mockResolvedValueOnce(new TextEncoder().encode('<html>Error</html>').buffer);
    await expect(provider.open(item)).rejects.toMatchObject({ code: 'invalid-data' });
    api.download.mockResolvedValueOnce(new TextEncoder().encode('%PDF-1.7\nchanged bytes').buffer);
    await expect(provider.open(item)).rejects.toMatchObject({ code: 'invalid-data' });
    expect(files.size).toBe(0);
  });

  it('keeps users isolated and validates every cache path segment', async () => {
    const { store } = createStore();
    const first = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => createApi());
    await first.open(item);
    const other = new ZoteroProvider('67890', new ZoteroCache(store, '67890'), () => null);
    expect(await other.hasLocal(item.key)).toBe(false);
    await expect(other.clearLocal('../bad')).rejects.toThrow();
    expect(() => new ZoteroCache(store, '../../Books')).toThrow();
  });

  it('ignores corrupt metadata and never trusts paths in local records', async () => {
    const { store, files } = createStore();
    const cache = new ZoteroCache(store, '12345');
    files.set(
      'external-library/zotero/12345/library.json',
      new TextEncoder().encode('{broken').buffer,
    );
    expect(await cache.readSnapshot()).toBe(null);
    files.set(
      'external-library/zotero/12345/items/ITEM0001.json',
      new TextEncoder().encode(
        JSON.stringify({
          schema: 1,
          provider: 'zotero',
          userId: '12345',
          itemKey: 'ITEM0001',
          path: '../../Books/something',
          attachment: { key: '../bad' },
        }),
      ).buffer,
    );
    expect(await cache.readLocal(item.key)).toBe(null);
    await cache.clearLocal(item.key);
    expect(
      [...files.keys()].every((path) => path.startsWith('external-library/zotero/12345/')),
    ).toBe(true);
  });

  it('does not lose a good cached library after a failed refresh', async () => {
    const { store } = createStore();
    const api = createApi();
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api);
    await provider.refresh();
    api.listItems.mockRejectedValueOnce(new Error('Offline'));
    await expect(provider.refresh()).rejects.toThrow();
    expect((await provider.loadCached())?.items).toEqual([item]);
  });

  it('reports an actionable missing stored PDF without caching a fake document', async () => {
    const { store } = createStore();
    const api = createApi();
    api.listAttachments.mockResolvedValue([]);
    await expect(
      new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api).open(item),
    ).rejects.toMatchObject({ code: 'no-pdf' });
    expect(api.download).not.toHaveBeenCalled();
  });
});

describe('Zotero concurrent download boundary', () => {
  it('coalesces repeated opens and clearing cancels the in-flight transfer before deletion', async () => {
    const { store, files } = createStore();
    const api = createApi();
    let finish: ((bytes: ArrayBuffer) => void) | undefined;
    api.download.mockImplementation(
      () =>
        new Promise<ArrayBuffer>((resolve) => {
          finish = resolve;
        }),
    );
    const provider = new ZoteroProvider('12345', new ZoteroCache(store, '12345'), () => api);
    const first = provider.open(item);
    const second = provider.open(item);
    const results = Promise.allSettled([first, second]);
    await vi.waitFor(() => expect(api.download).toHaveBeenCalledTimes(1));
    const clearing = provider.clearLocal(item.key);
    finish?.(pdf);
    expect((await results).every((result) => result.status === 'rejected')).toBe(true);
    await clearing;
    expect(files.size).toBe(0);
  });

  it('does not delete a good existing PDF if another save is cancelled', async () => {
    const { store } = createStore();
    const cache = new ZoteroCache(store, '12345');
    await cache.saveLocal(item, attachment, pdf);
    const controller = new AbortController();
    controller.abort();
    await expect(cache.saveLocal(item, attachment, pdf, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(await (await cache.readLocal(item.key))?.file.arrayBuffer()).toEqual(pdf);
  });
});
