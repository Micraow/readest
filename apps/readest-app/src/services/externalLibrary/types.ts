/** Provider documents never enter the ordinary Book/import/sync pipeline. */
export interface ExternalCollection {
  key: string;
  name: string;
  version: number;
  parentKey: string | null;
}

export interface ExternalCollectionNode extends ExternalCollection {
  children: ExternalCollectionNode[];
}

export interface ExternalItem {
  key: string;
  version: number;
  title: string;
  authors: string[];
  year: string;
  venue: string;
  collectionKeys: string[];
}

export interface ExternalAttachment {
  key: string;
  parentKey: string;
  version: number;
  filename: string;
  md5: string | null;
}

export interface ExternalLibrarySnapshot {
  schema: 1;
  provider: 'zotero';
  userId: string;
  fetchedAt: number;
  collections: ExternalCollection[];
  items: ExternalItem[];
}

export interface LocalDocumentRecord {
  schema: 1;
  provider: 'zotero';
  userId: string;
  itemKey: string;
  itemVersion: number;
  attachment: ExternalAttachment;
  checksum: string;
  byteLength: number;
  savedAt: number;
}

export interface DownloadProgress {
  received: number;
  total?: number;
}

export type LocalDocumentStatus = 'remote' | 'downloading' | 'local' | 'error';

export interface ExternalDocument {
  file: File;
  title: string;
  resumeKey: string;
}

/** A deliberately read-only source contract. Deletion is local cache only. */
export interface ExternalLibraryProvider {
  loadCached(): Promise<ExternalLibrarySnapshot | null>;
  refresh(signal?: AbortSignal): Promise<ExternalLibrarySnapshot>;
  open(
    item: ExternalItem,
    signal?: AbortSignal,
    onProgress?: (progress: DownloadProgress) => void,
  ): Promise<ExternalDocument>;
  hasLocal(itemKey: string): Promise<boolean>;
  clearLocal(itemKey: string): Promise<void>;
}

/** Only provider-owned relative paths are passed to this durable store. */
export interface ExternalLibraryStorage {
  exists(path: string): Promise<boolean>;
  read(path: string): Promise<ArrayBuffer | null>;
  write(path: string, data: ArrayBuffer): Promise<void>;
  remove(path: string): Promise<void>;
}
