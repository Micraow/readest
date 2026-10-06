import type {
  PDFDocumentProxy,
  PDFDocumentLoadingTask,
  PDFDataRangeTransport,
  PDFPageProxy,
  RenderTask,
} from '@pdfjs/pdf.mjs';
import {
  fingerprintFile,
  readAcademicCache,
  writeAcademicCache,
  type AcademicStorage,
} from './cache';
import { extractPageGeometry, intersectRects } from './geometry';
import { analyzeDocumentAsync, PARSER_VERSION, SCHEMA_VERSION } from './layout';
import type { AnalysisProgress, PageGeometry, Rect, ScholarlyDocument } from './types';

type PDFJS = typeof import('@pdfjs/pdf.mjs');
type Progress = (progress: AnalysisProgress) => void;
const MAX_PIXELS = 4_194_304;
const MAX_SIDE = 4096;
const aborted = () => new DOMException('Academic reading cancelled', 'AbortError');
const checkAbort = (signals: Array<AbortSignal | undefined>) => {
  if (signals.some((signal) => signal?.aborted)) throw aborted();
};
function abortable<T>(promise: Promise<T>, signals: Array<AbortSignal | undefined>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const cancel = () => {
      cleanup();
      reject(aborted());
    };
    const cleanup = () => {
      for (const signal of signals) signal?.removeEventListener('abort', cancel);
    };
    if (signals.some((signal) => signal?.aborted)) cancel();
    else for (const signal of signals) signal?.addEventListener('abort', cancel, { once: true });
    promise.then(
      (value) => {
        cleanup();
        resolve(value);
      },
      (error: unknown) => {
        cleanup();
        reject(error);
      },
    );
  });
}
const yieldPage = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

interface RangeSource {
  transport: PDFDataRangeTransport;
  failure: Promise<never>;
  stop(): void;
}
function createRangeSource(file: File, pdfjs: PDFJS): RangeSource {
  const transport = new pdfjs.PDFDataRangeTransport(file.size, null);
  const queue: Array<[number, number]> = [];
  let active = 0,
    stopped = false;
  let rejectFailure: (error: unknown) => void = () => {};
  const failure = new Promise<never>((_resolve, reject) => {
    rejectFailure = reject;
  });
  const stop = () => {
    stopped = true;
    queue.length = 0;
  };
  const fail = (error: unknown) => {
    stop();
    rejectFailure(error);
  };
  const pump = () => {
    while (!stopped && active < 6 && queue.length) {
      const [begin, end] = queue.shift()!;
      active++;
      void Promise.resolve()
        .then(() => file.slice(begin, end).arrayBuffer())
        .then((chunk) => {
          if (stopped) return;
          if (chunk.byteLength !== end - begin) throw new Error('Incomplete PDF range read');
          transport.onDataRange(begin, new Uint8Array(chunk));
        })
        .catch(fail)
        .finally(() => {
          active--;
          pump();
        });
    }
  };
  transport.requestDataRange = (begin, end) => {
    if (stopped) return;
    if (
      !Number.isInteger(begin) ||
      !Number.isInteger(end) ||
      begin < 0 ||
      end > file.size ||
      end <= begin
    ) {
      fail(new Error('Invalid PDF range request'));
      return;
    }
    queue.push([begin, end]);
    pump();
  };
  transport.abort = stop;
  return { transport, failure, stop };
}

export class NoTextLayerError extends Error {
  constructor() {
    super('Reading is unavailable for a PDF without a supported text layer');
    this.name = 'NoTextLayerError';
  }
}

export interface AcademicPdfSession {
  analyze(
    storage: AcademicStorage,
    onProgress?: Progress,
    signal?: AbortSignal,
  ): Promise<ScholarlyDocument>;
  renderRegion(
    page: number,
    box: Rect,
    canvas: HTMLCanvasElement,
    targetWidth: number,
    signal?: AbortSignal,
  ): Promise<void>;
  renderPage(page: number, canvas: HTMLCanvasElement, signal?: AbortSignal): Promise<void>;
  destroy(): Promise<void>;
}

/** Loaded only when the user selects Reading; no provider, Book or sync dependency. */
export async function openAcademicPdf(
  file: File,
  signal?: AbortSignal,
): Promise<AcademicPdfSession> {
  checkAbort([signal]);
  await abortable(import('@pdfjs/pdf.min.mjs'), [signal]);
  const pdfjs = (globalThis as typeof globalThis & { pdfjsLib: PDFJS }).pdfjsLib;
  // Keep the Original viewer's worker compatibility/image-memory hooks if installed.
  const vendorURL = (path: string) =>
    new URL(`/vendor/pdfjs/${path}`, globalThis.location?.href ?? 'http://localhost/').href;
  if (
    !pdfjs.GlobalWorkerOptions.workerSrc ||
    pdfjs.GlobalWorkerOptions.workerSrc === './pdf.worker.mjs'
  ) {
    pdfjs.GlobalWorkerOptions.workerSrc = vendorURL('pdf.worker.min.mjs');
  }
  const source = createRangeSource(file, pdfjs);
  checkAbort([signal]);
  const loadingTask = pdfjs.getDocument({
    range: source.transport,
    rangeChunkSize: 256 * 1024,
    disableAutoFetch: true,
    disableStream: true,
    cMapUrl: vendorURL('cmaps/'),
    cMapPacked: true,
    standardFontDataUrl: vendorURL('standard_fonts/'),
    wasmUrl: vendorURL(''),
    canvasMaxAreaInBytes: MAX_PIXELS * 4,
    useWorkerFetch: false,
  });
  try {
    const pdf = await abortable(Promise.race([loadingTask.promise, source.failure]), [signal]);
    checkAbort([signal]);
    return createSession(file, pdf, loadingTask, pdfjs, source, signal);
  } catch (error) {
    source.stop();
    await loadingTask.destroy();
    throw error;
  }
}

function createSession(
  file: File,
  pdf: PDFDocumentProxy,
  loadingTask: PDFDocumentLoadingTask,
  pdfjs: PDFJS,
  source: RangeSource,
  openingSignal?: AbortSignal,
): AcademicPdfSession {
  const lifetime = new AbortController();
  const renders = new Map<HTMLCanvasElement, RenderTask>();
  let destruction: Promise<void> | undefined;
  let fingerprint: string | undefined;
  let requestId = 0;
  const pageUsers = new Map<PDFPageProxy, number>();
  const holdPage = (page: PDFPageProxy) => {
    pageUsers.set(page, (pageUsers.get(page) ?? 0) + 1);
  };
  const releasePage = (page: PDFPageProxy) => {
    const users = (pageUsers.get(page) ?? 1) - 1;
    if (users) pageUsers.set(page, users);
    else {
      pageUsers.delete(page);
      page.cleanup();
    }
  };
  const signals = (signal?: AbortSignal) => [lifetime.signal, signal];
  const withOperationSignal = async <T>(
    signal: AbortSignal | undefined,
    run: (combined: AbortSignal) => Promise<T>,
  ): Promise<T> => {
    checkAbort(signals(signal));
    const combined = new AbortController();
    const cancel = () => combined.abort();
    for (const source of signals(signal)) source?.addEventListener('abort', cancel, { once: true });
    try {
      return await abortable(Promise.race([run(combined.signal), source.failure]), [
        combined.signal,
      ]);
    } finally {
      combined.abort();
      for (const source of signals(signal)) source?.removeEventListener('abort', cancel);
    }
  };

  const layout = async (
    pages: PageGeometry[],
    hash: string,
    onProgress: Progress | undefined,
    signal: AbortSignal,
  ): Promise<ScholarlyDocument> => {
    const progress = (completed: number, total: number) =>
      onProgress?.({ stage: 'layout', completed, total });
    if (typeof Worker !== 'undefined') {
      let worker: Worker | undefined;
      try {
        worker = new Worker(new URL('../../workers/academic.worker.ts', import.meta.url), {
          type: 'module',
        });
        const activeWorker = worker;
        const id = ++requestId;
        return await abortable(
          new Promise<ScholarlyDocument>((resolve, reject) => {
            activeWorker.onmessage = (
              event: MessageEvent<{
                id: number;
                document?: ScholarlyDocument;
                error?: string;
                progress?: { completed: number; total: number };
              }>,
            ) => {
              if (event.data.id !== id) return;
              if (event.data.progress)
                progress(event.data.progress.completed, event.data.progress.total);
              else if (event.data.document) resolve(event.data.document);
              else reject(new Error(event.data.error ?? 'Academic analysis failed'));
            };
            activeWorker.onerror = (event) => {
              event.preventDefault();
              reject(new Error('Academic layout worker unavailable'));
            };
            activeWorker.onmessageerror = () =>
              reject(new Error('Academic layout worker message failed'));
            activeWorker.postMessage({ id, pages, fingerprint: hash, pdfjsVersion: pdfjs.version });
          }),
          [signal],
        );
      } catch (error) {
        if (signal.aborted) throw aborted();
        // CSP/older webviews can reject module workers. The same deterministic
        // engine has a page-bounded yielding path, rather than a blocking loop.
        if (error instanceof DOMException && error.name === 'AbortError') throw error;
      } finally {
        worker?.terminate();
      }
    }
    return analyzeDocumentAsync(pages, hash, pdfjs.version, signal, progress);
  };

  const renderRegion: AcademicPdfSession['renderRegion'] = async (
    pageNumber,
    requested,
    canvas,
    targetWidth,
    signal,
  ) =>
    withOperationSignal(signal, async (operationSignal) => {
      if (
        ![requested.x, requested.y, requested.width, requested.height, targetWidth].every(
          Number.isFinite,
        ) ||
        requested.width <= 0 ||
        requested.height <= 0 ||
        targetWidth <= 0
      )
        throw new Error('Invalid PDF region');
      const page = await abortable(pdf.getPage(pageNumber), [operationSignal]);
      holdPage(page);
      try {
        const original = page.getViewport({ scale: 1 });
        const box = intersectRects(requested, {
          x: 0,
          y: 0,
          width: original.width,
          height: original.height,
        });
        if (!box || box.width < 0.001 || box.height < 0.001)
          throw new Error('PDF region is outside the page');
        const previous = renders.get(canvas);
        if (previous) {
          previous.cancel();
          await abortable(
            previous.promise.catch(() => {}),
            [operationSignal],
          );
        }
        checkAbort([operationSignal]);
        const cssScale = Math.min(
          targetWidth / box.width,
          MAX_SIDE / Math.max(box.width, box.height),
        );
        const dpr = Math.min(2, Math.max(1, globalThis.devicePixelRatio || 1));
        const scale = Math.min(
          cssScale * dpr,
          MAX_SIDE / Math.max(box.width, box.height),
          Math.sqrt(MAX_PIXELS / (box.width * box.height)),
        );
        canvas.width = Math.max(1, Math.floor(box.width * scale));
        canvas.height = Math.max(1, Math.floor(box.height * scale));
        canvas.style.width = `${box.width * cssScale}px`;
        canvas.style.height = `${box.height * cssScale}px`;
        const context = canvas.getContext('2d');
        if (!context) throw new Error('PDF canvas is unavailable');
        const task = page.render({
          canvas,
          canvasContext: context,
          viewport: page.getViewport({ scale }),
          transform: [1, 0, 0, 1, -box.x * scale, -box.y * scale],
          background: '#ffffff',
        });
        renders.set(canvas, task);
        const cancel = () => task.cancel();
        operationSignal.addEventListener('abort', cancel, { once: true });
        try {
          await abortable(task.promise, [operationSignal]);
        } finally {
          operationSignal.removeEventListener('abort', cancel);
          if (renders.get(canvas) === task) renders.delete(canvas);
        }
      } finally {
        releasePage(page);
      }
    });

  const destroy = (): Promise<void> => {
    if (destruction) return destruction;
    openingSignal?.removeEventListener('abort', destroyOnAbort);
    source.stop();
    lifetime.abort();
    for (const render of renders.values()) render.cancel();
    renders.clear();
    // PDF.js 6 removed PDFDocumentProxy.destroy; the loading task owns resources.
    destruction = loadingTask.destroy();
    return destruction;
  };
  const destroyOnAbort = () => {
    void destroy().catch(() => {});
  };
  openingSignal?.addEventListener('abort', destroyOnAbort, { once: true });

  return {
    async analyze(storage, onProgress, signal) {
      return withOperationSignal(signal, async (operationSignal) => {
        onProgress?.({ stage: 'hashing', completed: 0, total: file.size });
        fingerprint ??= await abortable(
          fingerprintFile(file, operationSignal, (completed, total) =>
            onProgress?.({ stage: 'hashing', completed, total }),
          ),
          [operationSignal],
        );
        onProgress?.({ stage: 'hashing', completed: file.size, total: file.size });
        const cached = await abortable(
          readAcademicCache(storage, fingerprint, SCHEMA_VERSION, PARSER_VERSION),
          [operationSignal],
        );
        if (
          cached &&
          cached.pageCount === pdf.numPages &&
          cached.metadata.pdfjsVersion === pdfjs.version
        ) {
          if (
            cached.pages.every((page) =>
              /^No extractable text layer\b/.test(page.unsupportedReason ?? ''),
            )
          )
            throw new NoTextLayerError();
          onProgress?.({ stage: 'cached', completed: pdf.numPages, total: pdf.numPages });
          return cached;
        }
        const pages: PageGeometry[] = [];
        onProgress?.({ stage: 'extracting', completed: 0, total: pdf.numPages });
        for (let n = 1; n <= pdf.numPages; n++) {
          checkAbort([operationSignal]);
          const page = await abortable(pdf.getPage(n), [operationSignal]);
          holdPage(page);
          try {
            pages.push(await abortable(extractPageGeometry(page, n, pdfjs.OPS), [operationSignal]));
          } finally {
            releasePage(page);
          }
          onProgress?.({ stage: 'extracting', completed: n, total: pdf.numPages });
          await abortable(yieldPage(), [operationSignal]);
        }
        onProgress?.({ stage: 'layout', completed: 0, total: pdf.numPages });
        const document = await layout(pages, fingerprint, onProgress, operationSignal);
        checkAbort([operationSignal]);
        if (
          document.pages.every((page) =>
            /^No extractable text layer\b/.test(page.unsupportedReason ?? ''),
          )
        )
          throw new NoTextLayerError();
        await abortable(writeAcademicCache(storage, document), [operationSignal]);
        return document;
      });
    },
    renderRegion,
    async renderPage(pageNumber, canvas, signal) {
      return withOperationSignal(signal, async (operationSignal) => {
        const page = await abortable(pdf.getPage(pageNumber), [operationSignal]);
        const viewport = page.getViewport({ scale: 1 });
        return renderRegion(
          pageNumber,
          { x: 0, y: 0, width: viewport.width, height: viewport.height },
          canvas,
          viewport.width,
          operationSignal,
        );
      });
    },
    destroy,
  };
}
