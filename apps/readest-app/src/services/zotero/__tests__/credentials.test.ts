// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ZoteroCredentialsStore } from '../credentials';
import type { ExternalLibraryStorage } from '../../externalLibrary/types';

const fixture = () => {
  const files = new Map<string, ArrayBuffer>();
  const storage: ExternalLibraryStorage = {
    exists: async (path) => files.has(path),
    read: async (path) => files.get(path) ?? null,
    write: vi.fn(async (path, bytes) => {
      files.set(path, bytes);
    }),
    remove: vi.fn(async (path) => {
      files.delete(path);
    }),
  };
  const text = () => [...files.values()].map((b) => new TextDecoder().decode(b)).join('');
  return { storage, files, text };
};

const ACCOUNT = 'external-library/zotero/account.json';

describe('Zotero credentials', () => {
  it('persists the API key locally under the Zotero Data tree so it survives a restart', async () => {
    const { storage, files } = fixture();
    const credentials = new ZoteroCredentialsStore(storage);
    expect(await credentials.save({ userId: '12345', apiKey: 'test-secret' })).toEqual({
      userId: '12345',
      connected: true,
    });
    expect([...files.keys()]).toEqual([ACCOUNT]);
    expect(await new ZoteroCredentialsStore(storage).getCredentials()).toEqual({
      userId: '12345',
      apiKey: 'test-secret',
    });
  });

  it('rejects an empty or control-character API key before writing', async () => {
    const { storage, files } = fixture();
    const credentials = new ZoteroCredentialsStore(storage);
    await expect(credentials.save({ userId: '12345', apiKey: '' })).rejects.toMatchObject({
      code: 'authentication',
    });
    await expect(credentials.save({ userId: '12345', apiKey: 'bad key' })).rejects.toMatchObject({
      code: 'authentication',
    });
    expect(files.size).toBe(0);
  });

  it('disconnect drops the key but keeps the user ID for offline browsing', async () => {
    const { storage } = fixture();
    const credentials = new ZoteroCredentialsStore(storage);
    await credentials.save({ userId: '12345', apiKey: 'test-secret' });
    await credentials.disconnect();
    expect(await credentials.getCredentials()).toBeNull();
    const account = await new ZoteroCredentialsStore(storage).getAccount();
    expect(account).toEqual({ userId: '12345', connected: false });
  });

  it('replaces the previous account key on reconnect', async () => {
    const { storage } = fixture();
    const credentials = new ZoteroCredentialsStore(storage);
    await credentials.save({ userId: '12345', apiKey: 'first-secret' });
    await credentials.save({ userId: '67890', apiKey: 'second-secret' });
    expect(await credentials.getCredentials()).toEqual({
      userId: '67890',
      apiKey: 'second-secret',
    });
  });

  it('restores the prior account when the write is cancelled before commit', async () => {
    const { storage } = fixture();
    const credentials = new ZoteroCredentialsStore(storage);
    await credentials.save({ userId: '12345', apiKey: 'old-secret' });
    const write = storage.write;
    const controller = new AbortController();
    storage.write = vi.fn(async (path, bytes) => {
      await write(path, bytes);
      controller.abort();
    });
    await expect(
      credentials.save({ userId: '67890', apiKey: 'new-secret' }, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    // The rejected save restored the previous file: old account still usable.
    expect(await credentials.getCredentials()).toEqual({ userId: '12345', apiKey: 'old-secret' });
  });
});
