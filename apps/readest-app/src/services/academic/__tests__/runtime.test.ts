// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AppService } from '@/types/system';
import type { ScholarlyDocument } from '../types';
import { openAcademicPdf } from '../runtime';

const mocks = vi.hoisted(() => ({
  getDocument: vi.fn(),
  destroy: vi.fn(),
  getPage: vi.fn(),
  layout: vi.fn(),
}));
vi.mock('@pdfjs/pdf.min.mjs', () => {
  (globalThis as unknown as { pdfjsLib: unknown }).pdfjsLib = {
    version: '6.2.108',
    OPS: {},
    PDFDataRangeTransport: class {
      onDataRange = vi.fn();
    },
    GlobalWorkerOptions: { workerSrc: '/configured-worker.mjs' },
    getDocument: mocks.getDocument,
  };
  return {};
});
vi.mock('../layout', () => ({
  SCHEMA_VERSION: 1,
  PARSER_VERSION: 'academic-1',
  analyzeDocumentAsync: mocks.layout,
  validateSourceCoverage: () => [],
}));
const storage = {
  exists: vi.fn(async () => false),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  createDir: vi.fn(),
} satisfies Pick<AppService, 'exists' | 'readFile' | 'writeFile' | 'createDir'>;
const page = () => ({
  rotate: 0,
  getViewport: vi.fn(({ scale }: { scale: number }) => ({
    width: 612 * scale,
    height: 792 * scale,
    transform: [scale, 0, 0, -scale, 0, 792 * scale],
  })),
  getTextContent: vi.fn(async () => ({ items: [], styles: {} })),
  getOperatorList: vi.fn(async () => ({ fnArray: [], argsArray: [] })),
  getStructTree: vi.fn(async () => null),
  cleanup: vi.fn(),
  render: vi.fn((_options: unknown) => ({ promise: Promise.resolve(), cancel: vi.fn() })),
});
const file = () => new File(['%PDF-fixture'], 'test.pdf', { type: 'application/pdf' });

beforeEach(() => {
  vi.clearAllMocks();
  mocks.destroy.mockResolvedValue(undefined);
  mocks.getPage.mockImplementation(async () => page());
  mocks.getDocument.mockReturnValue({
    promise: Promise.resolve({ numPages: 2, getPage: mocks.getPage }),
    destroy: mocks.destroy,
  });
  mocks.layout.mockImplementation(
    async (pages, fingerprint, pdfjsVersion) =>
      ({
        schemaVersion: 1,
        parserVersion: 'academic-1',
        fingerprint,
        pageCount: pages.length,
        pages: pages.map((p: object) => ({
          ...p,
          lines: [],
          columns: [],
          visualRegions: [],
          blockIds: [],
          suppressedItemIndices: [],
        })),
        metadata: { pdfjsVersion },
        blocks: [],
        readingOrder: [],
        sourceMap: {},
        warnings: [],
      }) satisfies ScholarlyDocument,
  );
});

describe('academic PDF session lifecycle', () => {
  it('opens only on request, extracts sequential pages, reports stages, caches and destroys loading task', async () => {
    const session = await openAcademicPdf(file());
    const progress = vi.fn();
    const doc = await session.analyze(storage, progress);
    expect(doc.pageCount).toBe(2);
    expect(mocks.getPage.mock.calls).toEqual([[1], [2]]);
    expect(progress.mock.calls.map(([p]) => p.stage)).toContain('hashing');
    expect(progress).toHaveBeenCalledWith({ stage: 'extracting', completed: 2, total: 2 });
    expect(storage.writeFile).toHaveBeenCalledTimes(1);
    await session.destroy();
    await session.destroy();
    expect(mocks.destroy).toHaveBeenCalledTimes(1);
    await expect(session.analyze(storage)).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('aborts during opening and destroys the loading task', async () => {
    mocks.getDocument.mockReturnValue({ promise: new Promise(() => {}), destroy: mocks.destroy });
    const controller = new AbortController();
    const pending = openAcademicPdf(file(), controller.signal);
    await vi.waitFor(() => expect(mocks.getDocument).toHaveBeenCalled());
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    expect(mocks.destroy).toHaveBeenCalledTimes(1);
  });
  it('yields between pages and stops before loading another page when cancelled', async () => {
    const controller = new AbortController();
    const session = await openAcademicPdf(file());
    await expect(
      session.analyze(
        storage,
        ({ stage, completed }) => {
          if (stage === 'extracting' && completed === 1) controller.abort();
        },
        controller.signal,
      ),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(mocks.getPage).toHaveBeenCalledTimes(1);
    expect(mocks.layout).not.toHaveBeenCalled();
    expect(storage.writeFile).not.toHaveBeenCalled();
    await session.destroy();
  });
  it('clips region rendering in viewport coordinates and caps canvas allocation', async () => {
    const p = page();
    mocks.getPage.mockResolvedValue(p);
    const session = await openAcademicPdf(file());
    const canvas = {
      width: 0,
      height: 0,
      style: { width: '', height: '' },
      getContext: vi.fn(() => ({})),
    } as unknown as HTMLCanvasElement;
    await session.renderRegion(1, { x: 100, y: 200, width: 200, height: 100 }, canvas, 10000);
    expect(canvas.width * canvas.height).toBeLessThanOrEqual(4_194_304);
    expect(Math.max(canvas.width, canvas.height)).toBeLessThanOrEqual(4096);
    const options = p.render.mock.calls[0]![0] as unknown as {
      transform: number[];
      viewport: { width: number };
    };
    const scale = options.viewport.width / 612;
    expect(options.transform).toEqual([1, 0, 0, 1, -100 * scale, -200 * scale]);
    await session.destroy();
  });
  it('cancels active rendering and analysis when the session is destroyed', async () => {
    const p = page();
    const cancel = vi.fn();
    p.render.mockReturnValue({ promise: new Promise(() => {}), cancel });
    mocks.getPage.mockResolvedValue(p);
    const session = await openAcademicPdf(file());
    const canvas = { style: {}, getContext: () => ({}) } as unknown as HTMLCanvasElement;
    const pending = session.renderPage(1, canvas);
    const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    await vi.waitFor(() => expect(p.render).toHaveBeenCalled());
    await session.destroy();
    await rejection;
    expect(cancel).toHaveBeenCalled();
  });
});

it('returns a stable AbortError even when cancellation is triggered by the first progress callback', async () => {
  const controller = new AbortController();
  const session = await openAcademicPdf(file());
  await expect(
    session.analyze(storage, () => controller.abort(), controller.signal),
  ).rejects.toMatchObject({ name: 'AbortError' });
  await session.destroy();
});

it('rejects zero, nonfinite and subpixel-degenerate crop geometry before allocating a canvas', async () => {
  const session = await openAcademicPdf(file());
  const canvas = {
    width: 0,
    height: 0,
    style: {},
    getContext: vi.fn(),
  } as unknown as HTMLCanvasElement;
  for (const width of [0, Number.POSITIVE_INFINITY, Number.MIN_VALUE]) {
    await expect(
      session.renderRegion(1, { x: 100, y: 100, width, height: width }, canvas, 1000),
    ).rejects.toThrow();
  }
  expect(canvas.getContext).not.toHaveBeenCalled();
  await session.destroy();
});

it('reports scanned documents unavailable while preserving the Original session lifecycle', async () => {
  mocks.layout.mockImplementationOnce(
    async (pages, fingerprint, pdfjsVersion) =>
      ({
        schemaVersion: 1,
        parserVersion: 'academic-1',
        fingerprint,
        pageCount: pages.length,
        pages: pages.map((p: object) => ({
          ...p,
          lines: [],
          columns: [],
          visualRegions: [],
          blockIds: [],
          suppressedItemIndices: [],
          unsupportedReason: 'No extractable text layer',
        })),
        metadata: { pdfjsVersion },
        blocks: [],
        readingOrder: [],
        sourceMap: {},
        warnings: [],
      }) satisfies ScholarlyDocument,
  );
  const session = await openAcademicPdf(file());
  await expect(session.analyze(storage)).rejects.toMatchObject({ name: 'NoTextLayerError' });
  expect(mocks.destroy).not.toHaveBeenCalled();
  await session.destroy();
});

it('gives the main event loop a turn for every page of a 100-page document', async () => {
  mocks.getDocument.mockReturnValue({
    promise: Promise.resolve({ numPages: 100, getPage: mocks.getPage }),
    destroy: mocks.destroy,
  });
  const session = await openAcademicPdf(file());
  let ticks = 0;
  const timer = setInterval(() => ticks++, 0);
  try {
    await session.analyze(storage);
    expect(mocks.getPage).toHaveBeenCalledTimes(100);
    expect(ticks).toBeGreaterThanOrEqual(99);
  } finally {
    clearInterval(timer);
    await session.destroy();
  }
});

it('uses and terminates the layout module worker when available', async () => {
  const terminate = vi.fn();
  class FakeWorker {
    onmessage?: (event: { data: unknown }) => void;
    onerror?: (event: Event) => void;
    terminate = terminate;
    postMessage(data: { id: number; fingerprint: string; pages: object[]; pdfjsVersion: string }) {
      this.onmessage?.({ data: { id: data.id, progress: { completed: 1, total: 2 } } });
      void mocks
        .layout(data.pages, data.fingerprint, data.pdfjsVersion)
        .then((document: ScholarlyDocument) =>
          this.onmessage?.({ data: { id: data.id, document } }),
        );
    }
  }
  vi.stubGlobal('Worker', FakeWorker);
  const session = await openAcademicPdf(file());
  const progress = vi.fn();
  try {
    await session.analyze(storage, progress);
    expect(terminate).toHaveBeenCalledTimes(1);
    expect(progress).toHaveBeenCalledWith({ stage: 'layout', completed: 1, total: 2 });
  } finally {
    await session.destroy();
    vi.unstubAllGlobals();
  }
});

it('opens with range transport without reading the whole File', async () => {
  const source = file();
  const read = vi.spyOn(source, 'arrayBuffer');
  const session = await openAcademicPdf(source);
  expect(read).not.toHaveBeenCalled();
  expect(mocks.getDocument).toHaveBeenCalledWith(
    expect.objectContaining({ range: expect.any(Object), disableAutoFetch: true }),
  );
  await session.destroy();
});

it('limits range reads to six and drops queued work after destroy without closing the File', async () => {
  const source = file();
  const releases: Array<() => void> = [];
  const slice = vi.spyOn(source, 'slice').mockImplementation(
    () =>
      ({
        arrayBuffer: () =>
          new Promise<ArrayBuffer>((resolve) => {
            releases.push(() => resolve(new ArrayBuffer(1)));
          }),
      }) as unknown as Blob,
  );
  const session = await openAcademicPdf(source);
  const range = (
    mocks.getDocument.mock.calls[0]![0] as {
      range: {
        requestDataRange(begin: number, end: number): void;
        onDataRange: ReturnType<typeof vi.fn>;
      };
    }
  ).range;
  for (let i = 0; i < 20; i++) range.requestDataRange(0, 1);
  await vi.waitFor(() => expect(slice).toHaveBeenCalledTimes(6));
  releases[0]!();
  await vi.waitFor(() => expect(slice).toHaveBeenCalledTimes(7));
  await session.destroy();
  for (const release of releases.slice(1)) release();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(slice).toHaveBeenCalledTimes(7);
  expect(range.onDataRange).toHaveBeenCalledTimes(1);
});

it('surfaces failed File ranges instead of hanging extraction', async () => {
  const source = file();
  vi.spyOn(source, 'slice').mockImplementation(
    () =>
      ({
        arrayBuffer: async () => {
          throw new Error('File read failed');
        },
      }) as unknown as Blob,
  );
  const session = await openAcademicPdf(source);
  const range = (
    mocks.getDocument.mock.calls[0]![0] as {
      range: { requestDataRange(begin: number, end: number): void };
    }
  ).range;
  mocks.getPage.mockReturnValueOnce(new Promise(() => {}));
  const canvas = { style: {}, getContext: vi.fn() } as unknown as HTMLCanvasElement;
  const pending = session.renderPage(1, canvas);
  const rejection = expect(pending).rejects.toThrow('File read failed');
  range.requestDataRange(0, 1);
  await rejection;
  await session.destroy();
});

it('does not clean a page while a peer canvas is still rendering it', async () => {
  const p = page();
  mocks.getPage.mockResolvedValue(p);
  const finish: Array<() => void> = [];
  p.render.mockImplementation(() => ({
    promise: new Promise<void>((resolve) => finish.push(resolve)),
    cancel: vi.fn(),
  }));
  const session = await openAcademicPdf(file());
  const canvas = () => ({ style: {}, getContext: () => ({}) }) as unknown as HTMLCanvasElement;
  const a = session.renderRegion(1, { x: 10, y: 10, width: 100, height: 100 }, canvas(), 100);
  const b = session.renderRegion(1, { x: 20, y: 20, width: 100, height: 100 }, canvas(), 100);
  await vi.waitFor(() => expect(finish).toHaveLength(2));
  finish[0]!();
  await a;
  expect(p.cleanup).not.toHaveBeenCalled();
  finish[1]!();
  await b;
  expect(p.cleanup).toHaveBeenCalledTimes(1);
  await session.destroy();
});

it('falls back to asynchronous analysis when module workers are blocked', async () => {
  vi.stubGlobal(
    'Worker',
    class {
      constructor() {
        throw new DOMException('Blocked by policy', 'SecurityError');
      }
    },
  );
  const session = await openAcademicPdf(file());
  try {
    expect((await session.analyze(storage)).pageCount).toBe(2);
    expect(mocks.layout).toHaveBeenCalledTimes(1);
  } finally {
    await session.destroy();
    vi.unstubAllGlobals();
  }
});

it('terminates an unfinished layout worker when analysis is cancelled', async () => {
  const terminate = vi.fn(),
    postMessage = vi.fn();
  vi.stubGlobal(
    'Worker',
    class {
      terminate = terminate;
      postMessage = postMessage;
    },
  );
  const controller = new AbortController();
  const session = await openAcademicPdf(file());
  try {
    const pending = session.analyze(storage, undefined, controller.signal);
    const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    await vi.waitFor(() => expect(postMessage).toHaveBeenCalled());
    controller.abort();
    await rejection;
    expect(terminate).toHaveBeenCalledTimes(1);
    expect(storage.writeFile).not.toHaveBeenCalled();
  } finally {
    await session.destroy();
    vi.unstubAllGlobals();
  }
});

it('reuses a valid cache without loading or extracting any page', async () => {
  const files = new Map<string, string>();
  const localStorage = {
    exists: async (name: string) => files.has(name),
    readFile: async (name: string) => files.get(name)!,
    createDir: async () => {},
    writeFile: async (name: string, _base: string, content: string | ArrayBuffer | File) => {
      files.set(name, String(content));
    },
  };
  const session = await openAcademicPdf(file());
  try {
    const first = await session.analyze(localStorage);
    mocks.getPage.mockClear();
    mocks.layout.mockClear();
    const progress = vi.fn();
    expect(await session.analyze(localStorage, progress)).toEqual(first);
    expect(mocks.getPage).not.toHaveBeenCalled();
    expect(mocks.layout).not.toHaveBeenCalled();
    expect(progress).toHaveBeenCalledWith({ stage: 'cached', completed: 2, total: 2 });
  } finally {
    await session.destroy();
  }
});
