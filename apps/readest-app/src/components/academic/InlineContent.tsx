import { Fragment, useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { AcademicLink } from '@/services/academic/navigation';
import { navigationElementId } from '@/services/academic/navigation';
import type { InlineRun, SourceSpan } from '@/services/academic/types';
import { useMathCanvasStyle } from './useMathCanvasStyle';

type InlineProps = {
  session: AcademicPdfSession;
  fontSize: number;
  root: RefObject<HTMLDivElement | null>;
  onZoom: (source: SourceSpan, trimBelow?: number) => void;
};

function InlineSource({
  run,
  session,
  fontSize,
  root,
  onZoom,
}: InlineProps & { run: Extract<InlineRun, { kind: 'source' }> }) {
  const _ = useTranslation();
  const mathCanvasStyle = useMathCanvasStyle();
  const host = useRef<HTMLButtonElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(false);
  const [width, setWidth] = useState(0);
  const [failed, setFailed] = useState(false);
  const box = run.source.boxes[0];
  useEffect(() => {
    const node = host.current;
    if (!node) return;
    const check = () => {
      const rect = node.getBoundingClientRect();
      setVisible(rect.bottom > -600 && rect.top < window.innerHeight + 600);
    };
    if (typeof IntersectionObserver === 'undefined') {
      check();
      const scroller = root.current;
      scroller?.addEventListener('scroll', check, { passive: true });
      window.addEventListener('resize', check);
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
    const measure = () => setWidth(Math.max(1, node.clientWidth));
    measure();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [fontSize, box]);
  useEffect(() => {
    const target = canvas.current;
    if (!target || !box || !visible || !width) return;
    const controller = new AbortController();
    setFailed(false);
    void session
      .renderRegion(run.source.page, box, target, width, controller.signal, run.trimBelow)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      target.width = 0;
      target.height = 0;
    };
  }, [session, run.source.page, run.trimBelow, box, visible, width]);
  if (!box) return run.text;
  const label = `${_('Equation')}: ${run.text}. ${_('Tap to zoom')}`;
  return (
    <button
      ref={host}
      type='button'
      className='bg-base-100 text-base-content relative inline-block max-w-full overflow-hidden rounded-sm p-0 focus-visible:outline focus-visible:outline-1'
      style={{
        width: `${box.width / run.fontSize}em`,
        aspectRatio: `${box.width} / ${box.height}`,
        verticalAlign: `${-(box.y + box.height - run.baseline) / run.fontSize}em`,
        lineHeight: 0,
      }}
      aria-label={label}
      title={_('Tap to zoom')}
      onClick={() => onZoom(run.source, run.trimBelow)}
    >
      <canvas
        ref={canvas}
        className='block max-w-full'
        style={mathCanvasStyle}
        aria-hidden='true'
      />
      {failed && (
        <span className='bg-base-100 absolute inset-0 overflow-auto text-[0.75em] leading-tight'>
          {run.text}
        </span>
      )}
    </button>
  );
}

export interface InlineReferences {
  links: AcademicLink[];
  prefix: string;
  onNavigate: (link: AcademicLink, anchor: HTMLAnchorElement) => void;
}

export default function InlineContent({
  runs,
  text,
  omitListMarker,
  references,
  ...props
}: InlineProps & {
  runs?: InlineRun[];
  text: string;
  omitListMarker?: boolean;
  references?: InlineReferences;
}) {
  const _ = useTranslation();
  const content = runs?.length ? runs.map((run) => run.text).join('') : text;
  const remove = omitListMarker
    ? (/^\s*(?:[•●▪◦*–-]|\d+[.)])\s+/.exec(content)?.[0].length ?? 0)
    : 0;
  const renderRuns = (start: number, end: number): ReactNode => {
    if (!runs?.length) return content.slice(start, end);
    let offset = 0;
    return runs.map((run, index) => {
      const runStart = offset;
      offset += run.text.length;
      if (offset <= start || runStart >= end) return null;
      if (run.kind === 'source') return <InlineSource key={index} run={run} {...props} />;
      const value = run.text.slice(Math.max(0, start - runStart), end - runStart);
      const style = {
        fontFamily: run.style?.fontFamily,
        fontStyle: run.style?.fontStyle,
        fontWeight: run.style?.fontWeight,
      };
      if (run.style?.verticalAlign === 'sub')
        return (
          <sub key={index} style={style}>
            {value}
          </sub>
        );
      if (run.style?.verticalAlign === 'super')
        return (
          <sup key={index} style={style}>
            {value}
          </sup>
        );
      return (
        <span key={index} style={style}>
          {value}
        </span>
      );
    });
  };
  const renderRange = (start: number, end: number): ReactNode => {
    if (!runs?.length) return content.slice(start, end);
    const words: { start: number; end: number }[] = [];
    let wordStart = start;
    let hasSource = false;
    let hasText = false;
    const finishWord = (wordEnd: number, nextStart: number) => {
      if (hasSource && hasText) words.push({ start: wordStart, end: wordEnd });
      wordStart = nextStart;
      hasSource = false;
      hasText = false;
    };
    let offset = 0;
    for (const run of runs) {
      const runStart = offset;
      offset += run.text.length;
      if (offset <= start || runStart >= end) continue;
      if (run.kind === 'source') {
        // A crop is atomic even when its alternative text contains spaces.
        hasSource = true;
        continue;
      }
      const from = Math.max(start, runStart);
      const value = run.text.slice(from - runStart, end - runStart);
      let consumed = 0;
      for (const space of value.matchAll(/\s+/g)) {
        if (space.index > consumed) hasText = true;
        finishWord(from + space.index, from + space.index + space[0].length);
        consumed = space.index + space[0].length;
      }
      if (consumed < value.length) hasText = true;
    }
    finishWord(end, end);
    if (!words.length) return renderRuns(start, end);
    const children: ReactNode[] = [];
    let cursor = start;
    for (const word of words) {
      if (cursor < word.start)
        children.push(<Fragment key={`text-${cursor}`}>{renderRuns(cursor, word.start)}</Fragment>);
      // Keep an unspaced glyph/operand together when it fits. Normal wrapping
      // remains available inside an oversized word; do not clip or force nowrap.
      children.push(
        <span key={`word-${word.start}`} className='inline-block max-w-full'>
          {renderRuns(word.start, word.end)}
        </span>,
      );
      cursor = word.end;
    }
    if (cursor < end)
      children.push(<Fragment key={`text-${cursor}`}>{renderRuns(cursor, end)}</Fragment>);
    return children;
  };
  if (!references?.links.length) return renderRange(remove, content.length);
  const children: ReactNode[] = [];
  let offset = remove;
  for (const link of references.links) {
    if (link.start < offset || link.end > content.length) continue;
    // Keep source zoom buttons outside links even if a stale caller supplies an invalid range.
    let runOffset = 0;
    const overlapsSource = runs?.some((run) => {
      const start = runOffset;
      runOffset += run.text.length;
      return run.kind === 'source' && runOffset > link.start && start < link.end;
    });
    if (overlapsSource) continue;
    children.push(<span key={`before-${link.id}`}>{renderRange(offset, link.start)}</span>);
    children.push(
      <a
        key={link.id}
        id={navigationElementId(references.prefix, link.id)}
        href={`#${encodeURIComponent(navigationElementId(references.prefix, link.target))}`}
        className='rounded-sm underline decoration-1 underline-offset-2 focus-visible:outline focus-visible:outline-2'
        aria-label={
          link.kind === 'reference'
            ? _('Reference {{number}}', { number: link.number })
            : _('Footnote {{number}}', { number: link.number })
        }
        onClick={(event) => {
          event.preventDefault();
          references.onNavigate(link, event.currentTarget);
        }}
      >
        {renderRange(link.start, link.end)}
      </a>,
    );
    offset = link.end;
  }
  children.push(<span key='after'>{renderRange(offset, content.length)}</span>);
  return children;
}
