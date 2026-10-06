import { stubTranslation as _ } from '@/utils/misc';
import type { ExternalLibraryStorage } from '../externalLibrary/types';
import { checkCancelled, object, validateUserId, ZoteroError, type ZoteroCredentials } from './api';
import { ZOTERO_ROOT } from './cache';

export interface ZoteroSecureStore {
  available(): Promise<boolean>;
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}
export interface ZoteroAccount {
  userId: string | null;
  mode: 'secure' | 'session';
  connected: boolean;
}
interface SavedAccount {
  userId: string;
  storage: 'secure' | 'session';
}
const accountPath = `${ZOTERO_ROOT}/account.json`;
const secretKey = (userId: string) => `readest.zotero.${validateUserId(userId)}.api-key`;

/** Ordinary persistence stores only a user ID and storage policy, never a key. */
export class ZoteroCredentialsStore {
  private session = new Map<string, string>();
  private pending: Promise<void> = Promise.resolve();
  constructor(
    private readonly storage: ExternalLibraryStorage,
    private readonly secure: ZoteroSecureStore,
  ) {}

  private async readAccount(): Promise<SavedAccount | null> {
    const bytes = await this.storage.read(accountPath);
    if (!bytes) return null;
    try {
      const raw = object(JSON.parse(new TextDecoder().decode(bytes)) as unknown);
      if (
        typeof raw['userId'] !== 'string' ||
        !['secure', 'session'].includes(String(raw['storage']))
      )
        return null;
      return {
        userId: validateUserId(raw['userId']),
        storage: raw['storage'] as 'secure' | 'session',
      };
    } catch {
      return null;
    }
  }

  private async available(): Promise<boolean> {
    try {
      return await this.secure.available();
    } catch {
      return false;
    }
  }

  private enqueue<T>(work: () => Promise<T>): Promise<T> {
    const result = this.pending.then(work);
    this.pending = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  }

  private async readCredentials(account: SavedAccount | null): Promise<ZoteroCredentials | null> {
    if (!account) return null;
    const inSession = this.session.get(account.userId);
    if (inSession) return { userId: account.userId, apiKey: inSession };
    if (account.storage !== 'secure' || !(await this.available())) return null;
    try {
      const apiKey = await this.secure.get(secretKey(account.userId));
      return apiKey ? { userId: account.userId, apiKey } : null;
    } catch {
      return null;
    }
  }

  getCredentials(): Promise<ZoteroCredentials | null> {
    return this.enqueue(async () => this.readCredentials(await this.readAccount()));
  }

  getAccount(): Promise<ZoteroAccount> {
    return this.enqueue(async () => {
      const account = await this.readAccount();
      const available = await this.available();
      return {
        userId: account?.userId ?? null,
        mode: account?.storage === 'session' || !available ? 'session' : 'secure',
        connected: !!(await this.readCredentials(account)),
      };
    });
  }

  /** Queue readers and writers together: no caller can observe an uncommitted key. */
  private async transaction<T>(
    signal: AbortSignal | undefined,
    work: (transaction: {
      previous: SavedAccount | null;
      setSecret(key: string, value: string): Promise<void>;
      removeSecret(key: string): Promise<void>;
      restoreSecret(key: string): Promise<void>;
      writeAccount(account: SavedAccount): Promise<void>;
    }) => Promise<T>,
  ): Promise<T> {
    checkCancelled(signal);
    const previousBytes = await this.storage.read(accountPath);
    const previous = await this.readAccount();
    checkCancelled(signal);
    const backups = new Map<string, string | null>();
    const changed = new Set<string>();
    let accountChanged = false;
    const remember = async (key: string) => {
      if (!backups.has(key)) backups.set(key, await this.secure.get(key));
      checkCancelled(signal);
    };
    const restoreSecret = async (key: string) => {
      if (!changed.has(key)) return;
      const value = backups.get(key);
      if (value == null) await this.secure.remove(key);
      else await this.secure.set(key, value);
      changed.delete(key);
    };
    try {
      return await work({
        previous,
        setSecret: async (key, value) => {
          checkCancelled(signal);
          await remember(key);
          // Mark before awaiting: a rejected native call may already have written.
          changed.add(key);
          await this.secure.set(key, value);
          checkCancelled(signal);
        },
        removeSecret: async (key) => {
          checkCancelled(signal);
          await remember(key);
          changed.add(key);
          await this.secure.remove(key);
          checkCancelled(signal);
        },
        restoreSecret,
        writeAccount: async (account) => {
          checkCancelled(signal);
          accountChanged = true;
          await this.storage.write(
            accountPath,
            new TextEncoder().encode(JSON.stringify(account)).buffer,
          );
          checkCancelled(signal);
        },
      });
    } catch (error) {
      let failed = false;
      for (const key of [...changed].reverse()) {
        try {
          await restoreSecret(key);
        } catch {
          failed = true;
        }
      }
      if (accountChanged) {
        try {
          if (previousBytes) await this.storage.write(accountPath, previousBytes);
          else await this.storage.remove(accountPath);
        } catch {
          failed = true;
        }
      }
      if (failed)
        throw new ZoteroError(
          'storage',
          _(
            'Could not restore the previous Zotero connection. Unlock the system keychain and check local storage before trying again',
          ),
        );
      throw error;
    }
  }

  save(credentials: ZoteroCredentials, signal?: AbortSignal): Promise<ZoteroAccount> {
    return this.enqueue(async () => {
      const userId = validateUserId(credentials.userId);
      if (
        !credentials.apiKey ||
        credentials.apiKey.length > 256 ||
        /[\s\x00-\x1f\x7f]/.test(credentials.apiKey)
      ) {
        throw new ZoteroError(
          'authentication',
          _('Enter a Zotero API key with library and file read access'),
        );
      }
      return this.transaction(signal, async (transaction) => {
        const { previous } = transaction;
        let mode: 'secure' | 'session' = 'session';
        if (await this.available()) {
          try {
            await transaction.setSecret(secretKey(userId), credentials.apiKey);
            mode = 'secure';
          } catch {
            checkCancelled(signal);
            // Only fall back after undoing any partially successful secure write.
            await transaction.restoreSecret(secretKey(userId));
          }
        }
        if (previous?.storage === 'secure' && (previous.userId !== userId || mode === 'session')) {
          try {
            await transaction.removeSecret(secretKey(previous.userId));
          } catch {
            checkCancelled(signal);
            throw new ZoteroError(
              'storage',
              _(
                'Could not remove the previous Zotero key. Unlock the system keychain and try again',
              ),
            );
          }
        }
        await transaction.writeAccount({ userId, storage: mode });
        // No asynchronous work after this commit boundary. Cancellation during
        // either persistence operation above restores both metadata and secrets.
        this.session = new Map([[userId, credentials.apiKey]]);
        return { userId, mode, connected: true };
      });
    });
  }

  disconnect(): Promise<void> {
    return this.enqueue(() =>
      this.transaction(undefined, async (transaction) => {
        const account = transaction.previous;
        if (!account) return;
        if (account.storage === 'secure') {
          try {
            await transaction.removeSecret(secretKey(account.userId));
          } catch {
            throw new ZoteroError(
              'storage',
              _('Could not remove the saved Zotero key. Unlock the system keychain and try again'),
            );
          }
        }
        await transaction.writeAccount({ userId: account.userId, storage: 'session' });
        this.session.clear();
      }),
    );
  }
}
