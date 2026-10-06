// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fetch as nativeFetch } from '@tauri-apps/plugin-http';
import { createNativeZoteroFetch } from '../transport';

const mocks = { invoke: vi.fn() };
afterEach(() => vi.unstubAllGlobals());

it('preserves an explicit empty Cookie through the installed Tauri HTTP JS-to-Rust IPC on every hop', async () => {
  vi.stubGlobal('window', { __TAURI_INTERNALS__: { invoke: mocks.invoke } });
  const requests: { url: string; headers: [string, string][]; maxRedirections: number }[] = [];
  mocks.invoke.mockImplementation(async (command: string, args: Record<string, unknown>) => {
    if (command === 'plugin:http|fetch') {
      requests.push(args['clientConfig'] as (typeof requests)[number]);
      return requests.length;
    }
    if (command === 'plugin:http|fetch_send') {
      const index = Number(args['rid']) - 1;
      return {
        status: index < 2 ? 302 : 200,
        statusText: '',
        url: requests[index]!.url,
        headers:
          index === 0
            ? [['Location', 'https://storage.example/file']]
            : index === 1
              ? [['Location', 'https://cdn.example/file']]
              : [],
        rid: index + 1,
      };
    }
    if (command === 'plugin:http|fetch_read_body') return new Uint8Array([1]);
    if (command === 'plugin:http|fetch_cancel_body') return;
    throw new Error('Unexpected IPC command');
  });
  const response = await createNativeZoteroFetch(nativeFetch)(
    'https://api.zotero.org/users/12345/items/ATTACH01/file',
    { redirect: 'follow', headers: { Authorization: 'Bearer fake-key' } },
  );
  await response.body?.cancel();
  expect(requests).toHaveLength(3);
  for (const [index, request] of requests.entries()) {
    expect(request.maxRedirections).toBe(0);
    const headers = new Headers(request.headers);
    expect(headers.has('Cookie')).toBe(true);
    expect(headers.get('Cookie')).toBe('');
    expect(headers.get('Authorization')).toBe(index === 0 ? 'Bearer fake-key' : null);
  }
});

it('keeps the native feature required to preserve explicit empty Cookie headers', () => {
  const manifest = readFileSync(
    path.resolve(import.meta.dirname, '../../../../src-tauri/Cargo.toml'),
    'utf8',
  );
  expect(manifest).toMatch(/tauri-plugin-http\s*=\s*\{[^}]*"unsafe-headers"/);
});
