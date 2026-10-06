// @vitest-environment node
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import type { AppService } from '@/types/system';
import type { ExternalLibraryStorage } from '../../externalLibrary/types';
import { createZoteroStorage, ZoteroRuntime } from '../runtime';

vi.mock('@/services/environment', () => ({ isTauriAppPlatform: () => false }));
const storeFixture = () => {
  const files = new Map<string, ArrayBuffer>();
  const storage: ExternalLibraryStorage = {
    exists: async (name) => files.has(name),
    read: async (name) => files.get(name) ?? null,
    write: async (name, bytes) => {
      files.set(name, bytes);
    },
    remove: async (name) => {
      files.delete(name);
    },
  };
  const secure = { available: async () => false, get: vi.fn(), set: vi.fn(), remove: vi.fn() };
  return { storage, secure, files };
};

describe('Zotero runtime boundary', () => {
  it('persists all metadata and PDFs only in the provider Data subtree', async () => {
    const service = {
      exists: vi.fn().mockResolvedValue(true),
      readFile: vi.fn().mockResolvedValue(new ArrayBuffer(4)),
      writeFile: vi.fn(),
      deleteFile: vi.fn(),
      createDir: vi.fn(),
    } satisfies Pick<AppService, 'exists' | 'readFile' | 'writeFile' | 'deleteFile' | 'createDir'>;
    const storage = createZoteroStorage(service);
    const name = 'external-library/zotero/12345/pdfs/ITEM0001/ATTACH01-1-abc.pdf';
    await storage.write(name, new ArrayBuffer(4));
    await storage.read(name);
    await storage.remove(name);
    expect(service.writeFile).toHaveBeenCalledWith(name, 'Data', expect.any(ArrayBuffer));
    expect(service.deleteFile).toHaveBeenCalledWith(name, 'Data');
    expect(service.createDir).toHaveBeenCalledWith(
      'external-library/zotero/12345/pdfs/ITEM0001',
      'Data',
      true,
    );
    await expect(
      storage.write('external-library/zotero/../../Books/file', new ArrayBuffer(0)),
    ).rejects.toThrow();
    await expect(storage.read('Books/normal-book.epub')).rejects.toThrow();
    expect(service.writeFile).toHaveBeenCalledTimes(1);
  });

  it('notifies settings listeners and restores offline provider without a session key after restart', async () => {
    const { storage, secure, files } = storeFixture();
    const fetcher = vi.fn().mockResolvedValue(new Response('[]'));
    const runtime = new ZoteroRuntime(storage, secure, fetcher);
    const listener = vi.fn();
    const unsubscribe = runtime.subscribe(listener);
    await runtime.connect({ userId: '12345', apiKey: 'test-secret' });
    expect(listener).toHaveBeenCalledTimes(1);
    expect((await runtime.load()).account.connected).toBe(true);
    const offline = await new ZoteroRuntime(storage, secure, vi.fn()).load();
    expect(offline.provider?.userId).toBe('12345');
    expect(offline.account.connected).toBe(false);
    expect(
      [...files.values()].map((value) => new TextDecoder().decode(value)).join(''),
    ).not.toContain('test-secret');
    unsubscribe();
    await runtime.disconnect();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('does not replace a working account if validation is denied or cancelled', async () => {
    const { storage, secure } = storeFixture();
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response('[]')));
    const runtime = new ZoteroRuntime(storage, secure, fetcher);
    await runtime.connect({ userId: '12345', apiKey: 'working-secret' });
    fetcher.mockResolvedValueOnce(new Response('Unauthorized', { status: 403 }));
    await expect(runtime.connect({ userId: '67890', apiKey: 'bad-secret' })).rejects.toMatchObject({
      code: 'authentication',
    });
    expect((await runtime.load()).account.userId).toBe('12345');
    const controller = new AbortController();
    controller.abort();
    await expect(
      runtime.connect({ userId: '67890', apiKey: 'other-secret' }, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect((await runtime.load()).account.userId).toBe('12345');
  });

  it('has no normal-book/import/upload/sync service dependency or remote mutation path', () => {
    const sourceRoot = path.resolve(import.meta.dirname, '..');
    for (const name of readdirSync(sourceRoot).filter((name) => name.endsWith('.ts'))) {
      const source = readFileSync(path.join(sourceRoot, name), 'utf8');
      expect(source).not.toMatch(
        /from\s+['"][^'"]*(?:bookService|ingestService|libraryStore|cloudService|services\/sync|types\/book)/,
      );
      expect(source).not.toMatch(
        /\b(?:importBook|ingestFile|updateBooks|uploadBook|uploadFile)\s*\(/,
      );
      expect(source).not.toMatch(/method:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/);
      expect(source).not.toMatch(/localStorage|sessionStorage/);
    }
  });
});

it('serializes an asynchronous load with account replacement without a wrong-user API', async () => {
  const { storage, secure } = storeFixture();
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response('[]')));
  const runtime = new ZoteroRuntime(storage, secure, fetcher);
  await runtime.connect({ userId: '12345', apiKey: 'first-secret' });
  const read = storage.read;
  let count = 0;
  let release: (() => void) | undefined;
  storage.read = async (name) => {
    const bytes = await read(name);
    if (++count === 2)
      await new Promise<void>((resolve) => {
        release = resolve;
      });
    return bytes;
  };
  const pending = runtime.load();
  await vi.waitFor(() => expect(release).toBeDefined());
  const replacing = runtime.connect({ userId: '67890', apiKey: 'second-secret' });
  release?.();
  await pending;
  await replacing;
  const loaded = await runtime.load();
  expect(loaded.account.connected).toBe(true);
  await loaded.provider?.refresh();
  expect(String(fetcher.mock.lastCall?.[0])).toContain('/users/67890/');
});

it('does not connect or notify when cancelled during account persistence', async () => {
  const { storage, secure, files } = storeFixture();
  const runtime = new ZoteroRuntime(storage, secure, async () => new Response('[]'));
  const listener = vi.fn();
  runtime.subscribe(listener);
  let release: (() => void) | undefined;
  const write = storage.write;
  storage.write = async (path, bytes) => {
    await new Promise<void>((resolve) => {
      release = resolve;
    });
    await write(path, bytes);
  };
  const controller = new AbortController();
  const pending = runtime.connect({ userId: '12345', apiKey: 'new-secret' }, controller.signal);
  const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  await vi.waitFor(() => expect(release).toBeDefined());
  controller.abort();
  release?.();
  await rejection;
  expect(listener).not.toHaveBeenCalled();
  expect((await runtime.load()).account.connected).toBe(false);
  expect(files.size).toBe(0);
});
