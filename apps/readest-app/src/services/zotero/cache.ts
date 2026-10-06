import { stubTranslation as _ } from '@/utils/misc';
import { md5 } from 'js-md5';
import type {
  ExternalAttachment,
  ExternalItem,
  ExternalLibrarySnapshot,
  ExternalLibraryStorage,
  LocalDocumentRecord,
} from '../externalLibrary/types';
import {
  checkCancelled,
  object,
  safeFilename,
  validateKey,
  validateUserId,
  ZoteroError,
} from './api';

export const ZOTERO_ROOT = 'external-library/zotero';
const encode = (value: unknown): ArrayBuffer =>
  new TextEncoder().encode(JSON.stringify(value)).buffer;
const isKey = (value: unknown): value is string =>
  typeof value === 'string' && /^[A-Z0-9]{8}$/.test(value);
const isVersion = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const isStrings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((entry) => typeof entry === 'string');
const isChecksum = (value: unknown): value is string =>
  typeof value === 'string' && /^[a-f0-9]{32}$/.test(value);

export function validatePdf(bytes: ArrayBuffer, expectedMd5?: string | null): string {
  const header = new TextDecoder('ascii').decode(bytes.slice(0, 1024));
  if (!header.includes('%PDF-'))
    throw new ZoteroError('invalid-data', _('Zotero did not return a valid PDF'));
  const checksum = md5(bytes);
  if (expectedMd5 && checksum !== expectedMd5)
    throw new ZoteroError(
      'invalid-data',
      _('The PDF checksum does not match Zotero. Refresh the library and try again'),
    );
  return checksum;
}

/** Durable, local-only store. A record is published only after complete PDF bytes. */
export class ZoteroCache {
  readonly root: string;
  private writes = new Map<string, Promise<void>>();
  constructor(
    private readonly storage: ExternalLibraryStorage,
    readonly userId: string,
  ) {
    this.root = `${ZOTERO_ROOT}/${validateUserId(userId)}`;
  }

  private async readJson(path: string): Promise<unknown> {
    const bytes = await this.storage.read(path);
    if (!bytes) return null;
    try {
      return JSON.parse(new TextDecoder().decode(bytes)) as unknown;
    } catch {
      return null;
    }
  }

  async readSnapshot(): Promise<ExternalLibrarySnapshot | null> {
    const raw = object(await this.readJson(`${this.root}/library.json`));
    if (
      raw['schema'] !== 1 ||
      raw['provider'] !== 'zotero' ||
      raw['userId'] !== this.userId ||
      typeof raw['fetchedAt'] !== 'number' ||
      !Array.isArray(raw['collections']) ||
      !Array.isArray(raw['items'])
    )
      return null;
    for (const row of raw['collections']) {
      const collection = object(row);
      if (
        !isKey(collection['key']) ||
        !isVersion(collection['version']) ||
        typeof collection['name'] !== 'string' ||
        (collection['parentKey'] !== null && !isKey(collection['parentKey']))
      )
        return null;
    }
    for (const row of raw['items']) {
      const item = object(row);
      if (
        !isKey(item['key']) ||
        !isVersion(item['version']) ||
        !['title', 'year', 'venue'].every((key) => typeof item[key] === 'string') ||
        !isStrings(item['authors']) ||
        !Array.isArray(item['collectionKeys']) ||
        !item['collectionKeys'].every(isKey)
      )
        return null;
    }
    return raw as unknown as ExternalLibrarySnapshot;
  }

  async writeSnapshot(snapshot: ExternalLibrarySnapshot): Promise<void> {
    if (snapshot.userId !== this.userId)
      throw new ZoteroError('invalid-data', _('The Zotero library does not match this account'));
    await this.storage.write(`${this.root}/library.json`, encode(snapshot));
  }

  private recordPath(itemKey: string): string {
    return `${this.root}/items/${validateKey(itemKey)}.json`;
  }
  private pdfPath(record: LocalDocumentRecord): string {
    return `${this.root}/pdfs/${validateKey(record.itemKey)}/${validateKey(record.attachment.key)}-${record.attachment.version}-${record.checksum}.pdf`;
  }

  async readRecord(itemKey: string): Promise<LocalDocumentRecord | null> {
    const raw = object(await this.readJson(this.recordPath(itemKey)));
    const attachment = object(raw['attachment']);
    if (
      raw['schema'] !== 1 ||
      raw['provider'] !== 'zotero' ||
      raw['userId'] !== this.userId ||
      raw['itemKey'] !== itemKey ||
      !isVersion(raw['itemVersion']) ||
      !isChecksum(raw['checksum']) ||
      typeof raw['byteLength'] !== 'number' ||
      !Number.isSafeInteger(raw['byteLength']) ||
      raw['byteLength'] <= 0 ||
      typeof raw['savedAt'] !== 'number' ||
      !isKey(attachment['key']) ||
      attachment['parentKey'] !== itemKey ||
      !isVersion(attachment['version']) ||
      typeof attachment['filename'] !== 'string' ||
      (attachment['md5'] !== null && !isChecksum(attachment['md5']))
    )
      return null;
    return raw as unknown as LocalDocumentRecord;
  }

  async hasLocal(itemKey: string): Promise<boolean> {
    const record = await this.readRecord(itemKey);
    return !!record && this.storage.exists(this.pdfPath(record));
  }

  async readLocal(itemKey: string): Promise<{ file: File; record: LocalDocumentRecord } | null> {
    const record = await this.readRecord(itemKey);
    if (!record) return null;
    const bytes = await this.storage.read(this.pdfPath(record));
    if (!bytes) return null;
    if (bytes.byteLength !== record.byteLength)
      throw new ZoteroError(
        'invalid-data',
        _('The saved PDF is incomplete. Clear its local copy and download it again'),
      );
    validatePdf(bytes, record.checksum);
    return {
      file: new File([bytes], safeFilename(record.attachment.filename, record.attachment.key), {
        type: 'application/pdf',
      }),
      record,
    };
  }

  private async serialize<T>(itemKey: string, work: () => Promise<T>): Promise<T> {
    const previous = this.writes.get(itemKey) ?? Promise.resolve();
    const result = previous.then(work);
    const tail = result.then(
      () => undefined,
      () => undefined,
    );
    this.writes.set(itemKey, tail);
    try {
      return await result;
    } finally {
      if (this.writes.get(itemKey) === tail) this.writes.delete(itemKey);
    }
  }

  saveLocal(
    item: ExternalItem,
    attachment: ExternalAttachment,
    bytes: ArrayBuffer,
    signal?: AbortSignal,
  ): Promise<LocalDocumentRecord> {
    return this.serialize(item.key, () => this.writeLocal(item, attachment, bytes, signal));
  }

  private async writeLocal(
    item: ExternalItem,
    attachment: ExternalAttachment,
    bytes: ArrayBuffer,
    signal?: AbortSignal,
  ): Promise<LocalDocumentRecord> {
    validateKey(item.key);
    validateKey(attachment.key);
    if (
      attachment.parentKey !== item.key ||
      !isVersion(item.version) ||
      !isVersion(attachment.version)
    )
      throw new ZoteroError('invalid-data', _('The PDF does not match this Zotero item'));
    checkCancelled(signal);
    const existing = await this.readLocal(item.key);
    checkCancelled(signal);
    // A local copy is immutable until explicitly cleared. A coalesced or
    // cancelled later caller must never overwrite/delete a valid offline PDF.
    if (existing) return existing.record;
    const checksum = validatePdf(bytes, attachment.md5);
    const record: LocalDocumentRecord = {
      schema: 1,
      provider: 'zotero',
      userId: this.userId,
      itemKey: item.key,
      itemVersion: item.version,
      attachment,
      checksum,
      byteLength: bytes.byteLength,
      savedAt: Date.now(),
    };
    const path = this.pdfPath(record);
    let published = false;
    try {
      await this.storage.write(path, bytes);
      checkCancelled(signal);
      await this.storage.write(this.recordPath(item.key), encode(record));
      published = true;
      checkCancelled(signal);
    } catch (error) {
      // Interrupted writes are never advertised as offline-ready. Attempt both
      // removals even if the filesystem cannot remove one incomplete object.
      await this.storage.remove(path).catch(() => undefined);
      if (published) await this.storage.remove(this.recordPath(item.key)).catch(() => undefined);
      throw error;
    }
    return record;
  }

  async clearLocal(itemKey: string): Promise<void> {
    validateKey(itemKey);
    await this.serialize(itemKey, async () => {
      const record = await this.readRecord(itemKey);
      if (record) await this.storage.remove(this.pdfPath(record));
      await this.storage.remove(this.recordPath(itemKey));
    });
  }
}
