import { stubTranslation as _ } from '@/utils/misc';
import type { ExternalLibraryStorage } from '../externalLibrary/types';
import { checkCancelled, object, validateUserId, ZoteroError, type ZoteroCredentials } from './api';
import { ZOTERO_ROOT } from './cache';

export interface ZoteroAccount {
  userId: string | null;
  connected: boolean;
}

/**
 * Zotero credentials live in the same local Data tree as the rest of the
 * library metadata, exactly like OPDS catalog passwords and ABS server tokens:
 * the API key is stored as a plain field at rest and never enters the settings
 * replica, so cloud sync cannot carry it in the clear. The key is validated
 * against Zotero before it is written, so a stored key always works.
 */
interface SavedAccount {
  userId: string;
  apiKey: string | null;
}
const accountPath = `${ZOTERO_ROOT}/account.json`;

const isValidKey = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.length > 0 &&
  value.length <= 256 &&
  !/[\s\x00-\x1f\x7f]/.test(value);

export class ZoteroCredentialsStore {
  private pending: Promise<void> = Promise.resolve();

  constructor(private readonly storage: ExternalLibraryStorage) {}

  private enqueue<T>(work: () => Promise<T>): Promise<T> {
    const result = this.pending.then(work);
    this.pending = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  }

  private async readAccount(): Promise<SavedAccount | null> {
    const bytes = await this.storage.read(accountPath);
    if (!bytes) return null;
    try {
      const raw = object(JSON.parse(new TextDecoder().decode(bytes)) as unknown);
      if (typeof raw['userId'] !== 'string') return null;
      const apiKey = raw['apiKey'];
      return {
        userId: validateUserId(raw['userId']),
        apiKey: isValidKey(apiKey) ? apiKey : null,
      };
    } catch {
      return null;
    }
  }

  private encode(account: SavedAccount): ArrayBuffer {
    return new TextEncoder().encode(JSON.stringify(account)).buffer;
  }

  getCredentials(): Promise<ZoteroCredentials | null> {
    return this.enqueue(async () => {
      const account = await this.readAccount();
      return account?.apiKey ? { userId: account.userId, apiKey: account.apiKey } : null;
    });
  }

  getAccount(): Promise<ZoteroAccount> {
    return this.enqueue(async () => {
      const account = await this.readAccount();
      return { userId: account?.userId ?? null, connected: !!account?.apiKey };
    });
  }

  save(credentials: ZoteroCredentials, signal?: AbortSignal): Promise<ZoteroAccount> {
    return this.enqueue(async () => {
      const userId = validateUserId(credentials.userId);
      if (!isValidKey(credentials.apiKey))
        throw new ZoteroError(
          'authentication',
          _('Enter a Zotero API key with library and file read access'),
        );
      checkCancelled(signal);
      const previous = await this.storage.read(accountPath);
      checkCancelled(signal);
      try {
        await this.storage.write(accountPath, this.encode({ userId, apiKey: credentials.apiKey }));
        checkCancelled(signal);
      } catch (error) {
        // Restore the prior file so a failed or cancelled write never strands
        // the account pointing at a key that was not fully stored.
        try {
          if (previous) await this.storage.write(accountPath, previous);
          else await this.storage.remove(accountPath);
        } catch {
          throw new ZoteroError(
            'storage',
            _(
              'Could not restore the previous Zotero connection. Check local storage before trying again',
            ),
          );
        }
        throw error;
      }
      return { userId, connected: true };
    });
  }

  disconnect(): Promise<void> {
    return this.enqueue(async () => {
      // Drop the key but keep the user ID so the cached library metadata stays
      // browsable offline. A refresh or download prompts for the key again.
      const account = await this.readAccount();
      if (!account) return;
      await this.storage.write(accountPath, this.encode({ userId: account.userId, apiKey: null }));
    });
  }
}
