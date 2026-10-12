import { sha256 } from '@noble/hashes/sha2';
import { z } from 'zod';
import { fingerprintFile, type AcademicStorage } from './cache';
import type { ScholarlyBlock, ScholarlyDocument } from './types';

const ROOT = 'academic/ovis';
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const positive = z.number().finite().positive();
const pageNumber = positive.int();
const nonempty = z.string().refine((value) => value.trim().length > 0, 'Must not be empty');
const box = z
  .object({
    x: z.number().finite().nonnegative(),
    y: z.number().finite().nonnegative(),
    width: positive,
    height: positive,
  })
  .strict();
const block = z.discriminatedUnion('kind', [
  z.object({ id: nonempty, kind: z.literal('markdown'), markdown: nonempty }).strict(),
  z
    .object({
      id: nonempty,
      kind: z.literal('visual'),
      role: z.enum(['figure', 'equation']),
      box,
      caption: nonempty.optional(),
    })
    .strict(),
  z
    .object({ id: nonempty, kind: z.literal('footnote'), markdown: nonempty, marker: nonempty })
    .strict(),
]);
const bundleSchema = z
  .object({
    format: z.literal('readest-ovis-reflow'),
    version: z.literal(1),
    pdfSha256: hash,
    pageCount: pageNumber,
    identity: z
      .object({
        modelSha256: hash,
        projectorSha256: hash,
        promptSha256: hash,
        runtimeRevision: z.string().regex(/^[a-f0-9]{40}$/),
        configuration: z.record(
          z.string(),
          z.union([z.string(), z.number().finite(), z.boolean()]),
        ),
      })
      .strict(),
    pages: z
      .array(
        z
          .object({
            page: pageNumber,
            width: positive,
            height: positive,
            blocks: z.array(block).min(1),
          })
          .strict(),
      )
      .min(1),
  })
  .strict();

export type OvisBundle = z.infer<typeof bundleSchema>;

/** Local model output is untrusted input, including when it comes back from disk. */
export function parseOvisBundle(value: unknown): OvisBundle {
  const bundle = bundleSchema.parse(value);
  const pages = new Set<number>();
  const ids = new Set<string>();
  for (const page of bundle.pages) {
    if (page.page > bundle.pageCount || pages.has(page.page)) {
      throw new Error('Ovis bundle has a duplicate or out-of-range PDF page');
    }
    pages.add(page.page);
    for (const block of page.blocks) {
      if (ids.has(block.id)) throw new Error('Ovis bundle has duplicate block IDs');
      ids.add(block.id);
      if (
        block.kind === 'visual' &&
        (block.box.x + block.box.width > page.width || block.box.y + block.box.height > page.height)
      ) {
        throw new Error('Ovis visual bounds extend outside the PDF page');
      }
    }
  }
  return bundle;
}

const checkAbort = (signal?: AbortSignal) => {
  if (signal?.aborted) throw new DOMException('Ovis import cancelled', 'AbortError');
};

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.entries(value)
      .filter(([, child]) => child !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([key, child]) => `${JSON.stringify(key)}:${canonicalJson(child)}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

const digest = (text: string): string =>
  Array.from(sha256(new TextEncoder().encode(text)), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
const identityHash = (bundle: OvisBundle) => digest(canonicalJson(bundle.identity));
const directory = (fingerprint: string) => `${ROOT}/${fingerprint}`;
const pointerPath = (fingerprint: string) => `${directory(fingerprint)}/current.json`;
const bundlePath = (fingerprint: string, identity: string, checksum: string) =>
  `${directory(fingerprint)}/${identity}-${checksum}.json`;

function toDocument(bundle: OvisBundle, identity: string): ScholarlyDocument {
  const pages = [...bundle.pages].sort((a, b) => a.page - b.page);
  const blocks: ScholarlyBlock[] = [];
  for (const page of pages) {
    for (const block of page.blocks) {
      const visual = block.kind === 'visual';
      blocks.push({
        id: block.id,
        type: visual ? 'visual-region' : block.kind === 'footnote' ? 'footnote' : 'paragraph',
        text: visual ? '' : block.markdown,
        markdown: visual ? block.caption : block.markdown,
        source: [{ page: page.page, boxes: visual ? [block.box] : [], itemIndices: [] }],
        order: blocks.length,
        confidence: 0,
        fontStats: { median: 12, min: 12, max: 12, names: [] },
        ...(visual ? { role: block.role, previewBox: block.box } : {}),
        ...(block.kind === 'footnote' ? { footnoteMarker: block.marker } : {}),
      });
    }
  }
  return {
    schemaVersion: 1,
    parserVersion: `ovis-import-1-${identity}`,
    fingerprint: bundle.pdfSha256,
    pageCount: bundle.pageCount,
    metadata: {
      pdfjsVersion: '',
      ovis: { identity, coveredPages: pages.map((page) => page.page) },
    },
    pages: pages.map((page) => ({
      page: page.page,
      width: page.width,
      height: page.height,
      rotation: 0,
      tagged: false,
      items: [],
      graphics: [],
      lines: [],
      columns: [],
      visualRegions: [],
      blockIds: page.blocks.map((block) => block.id),
      suppressedItemIndices: [],
    })),
    blocks,
    readingOrder: blocks.map((block) => block.id),
    sourceMap: Object.fromEntries(blocks.map((block) => [block.id, block.source])),
    warnings: [
      `Ovis reflow covers ${pages.length} of ${bundle.pageCount} PDF pages.`,
      'Ovis-generated text may contain recognition errors. Compare with the original PDF.',
    ],
  };
}

const pointerSchema = z
  .object({
    format: z.literal('readest-ovis-cache'),
    version: z.literal(1),
    pdfSha256: hash,
    identitySha256: hash,
    bundleSha256: hash,
  })
  .strict();
const envelopeSchema = z.object({ checksum: hash, payload: z.string() }).strict();

// The storage API has no cancellable/transactional write. Keep each PDF's pointer
// publication and rollback ordered, including writes already in flight on abort.
const publications = new Map<string, Promise<void>>();
async function publishPointer(
  fingerprint: string,
  content: string,
  storage: AcademicStorage,
  signal?: AbortSignal,
): Promise<void> {
  const previousPublication = publications.get(fingerprint);
  let release = () => {};
  const publication = new Promise<void>((resolve) => {
    release = resolve;
  });
  publications.set(fingerprint, publication);
  await previousPublication;
  try {
    checkAbort(signal);
    const path = pointerPath(fingerprint);
    const previous = (await storage.exists(path, 'Cache'))
      ? await storage.readFile(path, 'Cache', 'text')
      : 'null';
    if (typeof previous !== 'string') throw new Error('Cannot read the previous Ovis selection');
    checkAbort(signal);
    try {
      await storage.writeFile(path, 'Cache', content);
      checkAbort(signal);
    } catch (error) {
      // A rejected write may already have changed storage. Restore before letting
      // a newer publication proceed; null represents an absent previous selection.
      await storage.writeFile(path, 'Cache', previous);
      throw error;
    }
  } finally {
    release();
    if (publications.get(fingerprint) === publication) publications.delete(fingerprint);
  }
}

/** Import a locally produced bundle; inference and source pixel storage are deliberately separate. */
export async function importOvisBundle(
  file: Blob,
  bundleValue: unknown,
  storage: AcademicStorage,
  signal?: AbortSignal,
): Promise<ScholarlyDocument> {
  checkAbort(signal);
  const bundle = parseOvisBundle(bundleValue);
  const fingerprint = await fingerprintFile(file, signal);
  checkAbort(signal);
  if (fingerprint !== bundle.pdfSha256) throw new Error('Ovis bundle does not match this PDF');
  const identity = identityHash(bundle);
  const payload = canonicalJson(bundle);
  const checksum = digest(payload);
  const document = toDocument(bundle, identity);
  try {
    checkAbort(signal);
    await storage.createDir(directory(fingerprint), 'Cache', true);
    checkAbort(signal);
    await storage.writeFile(
      bundlePath(fingerprint, identity, checksum),
      'Cache',
      JSON.stringify({ checksum, payload }),
    );
    await publishPointer(
      fingerprint,
      JSON.stringify({
        format: 'readest-ovis-cache',
        version: 1,
        pdfSha256: fingerprint,
        identitySha256: identity,
        bundleSha256: checksum,
      }),
      storage,
      signal,
    );
  } catch {
    // Cache availability must not prevent reading an already validated local import.
  }
  checkAbort(signal);
  return document;
}

/** Rebuild from validated source output rather than trusting a serialized reader document. */
export async function readOvisCache(
  file: Blob,
  storage: AcademicStorage,
  signal?: AbortSignal,
): Promise<ScholarlyDocument | null> {
  const fingerprint = await fingerprintFile(file, signal);
  // Never reopen a pointer while its publication might still be rolled back.
  await publications.get(fingerprint);
  try {
    checkAbort(signal);
    if (!(await storage.exists(pointerPath(fingerprint), 'Cache'))) {
      checkAbort(signal);
      return null;
    }
    checkAbort(signal);
    const rawPointer = await storage.readFile(pointerPath(fingerprint), 'Cache', 'text');
    checkAbort(signal);
    if (typeof rawPointer !== 'string') return null;
    const pointer = pointerSchema.parse(JSON.parse(rawPointer));
    if (pointer.pdfSha256 !== fingerprint) return null;
    const path = bundlePath(fingerprint, pointer.identitySha256, pointer.bundleSha256);
    const rawEnvelope = await storage.readFile(path, 'Cache', 'text');
    checkAbort(signal);
    if (typeof rawEnvelope !== 'string') return null;
    const envelope = envelopeSchema.parse(JSON.parse(rawEnvelope));
    if (
      envelope.checksum !== pointer.bundleSha256 ||
      digest(envelope.payload) !== envelope.checksum
    )
      return null;
    const bundle = parseOvisBundle(JSON.parse(envelope.payload));
    if (
      bundle.pdfSha256 !== fingerprint ||
      identityHash(bundle) !== pointer.identitySha256 ||
      digest(canonicalJson(bundle)) !== envelope.checksum
    )
      return null;
    checkAbort(signal);
    return toDocument(bundle, pointer.identitySha256);
  } catch {
    checkAbort(signal);
    return null;
  }
}
