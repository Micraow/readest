import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import type { ViewSettings } from '@/types/book';
import { useTranslation } from '@/hooks/useTranslation';
import { useSettingsStore } from '@/store/settingsStore';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';

function VisualRegion({
  block,
  session,
  root,
  onZoom,
}: {
  block: ScholarlyBlock;
  session: AcademicPdfSession;
  root: RefObject<HTMLDivElement | null>;
  onZoom: (block: ScholarlyBlock) => void;
}) {
  const _ = useTranslation();
  const host = useRef<HTMLButtonElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(false);
  const [width, setWidth] = useState(0);
  const [failed, setFailed] = useState(false);
  const source = block.source[0];
  const box = source?.boxes[0];
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const check = () => {
      const rect = node.getBoundingClientRect();
      setVisible(rect.bottom > -600 && rect.top < window.innerHeight + 600);
    };
    if (typeof IntersectionObserver === 'undefined') {
      check();
      root.current?.addEventListener('scroll', check, { passive: true });
      window.addEventListener('resize', check);
      const scroller = root.current;
      return () => {
        scroller?.removeEventListener('scroll', check);
        window.removeEventListener('resize', check);
      };
    }
    const observer = new IntersectionObserver(
      (entries) => setVisible(entries.some((entry) => entry.isIntersecting)),
      { root: root.current, rootMargin: '600px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [root]);
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const measure = () => setWidth(Math.max(1, Math.round(node.clientWidth)));
    measure();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const target = canvas.current;
    if (!target || !source || !box || !visible || !width) return;
    const controller = new AbortController();
    setFailed(false);
    void session.renderRegion(source.page, box, target, width, controller.signal).catch(() => {
      if (!controller.signal.aborted) setFailed(true);
    });
    return () => {
      controller.abort();
      target.width = 0;
      target.height = 0;
    };
  }, [session, source, box, visible, width]);
  if (!source || !box) return null;
  const label = `${block.role ?? 'visual'}: ${_('Tap to zoom')}`;
  return (
    <figure className='my-6'>
      <button
        type='button'
        ref={host}
        className='eink-bordered border-base-300 relative block w-full overflow-hidden rounded border bg-white'
        style={{ aspectRatio: `${box.width} / ${box.height}` }}
        onClick={() => onZoom(block)}
        aria-label={label}
      >
        <canvas ref={canvas} className='block max-w-full' role='img' aria-label={label} />
        {failed && (
          <span className='absolute inset-0 flex items-center justify-center bg-white p-4 text-sm text-black'>
            {_('Preview unavailable. Tap to retry in the viewer.')}
          </span>
        )}
      </button>
      <figcaption className='text-base-content/60 mt-1 text-center text-xs'>
        {_('Tap to zoom')}
        {block.fallbackReason ? ` · ${_('Original layout preserved')}` : ''}
      </figcaption>
    </figure>
  );
}

/** One continuous flow; PDF pages are source coordinates, never visual separators. */
export default function ScholarlyReader({
  document: scholarly,
  session,
  onZoom,
  viewSettings,
}: {
  document: ScholarlyDocument;
  viewSettings?: Partial<ViewSettings>;
  session: AcademicPdfSession;
  onZoom: (block: ScholarlyBlock) => void;
}) {
  const root = useRef<HTMLDivElement>(null);
  const globalSettings = useSettingsStore((state) => state.settings.globalViewSettings);
  const settings = { ...globalSettings, ...viewSettings };
  const storageKey = `readest:academic-position:${scholarly.fingerprint}`;
  useLayoutEffect(() => {
    const element = root.current;
    if (!element) return;
    try {
      const saved = Number(localStorage.getItem(storageKey));
      if (Number.isFinite(saved) && saved > 0) element.scrollTop = saved;
    } catch {
      /* Device-local persistence is optional. */
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    const save = () => {
      try {
        localStorage.setItem(storageKey, String(element.scrollTop));
      } catch {
        /* Full storage. */
      }
    };
    const onScroll = () => {
      if (timer) return;
      timer = setTimeout(() => {
        timer = undefined;
        save();
      }, 250);
    };
    element.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pagehide', save);
    return () => {
      if (timer) clearTimeout(timer);
      save();
      element.removeEventListener('scroll', onScroll);
      window.removeEventListener('pagehide', save);
    };
  }, [storageKey]);
  const font = settings.defaultFont === 'Sans-serif' ? settings.sansSerifFont : settings.serifFont;
  return (
    <div
      ref={root}
      className='min-h-0 flex-1 overflow-y-auto overscroll-contain'
      data-testid='scholarly-scroll'
    >
      <article
        className='mx-auto max-w-3xl select-text px-5 py-6 sm:px-10'
        style={{
          fontSize: Math.max(16, settings.defaultFontSize || 18),
          lineHeight: Math.max(1.35, settings.lineHeight || 1.6),
          fontFamily: font ? `"${font}", serif` : 'serif',
        }}
      >
        {scholarly.blocks.map((block) => {
          const props = {
            'data-block-id': block.id,
            'data-source-page': block.source[0]?.page,
          };
          if (block.type === 'visual-region')
            return (
              <VisualRegion
                key={block.id}
                block={block}
                session={session}
                root={root}
                onZoom={onZoom}
              />
            );
          if (block.type === 'heading')
            return block.level === 1 ? (
              <h1 key={block.id} {...props} className='mb-4 mt-8 text-[1.5em] font-semibold'>
                {block.text}
              </h1>
            ) : (
              <h2 key={block.id} {...props} className='mb-3 mt-7 text-[1.2em] font-semibold'>
                {block.text}
              </h2>
            );
          if (block.type === 'list') {
            const items = block.listItems ?? [block.text];
            const numbered = items.every((item) => /^\s*\d+[.)]/.test(item));
            const children = items.map((item, index) => (
              <li key={`${block.id}-${index}`}>
                {item.replace(/^\s*(?:[•●▪◦*–-]|\d+[.)])\s+/, '')}
              </li>
            ));
            return numbered ? (
              <ol
                key={block.id}
                {...props}
                start={Number(/^\s*(\d+)/.exec(items[0] ?? '')?.[1] ?? 1)}
                className='mb-4 list-decimal space-y-1 pl-6'
              >
                {children}
              </ol>
            ) : (
              <ul key={block.id} {...props} className='mb-4 list-disc space-y-1 pl-6'>
                {children}
              </ul>
            );
          }
          return (
            <p
              key={block.id}
              {...props}
              className={
                block.type === 'footnote'
                  ? 'mb-4 text-[0.9em]'
                  : block.type === 'reference'
                    ? 'mb-3 pl-6 -indent-6 text-[0.95em]'
                    : 'mb-4'
              }
            >
              {block.text}
            </p>
          );
        })}
      </article>
    </div>
  );
}
