import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { SourceSpan } from '@/services/academic/types';

/** Full-page fallback using the dialog's PDF session, independent of layout analysis. */
export default function AcademicSourceView({
  session,
  page,
  onPageChange,
  source,
  geometry,
}: {
  session: AcademicPdfSession;
  page: number;
  onPageChange: (page: number) => void;
  source?: SourceSpan;
  geometry?: { width: number; height: number };
}) {
  const _ = useTranslation();
  const viewport = useRef<HTMLDivElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const [fitWidth, setFitWidth] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const [paintedPage, setPaintedPage] = useState<number | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  const pageLabel = _('Original PDF page');

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const measure = () => setFitWidth(Math.max(1, element.clientWidth));
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(element);
    window.addEventListener('resize', measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, []);

  useEffect(() => {
    const container = host.current;
    if (!container || !fitWidth) return;
    const controller = new AbortController();
    const canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', `${pageLabel} ${page}`);
    canvas.style.display = 'block';
    setStatus('loading');
    void (async () => {
      try {
        await session.renderPage(page, canvas, controller.signal, fitWidth * zoom);
        if (controller.signal.aborted) return;
        // Commit only a complete current render. Failed or stale navigation leaves
        // the previous page readable and labelled with its actual page number.
        const previous = container.querySelector('canvas');
        container.replaceChildren(canvas);
        if (previous) previous.width = previous.height = 0;
        setPaintedPage(page);
        setStatus('ready');
        if (viewport.current) viewport.current.scrollTop = viewport.current.scrollLeft = 0;
      } catch {
        if (!controller.signal.aborted) setStatus('failed');
      } finally {
        if (canvas.parentNode !== container) canvas.width = canvas.height = 0;
      }
    })();
    return () => {
      controller.abort();
    };
  }, [session, page, fitWidth, zoom, attempt, pageLabel]);

  useEffect(() => {
    const container = host.current;
    return () => {
      for (const canvas of container?.querySelectorAll('canvas') ?? []) {
        canvas.width = canvas.height = 0;
      }
      container?.replaceChildren();
    };
  }, []);

  const navigate = (value: number) => {
    if (Number.isInteger(value) && value >= 1 && value <= session.pageCount) onPageChange(value);
  };
  const highlight =
    paintedPage === source?.page && geometry && geometry.width > 0 && geometry.height > 0;
  return (
    <section aria-label={_('Original PDF pages')} className='flex h-full min-h-0 min-w-0 flex-col'>
      <div className='border-base-300 flex shrink-0 flex-wrap items-center gap-2 border-b p-2'>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          aria-label={_('Previous page')}
          disabled={page <= 1}
          onClick={() => navigate(page - 1)}
        >
          ←
        </button>
        <label className='flex min-w-0 items-center gap-1 text-sm'>
          {_('PDF page')}
          <input
            aria-label={_('PDF page')}
            className='input input-sm eink-bordered w-16'
            type='number'
            min={1}
            max={session.pageCount}
            value={page}
            onChange={(event) => navigate(event.currentTarget.valueAsNumber)}
          />
          <span>/ {session.pageCount}</span>
        </label>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          aria-label={_('Next page')}
          disabled={page >= session.pageCount}
          onClick={() => navigate(page + 1)}
        >
          →
        </button>
        <select
          aria-label={_('PDF zoom')}
          className='select select-sm eink-bordered w-auto'
          value={zoom}
          onChange={(event) => setZoom(Number(event.currentTarget.value))}
        >
          <option value={1}>{_('Fit width')}</option>
          <option value={1.5}>150%</option>
          <option value={2}>200%</option>
          <option value={3}>300%</option>
        </select>
      </div>
      <p className='shrink-0 px-3 py-1 text-xs'>
        {_('Original page image. Reflow is not applied in this view.')}
      </p>
      {source && (
        <p className='shrink-0 px-3 py-1 text-xs'>
          {_('Highlighted area marks the start of the reading block.')}
        </p>
      )}
      <div role='status' aria-live='polite' className='shrink-0 px-3 text-sm'>
        {status === 'loading'
          ? _('Loading PDF page…')
          : paintedPage !== null
            ? `${pageLabel} ${paintedPage}`
            : ''}
      </div>
      {status === 'failed' && (
        <div className='flex shrink-0 flex-wrap items-center gap-2 px-3 py-1'>
          <p role='alert'>
            {_('Could not load this PDF page. The previous page is kept when available.')}
          </p>
          <button
            type='button'
            className='btn btn-ghost btn-sm eink-bordered'
            onClick={() => setAttempt((value) => value + 1)}
          >
            {_('Retry')}
          </button>
        </div>
      )}
      <div
        ref={viewport}
        data-testid='academic-source-scroll'
        className='min-h-0 min-w-0 flex-1 overflow-auto'
      >
        <div className='relative w-fit'>
          <div ref={host} />
          {highlight && (
            <svg
              aria-hidden='true'
              className='pointer-events-none absolute inset-0 h-full w-full'
              viewBox={`0 0 ${geometry.width} ${geometry.height}`}
            >
              {source.boxes.map((box, index) => (
                <rect
                  key={index}
                  data-source-highlight=''
                  x={box.x}
                  y={box.y}
                  width={box.width}
                  height={box.height}
                  fill='none'
                  stroke='currentColor'
                  strokeWidth={2}
                />
              ))}
            </svg>
          )}
        </div>
      </div>
    </section>
  );
}
