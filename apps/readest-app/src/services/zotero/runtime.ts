import { stubTranslation as _ } from '@/utils/misc';
import type { AppService } from '@/types/system';
import type { ExternalLibraryStorage } from '../externalLibrary/types';
import { isTauriAppPlatform } from '@/services/environment';
import {
  checkCancelled,
  ZoteroApi,
  ZoteroError,
  type ZoteroCredentials,
  type ZoteroFetch,
} from './api';
import { ZoteroCache, ZOTERO_ROOT } from './cache';
import { ZoteroCredentialsStore, type ZoteroAccount, type ZoteroSecureStore } from './credentials';
import { ZoteroProvider } from './provider';
import { createNativeZoteroFetch } from './transport';

/** Only the durable Data subtree is exposed, never Books or the upload pipeline. */
export function createZoteroStorage(
  service: Pick<AppService, 'exists' | 'readFile' | 'writeFile' | 'deleteFile' | 'createDir'>,
): ExternalLibraryStorage {
  const validatePath = (path: string) => {
    if (
      !path.startsWith(`${ZOTERO_ROOT}/`) ||
      !path
        .split('/')
        .every((part) => /^[a-zA-Z0-9._-]+$/.test(part) && part !== '.' && part !== '..')
    )
      throw new ZoteroError('storage', _('Invalid Zotero cache path'));
    return path;
  };
  return {
    exists: (path) => service.exists(validatePath(path), 'Data'),
    async read(path) {
      validatePath(path);
      try {
        if (!(await service.exists(path, 'Data'))) return null;
        const bytes = await service.readFile(path, 'Data', 'binary');
        if (typeof bytes === 'string') throw new Error('Invalid binary data');
        return bytes;
      } catch {
        throw new ZoteroError('storage', _('Could not read the local Zotero cache'));
      }
    },
    async write(path, bytes) {
      validatePath(path);
      try {
        await service.createDir(path.slice(0, path.lastIndexOf('/')), 'Data', true);
        await service.writeFile(path, 'Data', bytes);
      } catch {
        throw new ZoteroError(
          'storage',
          _('Could not save the Zotero file locally. Check available storage'),
        );
      }
    },
    async remove(path) {
      validatePath(path);
      try {
        if (await service.exists(path, 'Data')) await service.deleteFile(path, 'Data');
      } catch {
        throw new ZoteroError('storage', _('Could not clear the local Zotero file'));
      }
    },
  };
}

const nativeSecureStore: ZoteroSecureStore = {
  async available() {
    if (!isTauriAppPlatform()) return false;
    const bridge = await import('@/utils/bridge');
    return (await bridge.isSyncKeychainAvailable()).available;
  },
  async get(key) {
    const result = await (await import('@/utils/bridge')).getSecureItem({ key });
    if (result.error) throw new Error('Keychain unavailable');
    return result.value ?? null;
  },
  async set(key, value) {
    const result = await (await import('@/utils/bridge')).setSecureItem({ key, value });
    if (!result.success) throw new Error('Keychain unavailable');
  },
  async remove(key) {
    const result = await (await import('@/utils/bridge')).clearSecureItem({ key });
    if (!result.success) throw new Error('Keychain unavailable');
  },
};

const runtimeFetch: ZoteroFetch = async (url, options) => {
  if (!isTauriAppPlatform()) return fetch(url, options);
  const { fetch: nativeFetch } = await import('@tauri-apps/plugin-http');
  return createNativeZoteroFetch(nativeFetch)(url, options);
};

export class ZoteroRuntime {
  private readonly credentials: ZoteroCredentialsStore;
  private api: ZoteroApi | null = null;
  private apiUserId: string | null = null;
  private providers = new Map<string, ZoteroProvider>();
  private listeners = new Set<() => void>();
  private revision = 0;

  constructor(
    private readonly storage: ExternalLibraryStorage,
    secure: ZoteroSecureStore,
    private readonly fetcher: ZoteroFetch,
  ) {
    this.credentials = new ZoteroCredentialsStore(storage, secure);
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
  private notify(): void {
    for (const listener of this.listeners) listener();
  }

  async load(): Promise<{ account: ZoteroAccount; provider: ZoteroProvider | null }> {
    const revision = this.revision;
    const account = await this.credentials.getAccount();
    const credentials = await this.credentials.getCredentials();
    if (revision !== this.revision) return this.load();
    // Reuse the API instance to preserve Backoff between UI operations.
    if (credentials) {
      if (!this.api || this.apiUserId !== credentials.userId)
        this.api = new ZoteroApi(credentials, this.fetcher);
      this.apiUserId = credentials.userId;
    } else {
      this.api = null;
      this.apiUserId = null;
    }
    let provider: ZoteroProvider | null = null;
    if (account.userId) {
      const userId = account.userId;
      provider =
        this.providers.get(userId) ??
        new ZoteroProvider(userId, new ZoteroCache(this.storage, userId), () =>
          this.apiUserId === userId ? this.api : null,
        );
      this.providers.set(userId, provider);
    }
    return { account, provider };
  }

  async connect(credentials: ZoteroCredentials, signal?: AbortSignal): Promise<ZoteroAccount> {
    const api = new ZoteroApi(credentials, this.fetcher);
    // Check library read access before replacing a working connection. File
    // access is tested only by a user-requested lazy PDF download.
    await api.listCollections(signal);
    checkCancelled(signal);
    const account = await this.credentials.save(credentials, signal);
    this.api = api;
    this.apiUserId = credentials.userId;
    this.revision++;
    this.notify();
    return account;
  }

  async disconnect(): Promise<void> {
    await this.credentials.disconnect();
    this.api = null;
    this.apiUserId = null;
    this.revision++;
    this.notify();
  }
}

const runtimes = new WeakMap<AppService, ZoteroRuntime>();
export function getZoteroRuntime(service: AppService): ZoteroRuntime {
  let runtime = runtimes.get(service);
  if (!runtime) {
    runtime = new ZoteroRuntime(createZoteroStorage(service), nativeSecureStore, runtimeFetch);
    runtimes.set(service, runtime);
  }
  return runtime;
}

/** Never render native/plugin/network exception text that may contain secrets. */
export function zoteroErrorMessage(error: unknown): string {
  return error instanceof ZoteroError
    ? error.message
    : _('The Zotero operation failed. Check your connection and local storage, then try again');
}
