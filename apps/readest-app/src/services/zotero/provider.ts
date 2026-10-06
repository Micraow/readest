import { stubTranslation as _ } from '@/utils/misc';
import type {
  DownloadProgress,
  ExternalDocument,
  ExternalItem,
  ExternalLibraryProvider,
  ExternalLibrarySnapshot,
} from '../externalLibrary/types';
import {
  checkCancelled,
  selectStoredPdf,
  validateKey,
  validateUserId,
  ZoteroApi,
  ZoteroError,
} from './api';
import { ZoteroCache } from './cache';

export type ZoteroReadApi = Pick<
  ZoteroApi,
  'listCollections' | 'listItems' | 'listAttachments' | 'download'
>;

interface ActiveOpen {
  controller: AbortController;
  promise: Promise<ExternalDocument>;
  progress: Set<(progress: DownloadProgress) => void>;
  cleanup: (() => void)[];
}

export class ZoteroProvider implements ExternalLibraryProvider {
  private opens = new Map<string, ActiveOpen>();
  constructor(
    readonly userId: string,
    private readonly cache: ZoteroCache,
    private readonly getApi: () => ZoteroReadApi | null,
  ) {
    validateUserId(userId);
    if (cache.userId !== userId)
      throw new ZoteroError('invalid-data', _('The Zotero library does not match this account'));
  }

  private requireApi(): ZoteroReadApi {
    const api = this.getApi();
    if (!api)
      throw new ZoteroError(
        'authentication',
        _('Enter your Zotero API key to refresh or download. Saved PDFs remain available offline'),
      );
    return api;
  }

  loadCached(): Promise<ExternalLibrarySnapshot | null> {
    return this.cache.readSnapshot();
  }
  hasLocal(itemKey: string): Promise<boolean> {
    return this.cache.hasLocal(itemKey);
  }
  async clearLocal(itemKey: string): Promise<void> {
    validateKey(itemKey);
    const active = this.opens.get(itemKey);
    if (active) {
      active.controller.abort();
      await active.promise.catch(() => undefined);
    }
    await this.cache.clearLocal(itemKey);
  }

  async refresh(signal?: AbortSignal): Promise<ExternalLibrarySnapshot> {
    const api = this.requireApi();
    // Sequential requests also respect Backoff headers across endpoints.
    const collections = await api.listCollections(signal);
    const items = await api.listItems(signal);
    checkCancelled(signal);
    const snapshot: ExternalLibrarySnapshot = {
      schema: 1,
      provider: 'zotero',
      userId: this.userId,
      fetchedAt: Date.now(),
      collections,
      items,
    };
    await this.cache.writeSnapshot(snapshot);
    return snapshot;
  }

  async open(
    item: ExternalItem,
    signal?: AbortSignal,
    onProgress?: (progress: DownloadProgress) => void,
  ): Promise<ExternalDocument> {
    validateKey(item.key);
    checkCancelled(signal);
    let active = this.opens.get(item.key);
    if (!active) {
      const controller = new AbortController();
      const progress = new Set<(value: DownloadProgress) => void>();
      const cleanup: (() => void)[] = [];
      const promise = Promise.resolve()
        .then(() =>
          this.openDocument(item, controller.signal, (value) => {
            for (const notify of progress) notify(value);
          }),
        )
        .finally(() => {
          for (const remove of cleanup) remove();
          this.opens.delete(item.key);
        });
      active = { controller, promise, progress, cleanup };
      this.opens.set(item.key, active);
    }
    if (onProgress) active.progress.add(onProgress);
    if (signal) {
      const controller = active.controller;
      const abort = () => controller.abort();
      signal.addEventListener('abort', abort, { once: true });
      active.cleanup.push(() => signal.removeEventListener('abort', abort));
    }
    return active.promise;
  }

  private async openDocument(
    item: ExternalItem,
    signal: AbortSignal,
    onProgress: (progress: DownloadProgress) => void,
  ): Promise<ExternalDocument> {
    checkCancelled(signal);
    const local = await this.cache.readLocal(item.key);
    checkCancelled(signal);
    if (local)
      return {
        file: local.file,
        title: item.title,
        resumeKey: this.resumeKey(item.key, local.record.attachment.key),
      };
    const api = this.requireApi();
    const attachment = selectStoredPdf(await api.listAttachments(item.key, signal));
    if (!attachment)
      throw new ZoteroError(
        'no-pdf',
        _('No stored PDF attachment was found. Only PDFs stored in Zotero Storage are supported'),
      );
    const bytes = await api.download(attachment, signal, onProgress);
    await this.cache.saveLocal(item, attachment, bytes, signal);
    checkCancelled(signal);
    return {
      file: new File([bytes], attachment.filename, { type: 'application/pdf' }),
      title: item.title,
      resumeKey: this.resumeKey(item.key, attachment.key),
    };
  }

  private resumeKey(itemKey: string, attachmentKey: string): string {
    return `zotero:${this.userId}:${itemKey}:${attachmentKey}`;
  }
}
