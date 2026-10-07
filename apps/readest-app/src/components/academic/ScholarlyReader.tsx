import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import type { ViewSettings } from '@/types/book';
import { useTranslation } from '@/hooks/useTranslation';
import { useSettingsStore } from '@/store/settingsStore';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyBlock, ScholarlyDocument, SourceSpan } from '@/services/academic/types';
import { visualRoleLabel } from './labels';
import InlineContent from './InlineContent';

const inlineZoomBlock = (
  block: ScholarlyBlock,
  source: SourceSpan,
  trimBelow?: number,
): ScholarlyBlock => ({
  ...block,
  type: 'visual-region',
  role: 'equation',
  text: '',
  source: [source],
  captions: undefined,
  previewBox: undefined,
  inlineRuns: undefined,
  listInlineRuns: undefined,
  trimBelow,
});

function sourceVisualRows(blocks: ScholarlyBlock[]): ScholarlyBlock[][] {
  const rows: ScholarlyBlock[][] = [];
  for (const block of blocks) {
    const previous = rows.at(-1)?.at(-1);
    const box = block.previewBox,
      peer = previous?.previewBox;
    const captions = block.captions?.flatMap((caption) => caption.source.boxes) ?? [];
    const peerCaptions = previous?.captions?.flatMap((caption) => caption.source.boxes) ?? [];
    const sameRow =
      box &&
      peer &&
      captions.length &&
      peerCaptions.length &&
      block.source[0]?.page === previous?.source[0]?.page &&
      box.x >= peer.x + peer.width - 2 &&
      Math.abs(
        Math.min(...captions.map((rect) => rect.y)) -
          Math.min(...peerCaptions.map((rect) => rect.y)),
      ) <
        Math.min(block.fontStats.median, previous!.fontStats.median) * 0.6;
    if (sameRow && rows.at(-1)!.length < 3) rows.at(-1)!.push(block);
    else rows.push([block]);
  }
  return rows;
}

function VisualRegion({
  block,
  session,
  root,
  onZoom,
  fontSize,
  sourceFontSize,
}: {
  block: ScholarlyBlock;
  fontSize: number;
  sourceFontSize?: number;
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
  const box = block.previewBox ?? source?.boxes[0];
  const maximumWidth =
    (block.role === 'equation' || block.previewBox) && box
      ? (box.width * fontSize) / Math.max(1, sourceFontSize ?? block.fontStats.median)
      : undefined;
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
  }, [maximumWidth]);
  useEffect(() => {
    const target = canvas.current;
    if (!target || !source || !box || !visible || !width) return;
    const controller = new AbortController();
    setFailed(false);
    const targetWidth = Math.min(width, maximumWidth ?? width);
    void session
      .renderRegion(source.page, box, target, targetWidth, controller.signal)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      target.width = 0;
      target.height = 0;
    };
  }, [session, source, box, visible, width, maximumWidth]);
  if (!source || !box) return null;
  const label = `${_(visualRoleLabel(block.role))}: ${_('Tap to zoom')}`;
  return (
    <figure className='mx-auto my-6' style={{ maxWidth: maximumWidth }}>
      <button
        type='button'
        ref={host}
        className='eink-bordered border-base-300 relative mx-auto block w-full overflow-hidden rounded border bg-white'
        style={{ aspectRatio: `${box.width} / ${box.height}`, maxWidth: maximumWidth }}
        onClick={() => onZoom(block)}
        aria-label={label}
      >
        <canvas ref={canvas} className='block max-w-full' role='img' aria-label={label} />
        {failed && (
          <span className='absolute inset-0 flex items-center justify-center bg-white p-4 text-sm text-black'>
            {_('Could not load the image. Tap to try again.')}
          </span>
        )}
      </button>
      {block.previewBox &&
        block.captions?.map((caption) => (
          <figcaption
            key={`${caption.role}-${caption.label}`}
            className='text-base-content/75 mt-3 text-[0.88em] leading-snug'
          >
            <InlineContent
              runs={caption.inlineRuns}
              text={caption.text}
              session={session}
              fontSize={fontSize * 0.88}
              root={root}
              onZoom={(source, trimBelow) => onZoom(inlineZoomBlock(block, source, trimBelow))}
            />
          </figcaption>
        ))}
      <figcaption className='text-base-content/60 mt-1 text-center text-xs'>
        {_('Tap to zoom')}
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
  scrollRef,
}: {
  document: ScholarlyDocument;
  viewSettings?: Partial<ViewSettings>;
  scrollRef?: RefObject<HTMLDivElement | null>;
  session: AcademicPdfSession;
  onZoom: (block: ScholarlyBlock) => void;
}) {
  const localRoot = useRef<HTMLDivElement>(null);
  const root = scrollRef ?? localRoot;
  const globalSettings = useSettingsStore((state) => state.settings.globalViewSettings);
  const settings = { ...globalSettings, ...viewSettings };
  const fontSize = Math.max(16, settings.defaultFontSize || 18);
  const sourceFonts = new Map(
    scholarly.pages.map((page) => {
      const sizes = page.items
        .filter((item) => item.text.trim().length > 8)
        .map((item) => item.fontSize)
        .sort((a, b) => a - b);
      return [page.page, sizes[Math.floor(sizes.length / 2)]];
    }),
  );
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
          fontSize,
          lineHeight: Math.max(1.35, settings.lineHeight || 1.6),
          fontFamily: font ? `"${font}", serif` : 'serif',
        }}
      >
        {sourceVisualRows(scholarly.blocks).map((row) => {
          const block = row[0]!;
          const props = {
            'data-block-id': block.id,
            'data-source-page': block.source[0]?.page,
          };
          const content = (
            <InlineContent
              runs={block.inlineRuns}
              text={block.text}
              session={session}
              fontSize={fontSize}
              root={root}
              onZoom={(source, trimBelow) => onZoom(inlineZoomBlock(block, source, trimBelow))}
            />
          );
          if (block.type === 'visual-region') {
            const visuals = row.map((visual) => (
              <VisualRegion
                key={visual.id}
                block={visual}
                fontSize={fontSize}
                sourceFontSize={
                  visual.role === 'equation'
                    ? undefined
                    : sourceFonts.get(visual.source[0]?.page ?? 0)
                }
                session={session}
                root={root}
                onZoom={onZoom}
              />
            ));
            return row.length === 1 ? (
              visuals[0]
            ) : (
              <div
                key={block.id}
                className={`grid items-start gap-x-6 ${row.length === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}`}
              >
                {visuals}
              </div>
            );
          }
          if (block.type === 'heading')
            return block.level === 1 ? (
              <h1 key={block.id} {...props} className='mb-4 mt-8 text-[1.5em] font-semibold'>
                {content}
              </h1>
            ) : (
              <h2 key={block.id} {...props} className='mb-3 mt-7 text-[1.2em] font-semibold'>
                {content}
              </h2>
            );
          if (block.type === 'list') {
            const items = block.listItems ?? [block.text];
            const numbered = items.every((item) => /^\s*\d+[.)]/.test(item));
            const children = items.map((item, index) => (
              <li key={`${block.id}-${index}`}>
                <InlineContent
                  runs={block.listInlineRuns?.[index]}
                  omitListMarker
                  text={item.replace(/^\s*(?:[•●▪◦*–-]|\d+[.)])\s+/, '')}
                  session={session}
                  fontSize={fontSize}
                  root={root}
                  onZoom={(source, trimBelow) => onZoom(inlineZoomBlock(block, source, trimBelow))}
                />
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
          if (block.type === 'footnote')
            return (
              <aside
                key={block.id}
                {...props}
                role='note'
                className='mb-4 border-s-2 border-base-300 ps-3 text-[0.9em] [&>sup:first-child]:me-1'
              >
                {content}
              </aside>
            );
          return (
            <p
              key={block.id}
              {...props}
              className={block.type === 'reference' ? 'mb-3 pl-6 -indent-6 text-[0.95em]' : 'mb-4'}
            >
              {content}
            </p>
          );
        })}
      </article>
    </div>
  );
}
