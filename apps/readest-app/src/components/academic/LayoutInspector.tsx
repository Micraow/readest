import { useEffect, useRef, useState } from 'react';
import type { Rect, ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';

const layers = {
  raw: 'Raw text items',
  lines: 'Detected lines',
  paragraphs: 'Paragraph blocks',
  columns: 'Detected columns',
  visuals: 'Visual regions',
  order: 'Reading order and roles',
} as const;
type Layer = keyof typeof layers;
const colors: Record<Layer, string> = {
  raw: '#64748b',
  lines: '#2563eb',
  paragraphs: '#16a34a',
  columns: '#d97706',
  visuals: '#dc2626',
  order: '#9333ea',
};
const union = (boxes: Rect[]): Rect => {
  const x = Math.min(...boxes.map((box) => box.x));
  const y = Math.min(...boxes.map((box) => box.y));
  return {
    x,
    y,
    width: Math.max(...boxes.map((box) => box.x + box.width)) - x,
    height: Math.max(...boxes.map((box) => box.y + box.height)) - y,
  };
};

/** Developer-only visual inspection. No remote logging or PDF/text export. */
export default function LayoutInspector({
  document: scholarly,
  renderPage,
  onClose,
}: {
  document: ScholarlyDocument;
  renderPage?: (page: number, canvas: HTMLCanvasElement, signal: AbortSignal) => Promise<void>;
  onClose: () => void;
}) {
  const [pageNumber, setPageNumber] = useState(1);
  const [enabled, setEnabled] = useState<Record<Layer, boolean>>({
    raw: true,
    lines: true,
    paragraphs: true,
    columns: true,
    visuals: true,
    order: true,
  });
  const [selected, setSelected] = useState<ScholarlyBlock | null>(null);
  const [renderError, setRenderError] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const page = scholarly.pages.find((entry) => entry.page === pageNumber);
  const pageBlocks = scholarly.blocks.filter((block) =>
    block.source.some((span) => span.page === pageNumber),
  );

  useEffect(() => {
    if (!canvas.current || !renderPage) return;
    const abort = new AbortController();
    setRenderError(false);
    void renderPage(pageNumber, canvas.current, abort.signal).catch(() => {
      if (!abort.signal.aborted) setRenderError(true);
    });
    return () => abort.abort();
  }, [pageNumber, renderPage]);

  if (process.env.NODE_ENV === 'production' || !page) return null;
  const rect = (box: Rect, layer: Layer, key: string, testId?: string) => (
    <rect
      key={key}
      {...box}
      data-testid={testId}
      fill='none'
      stroke={colors[layer]}
      strokeWidth={layer === 'columns' ? 1.5 : 0.7}
      vectorEffect='non-scaling-stroke'
    />
  );
  return (
    <section
      className='bg-base-100 text-base-content fixed inset-0 z-[70] flex flex-col overflow-auto p-4'
      aria-label='Academic PDF Layout Inspector'
    >
      <header className='mb-3 flex flex-wrap items-center gap-3'>
        <h2 className='font-semibold'>Academic PDF Layout Inspector</h2>
        <label>
          Page{' '}
          <select
            className='select select-sm eink-bordered w-auto'
            value={pageNumber}
            onChange={(event) => {
              setPageNumber(Number(event.target.value));
              setSelected(null);
            }}
          >
            {scholarly.pages.map((entry) => (
              <option key={entry.page} value={entry.page}>
                {entry.page}
              </option>
            ))}
          </select>
        </label>
        <button type='button' className='btn btn-contrast btn-sm ml-auto' onClick={onClose}>
          Close inspector
        </button>
      </header>
      <div className='mb-3 flex flex-wrap gap-4'>
        {(Object.keys(layers) as Layer[]).map((layer) => (
          <label key={layer} className='flex items-center gap-2 text-sm'>
            <input
              type='checkbox'
              className='checkbox checkbox-sm'
              checked={enabled[layer]}
              onChange={() =>
                setEnabled((previous) => ({ ...previous, [layer]: !previous[layer] }))
              }
            />
            {layers[layer]}
          </label>
        ))}
      </div>
      {renderError && <p role='alert'>Page preview failed. Geometry is still available.</p>}
      {page.unsupportedReason && (
        <p className='mb-2 text-sm'>Preserved original: {page.unsupportedReason}</p>
      )}
      <div className='grid min-h-0 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]'>
        <div
          className='relative self-start border border-neutral-300 bg-white'
          style={{ aspectRatio: `${page.width} / ${page.height}` }}
        >
          <canvas ref={canvas} className='absolute inset-0 h-full w-full' />
          <svg
            className='absolute inset-0 h-full w-full'
            viewBox={`0 0 ${page.width} ${page.height}`}
            aria-label='Page geometry overlays'
          >
            {enabled.raw &&
              page.items.map((item) => rect(item.box, 'raw', `raw-${item.index}`, 'raw-item-box'))}
            {enabled.lines && page.lines.map((line) => rect(line.box, 'lines', line.id))}
            {enabled.columns &&
              page.columns.map((column, index) => rect(column.box, 'columns', `column-${index}`))}
            {enabled.visuals &&
              page.visualRegions.map((visual, index) =>
                rect(visual.box, 'visuals', `visual-${index}`),
              )}
            {pageBlocks.map((block) => {
              const boxes = block.source
                .filter((span) => span.page === pageNumber)
                .flatMap((span) => span.boxes);
              if (!boxes.length) return null;
              const box = union(boxes);
              return (
                <g key={block.id}>
                  {enabled.paragraphs &&
                    block.type !== 'visual-region' &&
                    rect(box, 'paragraphs', block.id)}
                  {enabled.order && (
                    <text x={box.x} y={Math.max(8, box.y - 2)} fill={colors.order} fontSize={7}>
                      {block.order + 1}: {block.type}
                      {block.role ? `/${block.role}` : ''}
                    </text>
                  )}
                  <rect
                    {...box}
                    fill='transparent'
                    tabIndex={0}
                    role='button'
                    aria-label={`Inspect block ${block.order + 1} ${block.type}`}
                    className='cursor-pointer'
                    onClick={() => setSelected(block)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setSelected(block);
                      }
                    }}
                  />
                </g>
              );
            })}
          </svg>
        </div>
        <aside className='eink-bordered border-base-300 max-h-[70vh] overflow-auto rounded-lg border p-3 text-sm'>
          {selected ? (
            <div data-testid='block-details'>
              <h3 className='mb-2 font-semibold'>
                #{selected.order + 1} {selected.type}
                {selected.role ? ` / ${selected.role}` : ''}
              </h3>
              <p className='mb-3 whitespace-pre-wrap'>{selected.text || '(visual content)'}</p>
              <pre className='whitespace-pre-wrap break-all'>
                {JSON.stringify(
                  {
                    page: pageNumber,
                    bbox: union(
                      selected.source
                        .filter((span) => span.page === pageNumber)
                        .flatMap((span) => span.boxes),
                    ),
                    confidence: selected.confidence,
                    fontStatistics: selected.fontStats,
                    source: selected.source,
                    readingOrderIndex: selected.order,
                    reason: selected.fallbackReason,
                  },
                  null,
                  2,
                )}
              </pre>
              <h4 className='mt-3 font-semibold'>Source text items</h4>
              <pre className='whitespace-pre-wrap break-all'>
                {JSON.stringify(
                  page.items.filter((item) =>
                    selected.source.some(
                      (span) => span.page === pageNumber && span.itemIndices.includes(item.index),
                    ),
                  ),
                  null,
                  2,
                )}
              </pre>
            </div>
          ) : (
            <p>Select a block to inspect its source, text, fonts, confidence and reading order.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
