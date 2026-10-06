// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from 'vitest';

type Route = { matcher: (args: { url: URL; request: Request }) => boolean; handler: unknown };
const fixture = vi.hoisted(() => ({ routes: [] as Route[] }));
vi.mock('serwist', () => ({
  NetworkFirst: class NetworkFirst {},
  CacheFirst: class CacheFirst {},
  NetworkOnly: class NetworkOnly {},
  ExpirationPlugin: class ExpirationPlugin {},
  Serwist: class {
    constructor(options: { runtimeCaching: Route[] }) {
      fixture.routes = options.runtimeCaching;
    }
    addEventListeners() {}
  },
}));

beforeEach(async () => {
  vi.resetModules();
  vi.stubGlobal('self', { __SW_MANIFEST: [] });
  await import('@/sw');
});

describe('service worker private request boundary', () => {
  it.each([
    ['https://api.zotero.org/users/12345/items/top', {}],
    [
      'https://api.zotero.org/users/12345/items/ATTACH01/file',
      { headers: { Authorization: 'Bearer mock-key' } },
    ],
    ['https://storage.example.invalid/paper.pdf', { cache: 'no-store' as RequestCache }],
    ['https://example.invalid/private', { headers: { Authorization: 'Bearer mock-key' } }],
  ])('never caches private request %s in a catch-all strategy', (url, init) => {
    const request = new Request(url, init);
    const route = fixture.routes.find((entry) => entry.matcher({ url: new URL(url), request }));
    expect(route?.handler?.constructor.name).toBe('NetworkOnly');
  });
  it('keeps ordinary public font caching', () => {
    const url = 'https://fonts.example.invalid/font.woff2';
    const request = new Request(url);
    const route = fixture.routes.find((entry) => entry.matcher({ url: new URL(url), request }));
    expect(route?.handler?.constructor.name).toBe('CacheFirst');
  });
});
