import { stubTranslation as _ } from '@/utils/misc';
import { API_ORIGIN, checkCancelled, ZoteroError, type ZoteroFetch } from './api';

type NativeFetch = (
  url: string,
  options: RequestInit & { maxRedirections: number },
) => Promise<Response>;
const redirects = new Set([301, 302, 303, 307, 308]);

/** Native HTTP bypasses browser CORS; enforce explicit credential-free redirects. */
export function createNativeZoteroFetch(fetcher: NativeFetch): ZoteroFetch {
  return async (url, options) => {
    const initial = new URL(url);
    if (initial.origin !== API_ORIGIN || initial.username || initial.password)
      throw new ZoteroError('network', _('Unexpected Zotero request destination'));
    const canRedirect =
      options.redirect === 'follow' &&
      /^\/users\/[1-9]\d*\/items\/[A-Z0-9]{8}\/file$/.test(initial.pathname);
    let current = initial;
    const headers = new Headers(options.headers);
    // Installed plugin-http 2.6 does not pass `credentials` to Rust. This repo
    // enables unsafe-headers, so Cookie survives IPC. reqwest 0.12.28 fills its
    // shared cookie jar only when Cookie is absent, even for an empty value.
    headers.set('Cookie', '');
    for (let hop = 0; hop <= 5; hop++) {
      checkCancelled(options.signal ?? undefined);
      const response = await fetcher(current.href, {
        method: 'GET',
        signal: options.signal,
        headers: hop === 0 ? headers : new Headers({ Cookie: '' }),
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        cache: 'no-store',
        maxRedirections: 0,
      });
      if (options.signal?.aborted) {
        await response.body?.cancel();
        checkCancelled(options.signal);
      }
      if (!redirects.has(response.status)) return response;
      const location = response.headers.get('Location');
      await response.body?.cancel();
      if (!canRedirect || hop === 5)
        throw new ZoteroError('network', _('Unexpected Zotero redirect'));
      if (!location)
        throw new ZoteroError('network', _('Zotero returned an invalid file redirect'));
      let target: URL;
      try {
        target = new URL(location, current);
      } catch {
        throw new ZoteroError('network', _('Zotero returned an invalid file redirect'));
      }
      if (target.protocol !== 'https:' || target.username || target.password)
        throw new ZoteroError('network', _('Zotero returned an unsafe file redirect'));
      // Follow EVERY storage hop manually. Automatic redirects could inject a
      // destination's ambient cookies; neither auth nor caller headers survive.
      current = target;
    }
    throw new ZoteroError('network', _('Unexpected Zotero redirect'));
  };
}
