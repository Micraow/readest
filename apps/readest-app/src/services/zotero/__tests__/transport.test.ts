// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { createNativeZoteroFetch } from '../transport';

describe('native Zotero download transport', () => {
  it('follows a storage redirect only after removing all API credentials', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('', {
          status: 302,
          headers: { Location: 'https://zoterofilestorage.s3.amazonaws.com/file?signature=test' },
        }),
      )
      .mockResolvedValueOnce(new Response('%PDF-1.7'));
    const transport = createNativeZoteroFetch(fetcher);
    await transport('https://api.zotero.org/users/12345/items/ATTACH01/file', {
      method: 'GET',
      redirect: 'follow',
      headers: { Authorization: 'Bearer secret', 'Zotero-API-Key': 'secret' },
    });
    expect(fetcher.mock.calls[0]![1].maxRedirections).toBe(0);
    expect(new Headers(fetcher.mock.calls[1]![1].headers).get('Cookie')).toBe('');
    expect(new Headers(fetcher.mock.calls[1]![1].headers).has('Authorization')).toBe(false);
    expect(JSON.stringify(fetcher.mock.calls[1])).not.toContain('secret');
    expect(fetcher.mock.calls[1]![1].method).toBe('GET');
  });
  it('rejects non-HTTPS storage redirects', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response('', { status: 302, headers: { Location: 'http://attacker.invalid/file' } }),
      );
    await expect(
      createNativeZoteroFetch(fetcher)('https://api.zotero.org/users/12345/items/ATTACH01/file', {
        redirect: 'follow',
      }),
    ).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('does not follow metadata redirects or accept an arbitrary initial origin', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response('', { status: 302, headers: { Location: 'https://attacker.invalid/file' } }),
      );
    const transport = createNativeZoteroFetch(fetcher);
    await expect(
      transport('https://api.zotero.org/users/12345/items/top', { redirect: 'error' }),
    ).rejects.toThrow();
    await expect(
      transport('https://attacker.invalid/file', { headers: { Authorization: 'Bearer secret' } }),
    ).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});

it('suppresses a seeded ambient cookie jar on every native redirect hop', async () => {
  const jar = new Map([
    ['api.zotero.org', 'zotero_session=private'],
    ['storage.example', 'storage_session=private'],
    ['cdn.example', 'cdn_session=private'],
  ]);
  const observed: { host: string; cookie: string | null; authorization: string | null }[] = [];
  const fetcher = vi.fn(async (url: string, options: RequestInit & { maxRedirections: number }) => {
    const host = new URL(url).host;
    const headers = new Headers(options.headers);
    // Matches reqwest 0.12.28 CookieService: fill only if Cookie is absent.
    if (!headers.has('Cookie')) headers.set('Cookie', jar.get(host) ?? '');
    observed.push({
      host,
      cookie: headers.get('Cookie'),
      authorization: headers.get('Authorization'),
    });
    if (host === 'api.zotero.org')
      return new Response('', {
        status: 302,
        headers: { Location: 'https://storage.example/file' },
      });
    if (host === 'storage.example')
      return new Response('', { status: 307, headers: { Location: 'https://cdn.example/file' } });
    return new Response('%PDF-1.7');
  });
  await createNativeZoteroFetch(fetcher)('https://api.zotero.org/users/12345/items/ATTACH01/file', {
    redirect: 'follow',
    headers: { Authorization: 'Bearer fake-key', Cookie: 'must-not-send=private' },
  });
  expect(observed).toEqual([
    { host: 'api.zotero.org', cookie: '', authorization: 'Bearer fake-key' },
    { host: 'storage.example', cookie: '', authorization: null },
    { host: 'cdn.example', cookie: '', authorization: null },
  ]);
  expect(fetcher.mock.calls.every(([, options]) => options.maxRedirections === 0)).toBe(true);
});

it('rejects unsafe later redirects and bounds redirect loops', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response('', { status: 302, headers: { Location: 'https://storage.example/file' } }),
    )
    .mockResolvedValueOnce(
      new Response('', { status: 302, headers: { Location: 'http://storage.example/file' } }),
    );
  await expect(
    createNativeZoteroFetch(fetcher)('https://api.zotero.org/users/12345/items/ATTACH01/file', {
      redirect: 'follow',
    }),
  ).rejects.toThrow();
  expect(fetcher).toHaveBeenCalledTimes(2);
  const loop = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(
        new Response('', { status: 302, headers: { Location: 'https://storage.example/loop' } }),
      ),
    );
  await expect(
    createNativeZoteroFetch(loop)('https://api.zotero.org/users/12345/items/ATTACH01/file', {
      redirect: 'follow',
    }),
  ).rejects.toThrow();
  expect(loop.mock.calls.length).toBeLessThanOrEqual(6);
});
