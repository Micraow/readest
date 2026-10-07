import { sha256 as incrementalSha256 } from '@noble/hashes/sha2';
import { z } from 'zod';
import type { AppService } from '@/types/system';
import type { InlineRun, ScholarlyDocument, SourceSpan } from './types';
import { validateSourceCoverage } from './layout';

export type AcademicStorage = Pick<AppService, 'exists' | 'readFile' | 'writeFile' | 'createDir'>;
const ROOT = 'academic';
const hashPattern = /^[a-f0-9]{64}$/;
const finite = z.number().finite().min(-10_000_000).max(10_000_000);
const index = z.number().int().nonnegative();
const rect = z.object({
  x: finite,
  y: finite,
  width: finite.nonnegative(),
  height: finite.nonnegative(),
});
const source = z.object({
  page: index.positive(),
  boxes: z.array(rect),
  itemIndices: z.array(index),
});
const role = z.enum(['figure', 'table', 'algorithm', 'equation', 'unknown']);
const inlineRun = z.discriminatedUnion('kind', [
  z.object({
    kind: z.literal('text'),
    text: z.string(),
    source,
    style: z
      .object({
        fontStyle: z.literal('italic').optional(),
        fontWeight: z.literal('bold').optional(),
        verticalAlign: z.enum(['sub', 'super']).optional(),
      })
      .optional(),
  }),
  z.object({
    kind: z.literal('source'),
    text: z.string(),
    source,
    fontSize: finite.positive(),
    baseline: finite,
  }),
]);
const schema = z.object({
  schemaVersion: index,
  parserVersion: z.string(),
  fingerprint: z.string().regex(hashPattern),
  pageCount: index.positive(),
  metadata: z.object({ title: z.string().optional(), pdfjsVersion: z.string() }),
  pages: z.array(
    z.object({
      page: index.positive(),
      width: finite.positive(),
      height: finite.positive(),
      rotation: finite,
      tagged: z.boolean(),
      items: z.array(
        z.object({
          index,
          text: z.string(),
          box: rect,
          baseline: finite,
          fontSize: finite.nonnegative(),
          fontName: z.string(),
          fontFamily: z.string(),
          fontStyle: z.literal('italic').optional(),
          fontWeight: z.literal('bold').optional(),
          angle: finite,
          hasEOL: z.boolean(),
        }),
      ),
      graphics: z.array(z.object({ box: rect, kind: z.enum(['form', 'image', 'path', 'rule']) })),
      lines: z.array(
        z.object({
          id: z.string(),
          text: z.string(),
          box: rect,
          itemIndices: z.array(index),
          fontSize: finite.nonnegative(),
        }),
      ),
      columns: z.array(z.object({ box: rect, confidence: finite.min(0).max(1) })),
      visualRegions: z.array(z.object({ box: rect, role, confidence: finite.min(0).max(1) })),
      blockIds: z.array(z.string()),
      suppressedItemIndices: z.array(index),
      unsupportedReason: z.string().optional(),
    }),
  ),
  blocks: z.array(
    z.object({
      id: z.string(),
      type: z.enum(['heading', 'paragraph', 'list', 'reference', 'footnote', 'visual-region']),
      text: z.string(),
      source: z.array(source),
      order: index,
      confidence: finite.min(0).max(1),
      fontStats: z.object({
        median: finite.nonnegative(),
        min: finite.nonnegative(),
        max: finite.nonnegative(),
        names: z.array(z.string()),
      }),
      level: index.optional(),
      listItems: z.array(z.string()).optional(),
      inlineRuns: z.array(inlineRun).optional(),
      listInlineRuns: z.array(z.array(inlineRun)).optional(),
      previewBox: rect.optional(),
      role: role.optional(),
      captions: z
        .array(
          z.object({
            role: z.enum(['figure', 'table']),
            label: z.string().regex(/^(?:\d+|[IVX]+)$/i),
            text: z.string().min(1),
            source,
            inlineRuns: z.array(inlineRun).optional(),
          }),
        )
        .optional(),
      fallbackReason: z.string().optional(),
    }),
  ),
  readingOrder: z.array(z.string()),
  sourceMap: z.record(z.string(), z.array(source)),
  warnings: z.array(z.string()),
});

const checkAbort = (signal?: AbortSignal) => {
  if (signal?.aborted) throw new DOMException('Academic analysis cancelled', 'AbortError');
};
const sha256 = async (data: ArrayBuffer): Promise<string> =>
  Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');

/** Incremental full-file SHA256; bounded buffers also work with native range-backed Files. */
export async function fingerprintFile(
  file: Blob,
  signal?: AbortSignal,
  onProgress?: (completed: number, total: number) => void,
): Promise<string> {
  const hash = incrementalSha256.create();
  const chunkSize = 256 * 1024;
  try {
    checkAbort(signal);
    onProgress?.(0, file.size);
    for (let offset = 0; offset < file.size; offset += chunkSize) {
      checkAbort(signal);
      const end = Math.min(file.size, offset + chunkSize);
      const bytes = await file.slice(offset, end).arrayBuffer();
      checkAbort(signal);
      if (bytes.byteLength !== end - offset) throw new Error('Incomplete PDF range read');
      hash.update(new Uint8Array(bytes));
      onProgress?.(end, file.size);
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    }
    checkAbort(signal);
    return Array.from(hash.digest(), (byte) => byte.toString(16).padStart(2, '0')).join('');
  } finally {
    hash.destroy();
  }
}
const cachePath = (fingerprint: string, schemaVersion: number, parserVersion: string) =>
  `${ROOT}/${fingerprint}-${schemaVersion}-${encodeURIComponent(parserVersion)}.json`;

function validReferences(document: ScholarlyDocument): boolean {
  if (document.pages.length !== document.pageCount || validateSourceCoverage(document).length)
    return false;
  const pages = new Map(document.pages.map((page) => [page.page, page]));
  const blocks = new Map(document.blocks.map((block) => [block.id, block]));
  if (pages.size !== document.pageCount || blocks.size !== document.blocks.length) return false;
  if (
    document.pages.some(
      (page, i) =>
        page.page !== i + 1 ||
        new Set(page.items.map((item) => item.index)).size !== page.items.length,
    )
  )
    return false;
  if (
    document.readingOrder.length !== blocks.size ||
    new Set(document.readingOrder).size !== blocks.size
  )
    return false;
  if (document.readingOrder.some((id, order) => blocks.get(id)?.order !== order)) return false;
  if (Object.keys(document.sourceMap).length !== blocks.size) return false;
  const validInline = (runs: InlineRun[] | undefined, sources: SourceSpan[]) => {
    if (!runs) return true;
    const expected = new Set(
      sources.flatMap((span) => span.itemIndices.map((id) => `${span.page}:${id}`)),
    );
    const seen = new Set<string>();
    for (const run of runs) {
      const page = pages.get(run.source.page);
      if (!page || (run.source.itemIndices.length && !run.source.boxes.length)) return false;
      if (
        run.kind === 'source' &&
        (!run.source.itemIndices.length ||
          run.source.boxes.length !== 1 ||
          run.source.boxes.some(
            (box) =>
              box.width <= 0 ||
              box.height <= 0 ||
              box.x < 0 ||
              box.y < 0 ||
              box.x + box.width > page.width + 0.01 ||
              box.y + box.height > page.height + 0.01,
          ))
      )
        return false;
      for (const id of run.source.itemIndices) {
        const key = `${run.source.page}:${id}`;
        if (!expected.has(key) || seen.has(key)) return false;
        seen.add(key);
      }
    }
    return seen.size === expected.size;
  };
  for (const block of document.blocks) {
    if (
      !block.source.length ||
      JSON.stringify(document.sourceMap[block.id]) !== JSON.stringify(block.source)
    )
      return false;
    if (
      !validInline(block.inlineRuns, block.source) ||
      (block.listInlineRuns &&
        (block.type !== 'list' ||
          block.listInlineRuns.length !== block.listItems?.length ||
          !validInline(block.listInlineRuns.flat(), block.source)))
    )
      return false;
    if (block.previewBox) {
      const preview = block.previewBox,
        full = block.source[0]?.boxes[0];
      if (
        block.type !== 'visual-region' ||
        !block.captions?.length ||
        !full ||
        preview.width <= 0 ||
        preview.height <= 0 ||
        preview.x < full.x ||
        preview.y < full.y ||
        preview.x + preview.width > full.x + full.width + 0.01 ||
        preview.y + preview.height >
          Math.min(...block.captions.flatMap((caption) => caption.source.boxes.map((box) => box.y)))
      )
        return false;
    }
    for (const caption of block.captions ?? []) {
      const owned = new Set(
        block.source
          .filter((span) => span.page === caption.source.page)
          .flatMap((span) => span.itemIndices),
      );
      if (
        block.type !== 'visual-region' ||
        block.role !== caption.role ||
        !caption.source.boxes.length ||
        !caption.source.itemIndices.length ||
        caption.source.itemIndices.some((id) => !owned.has(id)) ||
        !validInline(caption.inlineRuns, [caption.source])
      )
        return false;
    }
    for (const span of block.source) {
      const page = pages.get(span.page);
      if (
        !page ||
        !span.boxes.length ||
        span.itemIndices.some((id) => !page.items.some((item) => item.index === id))
      )
        return false;
      if (!page.blockIds.includes(block.id)) return false;
    }
  }
  return document.pages.every((page) => {
    const ids = new Set(page.items.map((item) => item.index));
    return (
      page.blockIds.every((id) => blocks.get(id)?.source.some((span) => span.page === page.page)) &&
      page.suppressedItemIndices.every((id) => ids.has(id)) &&
      page.lines.every((line) => line.itemIndices.every((id) => ids.has(id)))
    );
  });
}

export async function readAcademicCache(
  storage: AcademicStorage,
  fingerprint: string,
  schemaVersion: number,
  parserVersion: string,
): Promise<ScholarlyDocument | null> {
  if (!hashPattern.test(fingerprint)) return null;
  try {
    const path = cachePath(fingerprint, schemaVersion, parserVersion);
    if (!(await storage.exists(path, 'Cache'))) return null;
    const raw = await storage.readFile(path, 'Cache', 'text');
    if (typeof raw !== 'string') return null;
    const envelope: unknown = JSON.parse(raw);
    const parsed = z
      .object({ checksum: z.string().regex(hashPattern), payload: z.string() })
      .safeParse(envelope);
    if (
      !parsed.success ||
      (await sha256(new TextEncoder().encode(parsed.data.payload).buffer)) !== parsed.data.checksum
    )
      return null;
    const result = schema.safeParse(JSON.parse(parsed.data.payload));
    if (!result.success) return null;
    const document = result.data;
    if (
      document.fingerprint !== fingerprint ||
      document.schemaVersion !== schemaVersion ||
      document.parserVersion !== parserVersion ||
      !validReferences(document)
    )
      return null;
    return document;
  } catch {
    return null;
  }
}

export async function writeAcademicCache(
  storage: AcademicStorage,
  document: ScholarlyDocument,
): Promise<void> {
  if (!hashPattern.test(document.fingerprint)) return;
  try {
    const payload = JSON.stringify(document);
    const checksum = await sha256(new TextEncoder().encode(payload).buffer);
    await storage.createDir(ROOT, 'Cache', true);
    await storage.writeFile(
      cachePath(document.fingerprint, document.schemaVersion, document.parserVersion),
      'Cache',
      JSON.stringify({ checksum, payload }),
    );
  } catch {
    // Cache availability must never prevent reading a locally available PDF.
  }
}
