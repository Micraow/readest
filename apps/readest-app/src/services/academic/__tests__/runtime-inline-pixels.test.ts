// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { openAcademicPdf } from '../runtime';

const mocks = vi.hoisted(() => ({ getDocument: vi.fn(), getPage: vi.fn() }));
vi.mock('@pdfjs/pdf.min.mjs', () => {
  (globalThis as unknown as { pdfjsLib: unknown }).pdfjsLib = {
    version: '6.2.108',
    OPS: {},
    PDFDataRangeTransport: class {},
    GlobalWorkerOptions: { workerSrc: '/configured-worker.mjs' },
    getDocument: mocks.getDocument,
  };
  return {};
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('devicePixelRatio', 2);
  mocks.getDocument.mockReturnValue({
    promise: Promise.resolve({ getPage: mocks.getPage }),
    destroy: vi.fn(async () => {}),
  });
});
afterEach(() => vi.unstubAllGlobals());

function fixture(renderPromise = Promise.resolve()) {
  const page = {
    getViewport: vi.fn(({ scale }: { scale: number }) => ({
      width: 612 * scale,
      height: 792 * scale,
    })),
    cleanup: vi.fn(),
    render: vi.fn(() => ({ promise: renderPromise, cancel: vi.fn() })),
  };
  mocks.getPage.mockResolvedValue(page);
  const data = new Uint8ClampedArray(12 * 18 * 4).fill(255);
  // Numerator, fraction bar and denominator, then next-row ink after a blank seam.
  for (const y of [0, 1, 4, 7, 8, 9, 10, 11, 16, 17]) {
    for (let x = 2; x < 10; x++) data.fill(0, (y * 12 + x) * 4, (y * 12 + x) * 4 + 3);
  }
  const context = {
    getImageData: vi.fn(() => ({ width: 12, height: 18, data })),
    putImageData: vi.fn(),
  };
  const canvas = {
    width: 0,
    height: 0,
    style: {},
    getContext: () => context,
  } as unknown as HTMLCanvasElement;
  return { page, canvas, context, data };
}

describe('inline source crop render cleanup', () => {
  it('whitens neighboring-row ink after rendering at the actual scale without resizing', async () => {
    const { canvas, context, data } = fixture();
    const keptInk = data.slice(0, 12 * 12 * 4);
    const session = await openAcademicPdf(new File(['%PDF-fixture'], 'test.pdf'));
    try {
      await session.renderRegion(
        1,
        { x: 10, y: 20, width: 6, height: 9 },
        canvas,
        6,
        undefined,
        25,
      );
      expect(context.getImageData).toHaveBeenCalledWith(0, 0, 12, 18);
      expect(context.putImageData).toHaveBeenCalledWith(
        { width: 12, height: 18, data },
        0,
        0,
        0,
        13,
        12,
        5,
      );
      expect(data.slice(0, 12 * 12 * 4)).toEqual(keptInk);
      expect(data.slice(13 * 12 * 4).every((value) => value === 255)).toBe(true);
      expect([canvas.width, canvas.height, canvas.style.width, canvas.style.height]).toEqual([
        12,
        18,
        '6px',
        '9px',
      ]);
    } finally {
      await session.destroy();
    }
  });

  it('leaves ordinary figures and equations untouched without an inline hint', async () => {
    const { canvas, context } = fixture();
    const session = await openAcademicPdf(new File(['%PDF-fixture'], 'test.pdf'));
    try {
      await session.renderRegion(1, { x: 10, y: 20, width: 6, height: 9 }, canvas, 6);
      expect(context.getImageData).not.toHaveBeenCalled();
      expect(context.putImageData).not.toHaveBeenCalled();
    } finally {
      await session.destroy();
    }
  });

  it('skips pixel reads and postprocessing if cancelled as rendering completes', async () => {
    const controller = new AbortController();
    let completeRender = () => {};
    const renderPromise = new Promise<void>((resolve) => {
      completeRender = resolve;
    });
    const { canvas, context, page } = fixture(renderPromise);
    const session = await openAcademicPdf(new File(['%PDF-fixture'], 'test.pdf'));
    try {
      const pending = session.renderRegion(
        1,
        { x: 10, y: 20, width: 6, height: 9 },
        canvas,
        6,
        controller.signal,
        25,
      );
      const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
      await vi.waitFor(() => expect(page.render).toHaveBeenCalled());
      // Resolve the render wait first, then abort before its continuation reads pixels.
      void renderPromise.then(() => controller.abort());
      completeRender();
      await rejection;
      expect(context.getImageData).not.toHaveBeenCalled();
      expect(context.putImageData).not.toHaveBeenCalled();
    } finally {
      await session.destroy();
    }
  });
});
