// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { ZoteroCredentialsStore } from '../credentials';
import type { ExternalLibraryStorage } from '../../externalLibrary/types';

const fixture = (available: boolean) => {
  const files = new Map<string, ArrayBuffer>();
  const secrets = new Map<string, string>();
  const storage: ExternalLibraryStorage = {
    exists: async (path) => files.has(path),
    read: async (path) => files.get(path) ?? null,
    write: vi.fn(async (path, bytes) => {
      files.set(path, bytes);
    }),
    remove: async (path) => {
      files.delete(path);
    },
  };
  const secure = {
    available: vi.fn(async () => available),
    get: vi.fn(async (key) => secrets.get(key) ?? null),
    set: vi.fn(async (key, value) => {
      secrets.set(key, value);
    }),
    remove: vi.fn(async (key) => {
      secrets.delete(key);
    }),
  };
  return { storage, secure, files, secrets };
};

describe('Zotero credential isolation', () => {
  it('keeps web fallback only in memory and never serializes its API key', async () => {
    const { storage, secure, files } = fixture(false);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    expect((await credentials.save({ userId: '12345', apiKey: 'test-secret' })).mode).toBe(
      'session',
    );
    expect(await credentials.getCredentials()).toEqual({ userId: '12345', apiKey: 'test-secret' });
    expect(
      [...files.values()].map((bytes) => new TextDecoder().decode(bytes)).join(''),
    ).not.toContain('test-secret');
    const restarted = new ZoteroCredentialsStore(storage, secure);
    expect((await restarted.getAccount()).userId).toBe('12345');
    expect(await restarted.getCredentials()).toBeNull();
    expect(secure.set).not.toHaveBeenCalled();
  });
  it('uses keyed OS storage when available, preserving cached account metadata on disconnect', async () => {
    const { storage, secure, files, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    expect((await credentials.save({ userId: '12345', apiKey: 'test-secret' })).mode).toBe(
      'secure',
    );
    expect(secrets.size).toBe(1);
    expect(await new ZoteroCredentialsStore(storage, secure).getCredentials()).toEqual({
      userId: '12345',
      apiKey: 'test-secret',
    });
    await credentials.disconnect();
    expect(secrets.size).toBe(0);
    expect((await credentials.getAccount()).userId).toBe('12345');
    expect(await credentials.getCredentials()).toBeNull();
    expect(files.size).toBe(1);
  });
  it('explicitly falls back to session-only if a keychain write fails', async () => {
    const { storage, secure } = fixture(true);
    secure.set.mockRejectedValueOnce(new Error('OS unavailable'));
    const credentials = new ZoteroCredentialsStore(storage, secure);
    expect((await credentials.save({ userId: '12345', apiKey: 'test-secret' })).mode).toBe(
      'session',
    );
    expect(await credentials.getCredentials()).toEqual({ userId: '12345', apiKey: 'test-secret' });
    expect(await new ZoteroCredentialsStore(storage, secure).getCredentials()).toBeNull();
  });
  it('does not claim disconnection if secure deletion fails', async () => {
    const { storage, secure } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'test-secret' });
    secure.remove.mockRejectedValueOnce(new Error('OS unavailable'));
    await expect(credentials.disconnect()).rejects.toMatchObject({ code: 'storage' });
    expect(await credentials.getCredentials()).toEqual({ userId: '12345', apiKey: 'test-secret' });
  });
  it('does not read an old keychain secret for an explicitly session-only account', async () => {
    const { storage, secure } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'old-secret' });
    secure.set.mockRejectedValueOnce(new Error('Locked'));
    await credentials.save({ userId: '12345', apiKey: 'new-secret' });
    expect(await new ZoteroCredentialsStore(storage, secure).getCredentials()).toBeNull();
  });
});

describe('replacing a Zotero account', () => {
  it('removes the previous account key before storing a different account', async () => {
    const { storage, secure, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'first-secret' });
    await credentials.save({ userId: '67890', apiKey: 'second-secret' });
    expect([...secrets.values()]).toEqual(['second-secret']);
  });
  it('keeps the previous account if its persisted key cannot be removed', async () => {
    const { storage, secure, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'first-secret' });
    secure.remove.mockRejectedValueOnce(new Error('Locked'));
    await expect(
      credentials.save({ userId: '67890', apiKey: 'second-secret' }),
    ).rejects.toMatchObject({ code: 'storage' });
    expect((await credentials.getAccount()).userId).toBe('12345');
    expect([...secrets.values()]).toEqual(['first-secret']);
  });
});

describe('cancelled credential transactions', () => {
  it.each([
    'account',
    'secure',
    'old-key',
  ] as const)('restores the prior account and key when cancelled during %s persistence', async (step) => {
    const { storage, secure, files, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'old-secret' });
    const before = new Map(files);
    const controller = new AbortController();
    let release: (() => void) | undefined;
    const gate = () =>
      new Promise<void>((resolve) => {
        release = resolve;
      });
    if (step === 'account') {
      const write = storage.write;
      storage.write = vi
        .fn()
        .mockImplementationOnce(async (path: string, bytes: ArrayBuffer) => {
          await write(path, bytes);
          await gate();
        })
        .mockImplementation(write);
    } else if (step === 'secure') {
      const set = secure.set.getMockImplementation()!;
      secure.set.mockImplementationOnce(async (key, value) => {
        await set(key, value);
        await gate();
      });
    } else {
      const remove = secure.remove.getMockImplementation()!;
      secure.remove.mockImplementationOnce(async (key) => {
        await remove(key);
        await gate();
      });
    }
    const pending = credentials.save({ userId: '67890', apiKey: 'new-secret' }, controller.signal);
    const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    await vi.waitFor(() => expect(release).toBeDefined());
    controller.abort();
    release?.();
    await rejection;
    expect(files).toEqual(before);
    expect([...secrets.values()]).toEqual(['old-secret']);
    expect(await new ZoteroCredentialsStore(storage, secure).getCredentials()).toEqual({
      userId: '12345',
      apiKey: 'old-secret',
    });
  });

  it('restores the same account secret after cancellation during replacement', async () => {
    const { storage, secure, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'old-secret' });
    const set = secure.set.getMockImplementation()!;
    const controller = new AbortController();
    secure.set.mockImplementationOnce(async (key, value) => {
      await set(key, value);
      controller.abort();
    });
    await expect(
      credentials.save({ userId: '12345', apiKey: 'new-secret' }, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect([...secrets.values()]).toEqual(['old-secret']);
    expect(await credentials.getCredentials()).toEqual({ userId: '12345', apiKey: 'old-secret' });
  });

  it('removes all new account persistence when the first connection is cancelled', async () => {
    const { storage, secure, files, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    const write = storage.write;
    const controller = new AbortController();
    storage.write = async (path, bytes) => {
      await write(path, bytes);
      controller.abort();
    };
    await expect(
      credentials.save({ userId: '12345', apiKey: 'new-secret' }, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(files.size).toBe(0);
    expect(secrets.size).toBe(0);
    expect((await credentials.getAccount()).connected).toBe(false);
  });

  it('serializes cancelled and successful replacements so rollback cannot clobber newer credentials', async () => {
    const { storage, secure, secrets } = fixture(true);
    const credentials = new ZoteroCredentialsStore(storage, secure);
    await credentials.save({ userId: '12345', apiKey: 'old-secret' });
    const set = secure.set.getMockImplementation()!;
    let release: (() => void) | undefined;
    secure.set.mockImplementationOnce(async (key, value) => {
      await set(key, value);
      await new Promise<void>((resolve) => {
        release = resolve;
      });
    });
    const cancelled = new AbortController();
    const first = credentials.save(
      { userId: '12345', apiKey: 'cancelled-secret' },
      cancelled.signal,
    );
    const rejection = expect(first).rejects.toMatchObject({ name: 'AbortError' });
    await vi.waitFor(() => expect(release).toBeDefined());
    const second = credentials.save({ userId: '67890', apiKey: 'final-secret' });
    cancelled.abort();
    release?.();
    await rejection;
    await second;
    expect([...secrets.values()]).toEqual(['final-secret']);
    expect(await credentials.getCredentials()).toEqual({ userId: '67890', apiKey: 'final-secret' });
  });
});
