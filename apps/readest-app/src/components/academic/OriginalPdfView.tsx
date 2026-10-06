import { useEffect, useRef, useState } from 'react';
import { DocumentLoader, type BookDoc } from '@/libs/document';
import type { ClosableFile } from '@/utils/file';
import type { FoliateView } from '@/types/view';
import { useTranslation } from '@/hooks/useTranslation';
import { useEnv } from '@/context/EnvContext';
import { useSettingsStore } from '@/store/settingsStore';
import { useThemeStore } from '@/store/themeStore';
import { getPDFPageColors } from '@/utils/style';

/** Original Readest/Foliate PDF rendering without normal Book/sync side effects. */
export default function OriginalPdfView({ file, resumeKey }: { file: File; resumeKey: string }) {
  const _ = useTranslation();
  const { appService } = useEnv();
  const settings = useSettingsStore((state) => state.settings.globalViewSettings);
  const themeCode = useThemeStore((state) => state.themeCode);
  const container = useRef<HTMLDivElement>(null);
  const viewRef = useRef<FoliateView | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [scrolled, setScrolled] = useState(settings.scrolled ?? false);
  const [zoom, setZoom] = useState(settings.zoomLevel ?? 100);
  const [zoomMode, setZoomMode] = useState(settings.zoomMode ?? 'fit-page');
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    let cancelled = false;
    let book: BookDoc | undefined;
    let view: FoliateView | undefined;
    let cleaned = false;
    let opening = true;
    setReady(false);
    setError(false);
    const storageKey = `readest:external-pdf-position:${resumeKey}`;
    const relocate = (event: Event) => {
      const detail = (event as CustomEvent<{ cfi?: string; section?: { current: number } }>).detail;
      if (detail.section) setPage(detail.section.current + 1);
      if (detail.cfi) {
        // Device-local position only, never a Book/config replica or provider write.
        try {
          localStorage.setItem(storageKey, detail.cfi);
        } catch {
          /* Storage may be full. */
        }
      }
    };
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      view?.removeEventListener('relocate', relocate);
      view?.close();
      view?.remove();
      if (viewRef.current === view) viewRef.current = null;
      void Promise.resolve(book?.destroy?.())
        .catch(() => undefined)
        .finally(() => {
          const closable = file as Partial<ClosableFile>;
          void closable.close?.().catch(() => undefined);
        });
    };
    const open = async () => {
      try {
        await import('foliate-js/view.js');
        book = (await new DocumentLoader(file).open()).book;
        if (cancelled) {
          cleanup();
          return;
        }
        const element = document.createElement('foliate-view') as FoliateView;
        view = element;
        element.style.cssText = 'display:block;width:100%;height:100%;';
        container.current?.append(element);
        await element.open(book);
        if (cancelled) {
          cleanup();
          return;
        }
        viewRef.current = element;
        element.renderer.setAttribute('zoom', settingsRef.current.zoomMode ?? 'fit-page');
        element.renderer.setAttribute('scale-factor', settingsRef.current.zoomLevel ?? 100);
        element.renderer.setAttribute('spread', settingsRef.current.spreadMode ?? 'none');
        element.renderer.setAttribute(
          'flow',
          settingsRef.current.scrolled ? 'scrolled' : 'paginated',
        );
        element.addEventListener('relocate', relocate);
        setPages(book.sections.length);
        let lastLocation = '';
        try {
          lastLocation = localStorage.getItem(storageKey) ?? '';
        } catch {
          /* Private browsing. */
        }
        try {
          await element.init({ lastLocation });
        } catch {
          await element.init({ lastLocation: '' });
        }
        if (!cancelled) setReady(true);
      } catch {
        cleanup();
        if (!cancelled) setError(true);
      } finally {
        opening = false;
        if (cancelled) cleanup();
      }
    };
    void open();
    return () => {
      cancelled = true;
      // If DocumentLoader is still resolving, its completion owns final cleanup.
      if (!opening) cleanup();
    };
  }, [file, resumeKey]);

  useEffect(() => {
    const renderer = viewRef.current?.renderer;
    if (!renderer) return;
    renderer.setAttribute('flow', scrolled ? 'scrolled' : 'paginated');
    renderer.setAttribute('zoom', zoomMode);
    renderer.setAttribute('scale-factor', zoom);
    renderer.pageColors =
      appService?.supportsCanvasContext2DFilter === false
        ? undefined
        : getPDFPageColors(settings, themeCode);
  }, [ready, scrolled, zoomMode, zoom, settings, themeCode, appService]);

  return (
    <div className='flex h-full min-h-0 flex-col'>
      <div className='border-base-300 flex flex-wrap items-center justify-center gap-2 border-b p-2'>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          disabled={!ready || page <= 1}
          onClick={() => void viewRef.current?.prev()}
          aria-label={_('Previous page')}
        >
          ‹
        </button>
        <label className='flex items-center gap-2 text-sm'>
          {_('Page')}
          <input
            className='input input-sm eink-bordered w-16'
            type='number'
            min={1}
            max={pages}
            value={page}
            disabled={!ready}
            aria-label={_('Page')}
            onChange={(event) => {
              const next = Math.min(pages, Math.max(1, Number(event.target.value)));
              if (Number.isFinite(next)) {
                setPage(next);
                viewRef.current?.goTo(next - 1);
              }
            }}
          />
          / {pages}
        </label>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          disabled={!ready || page >= pages}
          onClick={() => void viewRef.current?.next()}
          aria-label={_('Next page')}
        >
          ›
        </button>
        <select
          className='select select-sm eink-bordered w-auto'
          aria-label={_('PDF zoom')}
          value={zoomMode}
          onChange={(event) => setZoomMode(event.target.value as typeof zoomMode)}
        >
          <option value='fit-page'>{_('Fit Page')}</option>
          <option value='fit-width'>{_('Fit Width')}</option>
        </select>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          aria-label={_('Zoom out')}
          onClick={() => setZoom((value) => Math.max(50, value - 25))}
        >
          −
        </button>
        <span className='text-sm'>{zoom}%</span>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          aria-label={_('Zoom in')}
          onClick={() => setZoom((value) => Math.min(400, value + 25))}
        >
          +
        </button>
        <button
          type='button'
          className='btn btn-ghost btn-sm eink-bordered'
          aria-pressed={scrolled}
          onClick={() => setScrolled((value) => !value)}
        >
          {_('Scroll')}
        </button>
      </div>
      {error && (
        <p role='alert' className='p-4'>
          {_('Unable to open PDF')}
        </p>
      )}
      {!ready && !error && (
        <p role='status' className='p-4'>
          {_('Opening PDF…')}
        </p>
      )}
      <div ref={container} className='min-h-0 flex-1' />
    </div>
  );
}
