// @vitest-environment node
import { createHash } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';
import { fingerprintFile, type AcademicStorage } from '@/services/academic/cache';
import {
  importOvisBundle,
  parseOvisBundle,
  readOvisCache,
  type OvisBundle,
} from '@/services/academic/ovis';

const pdf = new Blob(['synthetic PDF fixture']);
const fixture = async (): Promise<OvisBundle> => ({
  format: 'readest-ovis-reflow',
  version: 1,
  pdfSha256: await fingerprintFile(pdf),
  pageCount: 6,
  identity: {
    modelSha256: 'a'.repeat(64),
    projectorSha256: 'b'.repeat(64),
    promptSha256: 'c'.repeat(64),
    runtimeRevision: 'd'.repeat(40),
    configuration: { adapterVersion: '1', temperature: 0, deterministic: true },
  },
  pages: [
    {
      page: 2,
      width: 612,
      height: 792,
      blocks: [
        { id: 'p2-text', kind: 'markdown', markdown: '# Synthetic title\n\nText [1](#note-1).' },
        {
          id: 'p2-figure',
          kind: 'visual',
          role: 'figure',
          box: { x: 20, y: 100, width: 200, height: 100 },
          caption: 'Figure 1. A **synthetic** chart.',
        },
        { id: 'note-1', kind: 'footnote', marker: '1', markdown: 'A synthetic footnote.' },
      ],
    },
    {
      page: 4,
      width: 612,
      height: 792,
      blocks: [
        {
          id: 'p4-equation',
          kind: 'visual',
          role: 'equation',
          box: { x: 30, y: 200, width: 300, height: 40 },
        },
      ],
    },
  ],
});

const storageFixture = () => {
  const files = new Map<string, string>();
  const storage = {
    exists: vi.fn(async (path: string) => files.has(path)),
    readFile: vi.fn(async (path: string) => files.get(path)!),
    writeFile: vi.fn(async (path: string, _base: string, content: string | ArrayBuffer | File) => {
      files.set(path, String(content));
    }),
    createDir: vi.fn(async () => {}),
  } satisfies AcademicStorage;
  return { storage, files };
};
const payloadPaths = (files: Map<string, string>) =>
  [...files.keys()].filter((path) => !path.endsWith('/current.json'));

describe('Ovis local reflow import', () => {
  it('imports partial pages honestly, preserving markdown, footnotes and exact visual boxes', async () => {
    const bundle = await fixture();
    const { storage } = storageFixture();
    const document = await importOvisBundle(pdf, bundle, storage);
    expect(document.fingerprint).toBe(bundle.pdfSha256);
    expect(document.pageCount).toBe(6);
    expect(document.metadata.ovis?.coveredPages).toEqual([2, 4]);
    expect(document.metadata.ovis?.identity).toMatch(/^[a-f0-9]{64}$/);
    expect(document.parserVersion).toContain(document.metadata.ovis!.identity);
    expect(document.warnings.join(' ')).toMatch(/2\s*(?:of|\/)\s*6/);
    expect(document.pages.map((page) => page.page)).toEqual([2, 4]);
    for (const page of document.pages) {
      expect(page.items).toEqual([]);
      expect(page.graphics).toEqual([]);
      expect(page.lines).toEqual([]);
      expect(page.columns).toEqual([]);
      expect(page.suppressedItemIndices).toEqual([]);
    }
    expect(document.blocks[0]).toMatchObject({
      type: 'paragraph',
      markdown:
        bundle.pages[0]!.blocks[0]!.kind === 'markdown' && bundle.pages[0]!.blocks[0]!.markdown,
      source: [{ page: 2, boxes: [], itemIndices: [] }],
    });
    expect(document.blocks[1]).toMatchObject({
      type: 'visual-region',
      role: 'figure',
      text: '',
      markdown: 'Figure 1. A **synthetic** chart.',
      source: [{ page: 2, boxes: [{ x: 20, y: 100, width: 200, height: 100 }], itemIndices: [] }],
    });
    expect(document.blocks[1]!.captions).toBeUndefined();
    expect(document.blocks[2]).toMatchObject({
      type: 'footnote',
      markdown: 'A synthetic footnote.',
      footnoteMarker: '1',
    });
    expect(document.blocks[3]).toMatchObject({ type: 'visual-region', role: 'equation' });
    for (const block of document.blocks) {
      expect(block.confidence).toBe(0);
      expect(block.fontStats).toEqual({ median: 12, min: 12, max: 12, names: [] });
      expect(document.sourceMap[block.id]).toEqual(block.source);
    }
    expect(document.readingOrder).toEqual(['p2-text', 'p2-figure', 'note-1', 'p4-equation']);
  });

  it('rejects an import for a different actual PDF before writing anything', async () => {
    const { storage } = storageFixture();
    await expect(
      importOvisBundle(new Blob(['different PDF']), await fixture(), storage),
    ).rejects.toThrow(/PDF/i);
    expect(storage.writeFile).not.toHaveBeenCalled();
  });

  it.each([
    [
      'no pages',
      (bundle: OvisBundle) => {
        bundle.pages = [];
      },
    ],
    [
      'empty page',
      (bundle: OvisBundle) => {
        bundle.pages[0]!.blocks = [];
      },
    ],
    [
      'duplicate page',
      (bundle: OvisBundle) => {
        bundle.pages[1]!.page = 2;
      },
    ],
    [
      'page beyond PDF',
      (bundle: OvisBundle) => {
        bundle.pages[1]!.page = 7;
      },
    ],
    [
      'duplicate block ID',
      (bundle: OvisBundle) => {
        bundle.pages[1]!.blocks[0]!.id = 'p2-text';
      },
    ],
    [
      'negative visual origin',
      (bundle: OvisBundle) => {
        const block = bundle.pages[0]!.blocks[1]!;
        if (block.kind === 'visual') block.box.x = -1;
      },
    ],
    [
      'out-of-page visual',
      (bundle: OvisBundle) => {
        const block = bundle.pages[0]!.blocks[1]!;
        if (block.kind === 'visual') block.box.width = 613;
      },
    ],
    [
      'non-finite configuration',
      (bundle: OvisBundle) => {
        bundle.identity.configuration['temperature'] = Infinity;
      },
    ],
    [
      'invalid model hash',
      (bundle: OvisBundle) => {
        bundle.identity.modelSha256 = 'model.gguf';
      },
    ],
    [
      'invalid runtime revision',
      (bundle: OvisBundle) => {
        bundle.identity.runtimeRevision = 'main';
      },
    ],
  ])('rejects %s', async (_label, mutate) => {
    const bundle = await fixture();
    mutate(bundle);
    expect(() => parseOvisBundle(bundle)).toThrow();
  });

  it('rejects unsupported attachments, nested configuration, and source paths', async () => {
    const bundle = await fixture();
    expect(() =>
      parseOvisBundle({ ...bundle, attachments: ['data:image/png;base64,AA=='] }),
    ).toThrow();
    expect(() => parseOvisBundle({ ...bundle, sourcePath: '/private/paper.pdf' })).toThrow();
    expect(() =>
      parseOvisBundle({
        ...bundle,
        identity: { ...bundle.identity, configuration: { nested: {} } },
      }),
    ).toThrow();
  });
});

describe('Ovis isolated cache', () => {
  it('round-trips through the latest pointer without touching the native cache', async () => {
    const { storage, files } = storageFixture();
    const nativePath = 'academic/native-document-1-native.json';
    files.set(nativePath, 'native untouched');
    const bundle = await fixture();
    const document = await importOvisBundle(pdf, bundle, storage);
    expect(await readOvisCache(pdf, storage)).toEqual(document);
    expect(files.get(nativePath)).toBe('native untouched');
    for (const [path, base] of storage.writeFile.mock.calls) {
      expect(path).toMatch(/^academic\/ovis\//);
      expect(base).toBe('Cache');
    }
    bundle.pages[0]!.blocks[0] = { id: 'new-text', kind: 'markdown', markdown: 'New import.' };
    const latest = await importOvisBundle(pdf, bundle, storage);
    expect(await readOvisCache(pdf, storage)).toEqual(latest);
    expect(payloadPaths(files).filter((path) => path !== nativePath)).toHaveLength(2);
    expect(await readOvisCache(new Blob(['different PDF']), storage)).toBeNull();
  });

  it.each([
    'modelSha256',
    'projectorSha256',
    'promptSha256',
    'runtimeRevision',
    'configuration',
  ] as const)('separates %s changes into different identity/cache keys', async (key) => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    const first = await importOvisBundle(pdf, bundle, storage);
    if (key === 'configuration') bundle.identity.configuration['temperature'] = 0.1;
    else bundle.identity[key] = 'e'.repeat(key === 'runtimeRevision' ? 40 : 64);
    const second = await importOvisBundle(pdf, bundle, storage);
    expect(second.metadata.ovis!.identity).not.toBe(first.metadata.ovis!.identity);
    expect(second.parserVersion).not.toBe(first.parserVersion);
    expect(payloadPaths(files)).toHaveLength(2);
  });

  it('canonicalizes object-key order and binds the content checksum separately', async () => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    const first = await importOvisBundle(pdf, bundle, storage);
    bundle.identity.configuration = { deterministic: true, temperature: 0, adapterVersion: '1' };
    const reordered = Object.fromEntries(Object.entries(bundle).reverse());
    const second = await importOvisBundle(pdf, reordered, storage);
    expect(second).toEqual(first);
    expect(payloadPaths(files)).toHaveLength(1);
    bundle.pages[0]!.blocks[0] = { id: 'p2-text', kind: 'markdown', markdown: 'Changed content.' };
    await importOvisBundle(pdf, bundle, storage);
    expect(payloadPaths(files)).toHaveLength(2);
  });

  it('rejects payload corruption and malformed pointers', async () => {
    const { storage, files } = storageFixture();
    await importOvisBundle(pdf, await fixture(), storage);
    const payloadPath = payloadPaths(files)[0]!;
    const original = files.get(payloadPath)!;
    files.set(payloadPath, original.replace('Synthetic title', 'Tampered title'));
    expect(await readOvisCache(pdf, storage)).toBeNull();
    files.set(payloadPath, original);
    const pointerPath = [...files.keys()].find((path) => path.endsWith('/current.json'))!;
    files.set(pointerPath, '{');
    expect(await readOvisCache(pdf, storage)).toBeNull();
  });

  it.each([
    'schema',
    'PDF fingerprint',
    'identity',
  ] as const)('revalidates %s even when a changed payload has a valid checksum', async (mismatch) => {
    const { storage, files } = storageFixture();
    await importOvisBundle(pdf, await fixture(), storage);
    const pointerPath = [...files.keys()].find((path) => path.endsWith('/current.json'))!;
    const pointer = JSON.parse(files.get(pointerPath)!) as {
      pdfSha256: string;
      identitySha256: string;
      bundleSha256: string;
    };
    const envelope = JSON.parse(files.get(payloadPaths(files)[0]!)!) as {
      payload: string;
      checksum: string;
    };
    const bundle = JSON.parse(envelope.payload) as OvisBundle;
    if (mismatch === 'schema') bundle.pages = [];
    else if (mismatch === 'PDF fingerprint') bundle.pdfSha256 = 'f'.repeat(64);
    else bundle.identity.modelSha256 = 'f'.repeat(64);
    envelope.payload = JSON.stringify(bundle);
    envelope.checksum = createHash('sha256').update(envelope.payload).digest('hex');
    pointer.bundleSha256 = envelope.checksum;
    files.set(pointerPath, JSON.stringify(pointer));
    const forgedPath = `academic/ovis/${pointer.pdfSha256}/${pointer.identitySha256}-${pointer.bundleSha256}.json`;
    files.set(forgedPath, JSON.stringify(envelope));
    expect(await readOvisCache(pdf, storage)).toBeNull();
  });

  it('keeps an imported document usable if persistence fails', async () => {
    const { storage } = storageFixture();
    storage.writeFile.mockRejectedValue(new Error('disk full'));
    const document = await importOvisBundle(pdf, await fixture(), storage);
    expect(document.blocks).toHaveLength(4);
    storage.exists.mockRejectedValue(new Error('offline'));
    expect(await readOvisCache(pdf, storage)).toBeNull();
  });

  it('aborts before import or cache reads when already cancelled', async () => {
    const { storage } = storageFixture();
    const controller = new AbortController();
    controller.abort();
    await expect(
      importOvisBundle(pdf, await fixture(), storage, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    await expect(readOvisCache(pdf, storage, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(storage.writeFile).not.toHaveBeenCalled();
    expect(storage.readFile).not.toHaveBeenCalled();
  });

  it('does not replace the current pointer when cancelled during a payload write', async () => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    const first = await importOvisBundle(pdf, bundle, storage);
    const controller = new AbortController();
    storage.writeFile.mockImplementationOnce(async (path, _base, content) => {
      files.set(path, String(content));
      controller.abort();
    });
    bundle.identity.configuration['temperature'] = 0.2;
    await expect(importOvisBundle(pdf, bundle, storage, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(await readOvisCache(pdf, storage)).toEqual(first);
  });

  it('stops before a write when cancelled while preparing the cache directory', async () => {
    const { storage } = storageFixture();
    const controller = new AbortController();
    storage.createDir.mockImplementationOnce(async () => {
      controller.abort();
    });
    await expect(
      importOvisBundle(pdf, await fixture(), storage, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(storage.writeFile).not.toHaveBeenCalled();
  });

  it('propagates cancellation during a pointer read instead of returning a stale document', async () => {
    const { storage, files } = storageFixture();
    await importOvisBundle(pdf, await fixture(), storage);
    const controller = new AbortController();
    storage.readFile.mockImplementationOnce(async (path) => {
      controller.abort();
      return files.get(path)!;
    });
    await expect(readOvisCache(pdf, storage, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(storage.readFile).toHaveBeenCalledTimes(1);
  });
  it('serializes pointer publication so a cancelled late write cannot replace a newer import', async () => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    await importOvisBundle(pdf, bundle, storage);
    const cancelled = structuredClone(bundle);
    cancelled.identity.configuration['revision'] = 'cancelled';
    const newer = structuredClone(bundle);
    newer.identity.configuration['revision'] = 'newer';
    let entered = () => {};
    const pointerEntered = new Promise<void>((resolve) => {
      entered = resolve;
    });
    let release = () => {};
    const pointerPaused = new Promise<void>((resolve) => {
      release = resolve;
    });
    let payloadWritten = () => {};
    const newerPayload = new Promise<void>((resolve) => {
      payloadWritten = resolve;
    });
    let pauseNextPointer = true;
    storage.writeFile.mockImplementation(async (path, _base, content) => {
      if (pauseNextPointer && path.endsWith('/current.json')) {
        pauseNextPointer = false;
        entered();
        await pointerPaused;
      } else if (!path.endsWith('/current.json') && String(content).includes('newer')) {
        payloadWritten();
      }
      files.set(path, String(content));
    });
    const controller = new AbortController();
    const pending = importOvisBundle(pdf, cancelled, storage, controller.signal);
    const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    await pointerEntered;
    controller.abort();
    const latestPending = importOvisBundle(pdf, newer, storage);
    await newerPayload;
    // Give an uncoordinated writer a chance to commit while the old write is held.
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    release();
    const latest = await latestPending;
    await rejection;
    expect(await readOvisCache(pdf, storage)).toEqual(latest);
  });

  it.each([
    true,
    false,
  ])('restores the previous selection after cancellation inside pointer write (existing=%s)', async (existing) => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    const original = existing ? await importOvisBundle(pdf, bundle, storage) : null;
    bundle.identity.configuration['revision'] = 'cancelled';
    const controller = new AbortController();
    let cancel = true;
    storage.writeFile.mockImplementation(async (path, _base, content) => {
      files.set(path, String(content));
      if (cancel && path.endsWith('/current.json')) {
        cancel = false;
        controller.abort();
      }
    });
    await expect(importOvisBundle(pdf, bundle, storage, controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(await readOvisCache(pdf, storage)).toEqual(original);
  });

  it('restores the previous pointer when the storage write mutates and then fails', async () => {
    const { storage, files } = storageFixture();
    const bundle = await fixture();
    const original = await importOvisBundle(pdf, bundle, storage);
    bundle.identity.configuration['revision'] = 'failed';
    let fail = true;
    storage.writeFile.mockImplementation(async (path, _base, content) => {
      files.set(path, String(content));
      if (fail && path.endsWith('/current.json')) {
        fail = false;
        throw new Error('commit failed');
      }
    });
    const usable = await importOvisBundle(pdf, bundle, storage);
    expect(usable.metadata.ovis?.identity).not.toBe(original.metadata.ovis?.identity);
    expect(await readOvisCache(pdf, storage)).toEqual(original);
  });
});
