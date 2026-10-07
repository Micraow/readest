// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { AppService } from '@/types/system';
import type { ScholarlyDocument } from '../types';
import { fingerprintFile, readAcademicCache, writeAcademicCache } from '../cache';

const hash = 'a'.repeat(64);
const fixture = (): ScholarlyDocument => ({
  schemaVersion: 1,
  parserVersion: 'academic-1',
  fingerprint: hash,
  pageCount: 1,
  metadata: { pdfjsVersion: '6.2.108' },
  pages: [
    {
      page: 1,
      width: 612,
      height: 792,
      rotation: 0,
      items: [],
      graphics: [],
      tagged: false,
      lines: [],
      columns: [],
      visualRegions: [],
      blockIds: [],
      suppressedItemIndices: [],
    },
  ],
  blocks: [],
  readingOrder: [],
  sourceMap: {},
  warnings: [],
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
  } satisfies Pick<AppService, 'exists' | 'readFile' | 'writeFile' | 'createDir'>;
  return { files, storage };
};

describe('academic content cache', () => {
  it('hashes every byte rather than a sampled prefix, independent of filename', async () => {
    const a = new Blob(['abc']);
    expect(await fingerprintFile(a)).toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    );
    expect(await fingerprintFile(new Blob(['abcd']))).not.toBe(await fingerprintFile(a));
  });
  it('rejects cancelled hashing', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(fingerprintFile(new Blob(['x']), controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
  });
  it('round-trips JSON under a source-neutral Cache path', async () => {
    const { files, storage } = storageFixture();
    const doc = fixture();
    await writeAcademicCache(storage, doc);
    expect([...files.keys()][0]).toContain(hash);
    expect(storage.writeFile).toHaveBeenCalledWith(
      expect.stringContaining('academic/'),
      'Cache',
      expect.any(String),
    );
    expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toEqual(doc);
    expect(await readAcademicCache(storage, hash, 2, 'academic-1')).toBeNull();
    expect(await readAcademicCache(storage, hash, 1, 'academic-2')).toBeNull();
    expect(await readAcademicCache(storage, 'b'.repeat(64), 1, 'academic-1')).toBeNull();
  });
  it('ignores malformed, modified and structurally inconsistent cache documents', async () => {
    const { files, storage } = storageFixture();
    await writeAcademicCache(storage, fixture());
    const key = [...files.keys()][0]!;
    const original = files.get(key)!;
    files.set(key, '{');
    expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
    files.set(key, original.replace('612', '999'));
    expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
    const invalid = fixture();
    invalid.readingOrder = ['missing'];
    await writeAcademicCache(storage, invalid);
    expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
  });
  it('treats storage failures as cache misses', async () => {
    const { storage } = storageFixture();
    storage.exists.mockRejectedValue(new Error('offline'));
    expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
  });
});

it('rejects malformed coordinates even with a valid JSON checksum', async () => {
  const { files, storage } = storageFixture();
  const doc = fixture();
  doc.pages[0]!.width = 1e100;
  await writeAcademicCache(storage, doc);
  expect(files.size).toBe(1);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
});

it('rejects omitted and duplicate source item ownership', async () => {
  const { storage } = storageFixture();
  const doc = fixture();
  doc.pages[0]!.items.push({
    index: 0,
    text: 'fixture',
    box: { x: 10, y: 10, width: 20, height: 10 },
    baseline: 20,
    fontSize: 10,
    fontName: 'f',
    fontFamily: '',
    angle: 0,
    hasEOL: false,
  });
  await writeAcademicCache(storage, doc);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
  doc.pages[0]!.suppressedItemIndices = [0, 0];
  await writeAcademicCache(storage, doc);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
});

it('hashes in bounded chunks, yields, and notices edits beyond the first chunk', async () => {
  const bytes = new Uint8Array(1_100_000);
  bytes[1_000_000] = 7;
  const file = new Blob([bytes]);
  const wholeRead = vi.spyOn(file, 'arrayBuffer');
  const slice = vi.spyOn(file, 'slice');
  const first = await fingerprintFile(file);
  expect(wholeRead).not.toHaveBeenCalled();
  expect(slice.mock.calls.length).toBeGreaterThan(1);
  expect(
    slice.mock.calls.every(([start, end]) => (end ?? file.size) - (start ?? 0) <= 262144),
  ).toBe(true);
  bytes[1_000_000] = 8;
  expect(await fingerprintFile(new Blob([bytes]))).not.toBe(first);
});

it('stops chunk hashing when cancelled between reads', async () => {
  const file = new Blob([new Uint8Array(800_000)]);
  const slice = vi.spyOn(file, 'slice');
  const controller = new AbortController();
  await expect(
    fingerprintFile(file, controller.signal, (completed) => {
      if (completed) controller.abort();
    }),
  ).rejects.toMatchObject({ name: 'AbortError' });
  expect(slice).toHaveBeenCalledTimes(1);
});

const captionFixture = (): ScholarlyDocument => {
  const doc = fixture();
  const captionBox = { x: 20, y: 80, width: 120, height: 10 };
  const figureBox = { x: 10, y: 10, width: 150, height: 90 };
  doc.pages[0]!.items = [
    {
      index: 0,
      text: 'Figure 1: Synthetic plot.',
      box: captionBox,
      baseline: 88,
      fontSize: 10,
      fontName: 'f',
      fontFamily: '',
      angle: 0,
      hasEOL: true,
    },
  ];
  const source = [{ page: 1, boxes: [figureBox], itemIndices: [0] }];
  doc.blocks = [
    {
      id: 'figure',
      type: 'visual-region',
      role: 'figure',
      text: '',
      source,
      order: 0,
      confidence: 0.9,
      fontStats: { median: 10, min: 10, max: 10, names: ['f'] },
      captions: [
        {
          role: 'figure',
          label: '1',
          text: 'Figure 1: Synthetic plot.',
          source: { page: 1, boxes: [captionBox], itemIndices: [0] },
        },
      ],
    },
  ];
  doc.pages[0]!.blockIds = ['figure'];
  doc.readingOrder = ['figure'];
  doc.sourceMap = { figure: source };
  return doc;
};

it('retains explicit caption associations on cached reopen without duplicate source ownership', async () => {
  const { storage } = storageFixture();
  const doc = captionFixture();
  await writeAcademicCache(storage, doc);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toEqual(doc);
});

it('rejects a caption association that refers to an item outside its owning visual', async () => {
  const { storage } = storageFixture();
  const doc = captionFixture();
  doc.pages[0]!.items.push({ ...doc.pages[0]!.items[0]!, index: 1, text: 'Unrelated source.' });
  doc.pages[0]!.suppressedItemIndices = [1];
  doc.blocks[0]!.captions![0]!.source.itemIndices = [1];
  await writeAcademicCache(storage, doc);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
});

it('rejects a mismatched caption kind rather than silently dropping its association', async () => {
  const { storage } = storageFixture();
  const doc = captionFixture();
  doc.blocks[0]!.role = 'table';
  await writeAcademicCache(storage, doc);
  expect(await readAcademicCache(storage, hash, 1, 'academic-1')).toBeNull();
});
